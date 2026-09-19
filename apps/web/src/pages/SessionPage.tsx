import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import type { DetectedQuestion, GeneratedAnswer, InterviewSession, TranscriptSegment } from "@interviewpilot/shared";
import { useAuth } from "../state/auth";
import { api } from "../lib/api";

type PipelineState = "idle" | "listening" | "transcribing" | "understanding" | "generating" | "ready" | "error";

export function SessionPage() {
  const { id } = useParams();
  const { token, demoMode } = useAuth();
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [partial, setPartial] = useState("");
  const [pipeline, setPipeline] = useState<PipelineState>("idle");
  const [error, setError] = useState("");
  const [manualQ, setManualQ] = useState("");
  const [streamText, setStreamText] = useState("");
  const [latestAnswer, setLatestAnswer] = useState<GeneratedAnswer | null>(null);
  const [search, setSearch] = useState("");
  const [audioSource, setAudioSource] = useState<"microphone" | "demo">("demo");
  const demoTimer = useRef<number | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const answeringRef = useRef(false);

  const load = useCallback(async () => {
    if (!token || !id) return;
    const res = await api.get<{ session: InterviewSession }>(`/api/sessions/${id}`, token);
    setSession(res.session);
    const last = res.session.answers.at(-1);
    if (last) setLatestAnswer(last);
  }, [token, id]);

  useEffect(() => {
    void load().catch((e) => setError(e.message));
  }, [load]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void (session?.status === "active" ? stopSession() : startSession());
      }
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "c" && latestAnswer) {
        e.preventDefault();
        void navigator.clipboard.writeText(latestAnswer.detailed || latestAnswer.concise || "");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, latestAnswer]);

  async function persist(patch: Partial<InterviewSession> & { status?: string }) {
    if (!token || !id) return;
    const res = await api.patch<{ session: InterviewSession }>(`/api/sessions/${id}`, patch, token);
    setSession(res.session);
    return res.session;
  }

  async function answerQuestion(text: string, category = "general") {
    if (!token || !id || answeringRef.current) return;
    answeringRef.current = true;
    setPipeline("understanding");
    setStreamText("");
    try {
      setPipeline("generating");
      // Prefer non-SSE JSON for reliability in demo; still show progressive UI
      const detect = await api.post<{ question: DetectedQuestion | null }>("/api/ai/detect-question", { text }, token);
      const q = detect.question || {
        id: `q_${Date.now()}`,
        text,
        category: category as DetectedQuestion["category"],
        confidence: 0.5,
        timestamp: new Date().toISOString(),
      };

      const res = await api.post<{ answer: GeneratedAnswer }>(
        "/api/ai/answer",
        { question: text, category: q.category, sessionId: id, responseMode: session?.responseMode, aiMode: session?.aiMode, language: session?.language },
        token
      );

      const answer = { ...res.answer, questionId: q.id };
      const full = answer.detailed || answer.concise || "";
      for (const chunk of full.match(/.{1,18}/g) || []) {
        setStreamText((prev) => prev + chunk);
        await new Promise((r) => setTimeout(r, 12));
      }
      setLatestAnswer(answer);
      setPipeline("ready");

      setSession((prev) => {
        if (!prev) return prev;
        const next = {
          ...prev,
          questions: [...prev.questions, q],
          answers: [...prev.answers, answer],
        };
        void persist({ questions: next.questions, answers: next.answers });
        return next;
      });
    } catch (err) {
      setPipeline("error");
      setError(err instanceof Error ? err.message : "Answer failed");
    } finally {
      answeringRef.current = false;
    }
  }

  async function onFinalSegment(seg: TranscriptSegment) {
    setPartial("");
    setSession((prev) => {
      if (!prev) return prev;
      const transcript = [...prev.transcript, seg];
      void persist({ transcript });
      return { ...prev, transcript };
    });
    setPipeline("transcribing");
    if (seg.speaker === "interviewer" || seg.isQuestion || /\?$|tell me|what is|write |how would|describe /i.test(seg.text)) {
      await answerQuestion(seg.text);
    } else {
      setPipeline("listening");
    }
  }

  function startDemoAudio() {
    const script = [
      { speaker: "interviewer" as const, text: "Tell me about yourself." },
      { speaker: "candidate" as const, text: "I am a data analyst experienced with SQL, Python, and dashboards." },
      { speaker: "interviewer" as const, text: "What is normalization in SQL?" },
      { speaker: "interviewer" as const, text: "Write a Python function to reverse a linked list." },
      { speaker: "interviewer" as const, text: "Tell me about a conflict you handled." },
    ];
    let i = 0;
    const tick = async () => {
      const item = script[i % script.length];
      i += 1;
      const words = item.text.split(" ");
      let built = "";
      for (const w of words) {
        built = built ? `${built} ${w}` : w;
        setPartial(built);
        setPipeline("transcribing");
        await new Promise((r) => setTimeout(r, 90));
      }
      await onFinalSegment({
        id: `seg_${Date.now()}`,
        speaker: item.speaker,
        text: item.text,
        timestamp: new Date().toISOString(),
        confidence: 0.93,
        isQuestion: item.speaker === "interviewer",
      });
    };
    void tick();
    demoTimer.current = window.setInterval(() => void tick(), 9000);
  }

  function startBrowserStt() {
    const SR =
      (window as unknown as { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition;
    if (!SR) {
      setError("Web Speech API unavailable in this browser. DEMO MODE transcript simulation is recommended.");
      setAudioSource("demo");
      startDemoAudio();
      return;
    }
    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = session?.language === "hi" ? "hi-IN" : session?.language === "te" ? "te-IN" : "en-US";
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const r = event.results[i];
        if (r.isFinal) {
          void onFinalSegment({
            id: `seg_${Date.now()}`,
            speaker: "unknown",
            text: r[0].transcript.trim(),
            timestamp: new Date().toISOString(),
            confidence: r[0].confidence,
          });
        } else interim += r[0].transcript;
      }
      if (interim) {
        setPartial(interim);
        setPipeline("transcribing");
      }
    };
    recognition.onerror = () => setError("Speech recognition error — retrying may help, or switch to DEMO MODE.");
    recognition.start();
    recognitionRef.current = recognition;
  }

  async function startSession() {
    setError("");
    await persist({ status: "active" });
    setPipeline("listening");
    if (audioSource === "microphone" && !demoMode) {
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
        startBrowserStt();
      } catch {
        setError("Microphone permission denied. You can continue with DEMO MODE or manual question input.");
        setAudioSource("demo");
        startDemoAudio();
      }
    } else {
      startDemoAudio();
    }
  }

  async function stopSession() {
    if (demoTimer.current) window.clearInterval(demoTimer.current);
    recognitionRef.current?.stop();
    setPartial("");
    setPipeline("idle");
    const ended = await persist({ status: "ended" });
    if (token && id) {
      const summary = await api.post<{ summary: InterviewSession["summary"] }>(
        "/api/ai/summarize",
        { sessionId: id },
        token
      );
      setSession((prev) => (prev ? { ...prev, summary: summary.summary as InterviewSession["summary"] } : prev));
      void ended;
    }
  }

  async function pauseSession() {
    if (demoTimer.current) window.clearInterval(demoTimer.current);
    recognitionRef.current?.stop();
    setPipeline("idle");
    await persist({ status: "paused" });
  }

  const filteredTranscript = useMemo(() => {
    const list = session?.transcript || [];
    if (!search.trim()) return list;
    return list.filter((t) => t.text.toLowerCase().includes(search.toLowerCase()));
  }, [session, search]);

  if (!session) {
    return <div className="text-mist">{error || "Loading session…"}</div>;
  }

  return (
    <div className="space-y-4 animate-fadeUp">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{session.title}</h1>
          <p className="text-sm text-mist">
            {session.sessionType.replace(/_/g, " ")} · {session.jobRole || "General"}
            {session.company ? ` @ ${session.company}` : ""} · {session.language.toUpperCase()}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip">{pipelineLabel(pipeline)}</span>
          {demoMode && <span className="chip border-accent/40 text-accent">DEMO MODE</span>}
          <span className="chip">{session.processingMode.toUpperCase()}</span>
        </div>
      </div>

      <div className="rounded-lg border border-warn/30 bg-warn/10 px-3 py-2 text-xs text-foam/90">
        Browser audio note: microphone works where permitted. Tab/system audio varies by browser. Use DEMO MODE or manual
        input if capture is unavailable. Users must follow interview rules and obtain consent before recording.
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr_0.85fr]">
        <section className="panel flex min-h-[420px] flex-col p-4" aria-label="Live transcript">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="font-semibold">Live transcript</h2>
            <input className="input max-w-[160px] py-1" placeholder="Search" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search transcript" />
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto pr-1">
            {filteredTranscript.map((t) => (
              <div key={t.id} className={`rounded-lg border px-3 py-2 ${t.isQuestion ? "border-accent/40 bg-accent/5" : "border-line/70"}`}>
                <div className="flex justify-between text-[11px] text-mist">
                  <span className="capitalize">{t.speaker}</span>
                  <span>{new Date(t.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="mt-1 text-sm">{t.text}</p>
              </div>
            ))}
            {partial && (
              <div className="rounded-lg border border-dashed border-line px-3 py-2 text-sm text-mist">
                <span className="animate-pulseSoft">Partial:</span> {partial}
              </div>
            )}
            {!filteredTranscript.length && !partial && <p className="text-sm text-mist">Transcript will appear when the session starts.</p>}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button className="btn-ghost" type="button" onClick={() => void persist({ transcript: [] })}>Clear</button>
            <button
              className="btn-ghost"
              type="button"
              onClick={() => void navigator.clipboard.writeText((session.transcript || []).map((t) => `${t.speaker}: ${t.text}`).join("\n"))}
            >
              Copy
            </button>
            <a className="btn-ghost" href={`/api/sessions/${session.id}/export?format=md`} onClick={(e) => { e.preventDefault(); void downloadExport(session.id, token!); }}>Export</a>
          </div>
        </section>

        <section className="panel flex min-h-[420px] flex-col p-4" aria-label="AI answer">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">AI answer</h2>
            <span className="text-xs text-mist">{session.responseMode} · {session.aiMode}</span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {streamText || latestAnswer ? (
              <div className="space-y-4">
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{streamText || latestAnswer?.detailed || latestAnswer?.concise}</p>
                {latestAnswer?.talkingPoints && (
                  <ul className="space-y-1 text-sm text-mist">
                    {latestAnswer.talkingPoints.map((p) => (
                      <li key={p}>• {p}</li>
                    ))}
                  </ul>
                )}
                {latestAnswer?.star && (
                  <div className="rounded-lg border border-line p-3 text-sm">
                    <div><strong>Situation:</strong> {latestAnswer.star.situation}</div>
                    <div className="mt-1"><strong>Task:</strong> {latestAnswer.star.task}</div>
                    <div className="mt-1"><strong>Action:</strong> {latestAnswer.star.action}</div>
                    <div className="mt-1"><strong>Result:</strong> {latestAnswer.star.result}</div>
                  </div>
                )}
                {latestAnswer?.code && (
                  <div className="space-y-2">
                    <div className="text-sm text-mist">{latestAnswer.code.approach}</div>
                    <pre className="overflow-x-auto rounded-lg bg-ink p-3 text-xs"><code>{latestAnswer.code.code}</code></pre>
                    <div className="flex flex-wrap gap-2">
                      <button className="btn-secondary" type="button" onClick={() => void navigator.clipboard.writeText(latestAnswer.code!.code)}>Copy code</button>
                      <button className="btn-ghost" type="button" onClick={() => void codeAction("explain", latestAnswer.code!.code, token!)}>Explain</button>
                      <button className="btn-ghost" type="button" onClick={() => void codeAction("optimize", latestAnswer.code!.code, token!)}>Optimize</button>
                      <button className="btn-ghost" type="button" onClick={() => void answerQuestion(session.questions.at(-1)?.text || "Give alternative approach", "coding")}>Alternative</button>
                    </div>
                    <p className="text-xs text-mist">Complexity: {latestAnswer.code.complexity}</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-mist">Detected questions will stream suggested answers here.</p>
            )}
          </div>
          <div className="mt-3 flex gap-2">
            <button
              className="btn-secondary"
              type="button"
              disabled={!latestAnswer}
              onClick={() => void navigator.clipboard.writeText(latestAnswer?.detailed || latestAnswer?.concise || "")}
            >
              Copy answer
            </button>
          </div>
        </section>

        <section className="panel flex min-h-[420px] flex-col p-4" aria-label="Context">
          <h2 className="mb-3 font-semibold">Context</h2>
          <div className="space-y-3 text-sm text-mist">
            <div>
              <div className="label">Instructions</div>
              <p>{session.instructions || "None"}</p>
            </div>
            <div>
              <div className="label">Job description</div>
              <p className="max-h-32 overflow-y-auto whitespace-pre-wrap">{session.jobDescription || "None"}</p>
            </div>
            <div>
              <div className="label">Documents linked</div>
              <p>{session.documentIds.length} document(s)</p>
            </div>
            <div>
              <div className="label">Questions detected</div>
              <ul className="mt-1 space-y-1">
                {session.questions.slice(-6).map((q) => (
                  <li key={q.id} className="rounded border border-line/70 px-2 py-1 text-foam/90">
                    <span className="chip mr-1">{q.category}</span>
                    {q.text}
                  </li>
                ))}
              </ul>
            </div>
            {session.summary && (
              <div>
                <div className="label">Summary</div>
                <p>{session.summary.summary}</p>
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="panel sticky bottom-3 flex flex-col gap-3 p-4 md:flex-row md:items-center">
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs text-mist">
            Audio
            <select
              className="input ml-2 w-auto py-1"
              value={audioSource}
              onChange={(e) => setAudioSource(e.target.value as "microphone" | "demo")}
              disabled={session.status === "active"}
            >
              <option value="demo">DEMO simulation</option>
              <option value="microphone">Microphone</option>
            </select>
          </label>
          <span className="text-xs text-mist" aria-live="polite">{pipelineLabel(pipeline)}</span>
        </div>
        <div className="flex flex-wrap gap-2 md:ml-auto">
          {session.status !== "active" ? (
            <button className="btn-primary" type="button" onClick={() => void startSession()}>Start</button>
          ) : (
            <>
              <button className="btn-secondary" type="button" onClick={() => void pauseSession()}>Pause</button>
              <button className="btn-secondary" type="button" onClick={() => void stopSession()}>End</button>
            </>
          )}
        </div>
        <form
          className="flex w-full flex-1 gap-2 md:max-w-xl"
          onSubmit={(e) => {
            e.preventDefault();
            if (!manualQ.trim()) return;
            void answerQuestion(manualQ.trim());
            setManualQ("");
          }}
        >
          <input
            className="input"
            placeholder="Type a question manually…"
            value={manualQ}
            onChange={(e) => setManualQ(e.target.value)}
            aria-label="Manual question input"
          />
          <button className="btn-primary" type="submit">Answer</button>
        </form>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
          {error}
          <button className="btn-ghost ml-2" type="button" onClick={() => setError("")}>Dismiss</button>
        </div>
      )}
    </div>
  );
}

function pipelineLabel(s: PipelineState): string {
  switch (s) {
    case "listening":
      return "Listening...";
    case "transcribing":
      return "Transcribing...";
    case "understanding":
      return "Understanding...";
    case "generating":
      return "Generating...";
    case "ready":
      return "Ready";
    case "error":
      return "Error";
    default:
      return "Idle";
  }
}

async function downloadExport(id: string, token: string) {
  const res = await fetch(`/api/sessions/${id}/export?format=md`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const text = await res.text();
  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `session-${id}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

async function codeAction(kind: "explain" | "optimize", code: string, token: string) {
  const path = kind === "explain" ? "/api/ai/code/explain" : "/api/ai/code/optimize";
  const res = await api.post<Record<string, unknown>>(path, { code }, token);
  const text = kind === "explain" ? String(res.explanation || "") : JSON.stringify(res.result, null, 2);
  await navigator.clipboard.writeText(text);
  alert(kind === "explain" ? "Explanation copied to clipboard." : "Optimization suggestion copied to clipboard.");
}
