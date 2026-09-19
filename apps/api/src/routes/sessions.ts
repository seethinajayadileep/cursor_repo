import { Router } from "express";
import { z } from "zod";
import { uid, nowIso, type InterviewSession } from "@interviewpilot/shared";
import type { AppContext } from "../context.js";
import { requireAuth } from "../middleware/auth.js";

function mapSession(row: Record<string, unknown>): InterviewSession {
  return {
    id: row.id as string,
    userId: row.user_id as string,
    title: row.title as string,
    sessionType: row.session_type as InterviewSession["sessionType"],
    jobRole: (row.job_role as string) || undefined,
    company: (row.company as string) || undefined,
    jobDescription: (row.job_description as string) || undefined,
    language: row.language as string,
    aiMode: row.ai_mode as InterviewSession["aiMode"],
    responseMode: row.response_mode as InterviewSession["responseMode"],
    instructions: (row.instructions as string) || undefined,
    status: row.status as InterviewSession["status"],
    processingMode: row.processing_mode as InterviewSession["processingMode"],
    createdAt: row.created_at as string,
    startedAt: (row.started_at as string) || undefined,
    endedAt: (row.ended_at as string) || undefined,
    durationSec: (row.duration_sec as number) || undefined,
    transcript: JSON.parse((row.transcript_json as string) || "[]"),
    questions: JSON.parse((row.questions_json as string) || "[]"),
    answers: JSON.parse((row.answers_json as string) || "[]"),
    documentIds: JSON.parse((row.document_ids_json as string) || "[]"),
    resumeId: (row.resume_id as string) || undefined,
    summary: row.summary_json ? JSON.parse(row.summary_json as string) : undefined,
  };
}

