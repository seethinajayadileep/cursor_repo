import express from "express";
import cors from "cors";
import helmet from "helmet";
import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";
import { loadConfig } from "@interviewpilot/config";
import { createDatabase } from "@interviewpilot/database";
import { createAIProvider } from "@interviewpilot/ai";
import { authRouter } from "./routes/auth.js";
import { sessionsRouter } from "./routes/sessions.js";
import { documentsRouter } from "./routes/documents.js";
import { aiRouter } from "./routes/ai.js";
import { settingsRouter, billingRouter, mockRouter, diagnosticsRouter } from "./routes/settings.js";
import { createAppContext } from "./context.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../../..");
dotenv.config({ path: path.join(root, ".env") });

const config = loadConfig();
const raw = (config.databaseUrl || "").replace(/^file:/, "");
const dbFile = path.isAbsolute(raw) ? raw : path.resolve(root, raw);
const db = createDatabase(`file:${dbFile}`);

const ai = createAIProvider({
  provider: config.aiProvider,
  openaiApiKey: config.openaiApiKey,
  anthropicApiKey: config.anthropicApiKey,
  googleApiKey: config.googleApiKey,
  demoMode: config.demoMode,
});

const ctx = createAppContext({ config, db, ai });

const app = express();
app.use(helmet({ contentSecurityPolicy: false }));
app.use(
  cors({
    origin: config.corsOrigin.split(",").map((s) => s.trim()),
    credentials: true,
  })
);
app.use(express.json({ limit: "2mb" }));

app.get("/api/health", (_req, res) => {
  res.json({
    ok: true,
    product: "InterviewPilot AI",
    demoMode: config.demoMode,
    aiProvider: ai.name,
    sttProvider: config.sttProvider,
    time: new Date().toISOString(),
  });
});

app.use("/api/auth", authRouter(ctx));
app.use("/api/sessions", sessionsRouter(ctx));
app.use("/api/documents", documentsRouter(ctx));
app.use("/api/ai", aiRouter(ctx));
app.use("/api/settings", settingsRouter(ctx));
app.use("/api/billing", billingRouter(ctx));
app.use("/api/mock", mockRouter(ctx));
app.use("/api/diagnostics", diagnosticsRouter(ctx));

app.use((err: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  const message = err instanceof Error ? err.message : "Unexpected server error";
  console.error(err);
  res.status(500).json({ error: message });
});

const port = config.port;
app.listen(port, () => {
  console.log(`InterviewPilot AI API listening on http://localhost:${port}`);
  console.log(`Mode: ${config.demoMode ? "DEMO" : "CLOUD/LOCAL"} | AI: ${ai.name}`);
});

export { app, ctx };
