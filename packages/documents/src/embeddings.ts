/** Lightweight local bag-of-words embedding for demo / offline RAG. */
export function embedText(text: string, dims = 64): number[] {
  const vec = new Array(dims).fill(0);
  const tokens = text.toLowerCase().match(/[a-z0-9_]+/g) || [];
  for (const tok of tokens) {
    let h = 2166136261;
    for (let i = 0; i < tok.length; i++) {
      h ^= tok.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    const idx = Math.abs(h) % dims;
    vec[idx] += 1;
  }
  const norm = Math.sqrt(vec.reduce((s, v) => s + v * v, 0)) || 1;
  return vec.map((v) => v / norm);
}

export function cosineSimilarity(a: number[], b: number[]): number {
  const n = Math.min(a.length, b.length);
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (let i = 0; i < n; i++) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  return dot / ((Math.sqrt(na) || 1) * (Math.sqrt(nb) || 1));
}

export function retrieveChunks(
  query: string,
  chunks: Array<{ id: string; text: string; embedding?: number[] }>,
  topK = 5
): Array<{ id: string; text: string; score: number }> {
  const q = embedText(query);
  return chunks
    .map((c) => ({
      id: c.id,
      text: c.text,
      score: cosineSimilarity(q, c.embedding || embedText(c.text)),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, topK);
}
