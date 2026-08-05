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
  redisUrl: process.env.REDIS_URL || process.env.REDIS_PRIVATE_URL || "",
  cacheTtlSeconds: Number(process.env.CACHE_TTL_SECONDS ?? 3600),
  dataDir: path.resolve(__dirname, "../../data"),
  jwtSecret:
    process.env.JWT_SECRET || "scout-dev-secret-change-me-in-production",
  telegramBotToken: process.env.TELEGRAM_BOT_TOKEN ?? "",
  telegramBotUsername: process.env.TELEGRAM_BOT_USERNAME ?? "",
  digestCron: process.env.DIGEST_CRON ?? "0 5 * * *",
  digestTimezone: process.env.DIGEST_TIMEZONE ?? "Asia/Kolkata",
  digestTopN: Number(process.env.DIGEST_TOP_N ?? 5),
  publicAppUrl:
    process.env.PUBLIC_APP_URL ?? process.env.CORS_ORIGIN?.split(",")[0] ??
    "http://localhost:3000",
} as const;

export const hasApify = Boolean(config.apifyToken);
export const hasOpenAI = Boolean(config.openaiApiKey);
export const hasPostgres = Boolean(config.databaseUrl);
export const hasRedis = Boolean(config.redisUrl);
export const hasTelegram = Boolean(config.telegramBotToken);
