"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { portalApi, setPortalToken } from "@/lib/portalApi";

export default function PortalAuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res =
        mode === "login"
          ? await portalApi.login({ email, password })
          : await portalApi.register({ email, password, name });
      setPortalToken(res.token);
      router.push("/portal/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auth failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-12">
      <p className="text-xs uppercase tracking-[0.2em] text-signal">Private portal</p>
      <h1 className="mt-2 font-display text-4xl text-mist">Scout Portal</h1>
      <p className="mt-2 text-sm text-ink-300">
        Login to manage resume skills, daily job digests, and Telegram alerts.
        Public search stays at{" "}
        <Link href="/" className="text-signal underline-offset-2 hover:underline">
          Discover
        </Link>
        .
      </p>

      <div className="mt-6 inline-flex rounded-full border border-white/10 p-1 text-sm">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={`rounded-full px-4 py-1.5 ${mode === "login" ? "bg-signal text-ink-950" : "text-ink-200"}`}
        >
          Login
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          className={`rounded-full px-4 py-1.5 ${mode === "register" ? "bg-signal text-ink-950" : "text-ink-200"}`}
        >
          Register
        </button>
      </div>

      <form onSubmit={onSubmit} className="mt-6 space-y-3">
        {mode === "register" && (
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name"
            className="w-full rounded-lg border border-white/10 bg-ink-950/60 px-3 py-2 text-sm text-mist outline-none focus:border-signal/40"
          />
        )}
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@email.com"
          className="w-full rounded-lg border border-white/10 bg-ink-950/60 px-3 py-2 text-sm text-mist outline-none focus:border-signal/40"
        />
        <input
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password (min 6)"
          className="w-full rounded-lg border border-white/10 bg-ink-950/60 px-3 py-2 text-sm text-mist outline-none focus:border-signal/40"
        />
        {error && <p className="text-sm text-red-300">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-signal px-4 py-2 text-sm font-semibold text-ink-950 disabled:opacity-60"
        >
          {loading ? "Please wait…" : mode === "login" ? "Login" : "Create account"}
        </button>
      </form>
    </div>
  );
}
