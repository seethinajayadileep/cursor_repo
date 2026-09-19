import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../state/auth";
import { api } from "../lib/api";

export function DashboardPage() {
  const { token, user, demoMode } = useAuth();
  const [sessions, setSessions] = useState<Array<Record<string, unknown>>>([]);
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([]);
  const [usage, setUsage] = useState<Record<string, number> | null>(null);

  useEffect(() => {
    if (!token) return;
    void (async () => {
      const s = await api.get<{ sessions: Array<Record<string, unknown>> }>("/api/sessions", token);
      const d = await api.get<{ documents: Array<Record<string, unknown>> }>("/api/documents", token);
      const u = await api.get<{ usage: Record<string, number> }>("/api/billing/usage", token);
      setSessions(s.sessions);
      setDocuments(d.documents);
      setUsage(u.usage);
    })();
  }, [token]);

  const stats = [
    ["Sessions completed", sessions.filter((s) => s.status === "ended").length],
    ["Questions answered", sessions.reduce((n, s) => n + ((s.answers as unknown[]) || []).length, 0)],
    ["Documents uploaded", documents.length],
    ["AI requests", usage?.ai_requests ?? 0],
  ];

  return (
    <div className="space-y-8 animate-fadeUp">
      <section>
        <h1 className="font-display text-4xl">Welcome, {user?.name?.split(" ")[0]}</h1>
        <p className="mt-2 text-mist">
          Your real-time copilot for interviews and conversations.
          {demoMode ? " DEMO MODE is active — no paid APIs required." : " Live providers configured."}
        </p>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-mist">Quick actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link className="btn-primary" to="/session/new">New Interview</Link>
          <Link className="btn-secondary" to="/mock-interview">Mock Interview</Link>
          <Link className="btn-secondary" to="/session/new?type=client_meeting">Meeting Assistant</Link>
          <Link className="btn-secondary" to="/resumes">Upload Resume</Link>
          <Link className="btn-secondary" to="/documents">Upload Document</Link>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(([label, value]) => (
          <div key={String(label)} className="panel p-4">
            <div className="text-xs uppercase tracking-wide text-mist">{label}</div>
            <div className="mt-2 text-3xl font-semibold">{value as number}</div>
          </div>
        ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">Recent sessions</h2>
            <Link className="text-sm text-accent" to="/sessions">View all</Link>
          </div>
          <ul className="space-y-3">
            {sessions.slice(0, 5).map((s) => (
              <li key={String(s.id)} className="flex items-center justify-between gap-3 border-b border-line/60 pb-3 last:border-0">
                <div>
                  <Link className="font-medium hover:text-accent" to={`/session/${s.id}`}>{String(s.title)}</Link>
                  <div className="text-xs text-mist">{String(s.sessionType)} · {String(s.status)}</div>
                </div>
                <span className="chip">{String(s.language || "en")}</span>
              </li>
            ))}
            {!sessions.length && <li className="text-sm text-mist">No sessions yet. Start one to see history here.</li>}
          </ul>
        </section>

        <section className="panel p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">Recent documents</h2>
            <Link className="text-sm text-accent" to="/documents">Manage</Link>
          </div>
          <ul className="space-y-3">
            {documents.slice(0, 5).map((d) => (
              <li key={String(d.id)} className="border-b border-line/60 pb-3 last:border-0">
                <div className="font-medium">{String(d.name)}</div>
                <div className="text-xs text-mist">{String(d.category)}</div>
              </li>
            ))}
            {!documents.length && <li className="text-sm text-mist">Upload a resume or job description to personalize answers.</li>}
          </ul>
        </section>
      </div>

      <section className="panel p-5">
        <h2 className="font-semibold">Recommended practice</h2>
        <ul className="mt-3 grid gap-2 md:grid-cols-2">
          {[
            "Tell me about yourself.",
            "What is normalization in SQL?",
            "Write a Python function to reverse a linked list.",
            "Tell me about a conflict you handled.",
            "How would you design a metrics dashboard?",
          ].map((q) => (
            <li key={q} className="rounded-lg border border-line/70 px-3 py-2 text-sm text-mist">{q}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
