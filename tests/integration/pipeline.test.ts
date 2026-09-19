import { describe, expect, it, beforeAll } from "vitest";
import path from "node:path";
import fs from "node:fs";
import bcrypt from "bcryptjs";
import { createDatabase } from "@interviewpilot/database";
import { createAIProvider } from "@interviewpilot/ai";
import { chunkText, cleanText, embedText, parseResume } from "@interviewpilot/documents";
import { uid, nowIso } from "@interviewpilot/shared";

describe("database + auth integration", () => {
  const dbFile = path.resolve("data/sqlite/test-interviewpilot.db");

  beforeAll(() => {
    if (fs.existsSync(dbFile)) fs.unlinkSync(dbFile);
  });

  it("creates user, stores document chunks, and generates demo answer", async () => {
    const db = createDatabase(`file:${dbFile}`);
    const userId = uid("user");
    const hash = await bcrypt.hash("testhash123", 10);
    db.prepare(
      "INSERT INTO users (id, email, name, password_hash, plan, created_at) VALUES (?, ?, ?, ?, 'free', ?)"
    ).run(userId, "test@example.com", "Test", hash, nowIso());

    const resumeText = cleanText(
      fs.readFileSync(path.resolve("samples/resumes/sample-data-analyst-resume.txt"), "utf8")
    );
    const docId = uid("doc");
    const profile = parseResume(resumeText);
    db.prepare(
      `INSERT INTO documents (id, user_id, name, category, mime_type, size_bytes, created_at, text_content, resume_json)
       VALUES (?, ?, ?, 'resume', 'text/plain', ?, ?, ?, ?)`
    ).run(docId, userId, "resume.txt", Buffer.byteLength(resumeText), nowIso(), resumeText, JSON.stringify(profile));

    chunkText(resumeText).forEach((chunk, index) => {
      db.prepare(
        "INSERT INTO document_chunks (id, document_id, chunk_index, text, embedding_json) VALUES (?, ?, ?, ?, ?)"
      ).run(uid("chunk"), docId, index, chunk, JSON.stringify(embedText(chunk)));
    });

    const count = db.prepare("SELECT COUNT(*) as c FROM document_chunks WHERE document_id = ?").get(docId) as {
      c: number;
    };
    expect(count.c).toBeGreaterThan(0);
    expect(profile.skills.length).toBeGreaterThan(0);

    const ai = createAIProvider({ provider: "demo", demoMode: true });
    const answer = await ai.generateAnswer({
      question: "What is normalization in SQL?",
      category: "technical",
      resume: profile,
      retrievedChunks: ["Normalization organizes data to reduce redundancy."],
      recentTranscript: [],
      previousAnswers: [],
      responseMode: "balanced",
      aiMode: "interview",
      language: "en",
    });
    expect(answer.concise.length).toBeGreaterThan(10);
    db.close();
  });
});
