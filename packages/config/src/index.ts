export interface EnvConfig {
  nodeEnv: string;
  port: number;
  databaseUrl: string;
  authSecret: string;
  aiProvider: string;
  openaiApiKey?: string;
  anthropicApiKey?: string;
  googleApiKey?: string;
  sttProvider: string;
  sttApiKey?: string;
  demoMode: boolean;
  corsOrigin: string;
  maxUploadMb: number;
}

function bool(v: string | undefined, d = false): boolean {
  if (v === undefined) return d;
  return ["1", "true", "yes", "on"].includes(v.toLowerCase());
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): EnvConfig {
  const openai = env.OPENAI_API_KEY;
  const anthropic = env.ANTHROPIC_API_KEY;
  const google = env.GOOGLE_API_KEY;
  const hasCloud = Boolean(openai || anthropic || google);
  const demoMode = bool(env.DEMO_MODE, !hasCloud);

  return {
    nodeEnv: env.NODE_ENV || "development",
    port: Number(env.PORT || 8787),
    databaseUrl: env.DATABASE_URL || "file:data/sqlite/interviewpilot.db",
    authSecret: env.AUTH_SECRET || "dev-only-change-me-interviewpilot",
    aiProvider: env.AI_PROVIDER || (demoMode ? "demo" : openai ? "openai" : anthropic ? "anthropic" : google ? "google" : "demo"),
    openaiApiKey: openai,
    anthropicApiKey: anthropic,
    googleApiKey: google,
    sttProvider: env.STT_PROVIDER || (demoMode ? "demo" : "browser"),
    sttApiKey: env.STT_API_KEY,
    demoMode,
    corsOrigin: env.CORS_ORIGIN || "http://localhost:5173",
    maxUploadMb: Number(env.MAX_UPLOAD_MB || 10),
  };
}

export const DEFAULT_SHORTCUTS = {
  startStopSession: "Ctrl+Shift+S",
  pauseResume: "Ctrl+Shift+P",
  focusAssistant: "Ctrl+Shift+A",
  copyLatestAnswer: "Ctrl+Shift+C",
  openDashboard: "Ctrl+Shift+D",
};
