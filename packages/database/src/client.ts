import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import { SCHEMA_SQL } from "./schema.js";

export type Db = Database.Database;

export function resolveSqlitePath(databaseUrl: string): string {
  if (databaseUrl.startsWith("file:")) {
    return path.resolve(databaseUrl.slice(5));
  }
  if (databaseUrl.startsWith("sqlite:")) {
    return path.resolve(databaseUrl.slice(7));
  }
  // Postgres URL — callers should use a different adapter; fall back to local sqlite
  if (databaseUrl.startsWith("postgres")) {
    return path.resolve("data/sqlite/interviewpilot.db");
  }
  return path.resolve(databaseUrl);
}

export function createDatabase(databaseUrl: string): Db {
  const file = resolveSqlitePath(databaseUrl);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new Database(file);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  db.exec(SCHEMA_SQL);
  return db;
}

export function migrate(db: Db): void {
  db.exec(SCHEMA_SQL);
}
