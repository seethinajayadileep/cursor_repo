import pg from "pg";
import { config, hasPostgres } from "../../config/index.js";
import type {
  BookmarkedJob,
  RankedJob,
  SavedSearch,
  SearchCriteria,
  SearchResult,
} from "../../types/index.js";
import { createId } from "../../utils/helpers.js";
import { FileStore } from "../cache/cacheService.js";

const { Pool } = pg;

export class DatabaseService {
  private pool: pg.Pool | null = null;
  private searches = new FileStore("searches.json");
  private bookmarks = new FileStore("bookmarks.json");
  private savedSearches = new FileStore("saved-searches.json");
  private resumes = new FileStore("resumes.json");
  private memorySearches: SearchResult[] = [];
  private memoryBookmarks: BookmarkedJob[] = [];
  private memorySaved: SavedSearch[] = [];
  private memoryResumes: Record<string, { text: string; skills: string[]; updatedAt: string }> =
    {};

  async init(): Promise<void> {
    if (!hasPostgres) {
      await this.loadFiles();
      console.log("[db] Using file-backed persistence");
      return;
    }

    try {
      this.pool = new Pool({ connectionString: config.databaseUrl });
      await this.pool.query("SELECT 1");
      await this.migrate();
      console.log("[db] Connected to PostgreSQL");
    } catch (error) {
      console.warn("[db] PostgreSQL unavailable, using file store:", error);
      if (this.pool) {
        try {
          await this.pool.end();
        } catch {
          /* ignore */
        }
      }
      this.pool = null;
      await this.loadFiles();
    }
  }

  mode(): "postgres" | "file" {
    return this.pool ? "postgres" : "file";
  }

  private async loadFiles(): Promise<void> {
    this.memorySearches = await this.searches.read<SearchResult[]>([]);
    this.memoryBookmarks = await this.bookmarks.read<BookmarkedJob[]>([]);
    this.memorySaved = await this.savedSearches.read<SavedSearch[]>([]);
    this.memoryResumes = await this.resumes.read({});
  }

