import pg from "pg";
import { config, hasPostgres } from "../../config/index.js";
import type {
  BookmarkedJob,
  RankedJob,
  SavedSearch,
  SearchCriteria,
  SearchResult,
} from "../../types/index.js";
import type {
  AlertRun,
  PortalPrefs,
  PortalUser,
  TelegramLink,
} from "../../types/portal.js";
import { createId } from "../../utils/helpers.js";
import { FileStore } from "../cache/cacheService.js";

const { Pool } = pg;

function defaultPrefs(userId: string): PortalPrefs {
  return {
    userId,
    role: "Software Engineer",
    roles: ["Software Engineer"],
    location: "Hyderabad",
    experienceLevel: "any",
    employmentType: "any",
    workMode: "any",
    companySize: "any",
    skillsMode: "auto",
    manualSkills: [],
    alertsEnabled: true,
    topN: 5,
    updatedAt: new Date().toISOString(),
  };
}

export class DatabaseService {
  private pool: pg.Pool | null = null;
  private searches = new FileStore("searches.json");
  private bookmarks = new FileStore("bookmarks.json");
  private savedSearches = new FileStore("saved-searches.json");
  private resumes = new FileStore("resumes.json");
  private users = new FileStore("portal-users.json");
  private prefsStore = new FileStore("portal-prefs.json");
  private telegramStore = new FileStore("portal-telegram.json");
  private alertRunsStore = new FileStore("portal-alert-runs.json");
  private sentJobsStore = new FileStore("portal-sent-jobs.json");
  private memorySearches: SearchResult[] = [];
  private memoryBookmarks: BookmarkedJob[] = [];
  private memorySaved: SavedSearch[] = [];
  private memoryResumes: Record<string, { text: string; skills: string[]; updatedAt: string }> =
    {};
  private memoryUsers: PortalUser[] = [];
  private memoryPrefs: Record<string, PortalPrefs> = {};
  private memoryTelegram: Record<string, TelegramLink> = {};
  private memoryAlertRuns: AlertRun[] = [];
  private memorySentJobs: Record<string, string[]> = {};

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
    this.memoryUsers = await this.users.read<PortalUser[]>([]);
    this.memoryPrefs = await this.prefsStore.read({});
    this.memoryTelegram = await this.telegramStore.read({});
    this.memoryAlertRuns = await this.alertRunsStore.read<AlertRun[]>([]);
    this.memorySentJobs = await this.sentJobsStore.read({});
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
      CREATE TABLE IF NOT EXISTS portal_users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE TABLE IF NOT EXISTS portal_prefs (
        user_id TEXT PRIMARY KEY REFERENCES portal_users(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        location TEXT NOT NULL,
        experience_level TEXT NOT NULL DEFAULT 'any',
        employment_type TEXT NOT NULL DEFAULT 'any',
        work_mode TEXT NOT NULL DEFAULT 'any',
        company_size TEXT NOT NULL DEFAULT 'any',
        salary_min INTEGER,
        salary_max INTEGER,
        alerts_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        top_n INTEGER NOT NULL DEFAULT 5,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE TABLE IF NOT EXISTS portal_telegram (
        user_id TEXT PRIMARY KEY REFERENCES portal_users(id) ON DELETE CASCADE,
        chat_id TEXT,
        username TEXT,
        link_token TEXT,
        linked_at TIMESTAMPTZ
      );
      CREATE TABLE IF NOT EXISTS portal_alert_runs (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        ran_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        status TEXT NOT NULL,
        jobs_sent INTEGER NOT NULL DEFAULT 0,
        message TEXT,
        preview JSONB
      );
      CREATE TABLE IF NOT EXISTS portal_sent_jobs (
        user_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        title TEXT,
        company TEXT,
        sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (user_id, job_id)
      );
      ALTER TABLE portal_prefs ADD COLUMN IF NOT EXISTS roles JSONB DEFAULT '[]'::jsonb;
      ALTER TABLE portal_prefs ADD COLUMN IF NOT EXISTS skills_mode TEXT DEFAULT 'auto';
      ALTER TABLE portal_prefs ADD COLUMN IF NOT EXISTS manual_skills JSONB DEFAULT '[]'::jsonb;
      CREATE INDEX IF NOT EXISTS idx_searches_created ON searches(created_at DESC);
      CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id);
      CREATE INDEX IF NOT EXISTS idx_portal_users_email ON portal_users(email);
      CREATE INDEX IF NOT EXISTS idx_portal_alert_runs_user ON portal_alert_runs(user_id, ran_at DESC);
      CREATE INDEX IF NOT EXISTS idx_portal_sent_jobs_user ON portal_sent_jobs(user_id, sent_at DESC);
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

  async createUser(user: PortalUser): Promise<void> {
    if (this.pool) {
      await this.pool.query(
        `INSERT INTO portal_users (id, email, name, password_hash, created_at)
         VALUES ($1,$2,$3,$4,$5)`,
        [user.id, user.email, user.name, user.passwordHash, user.createdAt]
      );
      return;
    }
    this.memoryUsers.push(user);
    await this.users.write(this.memoryUsers);
  }

  async findUserByEmail(email: string): Promise<PortalUser | null> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT id, email, name, password_hash, created_at FROM portal_users WHERE email = $1`,
        [email.toLowerCase()]
      );
      if (!rows[0]) return null;
      return {
        id: rows[0].id,
        email: rows[0].email,
        name: rows[0].name,
        passwordHash: rows[0].password_hash,
        createdAt: new Date(rows[0].created_at).toISOString(),
      };
    }
    return this.memoryUsers.find((u) => u.email === email.toLowerCase()) ?? null;
  }

  async findUserById(id: string): Promise<PortalUser | null> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT id, email, name, password_hash, created_at FROM portal_users WHERE id = $1`,
        [id]
      );
      if (!rows[0]) return null;
      return {
        id: rows[0].id,
        email: rows[0].email,
        name: rows[0].name,
        passwordHash: rows[0].password_hash,
        createdAt: new Date(rows[0].created_at).toISOString(),
      };
    }
    return this.memoryUsers.find((u) => u.id === id) ?? null;
  }

  async ensureDefaultPrefs(userId: string): Promise<PortalPrefs> {
    const existing = await this.getPrefs(userId);
    if (existing) return existing;
    const prefs = defaultPrefs(userId);
    await this.savePrefs(prefs);
    return prefs;
  }

  async getPrefs(userId: string): Promise<PortalPrefs | null> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT * FROM portal_prefs WHERE user_id = $1`,
        [userId]
      );
      if (!rows[0]) return null;
      const row = rows[0];
      const roles: string[] = Array.isArray(row.roles)
        ? row.roles.map(String).filter(Boolean)
        : row.role
          ? [String(row.role)]
          : ["Software Engineer"];
      return {
        userId: row.user_id,
        role: roles[0] || row.role || "Software Engineer",
        roles,
        location: row.location,
        experienceLevel: row.experience_level,
        employmentType: row.employment_type,
        workMode: row.work_mode,
        companySize: row.company_size,
        salaryMin: row.salary_min ?? undefined,
        salaryMax: row.salary_max ?? undefined,
        skillsMode: row.skills_mode === "manual" ? "manual" : "auto",
        manualSkills: Array.isArray(row.manual_skills)
          ? row.manual_skills.map(String)
          : [],
        alertsEnabled: row.alerts_enabled,
        topN: row.top_n,
        updatedAt: new Date(row.updated_at).toISOString(),
      };
    }
    const prefs = this.memoryPrefs[userId];
    if (!prefs) return null;
    return normalizePrefs(prefs as PortalPrefs);
  }

  async savePrefs(prefs: PortalPrefs): Promise<PortalPrefs> {
    const normalized = normalizePrefs({
      ...prefs,
      updatedAt: new Date().toISOString(),
    } as PortalPrefs);
    if (this.pool) {
      await this.pool.query(
        `INSERT INTO portal_prefs
          (user_id, role, location, experience_level, employment_type, work_mode, company_size,
           salary_min, salary_max, alerts_enabled, top_n, updated_at, roles, skills_mode, manual_skills)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
         ON CONFLICT (user_id) DO UPDATE SET
           role = EXCLUDED.role, location = EXCLUDED.location,
           experience_level = EXCLUDED.experience_level, employment_type = EXCLUDED.employment_type,
           work_mode = EXCLUDED.work_mode, company_size = EXCLUDED.company_size,
           salary_min = EXCLUDED.salary_min, salary_max = EXCLUDED.salary_max,
           alerts_enabled = EXCLUDED.alerts_enabled, top_n = EXCLUDED.top_n,
           updated_at = EXCLUDED.updated_at, roles = EXCLUDED.roles,
           skills_mode = EXCLUDED.skills_mode, manual_skills = EXCLUDED.manual_skills`,
        [
          normalized.userId,
          normalized.role,
          normalized.location,
          normalized.experienceLevel,
          normalized.employmentType,
          normalized.workMode,
          normalized.companySize,
          normalized.salaryMin ?? null,
          normalized.salaryMax ?? null,
          normalized.alertsEnabled,
          normalized.topN,
          normalized.updatedAt,
          JSON.stringify(normalized.roles),
          normalized.skillsMode,
          JSON.stringify(normalized.manualSkills),
        ]
      );
      return normalized;
    }
    this.memoryPrefs[normalized.userId] = normalized;
    await this.prefsStore.write(this.memoryPrefs);
    return normalized;
  }

  async setTelegramLinkToken(userId: string, token: string): Promise<void> {
    if (this.pool) {
      await this.pool.query(
        `INSERT INTO portal_telegram (user_id, link_token, chat_id, username, linked_at)
         VALUES ($1,$2,NULL,NULL,NULL)
         ON CONFLICT (user_id) DO UPDATE SET link_token = EXCLUDED.link_token`,
        [userId, token]
      );
      return;
    }
    const prev = this.memoryTelegram[userId];
    this.memoryTelegram[userId] = {
      userId,
      chatId: prev?.chatId ?? "",
      username: prev?.username ?? null,
      linkToken: token,
      linkedAt: prev?.linkedAt ?? null,
    };
    await this.telegramStore.write(this.memoryTelegram);
  }

  async linkTelegramByToken(
    token: string,
    chatId: string,
    username: string | null
  ): Promise<boolean> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `UPDATE portal_telegram
         SET chat_id = $1, username = $2, linked_at = NOW(), link_token = NULL
         WHERE link_token = $3 RETURNING user_id`,
        [chatId, username, token]
      );
      return rows.length > 0;
    }
    const entry = Object.values(this.memoryTelegram).find((t) => t.linkToken === token);
    if (!entry) return false;
    entry.chatId = chatId;
    entry.username = username;
    entry.linkedAt = new Date().toISOString();
    entry.linkToken = null;
    await this.telegramStore.write(this.memoryTelegram);
    return true;
  }

  async getTelegram(userId: string): Promise<TelegramLink | null> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT user_id, chat_id, username, link_token, linked_at FROM portal_telegram WHERE user_id = $1`,
        [userId]
      );
      if (!rows[0]) return null;
      return {
        userId: rows[0].user_id,
        chatId: rows[0].chat_id ?? "",
        username: rows[0].username,
        linkToken: rows[0].link_token,
        linkedAt: rows[0].linked_at ? new Date(rows[0].linked_at).toISOString() : null,
      };
    }
    return this.memoryTelegram[userId] ?? null;
  }

  async unlinkTelegram(userId: string): Promise<void> {
    if (this.pool) {
      await this.pool.query(`DELETE FROM portal_telegram WHERE user_id = $1`, [userId]);
      return;
    }
    delete this.memoryTelegram[userId];
    await this.telegramStore.write(this.memoryTelegram);
  }

  async linkTelegramByChatId(
    userId: string,
    chatId: string,
    username: string | null = null
  ): Promise<void> {
    const linkedAt = new Date().toISOString();
    if (this.pool) {
      await this.pool.query(
        `INSERT INTO portal_telegram (user_id, chat_id, username, link_token, linked_at)
         VALUES ($1,$2,$3,NULL,$4)
         ON CONFLICT (user_id) DO UPDATE SET
           chat_id = EXCLUDED.chat_id,
           username = EXCLUDED.username,
           link_token = NULL,
           linked_at = EXCLUDED.linked_at`,
        [userId, chatId, username, linkedAt]
      );
      return;
    }
    this.memoryTelegram[userId] = {
      userId,
      chatId,
      username,
      linkToken: null,
      linkedAt,
    };
    await this.telegramStore.write(this.memoryTelegram);
  }

  async getSentJobIds(userId: string): Promise<Set<string>> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT job_id FROM portal_sent_jobs WHERE user_id = $1`,
        [userId]
      );
      return new Set(rows.map((r) => String(r.job_id)));
    }
    return new Set(this.memorySentJobs[userId] ?? []);
  }

  async markJobsSent(
    userId: string,
    jobs: Array<{ id: string; title: string; company: string }>
  ): Promise<void> {
    if (jobs.length === 0) return;
    if (this.pool) {
      for (const job of jobs) {
        await this.pool.query(
          `INSERT INTO portal_sent_jobs (user_id, job_id, title, company, sent_at)
           VALUES ($1,$2,$3,$4,NOW())
           ON CONFLICT (user_id, job_id) DO NOTHING`,
          [userId, job.id, job.title, job.company]
        );
      }
      return;
    }
    const existing = new Set(this.memorySentJobs[userId] ?? []);
    for (const job of jobs) existing.add(job.id);
    this.memorySentJobs[userId] = [...existing];
    await this.sentJobsStore.write(this.memorySentJobs);
  }

  async listDigestUsers(): Promise<
    Array<{ user: PortalUser; prefs: PortalPrefs; telegram: TelegramLink }>
  > {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT u.id, u.email, u.name, u.password_hash, u.created_at,
                p.role, p.roles, p.location, p.experience_level, p.employment_type, p.work_mode,
                p.company_size, p.salary_min, p.salary_max, p.alerts_enabled, p.top_n, p.updated_at,
                p.skills_mode, p.manual_skills,
                t.chat_id, t.username, t.linked_at
         FROM portal_users u
         JOIN portal_prefs p ON p.user_id = u.id
         JOIN portal_telegram t ON t.user_id = u.id
         WHERE p.alerts_enabled = TRUE AND t.chat_id IS NOT NULL AND t.chat_id <> ''`
      );
      return rows.map((row) => {
        const roles: string[] = Array.isArray(row.roles) && row.roles.length
          ? row.roles.map(String).filter(Boolean)
          : row.role
            ? [String(row.role)]
            : ["Software Engineer"];
        return {
          user: {
            id: row.id,
            email: row.email,
            name: row.name,
            passwordHash: row.password_hash,
            createdAt: new Date(row.created_at).toISOString(),
          },
          prefs: {
            userId: row.id,
            role: roles[0] || row.role || "Software Engineer",
            roles,
            location: row.location,
            experienceLevel: row.experience_level,
            employmentType: row.employment_type,
            workMode: row.work_mode,
            companySize: row.company_size,
            salaryMin: row.salary_min ?? undefined,
            salaryMax: row.salary_max ?? undefined,
            skillsMode: row.skills_mode === "manual" ? "manual" : "auto",
            manualSkills: Array.isArray(row.manual_skills)
              ? row.manual_skills.map(String)
              : [],
            alertsEnabled: row.alerts_enabled,
            topN: row.top_n,
            updatedAt: new Date(row.updated_at).toISOString(),
          },
          telegram: {
            userId: row.id,
            chatId: row.chat_id,
            username: row.username,
            linkToken: null,
            linkedAt: row.linked_at ? new Date(row.linked_at).toISOString() : null,
          },
        };
      });
    }

    const out: Array<{ user: PortalUser; prefs: PortalPrefs; telegram: TelegramLink }> = [];
    for (const user of this.memoryUsers) {
      const rawPrefs = this.memoryPrefs[user.id];
      const telegram = this.memoryTelegram[user.id];
      if (!rawPrefs?.alertsEnabled || !telegram?.chatId) continue;
      out.push({ user, prefs: normalizePrefs(rawPrefs), telegram });
    }
    return out;
  }

  async saveAlertRun(run: AlertRun): Promise<void> {
    if (this.pool) {
      await this.pool.query(
        `INSERT INTO portal_alert_runs (id, user_id, ran_at, status, jobs_sent, message, preview)
         VALUES ($1,$2,$3,$4,$5,$6,$7)`,
        [
          run.id, run.userId, run.ranAt, run.status, run.jobsSent,
          run.message ?? null, JSON.stringify(run.preview ?? []),
        ]
      );
      return;
    }
    this.memoryAlertRuns.unshift(run);
    this.memoryAlertRuns = this.memoryAlertRuns.slice(0, 200);
    await this.alertRunsStore.write(this.memoryAlertRuns);
  }

  async listAlertRuns(userId: string, limit = 10): Promise<AlertRun[]> {
    if (this.pool) {
      const { rows } = await this.pool.query(
        `SELECT id, user_id, ran_at, status, jobs_sent, message, preview
         FROM portal_alert_runs WHERE user_id = $1 ORDER BY ran_at DESC LIMIT $2`,
        [userId, limit]
      );
      return rows.map((row) => ({
        id: row.id,
        userId: row.user_id,
        ranAt: new Date(row.ran_at).toISOString(),
        status: row.status,
        jobsSent: row.jobs_sent,
        message: row.message ?? undefined,
        preview: row.preview ?? [],
      }));
    }
    return this.memoryAlertRuns.filter((r) => r.userId === userId).slice(0, limit);
  }
}

