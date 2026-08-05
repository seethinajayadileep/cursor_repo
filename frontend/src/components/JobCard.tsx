"use client";

import { useState } from "react";
import clsx from "clsx";
import type { RankedJob } from "@/types";

interface Props {
  job: RankedJob;
  saved?: boolean;
  onToggleSave?: (job: RankedJob) => void;
}

export function JobCard({ job, saved, onToggleSave }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <article className="group animate-rise border-b border-white/10 py-6 transition first:pt-0 last:border-b-0 hover:bg-white/[0.02]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <ScoreBadge score={job.score} />
            <span className="text-xs uppercase tracking-[0.14em] text-ink-300">
              {job.workMode} · {job.employmentType}
            </span>
            {job.postedAt && (
              <span className="text-xs text-ink-400">
                Posted {formatRelative(job.postedAt)}
              </span>
            )}
          </div>
          <h3 className="font-display text-2xl text-mist transition group-hover:text-signal sm:text-[1.7rem]">
            {job.title}
          </h3>
          <p className="mt-1 text-ink-200">
            {job.company}
            <span className="text-ink-400"> · {job.location}</span>
          </p>
          {job.salary && (
            <p className="mt-1 text-sm text-signal-dim">{job.salary}</p>
          )}
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-ink-200">
            {job.reason}
          </p>
        </div>

        <div className="flex shrink-0 flex-row gap-2 sm:flex-col">
          {job.applyUrl && (
            <a
              href={job.applyUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center rounded-lg bg-signal px-4 py-2 text-sm font-semibold text-ink-950 transition hover:bg-signal-glow"
            >
              {job.isExternalApply ? "Apply" : "Apply on LinkedIn"}
            </a>
          )}
          {job.isExternalApply && job.linkedinUrl && (
            <a
              href={job.linkedinUrl}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-white/15 px-4 py-2 text-center text-sm text-ink-200 transition hover:border-signal/40 hover:text-signal"
            >
              LinkedIn
            </a>
          )}
          <button
            type="button"
            onClick={() => onToggleSave?.(job)}
            className={clsx(
              "rounded-lg border px-4 py-2 text-sm transition",
              saved
                ? "border-signal/50 bg-signal/10 text-signal"
                : "border-white/15 text-ink-200 hover:border-signal/40 hover:text-signal"
            )}
          >
            {saved ? "Saved" : "Save"}
          </button>
        </div>
      </div>

      <div className="mt-4 whitespace-pre-line text-sm leading-relaxed text-ink-300">
        {job.summary}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {job.requiredSkills.slice(0, 6).map((skill) => {
          const missing = job.missingSkills.some(
            (m) => m.toLowerCase() === skill.toLowerCase()
          );
          return (
            <span
              key={skill}
              className={clsx(
                "rounded-md px-2 py-1 text-xs",
                missing
                  ? "bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/30"
                  : "bg-white/5 text-ink-200"
              )}
              title={missing ? "Missing from your profile" : "Matched skill"}
            >
              {skill}
              {missing ? " · gap" : ""}
            </span>
          );
        })}
        <span className="rounded-md bg-white/5 px-2 py-1 text-xs text-ink-300">
          Interview: {job.interviewDifficulty}
        </span>
      </div>

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mt-4 text-sm text-signal underline-offset-4 hover:underline"
      >
        {expanded ? "Hide AI coaching" : "Resume tips & details"}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 rounded-xl border border-white/10 bg-ink-950/50 p-4 text-sm text-ink-200">
          <div>
            <p className="mb-1 text-xs uppercase tracking-[0.16em] text-ink-400">
              Resume improvements
            </p>
            <ul className="list-disc space-y-1 pl-5">
              {job.resumeTips.map((tip) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          </div>
          {job.missingSkills.length > 0 && (
            <div>
              <p className="mb-1 text-xs uppercase tracking-[0.16em] text-ink-400">
                Skills to highlight or learn
              </p>
              <p>{job.missingSkills.join(", ")}</p>
            </div>
          )}
          <p className="text-ink-300 line-clamp-6">{job.description}</p>
        </div>
      )}
    </article>
  );
}

function ScoreBadge({ score }: { score: number }) {
  const tone =
    score >= 85
      ? "bg-signal text-ink-950"
      : score >= 70
        ? "bg-signal/20 text-signal"
        : "bg-white/10 text-ink-200";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold tabular-nums",
        tone
      )}
    >
      AI {score}
    </span>
  );
}

function formatRelative(iso: string): string {
  const days = Math.round(
    (Date.now() - new Date(iso).getTime()) / (1000 * 60 * 60 * 24)
  );
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 14) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}
