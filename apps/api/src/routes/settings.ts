import { Router } from "express";
import type { AppContext } from "../context.js";
import { requireAuth } from "../middleware/auth.js";
import { DEFAULT_SHORTCUTS } from "@interviewpilot/config";
import { BILLING_PLANS } from "@interviewpilot/shared";

export function settingsRouter(ctx: AppContext) {
  const router = Router();
  router.use(requireAuth(ctx));

  router.get("/", (req, res) => {
    const row = ctx.db.prepare("SELECT settings_json FROM settings WHERE user_id = ?").get(req.user!.id) as
      | { settings_json: string }
      | undefined;
    const settings = row
      ? JSON.parse(row.settings_json)
      : {
          theme: "dark",
          language: "en",
          aiProvider: ctx.config.aiProvider,
          sttProvider: ctx.config.sttProvider,
          processingMode: ctx.config.demoMode ? "demo" : "cloud",
          responseMode: "balanced",
          aiMode: "interview",
          alwaysOnTop: false,
          compactMode: false,
          analyticsOptIn: false,
          shortcuts: DEFAULT_SHORTCUTS,
        };
    res.json({ settings });
  });

  router.put("/", (req, res) => {
    const current = ctx.db.prepare("SELECT settings_json FROM settings WHERE user_id = ?").get(req.user!.id) as
      | { settings_json: string }
      | undefined;
    const merged = { ...(current ? JSON.parse(current.settings_json) : {}), ...(req.body || {}) };
    if (current) {
      ctx.db.prepare("UPDATE settings SET settings_json = ? WHERE user_id = ?").run(JSON.stringify(merged), req.user!.id);
    } else {
      ctx.db.prepare("INSERT INTO settings (user_id, settings_json) VALUES (?, ?)").run(req.user!.id, JSON.stringify(merged));
    }
    res.json({ settings: merged });
  });

  router.get("/privacy", (req, res) => {
    const usage = ctx.db.prepare("SELECT * FROM usage WHERE user_id = ?").get(req.user!.id);
    res.json({
      microphoneStatus: "user-controlled",
      audioSource: "microphone|browser|desktop",
      aiProvider: ctx.ai.name,
      dataStorageMode: ctx.config.demoMode ? "local-sqlite+demo" : "configured-provider",
      cloudProcessing: !ctx.config.demoMode && ctx.ai.name !== "demo" && ctx.ai.name !== "local",
      localProcessing: ctx.config.demoMode || ctx.ai.name === "local" || ctx.ai.name === "demo",
      usage,
      notice:
        "InterviewPilot AI never secretly records audio or captures screens. Uploads and captures require explicit user action. Users must comply with interview/meeting rules and obtain consent where required.",
    });
  });

  router.post("/privacy/clear-local", (req, res) => {
    const userId = req.user!.id;
    const docs = ctx.db.prepare("SELECT id FROM documents WHERE user_id = ?").all(userId) as Array<{ id: string }>;
    for (const d of docs) ctx.db.prepare("DELETE FROM document_chunks WHERE document_id = ?").run(d.id);
    ctx.db.prepare("DELETE FROM documents WHERE user_id = ?").run(userId);
    ctx.db.prepare("DELETE FROM sessions WHERE user_id = ?").run(userId);
    ctx.db.prepare("DELETE FROM mock_interviews WHERE user_id = ?").run(userId);
    ctx.db
      .prepare(
        "UPDATE usage SET stt_seconds=0, llm_tokens=0, document_processing=0, ai_requests=0, storage_bytes=0 WHERE user_id = ?"
      )
      .run(userId);
    res.json({ ok: true });
  });

  return router;
}

export function billingRouter(ctx: AppContext) {
  const router = Router();
  router.use(requireAuth(ctx));

  router.get("/plans", (_req, res) => {
    res.json({ plans: BILLING_PLANS, note: "Placeholder pricing until a payment provider is configured." });
  });

  router.get("/usage", (req, res) => {
    const usage = ctx.db.prepare("SELECT * FROM usage WHERE user_id = ?").get(req.user!.id);
    const user = ctx.db.prepare("SELECT plan FROM users WHERE id = ?").get(req.user!.id) as { plan: string };
    res.json({ usage, plan: user?.plan || "free" });
  });

  router.post("/dev-simulate", (req, res) => {
    if (ctx.config.nodeEnv === "production" && !ctx.config.demoMode) {
      return res.status(403).json({ error: "DEV ONLY billing simulator disabled in production" });
    }
    const plan = String(req.body?.plan || "pro");
    if (!["free", "pro", "premium"].includes(plan)) return res.status(400).json({ error: "Invalid plan" });
    ctx.db.prepare("UPDATE users SET plan = ? WHERE id = ?").run(plan, req.user!.id);
    res.json({
      ok: true,
      plan,
      label: "DEV ONLY — simulated plan change; no real payment processed",
    });
  });

  return router;
}

