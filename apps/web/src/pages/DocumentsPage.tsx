import { useEffect, useState } from "react";
import { useAuth } from "../state/auth";
import { api } from "../lib/api";

export function DocumentsPage() {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([]);
  const [category, setCategory] = useState("custom");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    if (!token) return;
    const res = await api.get<{ documents: Array<Record<string, unknown>> }>("/api/documents", token);
    setDocuments(res.documents);
  }

  useEffect(() => {
    void refresh().catch((e) => setError(e.message));
  }, [token]);

  async function onUpload(file: File) {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("category", category);
      await api.post("/api/documents/upload", fd, token);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6 animate-fadeUp">
      <div>
        <h1 className="font-display text-4xl">Documents</h1>
        <p className="mt-2 text-mist">Upload PDF, DOCX, or TXT. Text is extracted, chunked, and embedded for RAG retrieval.</p>
      </div>
      <div className="panel flex flex-wrap items-end gap-3 p-5">
        <div>
          <label className="label" htmlFor="cat">Category</label>
          <select id="cat" className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
            {["resume", "job_description", "company_information", "project_information", "study_material", "sales_material", "custom"].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <input
          type="file"
          accept=".pdf,.docx,.txt,application/pdf,text/plain"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void onUpload(f);
          }}
        />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <ul className="space-y-3">
        {documents.map((d) => (
          <li key={String(d.id)} className="panel flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <div className="font-medium">{String(d.name)}</div>
              <div className="text-xs text-mist">{String(d.category)} · {String(d.mimeType)} · {String(d.sizeBytes)} bytes</div>
              <p className="mt-2 max-w-3xl text-sm text-mist">{String(d.textPreview || "")}</p>
            </div>
            <button
              className="btn-ghost text-danger"
              type="button"
              onClick={async () => {
                await api.delete(`/api/documents/${d.id}`, token);
                await refresh();
              }}
            >
              Delete
            </button>
          </li>
        ))}
        {!documents.length && <li className="text-sm text-mist">No documents yet.</li>}
      </ul>
    </div>
  );
}

export function ResumesPage() {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([]);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (!token) return;
    void api.get<{ documents: Array<Record<string, unknown>> }>("/api/documents", token).then((res) => {
      setDocuments(res.documents.filter((d) => d.category === "resume"));
    });
  }, [token]);

  return (
    <div className="space-y-6 animate-fadeUp">
      <div>
        <h1 className="font-display text-4xl">Resumes</h1>
        <p className="mt-2 text-mist">Upload resumes to build a structured profile used for factual answer grounding.</p>
      </div>
      <div className="panel p-5">
        <input
          type="file"
          accept=".pdf,.docx,.txt,application/pdf,text/plain"
          onChange={async (e) => {
            const f = e.target.files?.[0];
            if (!f || !token) return;
            const fd = new FormData();
            fd.append("file", f);
            fd.append("category", "resume");
            await api.post("/api/documents/upload", fd, token);
            const res = await api.get<{ documents: Array<Record<string, unknown>> }>("/api/documents", token);
            setDocuments(res.documents.filter((d) => d.category === "resume"));
          }}
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ul className="space-y-2">
          {documents.map((d) => (
            <li key={String(d.id)}>
              <button
                type="button"
                className="panel w-full p-4 text-left hover:border-accent/40"
                onClick={async () => {
                  const res = await api.get<{ document: Record<string, unknown> }>(`/api/documents/${d.id}`, token);
                  setSelected(res.document);
                }}
              >
                <div className="font-medium">{String(d.name)}</div>
                <div className="text-xs text-mist">{String(d.createdAt)}</div>
              </button>
            </li>
          ))}
        </ul>
        <div className="panel p-5">
          <h2 className="font-semibold">Resume profile</h2>
          {selected?.resume ? (
            <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs text-mist">{JSON.stringify(selected.resume, null, 2)}</pre>
          ) : (
            <p className="mt-3 text-sm text-mist">Select a resume to inspect extracted skills, experience, and projects.</p>
          )}
        </div>
      </div>
    </div>
  );
}
