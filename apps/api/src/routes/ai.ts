import { Router } from "express";
import { uid, nowIso } from "@interviewpilot/shared";
import { classifyQuestion, looksLikeQuestion } from "@interviewpilot/ai";
import type { AppContext } from "../context.js";
import { requireAuth } from "../middleware/auth.js";

export function aiRouter(ctx: AppContext) {
  const router = Router();
  router.use(requireAuth(ctx));

  router.post("/detect-question", (req, res) => {
    const text = String(req.body?.text || "").trim();
    if (!text) return res.status(400).json({ error: "text required" });
    const isQuestion = looksLikeQuestion(text);
    const { category, confidence } = classifyQuestion(text);
    res.json({
      isQuestion,
      question: isQuestion
        ? {
            id: uid("q"),
            text,
            category,
            confidence,
            timestamp: nowIso(),
          }
        : null,
    });
  });

  router.post("/answer", async (req, res) => {
    try {
      const {
        question,
        category = "general",
        sessionId,
        responseMode = "balanced",
        aiMode = "interview",
        language = "en",
        stream = false,
      } = req.body || {};
      if (!question) return res.status(400).json({ error: "question required" });

      let resume;
      let jobDescription = "";
      let instructions = "";
      let documentIds: string[] = [];
      let recentTranscript = [];
      let previousAnswers: string[] = [];

      if (sessionId) {
        const session = ctx.db
          .prepare("SELECT * FROM sessions WHERE id = ? AND user_id = ?")
          .get(sessionId, req.user!.id) as Record<string, unknown> | undefined;
        if (session) {
          jobDescription = (session.job_description as string) || "";
          instructions = (session.instructions as string) || "";
          documentIds = JSON.parse((session.document_ids_json as string) || "[]");
          recentTranscript = JSON.parse((session.transcript_json as string) || "[]");
          previousAnswers = (JSON.parse((session.answers_json as string) || "[]") as Array<{ concise?: string; detailed?: string }>)
            .map((a) => a.detailed || a.concise || "")
            .filter(Boolean);
          if (session.resume_id) {
            const doc = ctx.db
              .prepare("SELECT resume_json FROM documents WHERE id = ? AND user_id = ?")
              .get(session.resume_id, req.user!.id) as { resume_json?: string } | undefined;
            if (doc?.resume_json) resume = JSON.parse(doc.resume_json);
          }
        }
      }

      // Fallback: latest resume for user
      if (!resume) {
        const doc = ctx.db
          .prepare(
            "SELECT resume_json FROM documents WHERE user_id = ? AND category = 'resume' AND resume_json IS NOT NULL ORDER BY created_at DESC LIMIT 1"
          )
          .get(req.user!.id) as { resume_json?: string } | undefined;
        if (doc?.resume_json) resume = JSON.parse(doc.resume_json);
      }

      let retrievedChunks: string[] = [];
      if (documentIds.length) {
        const placeholders = documentIds.map(() => "?").join(",");
        const rows = ctx.db
          .prepare(
            `SELECT c.text, c.embedding_json FROM document_chunks c
             WHERE c.document_id IN (${placeholders})`
          )
          .all(...documentIds) as Array<{ text: string; embedding_json: string }>;
        // simple lexical rank
        const q = String(question).toLowerCase();
        retrievedChunks = rows
          .map((r) => ({
            text: r.text,
            score: q.split(/\\s+/).filter((w) => w.length > 3 && r.text.toLowerCase().includes(w)).length,
          }))
          .sort((a, b) => b.score - a.score)
          .slice(0, 5)
          .map((r) => r.text);
      }

      const answerContext = {
        question: String(question),
        category: String(category),
        resume,
        jobDescription,
        instructions,
        retrievedChunks,
        recentTranscript,
        previousAnswers,
        responseMode,
        aiMode,
        language,
      };

      if (stream) {
        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");
        const answer = await ctx.ai.streamAnswer(answerContext, (token) => {
          res.write(`data: ${JSON.stringify({ type: "token", token })}\\n\\n`);
        });
        ctx.db
          .prepare("UPDATE usage SET ai_requests = ai_requests + 1, llm_tokens = llm_tokens + ? WHERE user_id = ?")
          .run(Math.ceil((answer.detailed || answer.concise || "").length / 4), req.user!.id);
        res.write(`data: ${JSON.stringify({ type: "done", answer })}\\n\\n`);
        return res.end();
      }

      const answer = await ctx.ai.generateAnswer(answerContext);
      ctx.db
        .prepare("UPDATE usage SET ai_requests = ai_requests + 1, llm_tokens = llm_tokens + ? WHERE user_id = ?")
        .run(Math.ceil((answer.detailed || answer.concise || "").length / 4), req.user!.id);
      res.json({ answer, provider: ctx.ai.name, demoMode: ctx.config.demoMode });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Answer generation failed";
      ctx.errors.push({ at: nowIso(), message });
      res.status(500).json({ error: message });
    }
  });

  router.post("/summarize", async (req, res) => {
    const { transcript, sessionId } = req.body || {};
    let text = String(transcript || "");
    if (!text && sessionId) {
      const session = ctx.db
        .prepare("SELECT transcript_json FROM sessions WHERE id = ? AND user_id = ?")
        .get(sessionId, req.user!.id) as { transcript_json: string } | undefined;
      if (session) {
        const segs = JSON.parse(session.transcript_json || "[]") as Array<{ speaker: string; text: string }>;
        text = segs.map((s) => `${s.speaker}: ${s.text}`).join("\\n");
      }
    }
    if (!text) return res.status(400).json({ error: "transcript required" });
    const summary = await ctx.ai.summarizeMeeting(text);
    if (sessionId) {
      ctx.db.prepare("UPDATE sessions SET summary_json = ? WHERE id = ? AND user_id = ?").run(
        JSON.stringify(summary),
        sessionId,
        req.user!.id
      );
    }
    res.json({ summary, provider: ctx.ai.name });
  });

  router.post("/vision", async (req, res) => {
    // Explicit user-provided image context only. No silent capture.
    const { prompt, imageBase64 } = req.body || {};
    if (!imageBase64) return res.status(400).json({ error: "imageBase64 required (user-initiated capture/upload only)" });
    if (ctx.config.demoMode || ctx.ai.name === "demo") {
      return res.json({
        analysis:
          "DEMO MODE: Image received. Configure a vision-capable AI provider to analyze coding questions, diagrams, SQL, errors, or architecture screenshots. No silent screen capture is performed.",
        prompt: prompt || null,
      });
    }
    res.json({
      analysis:
        "Vision provider configured path ready. Connect a vision-capable model key to enable full screenshot understanding.",
      prompt: prompt || null,
    });
  });

  router.post("/code/explain", async (req, res) => {
    const code = String(req.body?.code || "");
    if (!code) return res.status(400).json({ error: "code required" });
    const answer = await ctx.ai.generateAnswer({
      question: `Explain this code:\\n${code}`,
      category: "coding",
      retrievedChunks: [],
      recentTranscript: [],
      previousAnswers: [],
      responseMode: "balanced",
      aiMode: "coding",
      language: "en",
    });
    res.json({ explanation: answer.detailed || answer.concise });
  });

  router.post("/code/optimize", async (req, res) => {
    const code = String(req.body?.code || "");
    const answer = await ctx.ai.generateAnswer({
      question: `Optimize this solution and explain trade-offs:\\n${code}`,
      category: "coding",
      retrievedChunks: [],
      recentTranscript: [],
      previousAnswers: [],
      responseMode: "detailed",
      aiMode: "coding",
      language: "en",
    });
    res.json({ result: answer });
  });

  router.post("/code/alternative", async (req, res) => {
    const question = String(req.body?.question || "Provide an alternative approach");
    const answer = await ctx.ai.generateAnswer({
      question: `${question}\\nProvide an alternative approach.`,
      category: "coding",
      retrievedChunks: [],
      recentTranscript: [],
      previousAnswers: [],
      responseMode: "balanced",
      aiMode: "coding",
      language: "en",
    });
    res.json({ result: answer });
  });

  return router;
}
