import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import bcrypt from "bcryptjs";
import dotenv from "dotenv";
import { loadConfig, DEFAULT_SHORTCUTS } from "@interviewpilot/config";
import { createDatabase } from "@interviewpilot/database";
import { parseResume, chunkText, embedText, cleanText } from "@interviewpilot/documents";
import { uid, nowIso } from "@interviewpilot/shared";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../../..");
dotenv.config({ path: path.join(root, ".env") });

const config = loadConfig();
const raw = (config.databaseUrl || "").replace(/^file:/, "");
const dbPath = path.isAbsolute(raw) ? raw : path.resolve(root, raw);
const db = createDatabase(`file:${dbPath}`);

async function main() {
  const email = "demo@interviewpilot.ai";
  const existing = db.prepare("SELECT id FROM users WHERE email = ?").get(email) as { id: string } | undefined;
  let userId = existing?.id;
  if (!userId) {
    userId = uid("user");
    const hash = await bcrypt.hash("demo12345", 12);
    db.prepare(
      "INSERT INTO users (id, email, name, password_hash, plan, created_at) VALUES (?, ?, ?, ?, 'pro', ?)"
    ).run(userId, email, "Demo User", hash, nowIso());
    db.prepare("INSERT INTO settings (user_id, settings_json) VALUES (?, ?)").run(
      userId,
      JSON.stringify({
        theme: "dark",
        language: "en",
        aiProvider: "demo",
        sttProvider: "demo",
        processingMode: "demo",
        responseMode: "balanced",
        aiMode: "interview",
        alwaysOnTop: false,
        compactMode: false,
        analyticsOptIn: false,
        shortcuts: DEFAULT_SHORTCUTS,
      })
    );
    db.prepare(
      "INSERT INTO usage (user_id, stt_seconds, llm_tokens, document_processing, ai_requests, storage_bytes) VALUES (?,0,0,0,0,0)"
    ).run(userId);
  }

  const resumePath = path.join(root, "samples/resumes/sample-data-analyst-resume.txt");
  const jdPath = path.join(root, "samples/job-descriptions/sample-data-analyst-jd.txt");
  const resumeText = cleanText(fs.readFileSync(resumePath, "utf8"));
  const jdText = cleanText(fs.readFileSync(jdPath, "utf8"));

  function upsertDoc(name: string, category: string, text: string) {
    const found = db
      .prepare("SELECT id FROM documents WHERE user_id = ? AND name = ?")
      .get(userId!, name) as { id: string } | undefined;
    if (found) return found.id;
    const id = uid("doc");
    const resumeJson = category === "resume" ? JSON.stringify(parseResume(text)) : null;
    db.prepare(
      `INSERT INTO documents (id, user_id, name, category, mime_type, size_bytes, created_at, text_content, resume_json)
       VALUES (?, ?, ?, ?, 'text/plain', ?, ?, ?, ?)`
    ).run(id, userId, name, category, Buffer.byteLength(text), nowIso(), text, resumeJson);
    chunkText(text).forEach((chunk, index) => {
      db.prepare(
        "INSERT INTO document_chunks (id, document_id, chunk_index, text, embedding_json) VALUES (?, ?, ?, ?, ?)"
      ).run(uid("chunk"), id, index, chunk, JSON.stringify(embedText(chunk)));
    });
    return id;
  }

  const resumeId = upsertDoc("SAMPLE Resume — Data Analyst.txt", "resume", resumeText);
  const jdId = upsertDoc("SAMPLE Job Description — Data Analyst.txt", "job_description", jdText);

  const sessExists = db
    .prepare("SELECT id FROM sessions WHERE user_id = ? AND title LIKE 'SAMPLE%'")
    .get(userId) as { id: string } | undefined;
  if (!sessExists) {
    db.prepare(
      `INSERT INTO sessions (
        id, user_id, title, session_type, job_role, company, job_description, language,
        ai_mode, response_mode, instructions, status, processing_mode, created_at,
        transcript_json, questions_json, answers_json, document_ids_json, resume_id, summary_json
      ) VALUES (?, ?, ?, 'technical_interview', 'Data Analyst', 'SampleCorp', ?, 'en',
        'interview', 'balanced', 'Keep answers concise and conversational.', 'ended', 'demo', ?,
        ?, '[]', '[]', ?, ?, ?)`
    ).run(
      uid("sess"),
      userId,
      "SAMPLE Technical Interview — Data Analyst",
      jdText,
      nowIso(),
      JSON.stringify([
        {
          id: "seg_sample_1",
          speaker: "interviewer",
          text: "What is normalization in SQL?",
          timestamp: nowIso(),
          isQuestion: true,
          questionCategory: "technical",
        },
      ]),
      JSON.stringify([resumeId, jdId]),
      resumeId,
      JSON.stringify({
        summary: "Sample completed technical interview focused on SQL fundamentals.",
        keyPoints: ["SQL normalization", "Resume-aligned answers"],
        decisions: [],
        questions: ["What is normalization in SQL?"],
        actionItems: [],
        importantDates: [],
        peopleMentioned: [],
        followUpTasks: ["Practice Python linked-list reversal"],
      })
    );
  }

  console.log("Seed complete");
  console.log("Demo login: demo@interviewpilot.ai / demo12345");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
