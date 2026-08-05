"use client";

interface Props {
  percent: number;
  message: string;
}

const stages = [
  "Queued",
  "Scraping with Apify",
  "Cleaning data",
  "AI ranking",
  "Ready",
];

export function LoadingProgress({ percent, message }: Props) {
  return (
    <div className="animate-rise rounded-2xl border border-signal/20 bg-ink-950/60 p-6 backdrop-blur">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="font-display text-xl text-mist">Scouting openings…</p>
        <span className="text-sm tabular-nums text-signal">{percent}%</span>
      </div>
      <div className="mb-4 h-2 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full origin-left rounded-full bg-gradient-to-r from-signal-dim to-signal transition-all duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="mb-4 text-sm text-ink-200">{message}</p>
      <div className="flex flex-wrap gap-2">
        {stages.map((stage, i) => {
          const active = percent >= (i + 1) * 20;
          return (
            <span
              key={stage}
              className={`rounded-md px-2.5 py-1 text-xs ${
                active
                  ? "bg-signal/15 text-signal"
                  : "bg-white/5 text-ink-400"
              }`}
            >
              {stage}
            </span>
          );
        })}
      </div>
      <div className="mt-5 h-1.5 w-full overflow-hidden rounded-full bg-white/5">
        <div className="h-full w-full origin-left animate-pulse-bar bg-signal/70" />
      </div>
    </div>
  );
}
