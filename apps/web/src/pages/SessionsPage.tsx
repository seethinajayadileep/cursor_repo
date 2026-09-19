import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../state/auth";
import { api } from "../lib/api";

export function SessionsPage() {
  const { token } = useAuth();
  const [q, setQ] = useState("");
  const [sessions, setSessions] = useState<Array<Record<string, unknown>>>([]);

  async function refresh(query = q) {
    if (!token) return;
    const res = await api.get<{ sessions: Array<Record<string, unknown>> }>(`/api/sessions?q=${encodeURIComponent(query)}`, token);
    setSessions(res.sessions);
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="space-y-6 animate-fadeUp">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-4xl">Session history</h1>
          <p className="mt-2 text-mist">Search, open, export, or delete past sessions.</p>
        </div>
        <Link className="btn-primary" to="/session/new">New session</Link>
      </div>
      <div className="flex gap-2">
        <input className="input max-w-md" placeholder="Search sessions" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn-secondary" type="button" onClick={() => void refresh()}>Search</button>
      </div>
      <ul className="space-y-3">
        {sessions.map((s) => (
          <li key={String(s.id)} className="panel flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <Link className="font-medium hover:text-accent" to={`/session/${s.id}`}>{String(s.title)}</Link>
              <div className="text-xs text-mist">
                {String(s.sessionType)} · {String(s.status)} · {String(s.createdAt)}
              </div>
            </div>
            <div className="flex gap-2">
              <Link className="btn-ghost" to={`/session/${s.id}`}>Open</Link>
              <button
                className="btn-ghost text-danger"
                type="button"
                onClick={async () => {
                  await api.delete(`/api/sessions/${s.id}`, token);
                  await refresh();
                }}
              >
                Delete
              </button>
            </div>
          </li>
        ))}
        {!sessions.length && <li className="text-sm text-mist">No sessions found.</li>}
      </ul>
    </div>
  );
}
