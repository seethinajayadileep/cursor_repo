import { Link } from "react-router-dom";
import { LogoMark } from "../components/AppShell";
import { BILLING_PLANS } from "@interviewpilot/shared";

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5">
        <div className="flex items-center gap-3">
          <LogoMark />
          <div>
            <div className="font-semibold">InterviewPilot AI</div>
            <div className="text-xs text-mist">Real-time interview & meeting copilot</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link className="btn-ghost" to="/login">
            Log in
          </Link>
          <Link className="btn-primary" to="/signup">
            Start Free
          </Link>
        </div>
      </header>

      <section className="relative mx-auto grid max-w-6xl gap-10 px-4 pb-16 pt-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div className="animate-fadeUp">
          <p className="mb-3 font-display text-5xl leading-none text-foam md:text-6xl lg:text-7xl">InterviewPilot AI</p>
          <h1 className="max-w-xl text-2xl font-semibold text-foam/95 md:text-3xl">
            Think clearly. Answer confidently. In real time.
          </h1>
          <p className="mt-4 max-w-xl text-base text-mist">
            InterviewPilot AI listens, understands your conversation, and helps you prepare better answers using your
            resume, job description, and knowledge base.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link className="btn-primary" to="/signup">
              Start Free
            </Link>
            <Link className="btn-secondary" to="/signup">
              Try Mock Interview
            </Link>
          </div>
          <p className="mt-5 max-w-xl text-xs text-mist/80">
            Practice and productivity tool — not a guarantee of interview outcomes. Some interviews prohibit AI
            assistance; follow platform rules and obtain consent before recording.
          </p>
        </div>
        <div
          className="relative min-h-[320px] overflow-hidden rounded-2xl border border-line bg-[radial-gradient(circle_at_30%_20%,rgba(61,220,151,0.25),transparent_45%),radial-gradient(circle_at_80%_60%,rgba(76,141,255,0.28),transparent_40%),linear-gradient(160deg,#101827,#0b1220)] p-6 shadow-glow animate-fadeUp"
          aria-hidden="true"
        >
          <div className="absolute inset-0 opacity-40" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 30h60M30 0v60' stroke='%23243049' stroke-width='1'/%3E%3C/svg%3E\")" }} />
          <div className="relative space-y-3">
            <div className="chip">Live session</div>
            <div className="panel p-4">
              <div className="text-xs text-mist">Interviewer</div>
              <p className="mt-1 text-sm">What is normalization in SQL?</p>
            </div>
            <div className="panel border-accent/30 p-4">
              <div className="flex items-center justify-between text-xs text-accent">
                <span>Suggested answer</span>
                <span className="animate-pulseSoft">Ready</span>
              </div>
              <p className="mt-2 text-sm leading-relaxed">
                Normalization organizes relational data to reduce redundancy — starting with first normal form and
                building toward clearer dependencies…
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-line/70 bg-panel/40 py-16">
        <div className="mx-auto max-w-6xl px-4">
          <h2 className="font-display text-4xl">Built for real conversations</h2>
          <p className="mt-2 max-w-2xl text-mist">One purpose per capability — fast feedback when you need it.</p>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Real-time transcription", "Partial and final transcripts with timestamps."],
              ["AI answer assistance", "Resume-aware suggestions streamed as you go."],
              ["Resume intelligence", "Structured profile extraction — no invented experience."],
              ["Coding support", "Approach, code, complexity, and edge cases."],
              ["Mock interviews", "Practice with feedback for preparation — not predictions."],
              ["AI meeting notes", "Summaries, decisions, and action items."],
              ["Document knowledge", "RAG over your PDF, DOCX, and TXT uploads."],
              ["Multilingual architecture", "English, Hindi, Telugu to start — expandable."],
            ].map(([title, body]) => (
              <div key={title} className="border-l border-accent/30 pl-4">
                <h3 className="font-semibold">{title}</h3>
                <p className="mt-2 text-sm text-mist">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="font-display text-4xl">Pricing</h2>
        <p className="mt-2 text-mist">Placeholder plans until a payment provider is configured.</p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {BILLING_PLANS.map((plan) => (
            <div key={plan.id} className="panel p-5">
              <div className="text-sm uppercase tracking-wide text-mist">{plan.name}</div>
              <div className="mt-2 text-3xl font-semibold">${plan.priceMonthly}<span className="text-base text-mist">/mo</span></div>
              <ul className="mt-4 space-y-2 text-sm text-mist">
                {plan.features.map((f) => (
                  <li key={f}>• {f}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-line/70 py-16">
        <div className="mx-auto max-w-6xl px-4">
          <h2 className="font-display text-4xl">FAQ</h2>
          <div className="mt-6 space-y-4">
            {[
              ["Does this guarantee interview success?", "No. InterviewPilot AI is a preparation and productivity assistant, not a guarantee of outcomes or accuracy."],
              ["Can I use it without API keys?", "Yes. DEMO MODE simulates transcription, question detection, and answers so you can explore the product immediately."],
              ["Is audio recorded secretly?", "No. Capture requires explicit user action and visible controls. You can delete sessions, documents, and your account."],
              ["Web vs desktop audio?", "Browsers differ in tab/system audio support. The web app explains limitations; the desktop app adds tray, shortcuts, and optional system-audio paths where the OS allows."],
            ].map(([q, a]) => (
              <details key={q} className="panel p-4">
                <summary className="cursor-pointer font-medium">{q}</summary>
                <p className="mt-2 text-sm text-mist">{a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="font-display text-4xl">Privacy</h2>
        <p className="mt-3 max-w-3xl text-mist">
          You control microphone access, uploads, and screenshot context. We do not secretly record audio or capture
          screens. Prefer local/demo processing when credentials are not configured. Delete data anytime from Settings →
          Privacy.
        </p>
      </section>

      <footer className="border-t border-line/70 py-10">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 text-sm text-mist md:flex-row md:items-center md:justify-between">
          <div>
            <div className="font-semibold text-foam">InterviewPilot AI</div>
            <div>Your real-time AI copilot for interviews, meetings and technical conversations.</div>
          </div>
          <div className="flex gap-4">
            <Link to="/help">Help</Link>
            <Link to="/login">Log in</Link>
            <Link to="/signup">Sign up</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
