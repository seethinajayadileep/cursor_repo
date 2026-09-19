import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";
import { loadConfig } from "@interviewpilot/config";
import { createDatabase, migrate } from "@interviewpilot/database";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../../..");
dotenv.config({ path: path.join(root, ".env") });

const config = loadConfig();
const raw = (config.databaseUrl || "").replace(/^file:/, "");
const dbPath = path.isAbsolute(raw) ? raw : path.resolve(root, raw);
const db = createDatabase(`file:${dbPath}`);
migrate(db);
console.log("Migrations applied:", dbPath);
