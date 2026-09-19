# Documents

Pipeline: Upload → validate → extract (PDF/DOCX/TXT) → clean → chunk → embed → store → retrieve.

Resume category also runs `parseResume` into structured JSON.

Retrieval uses local bag-of-words embeddings for offline/demo RAG; swap for cloud embeddings by extending `packages/documents/src/embeddings.ts`.