export function sessionsRouter(ctx: AppContext) {
  const router = Router();
  router.use(requireAuth(ctx));

  router.get("/", (req, res) => {
    const q = String(req.query.q || "").toLowerCase();
    const rows = ctx.db
      .prepare("SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC")
      .all(req.user!.id) as Array<Record<string, unknown>>;
    const sessions = rows.map(mapSession).filter((s) => {
      if (!q) return true;
      return `${s.title} ${s.company || ""} ${s.jobRole || ""} ${s.sessionType}`.toLowerCase().includes(q);
    });
    res.json({ sessions });
  });

  router.get("/:id", (req, res) => {
    const row = ctx.db
      .prepare("SELECT * FROM sessions WHERE id = ? AND user_id = ?")
      .get(req.params.id, req.user!.id) as Record<string, unknown> | undefined;
    if (!row) return res.status(404).json({ error: "Session not found" });
    res.json({ session: mapSession(row) });
  });

  router.post("/", (req, res) => {
    const schema = z.object({
      title: z.string().min(1).max(200).optional(),
      sessionType: z.string(),
      jobRole: z.string().optional(),
      company: z.string().optional(),
      jobDescription: z.string().optional(),
      language: z.string().default("en"),
      aiMode: z.string().default("interview"),
      responseMode: z.string().default("balanced"),
      instructions: z.string().optional(),
      documentIds: z.array(z.string()).default([]),
      resumeId: z.string().optional(),
    });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: "Invalid session payload" });

    const id = uid("sess");
    const createdAt = nowIso();
    const title =
      parsed.data.title ||
      `${parsed.data.sessionType.replace(/_/g, " ")} — ${parsed.data.jobRole || "General"}${
        parsed.data.company ? ` @ ${parsed.data.company}` : ""
      }`;

    ctx.db
      .prepare(
        `INSERT INTO sessions (
          id, user_id, title, session_type, job_role, company, job_description, language,
          ai_mode, response_mode, instructions, status, processing_mode, created_at,
          transcript_json, questions_json, answers_json, document_ids_json, resume_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, '[]', '[]', '[]', ?, ?)`
      )
      .run(
        id,
        req.user!.id,
        title,
        parsed.data.sessionType,
        parsed.data.jobRole || null,
        parsed.data.company || null,
        parsed.data.jobDescription || null,
        parsed.data.language,
        parsed.data.aiMode,
        parsed.data.responseMode,
        parsed.data.instructions || null,
        ctx.config.demoMode ? "demo" : "cloud",
        createdAt,
        JSON.stringify(parsed.data.documentIds),
        parsed.data.resumeId || null
      );

    const row = ctx.db.prepare("SELECT * FROM sessions WHERE id = ?").get(id) as Record<string, unknown>;
    res.status(201).json({ session: mapSession(row) });
  });

  router.patch("/:id", (req, res) => {
    const row = ctx.db
      .prepare("SELECT * FROM sessions WHERE id = ? AND user_id = ?")
      .get(req.params.id, req.user!.id) as Record<string, unknown> | undefined;
    if (!row) return res.status(404).json({ error: "Session not found" });

    const session = mapSession(row);
    const body = req.body || {};

    if (body.status === "active" && session.status !== "active") {
      session.status = "active";
      session.startedAt = session.startedAt || nowIso();
    }
    if (body.status === "paused") session.status = "paused";
    if (body.status === "ended") {
      session.status = "ended";
      session.endedAt = nowIso();
      if (session.startedAt) {
        session.durationSec = Math.max(
          0,
          Math.round((Date.parse(session.endedAt) - Date.parse(session.startedAt)) / 1000)
        );
      }
    }
    if (body.transcript) session.transcript = body.transcript;
    if (body.questions) session.questions = body.questions;
    if (body.answers) session.answers = body.answers;
    if (body.summary) session.summary = body.summary;
    if (body.title) session.title = body.title;

    ctx.db
      .prepare(
        `UPDATE sessions SET status=?, started_at=?, ended_at=?, duration_sec=?, title=?,
         transcript_json=?, questions_json=?, answers_json=?, summary_json=? WHERE id=?`
      )
      .run(
        session.status,
        session.startedAt || null,
        session.endedAt || null,
        session.durationSec || null,
        session.title,
        JSON.stringify(session.transcript),
        JSON.stringify(session.questions),
        JSON.stringify(session.answers),
        session.summary ? JSON.stringify(session.summary) : null,
        session.id
      );

    res.json({ session });
  });

  router.delete("/:id", (req, res) => {
    const info = ctx.db
      .prepare("DELETE FROM sessions WHERE id = ? AND user_id = ?")
      .run(req.params.id, req.user!.id);
    if (!info.changes) return res.status(404).json({ error: "Session not found" });
    res.json({ ok: true });
  });

  router.get("/:id/export", (req, res) => {
    const row = ctx.db
      .prepare("SELECT * FROM sessions WHERE id = ? AND user_id = ?")
      .get(req.params.id, req.user!.id) as Record<string, unknown> | undefined;
    if (!row) return res.status(404).json({ error: "Session not found" });
    const session = mapSession(row);
    const format = String(req.query.format || "md");
    if (format === "json") {
      res.setHeader("Content-Type", "application/json");
      return res.send(JSON.stringify(session, null, 2));
    }
    const md = [
      `# ${session.title}`,
      "",
      `- Type: ${session.sessionType}`,
      `- Role: ${session.jobRole || "n/a"}`,
      `- Company: ${session.company || "n/a"}`,
      `- Duration: ${session.durationSec || 0}s`,
      "",
      "## Transcript",
      ...session.transcript.map((t) => `- **${t.speaker}** (${t.timestamp}): ${t.text}`),
      "",
      "## Questions & Answers",
      ...session.questions.map((q) => {
        const a = session.answers.find((x) => x.questionId === q.id);
        return `### ${q.text}\\n${a?.detailed || a?.concise || "_No answer_"}`;
      }),
      "",
      "## Summary",
      session.summary?.summary || "_No summary_",
    ].join("\\n");
    if (format === "txt") {
      res.setHeader("Content-Type", "text/plain");
      return res.send(md.replace(/[#*_`]/g, ""));
    }
    res.setHeader("Content-Type", "text/markdown");
    res.send(md);
  });

  return router;
}