function normalizePrefs(input: Partial<PortalPrefs> & { userId: string }): PortalPrefs {
  const defaults = defaultPrefs(input.userId);
  const rolesFromList = Array.isArray(input.roles)
    ? input.roles.map(String).map((r) => r.trim()).filter(Boolean)
    : [];
  const roles =
    rolesFromList.length > 0
      ? rolesFromList
      : input.role?.trim()
        ? [input.role.trim()]
        : defaults.roles;

  const manualSkills = Array.isArray(input.manualSkills)
    ? input.manualSkills.map(String).map((s) => s.trim()).filter(Boolean)
    : [];

  return {
    userId: input.userId,
    roles,
    role: roles[0] || defaults.role,
    location: (input.location || defaults.location).trim() || defaults.location,
    experienceLevel: input.experienceLevel || defaults.experienceLevel,
    employmentType: input.employmentType || defaults.employmentType,
    workMode: input.workMode || defaults.workMode,
    companySize: input.companySize || defaults.companySize,
    salaryMin: input.salaryMin,
    salaryMax: input.salaryMax,
    skillsMode: input.skillsMode === "manual" ? "manual" : "auto",
    manualSkills,
    alertsEnabled: input.alertsEnabled ?? defaults.alertsEnabled,
    topN: Math.max(1, Math.min(10, Number(input.topN) || defaults.topN)),
    updatedAt: input.updatedAt || new Date().toISOString(),
  };
}

export const databaseService = new DatabaseService();