export function mockRouter(ctx: AppContext) {
  const router = Router();
  router.use(requireAuth(ctx));

  router.post("/start", async (req, res) => {
    const {
      role = "Software Engineer",
      company = "",
      experienceLevel = "mid",
      interviewType = "mixed",
      language = "en",
      difficulty = "medium",
    } = req.body || {};
    const id = uid("mock");
    const createdAt = nowIso();
    const question = await ctx.ai.mockQuestion(role, difficulty, []);
    ctx.db
      .prepare(
        `INSERT INTO mock_interviews (id, user_id, role, company, experience_level, interview_type, language, difficulty, feedback_json, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        id,
        req.user!.id,
        role,
        company,
        experienceLevel,
        interviewType,
        language,
        difficulty,
        JSON.stringify({ questions: [question], answers: [], evaluations: [] }),
        createdAt
      );
    res.status(201).json({
      mock: { id, role, company, experienceLevel, interviewType, language, difficulty, question },
      disclaimer: "Mock interview feedback is for practice only and does not guarantee real interview performance.",
    });
  });

  router.post("/:id/answer", async (req, res) => {
    const row = ctx.db
      .prepare("SELECT * FROM mock_interviews WHERE id = ? AND user_id = ?")
      .get(req.params.id, req.user!.id) as Record<string, unknown> | undefined;
    if (!row) return res.status(404).json({ error: "Mock interview not found" });
    const state = JSON.parse((row.feedback_json as string) || "{}") as {
      questions: string[];
      answers: string[];
      evaluations: unknown[];
    };
    const question = String(req.body?.question || state.questions.at(-1) || "");
    const answer = String(req.body?.answer || "");
    const evaluation = await ctx.ai.evaluateAnswer(question, answer);
    state.answers.push(answer);
    state.evaluations.push(evaluation);
    const nextQuestion = await ctx.ai.mockQuestion(String(row.role), String(row.difficulty), state.questions);
    state.questions.push(nextQuestion);
    ctx.db.prepare("UPDATE mock_interviews SET feedback_json = ? WHERE id = ?").run(JSON.stringify(state), req.params.id);
    res.json({ evaluation, nextQuestion, disclaimer: "Practice feedback only." });
  });

  router.post("/:id/finish", (req, res) => {
    const row = ctx.db
      .prepare("SELECT * FROM mock_interviews WHERE id = ? AND user_id = ?")
      .get(req.params.id, req.user!.id) as Record<string, unknown> | undefined;
    if (!row) return res.status(404).json({ error: "Mock interview not found" });
    const state = JSON.parse((row.feedback_json as string) || "{}");
    res.json({
      feedback: state,
      overall:
        "Review clarity, structure, and resume-specific examples. This evaluation is for practice and is not a guarantee of real interview outcomes.",
    });
  });

  return router;
}

export function diagnosticsRouter(ctx: AppContext) {
  const router = Router();
  router.use(requireAuth(ctx));

  router.get("/", (req, res) => {
    const dbOk = !!ctx.db.prepare("SELECT 1 as ok").get();
    res.json({
      sttProvider: ctx.config.sttProvider,
      aiProvider: ctx.ai.name,
      connectionState: "ok",
      uptimeMs: Date.now() - ctx.startedAt,
      requestCount: ctx.requestCount,
      errors: ctx.errors.slice(-20),
      audioSource: "abstracted",
      databaseStatus: dbOk ? "ok" : "error",
      demoMode: ctx.config.demoMode,
      // Never expose API keys
      secretsConfigured: {
        openai: Boolean(ctx.config.openaiApiKey),
        anthropic: Boolean(ctx.config.anthropicApiKey),
        google: Boolean(ctx.config.googleApiKey),
        stt: Boolean(ctx.config.sttApiKey),
      },
    });
  });

  return router;
}

function uid(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36).slice(-4)}`;
}

function nowIso(): string {
  return new Date().toISOString();
}
