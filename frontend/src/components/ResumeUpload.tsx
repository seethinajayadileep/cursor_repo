"use client";

import { FormEvent, useState } from "react";
import { api, getUserId } from "@/lib/api";

export function ResumeUpload() {
  const [status, setStatus] = useState<string | null>(null);
  const [skills, setSkills] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fileInput = form.elements.namedItem("resume") as HTMLInputElement;
    const textInput = form.elements.namedItem("text") as HTMLTextAreaElement;
    const file = fileInput.files?.[0];
    const text = textInput.value.trim();
    if (!file && !text) {
      setStatus("Paste resume text or upload a PDF / TXT file.");
      return;
    }
    setLoading(true);
    setStatus(null);
    try {
      const res = await api.uploadResume(getUserId(), file, text || undefined);
      setSkills(res.skills);
      setStatus(res.message);
      setFileName(file?.name ?? null);
      form.reset();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="space-y-3 rounded-xl border border-white/10 bg-ink-950/40 p-4"
    >
      <div>
        <h3 className="font-display text-lg text-mist">Resume for ranking</h3>
        <p className="text-sm text-ink-300">
          Upload a PDF or paste highlights to personalize AI match scores.
        </p>
      </div>
      <textarea
        name="text"
        rows={4}
        placeholder="Paste resume highlights (optional if uploading PDF)…"
        className="w-full rounded-lg border border-white/10 bg-ink-900/70 px-3 py-2 text-sm text-mist outline-none focus:border-signal/50"
      />
      <input
        name="resume"
        type="file"
        accept=".pdf,.txt,.md,.csv,application/pdf,text/plain"
        onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
        className="block w-full text-sm text-ink-300 file:mr-3 file:rounded-md file:border-0 file:bg-signal/20 file:px-3 file:py-1.5 file:text-signal"
      />
      {fileName && (
        <p className="text-xs text-ink-400">Selected: {fileName}</p>
      )}
      <button
        type="submit"
        disabled={loading}
        className="rounded-lg border border-signal/40 px-4 py-2 text-sm text-signal transition hover:bg-signal/10 disabled:opacity-60"
      >
        {loading ? "Parsing…" : "Save resume"}
      </button>
      {status && <p className="text-sm text-ink-200">{status}</p>}
      {skills.length > 0 && (
        <p className="text-xs text-ink-400">
          Detected: {skills.slice(0, 10).join(", ")}
        </p>
      )}
    </form>
  );
}
