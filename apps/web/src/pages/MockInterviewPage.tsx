import { FormEvent, useState } from "react";
import { useAuth } from "../state/auth";
import { api } from "../lib/api";

export function MockInterviewPage() {
  const { token } = useAuth();
  const [role, setRole] = useState("Data Analyst");
  const [company, setCompany] = useState("SampleCorp");
  const [difficulty, setDifficulty] = useState("medium");
  const [mockId, setMockId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState<Record<string, unknown> | null>(null);
  const [finalFeedback, setFinalFeedback] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function start(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.post<{ mock: { id: string; question: string } }>("/api/mock/start", { role, company, difficulty }, token);
      setMockId(res.mock.id);
      setQuestion(res.mock.question);
      setEvaluation(null);
      setFinalFeedback(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start mock");
    } finally {
      setBusy(false);
    }
  }

  async function submitAnswer(e: FormEvent) {
    e.preventDefault();
    if (!token || !mockId) return;
    setBusy(true);
    try {
      const res = await api.post<{ evaluation: Record<string, unknown>; nextQuestion: string }>(
        `/api/mock/${mockId}/answer`,
        { question, answer },
        token
      );
      setEvaluation(res.evaluation);
      setQuestion(res.nextQuestion);
      setAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    if (!token || !mockId) return;
    const res = await api.post<{ feedback: Record<string, unknown>; overall: string }>(`/api/mock/${mockId}/finish`, {}, token);
    setFinalFeedback({ ...res.feedback, overall: res.overall });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-fadeUp">
      <div>
        <h1 className="font-display text-4xl">Mock interview</h1>
        <p className="mt-2 text-mist">
          Practice with constructive feedback. This is not a prediction of real interview performance.
        </p>
      </div>

      {!mockId ? (
        <form className="panel space-y-4 p-6" onSubmit={start}>
          <div>
            <label className="label" htmlFor="role">Role</label>
            <input id="role" className="input" value={role} onChange={(e) => setRole(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="company">Company</label>
            <input id="company" className="input" value={company} onChange={(e) => setCompany(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="diff">Difficulty</label>
            <select id="diff" className="input" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
          <button className="btn-primary" disabled={busy}>{busy ? "Starting…" : "Start mock interview"}</button>
        </form>
      ) : (
        <div className="space-y-4">
          <div className="panel p-5">
            <div className="text-xs uppercase tracking-wide text-mist">Interviewer</div>
            <p className="mt-2 text-lg font-medium">{question}</p>
          </div>
          <form className="panel space-y-3 p-5" onSubmit={submitAnswer}>
            <label className="label" htmlFor="answer">Your answer</label>
            <textarea id="answer" className="input min-h-36" value={answer} onChange={(e) => setAnswer(e.target.value)} required />
            <div className="flex flex-wrap gap-2">
              <button className="btn-primary" disabled={busy}>Submit answer</button>
              <button className="btn-secondary" type="button" onClick={() => void finish()}>Finish & review</button>
            </div>
          </form>
          {evaluation && (
            <div className="panel space-y-2 p-5 text-sm">
              <h2 className="font-semibold">Practice feedback</h2>
              <pre className="overflow-x-auto whitespace-pre-wrap text-mist">{JSON.stringify(evaluation, null, 2)}</pre>
            </div>
          )}
          {finalFeedback && (
            <div className="panel space-y-2 p-5 text-sm">
              <h2 className="font-semibold">Session review</h2>
              <p className="text-mist">{String(finalFeedback.overall || "")}</p>
              <pre className="overflow-x-auto whitespace-pre-wrap text-mist">{JSON.stringify(finalFeedback, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}
