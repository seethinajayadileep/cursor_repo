import fs from "fs/promises";
import path from "path";
import { Redis } from "ioredis";
import { config, hasRedis } from "../../config/index.js";

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

export class CacheService {
  private redis: Redis | null = null;
  private memory = new Map<string, CacheEntry<unknown>>();
  private ready = false;

  async init(): Promise<void> {
    if (!hasRedis) {
      this.ready = true;
      console.log("[cache] Using in-memory cache");
      return;
    }

    try {
      this.redis = new Redis(config.redisUrl, {
        maxRetriesPerRequest: 1,
        lazyConnect: true,
        enableOfflineQueue: false,
      });
      await this.redis.connect();
      await this.redis.ping();
      this.ready = true;
      console.log("[cache] Connected to Redis");
    } catch (error) {
      console.warn("[cache] Redis unavailable, falling back to memory:", error);
      if (this.redis) {
        try {
          this.redis.disconnect();
        } catch {
          /* ignore */
        }
      }
      this.redis = null;
      this.ready = true;
    }
  }

  async get<T>(key: string): Promise<T | null> {
    if (this.redis) {
      try {
        const raw = await this.redis.get(key);
        return raw ? (JSON.parse(raw) as T) : null;
      } catch {
        /* fall through */
      }
    }

    const entry = this.memory.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiresAt) {
      this.memory.delete(key);
      return null;
    }
    return entry.value as T;
  }

  async set<T>(key: string, value: T, ttlSeconds = config.cacheTtlSeconds): Promise<void> {
    if (this.redis) {
      try {
        await this.redis.set(key, JSON.stringify(value), "EX", ttlSeconds);
        return;
      } catch {
        /* fall through */
      }
    }
    this.memory.set(key, {
      value,
      expiresAt: Date.now() + ttlSeconds * 1000,
    });
  }

  async del(key: string): Promise<void> {
    if (this.redis) {
      try {
        await this.redis.del(key);
      } catch {
        /* ignore */
      }
    }
    this.memory.delete(key);
  }

  mode(): "redis" | "memory" {
    return this.redis ? "redis" : "memory";
  }

  isReady(): boolean {
    return this.ready;
  }
}

export class FileStore {
  constructor(private fileName: string) {}

  private filePath(): string {
    return path.join(config.dataDir, this.fileName);
  }

  async read<T>(fallback: T): Promise<T> {
    try {
      await fs.mkdir(config.dataDir, { recursive: true });
      const raw = await fs.readFile(this.filePath(), "utf8");
      return JSON.parse(raw) as T;
    } catch {
      return fallback;
    }
  }

  async write<T>(data: T): Promise<void> {
    await fs.mkdir(config.dataDir, { recursive: true });
    await fs.writeFile(this.filePath(), JSON.stringify(data, null, 2), "utf8");
  }
}

export const cacheService = new CacheService();
