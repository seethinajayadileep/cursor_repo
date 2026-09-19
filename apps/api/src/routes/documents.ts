import { Router } from "express";
import multer from "multer";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { uid, nowIso } from "@interviewpilot/shared";
import {
  extractTextFromBuffer,
  cleanText,
  chunkText,
  parseResume,
  embedText,
  retrieveChunks,
} from "@interviewpilot/documents";
import type { AppContext } from "../context.js";
import { requireAuth } from "../middleware/auth.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const uploadDir = path.resolve(__dirname, "../../../../data/uploads");
fs.mkdirSync(uploadDir, { recursive: true });

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ok =
      /pdf|text|plain|msword|wordprocessingml|officedocument/i.test(file.mimetype) ||
      /\\.(pdf|txt|docx|doc)$/i.test(file.originalname);
    cb(null, ok);
  },
});

export function documentsRouter(ctx: AppContext) {
  const router = Router();
  router.use(requireAuth(ctx));

  router.get("/", (req, res) => {
    const rows = ctx.db
      .prepare(
        "SELECT id, user_id, name, category, mime_type, size_bytes, created_at, substr(text_content,1,240) as text_preview FROM documents WHERE user_id = ? ORDER BY created_at DESC"
      )
      .all(req.user!.id) as Array<Record<string, unknown>>;
    const documents = rows.map((r) => ({
      id: r.id,
      userId: r.user_id,
      name: r.name,
      category: r.category,
      mimeType: r.mime_type,
      sizeBytes: r.size_bytes,
      createdAt: r.created_at,
      textPreview: r.text_preview,
    }));
    res.json({ documents });
  });

  router.post("/upload", upload.single("file"), async (req, res) => {
    try {
      if (!req.file) return res.status(400).json({ error: "File required" });
      const category = String(req.body.category || "custom");
      const text = cleanText(await extractTextFromBuffer(req.file.buffer, req.file.mimetype, req.file.originalname));
      if (!text) return res.status(400).json({ error: "Could not extract text from file" });

      const id = uid("doc");
      const createdAt = nowIso();
      const resumeJson = category === "resume" ? JSON.stringify(parseResume(text)) : null;

      ctx.db
        .prepare(
          `INSERT INTO documents (id, user_id, name, category, mime_type, size_bytes, created_at, text_content, resume_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
        )
        .run(
          id,
          req.user!.id,
          req.file.originalname,
          category,
          req.file.mimetype || "application/octet-stream",
          req.file.size,
          createdAt,
          text,
          resumeJson
        );

      const chunks = chunkText(text);
      const insertChunk = ctx.db.prepare(
        "INSERT INTO document_chunks (id, document_id, chunk_index, text, embedding_json) VALUES (?, ?, ?, ?, ?)"
      );
      const tx = ctx.db.transaction(() => {
        chunks.forEach((chunk, index) => {
          insertChunk.run(uid("chunk"), id, index, chunk, JSON.stringify(embedText(chunk)));
        });
      });
      tx();

      ctx.db
        .prepare("UPDATE usage SET document_processing = document_processing + 1, storage_bytes = storage_bytes + ? WHERE user_id = ?")
        .run(req.file.size, req.user!.id);

      // Persist original optionally for desktop/local mode
      fs.writeFileSync(path.join(uploadDir, `${id}-${req.file.originalname.replace(/[^a-zA-Z0-9._-]/g, "_")}`), req.file.buffer);

      res.status(201).json({
        document: {
          id,
          userId: req.user!.id,
          name: req.file.originalname,
          category,
          mimeType: req.file.mimetype,
          sizeBytes: req.file.size,
          createdAt,
          textPreview: text.slice(0, 240),
          chunkCount: chunks.length,
          resume: resumeJson ? JSON.parse(resumeJson) : undefined,
        },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      res.status(400).json({ error: message });
    }
  });

  router.post("/text", (req, res) => {
    const { name, category, text } = req.body || {};
    if (!text || !name) return res.status(400).json({ error: "name and text required" });
    const cleaned = cleanText(String(text));
    const id = uid("doc");
    const createdAt = nowIso();
    const resumeJson = category === "resume" ? JSON.stringify(parseResume(cleaned)) : null;
    ctx.db
      .prepare(
        `INSERT INTO documents (id, user_id, name, category, mime_type, size_bytes, created_at, text_content, resume_json)
         VALUES (?, ?, ?, ?, 'text/plain', ?, ?, ?, ?)`
      )
      .run(id, req.user!.id, String(name), String(category || "custom"), Buffer.byteLength(cleaned), createdAt, cleaned, resumeJson);

    const chunks = chunkText(cleaned);
    const insertChunk = ctx.db.prepare(
      "INSERT INTO document_chunks (id, document_id, chunk_index, text, embedding_json) VALUES (?, ?, ?, ?, ?)"
    );
    chunks.forEach((chunk, index) => {
      insertChunk.run(uid("chunk"), id, index, chunk, JSON.stringify(embedText(chunk)));
    });

    res.status(201).json({
      document: {
        id,
        name,
        category: category || "custom",
        chunkCount: chunks.length,
        resume: resumeJson ? JSON.parse(resumeJson) : undefined,
      },
    });
  });

  router.get("/:id", (req, res) => {
    const row = ctx.db
      .prepare("SELECT * FROM documents WHERE id = ? AND user_id = ?")
      .get(req.params.id, req.user!.id) as Record<string, unknown> | undefined;
    if (!row) return res.status(404).json({ error: "Document not found" });
    const chunkCount = (
      ctx.db.prepare("SELECT COUNT(*) as c FROM document_chunks WHERE document_id = ?").get(row.id) as { c: number }
    ).c;
    res.json({
      document: {
        id: row.id,
        name: row.name,
        category: row.category,
        mimeType: row.mime_type,
        sizeBytes: row.size_bytes,
        createdAt: row.created_at,
        text: row.text_content,
        resume: row.resume_json ? JSON.parse(row.resume_json as string) : undefined,
        chunkCount,
      },
    });
  });

  router.post("/retrieve", (req, res) => {
    const { query, documentIds, topK } = req.body || {};
    if (!query) return res.status(400).json({ error: "query required" });
    let chunks: Array<{ id: string; text: string; embedding?: number[] }> = [];
    if (Array.isArray(documentIds) && documentIds.length) {
      const placeholders = documentIds.map(() => "?").join(",");
      const rows = ctx.db
        .prepare(
          `SELECT c.id, c.text, c.embedding_json FROM document_chunks c
           JOIN documents d ON d.id = c.document_id
           WHERE d.user_id = ? AND c.document_id IN (${placeholders})`
        )
        .all(req.user!.id, ...documentIds) as Array<{ id: string; text: string; embedding_json: string }>;
      chunks = rows.map((r) => ({ id: r.id, text: r.text, embedding: JSON.parse(r.embedding_json || "[]") }));
    } else {
      const rows = ctx.db
        .prepare(
          `SELECT c.id, c.text, c.embedding_json FROM document_chunks c
           JOIN documents d ON d.id = c.document_id WHERE d.user_id = ?`
        )
        .all(req.user!.id) as Array<{ id: string; text: string; embedding_json: string }>;
      chunks = rows.map((r) => ({ id: r.id, text: r.text, embedding: JSON.parse(r.embedding_json || "[]") }));
    }
    const results = retrieveChunks(String(query), chunks, Number(topK) || 5);
    res.json({ results });
  });

  router.delete("/:id", (req, res) => {
    const row = ctx.db
      .prepare("SELECT id FROM documents WHERE id = ? AND user_id = ?")
      .get(req.params.id, req.user!.id);
    if (!row) return res.status(404).json({ error: "Document not found" });
    ctx.db.prepare("DELETE FROM document_chunks WHERE document_id = ?").run(req.params.id);
    ctx.db.prepare("DELETE FROM documents WHERE id = ?").run(req.params.id);
    res.json({ ok: true });
  });

  return router;
}
