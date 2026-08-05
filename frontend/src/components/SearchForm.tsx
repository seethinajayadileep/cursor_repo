"use client";

import { FormEvent, useState } from "react";
import clsx from "clsx";
import type { SearchCriteria } from "@/types";

interface Props {
  loading?: boolean;
  initial?: Partial<SearchCriteria>;
  onSearch: (criteria: SearchCriteria & { naturalLanguage?: string }) => void;
  onNaturalSearch: (query: string) => void;
}

const selectClass =
  "w-full rounded-lg border border-white/10 bg-ink-900/80 px-3 py-2 text-sm text-mist outline-none transition focus:border-signal/50 dark:bg-ink-950/80";

export function SearchForm({
  loading,
  initial,
  onSearch,
  onNaturalSearch,
}: Props) {
  const [role, setRole] = useState(initial?.role ?? "Software Engineer");
  const [location, setLocation] = useState(initial?.location ?? "Remote");
  const [experienceLevel, setExperienceLevel] = useState(
    initial?.experienceLevel ?? "any"
  );
  const [employmentType, setEmploymentType] = useState(
    initial?.employmentType ?? "any"
  );
  const [workMode, setWorkMode] = useState(initial?.workMode ?? "any");
  const [companySize, setCompanySize] = useState(initial?.companySize ?? "any");
  const [salaryMin, setSalaryMin] = useState(
    initial?.salaryMin?.toString() ?? ""
  );
  const [salaryMax, setSalaryMax] = useState(
    initial?.salaryMax?.toString() ?? ""
  );
  const [nlQuery, setNlQuery] = useState(
    initial?.naturalLanguage ??
      "Remote Python jobs in Europe paying over €80k"
  );
  const [showFilters, setShowFilters] = useState(false);
  const [mode, setMode] = useState<"structured" | "natural">("structured");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (mode === "natural") {
      onNaturalSearch(nlQuery.trim());
      return;
    }
    onSearch({
      role: role.trim(),
      location: location.trim(),
      experienceLevel,
      employmentType,
      workMode,
      companySize,
      salaryMin: salaryMin ? Number(salaryMin) : undefined,
      salaryMax: salaryMax ? Number(salaryMax) : undefined,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4">
      <div className="inline-flex rounded-full border border-white/10 bg-ink-950/50 p-1 text-sm">
        <button
          type="button"
          onClick={() => setMode("structured")}
          className={clsx(
            "rounded-full px-4 py-1.5 transition",
            mode === "structured"
              ? "bg-signal text-ink-950"
              : "text-ink-200 hover:text-mist"
          )}
        >
          Role search
        </button>
        <button
          type="button"
          onClick={() => setMode("natural")}
          className={clsx(
            "rounded-full px-4 py-1.5 transition",
            mode === "natural"
              ? "bg-signal text-ink-950"
              : "text-ink-200 hover:text-mist"
          )}
        >
          Natural language
        </button>
      </div>

      {mode === "structured" ? (
        <div className="grid gap-3 sm:grid-cols-[1.2fr_1fr_auto]">
          <label className="block">
            <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-ink-300">
              Job role
            </span>
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              required
              placeholder="Software Engineer"
              className={selectClass}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-ink-300">
              Location
            </span>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Bangalore, Remote, London"
              className={selectClass}
            />
          </label>
          <div className="flex items-end gap-2">
            <button
              type="button"
              onClick={() => setShowFilters((v) => !v)}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-ink-200 transition hover:border-signal/40 hover:text-signal"
            >
              Filters
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-signal px-5 py-2 text-sm font-semibold text-ink-950 transition hover:bg-signal-glow disabled:opacity-60"
            >
              {loading ? "Searching…" : "Find jobs"}
            </button>
          </div>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <label className="block">
            <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-ink-300">
              Describe what you want
            </span>
            <input
              value={nlQuery}
              onChange={(e) => setNlQuery(e.target.value)}
              required
              className={selectClass}
            />
          </label>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-signal px-5 py-2 text-sm font-semibold text-ink-950 transition hover:bg-signal-glow disabled:opacity-60 sm:w-auto"
            >
              {loading ? "Parsing…" : "Search"}
            </button>
          </div>
        </div>
      )}

      {showFilters && mode === "structured" && (
        <div className="grid animate-rise gap-3 rounded-xl border border-white/10 bg-ink-950/40 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <FilterSelect
            label="Experience"
            value={experienceLevel}
            onChange={setExperienceLevel}
            options={[
              ["any", "Any level"],
              ["internship", "Internship"],
              ["entry", "Entry"],
              ["mid", "Mid"],
              ["senior", "Senior"],
              ["lead", "Lead / Staff"],
              ["executive", "Executive"],
            ]}
          />
          <FilterSelect
            label="Employment"
            value={employmentType}
            onChange={setEmploymentType}
            options={[
              ["any", "Any type"],
              ["full-time", "Full-time"],
              ["part-time", "Part-time"],
              ["contract", "Contract"],
              ["internship", "Internship"],
            ]}
          />
          <FilterSelect
            label="Work mode"
            value={workMode}
            onChange={setWorkMode}
            options={[
              ["any", "Any"],
              ["remote", "Remote"],
              ["hybrid", "Hybrid"],
              ["onsite", "Onsite"],
            ]}
          />
          <FilterSelect
            label="Company size"
            value={companySize}
            onChange={setCompanySize}
            options={[
              ["any", "Any size"],
              ["startup", "Startup"],
              ["small", "Small"],
              ["medium", "Medium"],
              ["large", "Large"],
              ["enterprise", "Enterprise"],
            ]}
          />
          <label className="block">
            <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-ink-300">
              Salary min
            </span>
            <input
              type="number"
              min={0}
              value={salaryMin}
              onChange={(e) => setSalaryMin(e.target.value)}
              placeholder="80000"
              className={selectClass}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-ink-300">
              Salary max
            </span>
            <input
              type="number"
              min={0}
              value={salaryMax}
              onChange={(e) => setSalaryMax(e.target.value)}
              placeholder="200000"
              className={selectClass}
            />
          </label>
        </div>
      )}
    </form>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-ink-300">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={selectClass}
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}
