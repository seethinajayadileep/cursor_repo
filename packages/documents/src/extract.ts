import mammoth from "mammoth";

export async function extractTextFromBuffer(
  buffer: Buffer,
  mimeType: string,
  fileName: string
): Promise<string> {
  const lower = fileName.toLowerCase();
  if (mimeType.includes("text") || lower.endsWith(".txt")) {
    return buffer.toString("utf8");
  }
  if (
    mimeType.includes("wordprocessingml") ||
    mimeType.includes("msword") ||
    lower.endsWith(".docx") ||
    lower.endsWith(".doc")
  ) {
    const result = await mammoth.extractRawText({ buffer });
    return result.value || "";
  }
  if (mimeType.includes("pdf") || lower.endsWith(".pdf")) {
    // Dynamic import keeps optional; fall back to latin1 text scrape if parser fails
    try {
      const pdfParse = (await import("pdf-parse")).default as (b: Buffer) => Promise<{ text: string }>;
      const parsed = await pdfParse(buffer);
      return parsed.text || "";
    } catch {
      const raw = buffer.toString("latin1");
      const matches = raw.match(/\((?:\\.|[^\\)])+\)/g) || [];
      const text = matches
        .map((m) => m.slice(1, -1).replace(/\\n/g, "\n").replace(/\\(.)/g, "$1"))
        .join(" ");
      return text.replace(/[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]/g, " ").trim();
    }
  }
  throw new Error(`Unsupported file type: ${mimeType || fileName}`);
}

export function cleanText(text: string): string {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function chunkText(text: string, chunkSize = 800, overlap = 120): string[] {
  const cleaned = cleanText(text);
  if (!cleaned) return [];
  const chunks: string[] = [];
  let i = 0;
  while (i < cleaned.length) {
    const end = Math.min(cleaned.length, i + chunkSize);
    chunks.push(cleaned.slice(i, end));
    if (end >= cleaned.length) break;
    i = Math.max(0, end - overlap);
  }
  return chunks;
}
