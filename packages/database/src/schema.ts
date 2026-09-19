export const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'free',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  session_type TEXT NOT NULL,
  job_role TEXT,
  company TEXT,
  job_description TEXT,
  language TEXT NOT NULL DEFAULT 'en',
  ai_mode TEXT NOT NULL DEFAULT 'interview',
  response_mode TEXT NOT NULL DEFAULT 'balanced',
  instructions TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  processing_mode TEXT NOT NULL DEFAULT 'demo',
  created_at TEXT NOT NULL,
  started_at TEXT,
  ended_at TEXT,
  duration_sec INTEGER,
  transcript_json TEXT NOT NULL DEFAULT '[]',
  questions_json TEXT NOT NULL DEFAULT '[]',
  answers_json TEXT NOT NULL DEFAULT '[]',
  document_ids_json TEXT NOT NULL DEFAULT '[]',
  resume_id TEXT,
  summary_json TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  text_content TEXT NOT NULL,
  resume_json TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS document_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  embedding_json TEXT,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS settings (
  user_id TEXT PRIMARY KEY,
  settings_json TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS usage (
  user_id TEXT PRIMARY KEY,
  stt_seconds INTEGER NOT NULL DEFAULT 0,
  llm_tokens INTEGER NOT NULL DEFAULT 0,
  document_processing INTEGER NOT NULL DEFAULT 0,
  ai_requests INTEGER NOT NULL DEFAULT 0,
  storage_bytes INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS mock_interviews (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_id TEXT,
  role TEXT NOT NULL,
  company TEXT,
  experience_level TEXT,
  interview_type TEXT,
  language TEXT NOT NULL DEFAULT 'en',
  difficulty TEXT NOT NULL DEFAULT 'medium',
  feedback_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
`;
