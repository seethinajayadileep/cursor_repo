import { Router } from "express";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { uid, nowIso } from "@interviewpilot/shared";
import type { AppContext } from "../context.js";
import { requireAuth, signToken } from "../middleware/auth.js";
import { DEFAULT_SHORTCUTS } from "@interviewpilot/config";

export function authRouter(ctx: AppContext) {
  const router = Router();

  router.post("/signup", async (req, res) => {
    const schema = z.object({
      email: z.string().email(),
      password: z.string().min(8),
      name: z.string().min(1).max(120),
    });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: "Invalid signup data" });

    const existing = ctx.db.prepare("SELECT id FROM users WHERE email = ?").get(parsed.data.email.toLowerCase());
    if (existing) return res.status(409).json({ error: "Email already registered" });

    const id = uid("user");
    const passwordHash = await bcrypt.hash(parsed.data.password, 12);
    const createdAt = nowIso();
    ctx.db
      .prepare("INSERT INTO users (id, email, name, password_hash, plan, created_at) VALUES (?, ?, ?, ?, 'free', ?)")
      .run(id, parsed.data.email.toLowerCase(), parsed.data.name, passwordHash, createdAt);

    ctx.db
      .prepare("INSERT INTO settings (user_id, settings_json) VALUES (?, ?)")
      .run(
        id,
        JSON.stringify({
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
        })
      );
    ctx.db
      .prepare(
        "INSERT INTO usage (user_id, stt_seconds, llm_tokens, document_processing, ai_requests, storage_bytes) VALUES (?,0,0,0,0,0)"
      )
      .run(id);

    const user = { id, email: parsed.data.email.toLowerCase(), name: parsed.data.name, plan: "free" };
    const token = signToken(ctx, user);
    res.status(201).json({ user, token, demoMode: ctx.config.demoMode });
  });

  router.post("/login", async (req, res) => {
    const schema = z.object({ email: z.string().email(), password: z.string().min(1) });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: "Invalid credentials" });

    const row = ctx.db
      .prepare("SELECT id, email, name, plan, password_hash FROM users WHERE email = ?")
      .get(parsed.data.email.toLowerCase()) as
      | { id: string; email: string; name: string; plan: string; password_hash: string }
      | undefined;

    if (!row) return res.status(401).json({ error: "Invalid email or password" });
    const ok = await bcrypt.compare(parsed.data.password, row.password_hash);
    if (!ok) return res.status(401).json({ error: "Invalid email or password" });

    const user = { id: row.id, email: row.email, name: row.name, plan: row.plan };
    res.json({ user, token: signToken(ctx, user), demoMode: ctx.config.demoMode });
  });

  router.get("/me", requireAuth(ctx), (req, res) => {
    const row = ctx.db
      .prepare("SELECT id, email, name, plan, created_at FROM users WHERE id = ?")
      .get(req.user!.id) as { id: string; email: string; name: string; plan: string; created_at: string } | undefined;
    if (!row) return res.status(404).json({ error: "User not found" });
    res.json({ user: { id: row.id, email: row.email, name: row.name, plan: row.plan, createdAt: row.created_at } });
  });

  router.post("/logout", requireAuth(ctx), (_req, res) => {
    res.json({ ok: true });
  });

  router.delete("/account", requireAuth(ctx), (req, res) => {
    const userId = req.user!.id;
    const docs = ctx.db.prepare("SELECT id FROM documents WHERE user_id = ?").all(userId) as Array<{ id: string }>;
    for (const d of docs) {
      ctx.db.prepare("DELETE FROM document_chunks WHERE document_id = ?").run(d.id);
    }
    ctx.db.prepare("DELETE FROM documents WHERE user_id = ?").run(userId);
    ctx.db.prepare("DELETE FROM sessions WHERE user_id = ?").run(userId);
    ctx.db.prepare("DELETE FROM mock_interviews WHERE user_id = ?").run(userId);
    ctx.db.prepare("DELETE FROM settings WHERE user_id = ?").run(userId);
    ctx.db.prepare("DELETE FROM usage WHERE user_id = ?").run(userId);
    ctx.db.prepare("DELETE FROM users WHERE id = ?").run(userId);
    res.json({ ok: true });
  });

  return router;
}