  private async migrate(): Promise<void> {
    if (!this.pool) return;
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS searches (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        criteria JSONB NOT NULL,
        jobs JSONB NOT NULL,
        total INTEGER NOT NULL,
        cached BOOLEAN NOT NULL DEFAULT FALSE,
        mode TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE TABLE IF NOT EXISTS bookmarks (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        job JSONB NOT NULL,
        saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE TABLE IF NOT EXISTS saved_searches (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        criteria JSONB NOT NULL,
        alert_email TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE TABLE IF NOT EXISTS resumes (
        user_id TEXT PRIMARY KEY,
        text TEXT NOT NULL,
        skills JSONB NOT NULL DEFAULT '[]',
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE INDEX IF NOT EXISTS idx_searches_created ON searches(created_at DESC);
      CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id);
    `);
  }

  async saveSearchResult(result: SearchResult, userId = "anonymous"): Promise<void> {
    if (this.pool) {
      await this.pool.query(
        `INSERT INTO searches (id, user_id, criteria, jobs, total, cached, mode, created_at)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
         ON CONFLICT (id) DO UPDATE SET jobs = EXCLUDED.jobs, total = EXCLUDED.total`,
        [
          result.searchId,
          userId,
          JSON.stringify(result.criteria),
          JSON.stringify(result.jobs),
          result.total,
          result.cached,
          result.mode,
          result.createdAt,
        ]
      );
      return;
    }

    this.memorySearches = [
      result,
      ...this.memorySearches.filter((s) => s.searchId !== result.searchId),
    ].slice(0, 100);
    await this.searches.write(this.memorySearches);
  }

  async getSearch(searchId: string): Promise<SearchResult | null> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT id, criteria, jobs, total, cached, mode, created_at FROM searches WHERE id = $1`,
        [searchId]
      );
      if (!rows[0]) return null;
      const row = rows[0];
      return {
        searchId: row.id,
        criteria: row.criteria,
        jobs: row.jobs,
        total: row.total,
        cached: row.cached,
        mode: row.mode,
        createdAt: new Date(row.created_at).toISOString(),
      };
    }
    return this.memorySearches.find((s) => s.searchId === searchId) ?? null;
  }

  async listSearches(limit = 20): Promise<SearchResult[]> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT id, criteria, jobs, total, cached, mode, created_at
         FROM searches ORDER BY created_at DESC LIMIT $1`,
        [limit]
      );
      return rows.map((row) => ({
        searchId: row.id,
        criteria: row.criteria,
        jobs: row.jobs,
        total: row.total,
        cached: row.cached,
        mode: row.mode,
        createdAt: new Date(row.created_at).toISOString(),
      }));
    }
    return this.memorySearches.slice(0, limit);
  }

  async addBookmark(userId: string, job: RankedJob): Promise<BookmarkedJob> {
    const bookmark: BookmarkedJob = {
      id: createId("bm"),
      userId,
      job,
      savedAt: new Date().toISOString(),
    };

    if (this.pool) {
      await this.pool.query(
        `INSERT INTO bookmarks (id, user_id, job, saved_at) VALUES ($1,$2,$3,$4)`,
        [bookmark.id, userId, JSON.stringify(job), bookmark.savedAt]
      );
      return bookmark;
    }

    this.memoryBookmarks = [
      bookmark,
      ...this.memoryBookmarks.filter(
        (b) => !(b.userId === userId && b.job.id === job.id)
      ),
    ];
    await this.bookmarks.write(this.memoryBookmarks);
    return bookmark;
  }

  async removeBookmark(userId: string, bookmarkId: string): Promise<boolean> {
    if (this.pool) {
      const res = await this.pool.query(
        `DELETE FROM bookmarks WHERE id = $1 AND user_id = $2`,
        [bookmarkId, userId]
      );
      return (res.rowCount ?? 0) > 0;
    }
    const before = this.memoryBookmarks.length;
    this.memoryBookmarks = this.memoryBookmarks.filter(
      (b) => !(b.id === bookmarkId && b.userId === userId)
    );
    await this.bookmarks.write(this.memoryBookmarks);
    return this.memoryBookmarks.length < before;
  }

  async listBookmarks(userId: string): Promise<BookmarkedJob[]> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT id, user_id, job, saved_at FROM bookmarks WHERE user_id = $1 ORDER BY saved_at DESC`,
        [userId]
      );
      return rows.map((row) => ({
        id: row.id,
        userId: row.user_id,
        job: row.job,
        savedAt: new Date(row.saved_at).toISOString(),
      }));
    }
    return this.memoryBookmarks.filter((b) => b.userId === userId);
  }

  async saveSearchAlert(
    userId: string,
    criteria: SearchCriteria,
    alertEmail?: string
  ): Promise<SavedSearch> {
    const saved: SavedSearch = {
      id: createId("ss"),
      userId,
      criteria,
      createdAt: new Date().toISOString(),
      alertEmail: alertEmail ?? null,
    };

    if (this.pool) {
      await this.pool.query(
        `INSERT INTO saved_searches (id, user_id, criteria, alert_email, created_at)
         VALUES ($1,$2,$3,$4,$5)`,
        [saved.id, userId, JSON.stringify(criteria), alertEmail ?? null, saved.createdAt]
      );
      return saved;
    }

    this.memorySaved.unshift(saved);
    await this.savedSearches.write(this.memorySaved);
    return saved;
  }

  async listSavedSearches(userId: string): Promise<SavedSearch[]> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT id, user_id, criteria, alert_email, created_at FROM saved_searches
         WHERE user_id = $1 ORDER BY created_at DESC`,
        [userId]
      );
      return rows.map((row) => ({
        id: row.id,
        userId: row.user_id,
        criteria: row.criteria,
        alertEmail: row.alert_email,
        createdAt: new Date(row.created_at).toISOString(),
      }));
    }
    return this.memorySaved.filter((s) => s.userId === userId);
  }

  async saveResume(
    userId: string,
    text: string,
    skills: string[]
  ): Promise<void> {
    const updatedAt = new Date().toISOString();
    if (this.pool) {
      await this.pool.query(
        `INSERT INTO resumes (user_id, text, skills, updated_at)
         VALUES ($1,$2,$3,$4)
         ON CONFLICT (user_id) DO UPDATE SET text = EXCLUDED.text, skills = EXCLUDED.skills, updated_at = EXCLUDED.updated_at`,
        [userId, text, JSON.stringify(skills), updatedAt]
      );
      return;
    }
    this.memoryResumes[userId] = { text, skills, updatedAt };
    await this.resumes.write(this.memoryResumes);
  }

  async getResume(
    userId: string
  ): Promise<{ text: string; skills: string[]; updatedAt: string } | null> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT text, skills, updated_at FROM resumes WHERE user_id = $1`,
        [userId]
      );
      if (!rows[0]) return null;
      return {
        text: rows[0].text,
        skills: rows[0].skills,
        updatedAt: new Date(rows[0].updated_at).toISOString(),
      };
    }
    return this.memoryResumes[userId] ?? null;
  }
}

export const databaseService = new DatabaseService();
