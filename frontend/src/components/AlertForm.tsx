"use client";

import { FormEvent, useState } from "react";
import { api, getUserId } from "@/lib/api";
import type { SearchCriteria } from "@/types";

export function AlertForm({ criteria }: { criteria: SearchCriteria | null }) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!criteria) {
      setMessage("Run a search first.");
      return;
    }
    try {
      const res = (await api.createAlert(getUserId(), email, criteria)) as {
        message: string;
      };
      setMessage(res.message);
      setEmail("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-2 sm:flex-row">
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@company.com"
        className="flex-1 rounded-lg border border-white/10 bg-ink-900/70 px-3 py-2 text-sm text-mist outline-none focus:border-signal/50"
      />
      <button
        type="submit"
        className="rounded-lg border border-white/15 px-4 py-2 text-sm text-ink-200 transition hover:border-signal/40 hover:text-signal"
      >
        Email alerts
      </button>
      {message && (
        <p className="text-xs text-ink-300 sm:absolute sm:mt-12">{message}</p>
      )}
    </form>
  );
}
