import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(__dirname, "../../../.env") });
dotenv.config();

export const config = {
  port: Number(process.env.PORT ?? 4000),
  nodeEnv: process.env.NODE_ENV ?? "development",
  corsOrigin: process.env.CORS_ORIGIN ?? "http://localhost:3000",
  apifyToken: process.env.APIFY_API_TOKEN ?? "",
  apifyActorId:
    process.env.APIFY_ACTOR_ID ?? "curious_coder/linkedin-jobs-scraper",
  openaiApiKey: process.env.OPENAI_API_KEY ?? "",
  openaiModel: process.env.OPENAI_MODEL ?? "gpt-4o-mini",
  databaseUrl: process.env.DATABASE_URL ?? "",
  redisUrl: process.env.REDIS_URL ?? "",
  cacheTtlSeconds: Number(process.env.CACHE_TTL_SECONDS ?? 3600),
  dataDir: path.resolve(__dirname, "../../data"),
} as const;

export const hasApify = Boolean(config.apifyToken);
export const hasOpenAI = Boolean(config.openaiApiKey);
export const hasPostgres = Boolean(config.databaseUrl);
export const hasRedis = Boolean(config.redisUrl);
