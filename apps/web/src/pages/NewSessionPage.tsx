import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { SESSION_TYPES, SUPPORTED_LANGUAGES } from "@interviewpilot/shared";
import { useAuth } from "../state/auth";
import { api } from "../lib/api";

const steps = [
  "Session type",
  "Role",
  "Company",
  "Job description",
  "Resume",
  "Documents",
  "AI instructions",
  "Language",
];

export function NewSessionPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [step, setStep] = useState(0);
  const [sessionType, setSessionType] = useState(params.get("type") || "job_interview");
  const [jobRole, setJobRole] = useState("Data Analyst");
  const [company, setCompany] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [instructions, setInstructions] = useState("Keep answers concise and conversational.");
  const [language, setLanguage] = useState("en");
  const [aiMode, setAiMode] = useState("interview");
  const [responseMode, setResponseMode] = useState("balanced");
  const [documents, setDocuments] = useState<Array<{ id: string; name: string; category: string }>>([]);
  const [resumeId, setResumeId] = useState<string>("");
  const [docIds, setDocIds] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    void api.get<{ documents: Array<{ id: string; name: string; category: string }> }>("/api/documents", token).then((d) => {
      setDocuments(d.documents);
      const resume = d.documents.find((x) => x.category === "resume");
      if (resume) setResumeId(resume.id);
    });
  }, [token]);

  const resumes = useMemo(() => documents.filter((d) => d.category === "resume"), [documents]);
  const otherDocs = useMemo(() => documents.filter((d) => d.category !== "resume"), [documents]);

  async function upload(file: File, category: string) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("category", category);
    const res = await api.post<{ document: { id: string; name: string; category: string } }>("/api/documents/upload", fd, token);
    setDocuments((prev) => [res.document, ...prev]);
    if (category === "resume") setResumeId(res.document.id);
    else setDocIds((prev) => [...new Set([...prev, res.document.id])]);
    return res.document;
  }

  async function pasteJd() {
    if (!jobDescription.trim() || !token) return;
    const res = await api.post<{ document: { id: string } }>(
      "/api/documents/text",
      { name: "Job Description.txt", category: "job_description", text: jobDescription },
      token
    );
    setDocIds((prev) => [...new Set([...prev, res.document.id])]);
  }

  async function createSession(e?: FormEvent) {
    e?.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      if (jobDescription.trim()) await pasteJd();
      const res = await api.post<{ session: { id: string } }>(
        "/api/sessions",
        {
          sessionType,
          jobRole,
          company,
          jobDescription,
          language,
          aiMode,
          responseMode,
          instructions,
          resumeId: resumeId || undefined,
          documentIds: [...docIds, ...(resumeId ? [resumeId] : [])],
        },
        token
      );
      navigate(`/session/${res.session.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create session");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl animate-fadeUp">
      <h1 className="font-display text-4xl">Create new session</h1>
      <p className="mt-2 text-mist">Step {step + 1} of {steps.length}: {steps[step]}</p>
      <div className="mt-4 flex gap-1" aria-hidden>
        {steps.map((s, i) => (
          <div key={s} className={`h-1 flex-1 rounded ${i <= step ? "bg-accent" : "bg-line"}`} />
        ))}
      </div>

      <form
        className="panel mt-6 space-y-4 p-6"
        onSubmit={(e) => {
          e.preventDefault();
          if (step < steps.length - 1) {
            setStep((s) => s + 1);
            return;
          }
          void createSession();
        }}
      >
        {step === 0 && (
          <div className="grid gap-2 sm:grid-cols-2">
            {SESSION_TYPES.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`rounded-lg border px-3 py-3 text-left text-sm ${sessionType === t.id ? "border-accent bg-accent/10" : "border-line hover:border-accent/40"}`}
                onClick={() => setSessionType(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
        {step === 1 && (
          <div>
            <label className="label" htmlFor="role">Job role</label>
            <input id="role" className="input" value={jobRole} onChange={(e) => setJobRole(e.target.value)} placeholder="Data Analyst" />
          </div>
        )}
        {step === 2 && (
          <div>
            <label className="label" htmlFor="company">Company</label>
            <input id="company" className="input" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Optional" />
          </div>
        )}
        {step === 3 && (
          <div className="space-y-3">
            <label className="label" htmlFor="jd">Job description</label>
            <textarea id="jd" className="input min-h-40" value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} placeholder="Paste JD text" />
            <input
              type="file"
              accept=".pdf,.docx,.txt,application/pdf,text/plain"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                const doc = await upload(f, "job_description");
                setDocIds((prev) => [...new Set([...prev, doc.id])]);
              }}
            />
          </div>
        )}
        {step === 4 && (
          <div className="space-y-3">
            <label className="label">Resume</label>
            <select className="input" value={resumeId} onChange={(e) => setResumeId(e.target.value)}>
              <option value="">Select existing resume</option>
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
            <input
              type="file"
              accept=".pdf,.docx,.txt,application/pdf,text/plain"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (f) await upload(f, "resume");
              }}
            />
          </div>
        )}
        {step === 5 && (
          <div className="space-y-3">
            <label className="label">Additional documents</label>
            <div className="space-y-2">
              {otherDocs.map((d) => (
                <label key={d.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={docIds.includes(d.id)}
                    onChange={(e) =>
                      setDocIds((prev) => (e.target.checked ? [...prev, d.id] : prev.filter((x) => x !== d.id)))
                    }
                  />
                  {d.name} <span className="chip">{d.category}</span>
                </label>
              ))}
            </div>
            <input
              type="file"
              accept=".pdf,.docx,.txt,application/pdf,text/plain"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (f) await upload(f, "custom");
              }}
            />
          </div>
        )}
        {step === 6 && (
          <div className="space-y-3">
            <label className="label" htmlFor="instr">AI instructions</label>
            <textarea id="instr" className="input min-h-28" value={instructions} onChange={(e) => setInstructions(e.target.value)} />
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label">AI mode</label>
                <select className="input" value={aiMode} onChange={(e) => setAiMode(e.target.value)}>
                  {["interview", "coding", "hr", "sales", "meeting", "study"].map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Response mode</label>
                <select className="input" value={responseMode} onChange={(e) => setResponseMode(e.target.value)}>
                  {["fast", "balanced", "detailed"].map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}
        {step === 7 && (
          <div>
            <label className="label">Language</label>
            <select className="input" value={language} onChange={(e) => setLanguage(e.target.value)}>
              {SUPPORTED_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))}
            </select>
            <p className="mt-2 text-xs text-mist">Architecture supports adding more languages without rewriting core flows.</p>
          </div>
        )}

        {error && <p className="text-sm text-danger" role="alert">{error}</p>}

        <div className="flex justify-between gap-3 pt-2">
          <button type="button" className="btn-ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
            Back
          </button>
          <div className="flex gap-2">
            {step < steps.length - 1 && (
              <button type="button" className="btn-ghost" onClick={() => setStep(steps.length - 1)}>
                Skip to end
              </button>
            )}
            {step < steps.length - 1 ? (
              <button type="button" className="btn-primary" onClick={() => setStep((s) => Math.min(steps.length - 1, s + 1))}>
                Continue
              </button>
            ) : (
              <button type="submit" className="btn-primary" disabled={busy}>
                {busy ? "Starting…" : "Start Session"}
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
