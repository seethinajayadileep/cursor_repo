import { extractText, getDocumentProxy } from "unpdf";

export type UploadedResumeFile = {
  buffer: Buffer;
  mimetype?: string;
  originalname?: string;
};

export async function extractResumeText(
  file: UploadedResumeFile | undefined,
  fallbackText = ""
): Promise<{ text: string; source: "pdf" | "text" | "file-text" | "empty" }> {
  const pasted = fallbackText?.trim() ?? "";

  if (!file) {
    return {
      text: pasted,
      source: pasted ? "text" : "empty",
    };
  }

  const mime = (file.mimetype || "").toLowerCase();
  const name = (file.originalname || "").toLowerCase();
  const isPdf = mime.includes("pdf") || name.endsWith(".pdf");

  if (isPdf) {
    try {
      const bytes = new Uint8Array(file.buffer);
      const pdf = await getDocumentProxy(bytes);
      const { text } = await extractText(pdf, { mergePages: true });
      const extracted = String(text || "").replace(/\s+/g, " ").trim();
      if (!extracted) {
        throw new Error(
          "No extractable text in PDF (it may be a scanned image). Paste text instead."
        );
      }
      const combined = pasted ? `${extracted}\n\n${pasted}` : extracted;
      return { text: combined, source: "pdf" };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to parse PDF resume";
      throw new Error(message);
    }
  }

  const decoded = file.buffer.toString("utf8").trim();
  const combined = [decoded, pasted].filter(Boolean).join("\n\n");
  return { text: combined, source: "file-text" };
}
