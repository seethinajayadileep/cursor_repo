"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getPortalToken,
  portalApi,
  setPortalToken,
  type PortalMe,
} from "@/lib/portalApi";

export default function PortalDashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<PortalMe | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [prefs, setPrefs] = useState<PortalMe["prefs"] | null>(null);
  const [rolesText, setRolesText] = useState("Software Engineer");
  const [manualSkillsText, setManualSkillsText] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [tgLink, setTgLink] = useState<string | null>(null);
  const [tgToken, setTgToken] = useState<string | null>(null);
  const [chatIdInput, setChatIdInput] = useState("");

  async function load() {
    try {
      const me = await portalApi.me();
      setData(me);
      const normalizedPrefs: PortalMe["prefs"] = {
        ...me.prefs,
        roles:
          me.prefs.roles?.length > 0
            ? me.prefs.roles
            : me.prefs.role
              ? [me.prefs.role]
              : ["Software Engineer"],
        skillsMode: me.prefs.skillsMode === "manual" ? "manual" : "auto",
        manualSkills: me.prefs.manualSkills ?? [],
      };
      setPrefs(normalizedPrefs);
      setRolesText(normalizedPrefs.roles.join(", "));
      setManualSkillsText(normalizedPrefs.manualSkills.join(", "));
      setError(null);
    } catch (err) {
      setPortalToken(null);
      router.replace("/portal");
      setError(err instanceof Error ? err.message : "Session expired");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!getPortalToken()) {
      router.replace("/portal");
      return;
    }
    void load();
  }, [router]);

  async function savePrefs(e: FormEvent) {
    e.preventDefault();
    if (!prefs) return;
    const roles = rolesText
      .split(/[,|\n]/)
      .map((r) => r.trim())
      .filter(Boolean)
      .slice(0, 5);
    if (roles.length === 0) {
      setStatus("Add at least one role");
      return;
    }
    const manualSkills = manualSkillsText
      .split(/[,|\n]/)
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 40);

    setStatus("Saving preferences…");
    try {
      const payload: PortalMe["prefs"] = {
        ...prefs,
        roles,
        role: roles[0],
        skillsMode: prefs.skillsMode,
        manualSkills,
      };
      const res = await portalApi.savePrefs(payload);
      setPrefs(res.prefs);
      setRolesText((res.prefs.roles ?? [res.prefs.role]).join(", "));
      setManualSkillsText((res.prefs.manualSkills ?? []).join(", "));
      setStatus("Preferences saved");
      await load();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Failed");
    }
  }

  async function uploadResume(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const file = (form.elements.namedItem("resume") as HTMLInputElement).files?.[0];
    setStatus("Parsing resume…");
    try {
      const res = await portalApi.uploadResume(file, resumeText || undefined);
      setStatus(res.message);
      setResumeText("");
      form.reset();
      await load();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Upload failed");
    }
  }

  async function connectTelegram() {
    setStatus("Creating Telegram link…");
    try {
      const res = await portalApi.linkTelegram();
      setTgLink(res.deepLink);
      setTgToken(res.token);
      setStatus(res.instructions);
      if (res.deepLink) {
        window.open(res.deepLink, "_blank", "noopener,noreferrer");
      }
      // Poll for successful link after user presses Start
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const me = await portalApi.me();
        if (me.telegram.linked) {
          setData(me);
          setStatus("Telegram connected ✅");
          return;
        }
      }
      setStatus(
        "Still waiting for Start in Telegram. You can also paste your Chat ID below."
      );
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Failed");
    }
  }

  async function connectByChatId(e: FormEvent) {
    e.preventDefault();
    const chatId = chatIdInput.trim();
    if (!chatId) {
      setStatus("Enter your Telegram chat ID");
      return;
    }
    setStatus("Linking Chat ID…");
    try {
      await portalApi.connectChatId(chatId);
      setStatus("Telegram connected via Chat ID ✅");
      setChatIdInput("");
      await load();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Chat ID link failed");
    }
  }

  async function runDigestNow() {
    setStatus("Running digest (may take ~30s)…");
    try {
      const res = await portalApi.runDigest();
      setStatus(
        res.ok
          ? `Digest sent (${res.latest?.jobsSent ?? 0} fresh jobs)`
          : res.latest?.message || "Digest finished with issues"
      );
      await load();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Digest failed");
    }
  }

  function logout() {
    setPortalToken(null);
    router.push("/portal");
  }

  if (loading) {
    return <p className="px-4 py-12 text-ink-300">Loading portal…</p>;
  }

  if (!data || !prefs) {
    return (
      <p className="px-4 py-12 text-red-300">{error || "Unable to load portal"}</p>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-signal">Portal</p>
          <h1 className="font-display text-4xl text-mist">Hi, {data.user.name}</h1>
          <p className="mt-1 text-sm text-ink-300">
            {data.user.email} · Digests at 5:00 AM ({data.schedule.timezone})
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/"
            className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-ink-200 hover:text-signal"
          >
            Public Discover
          </Link>
          <button
            type="button"
            onClick={logout}
            className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-ink-200"
          >
            Logout
          </button>
        </div>
      </div>

      {status && (
        <p className="mt-4 rounded-lg border border-signal/20 bg-signal/10 px-3 py-2 text-sm text-signal">
          {status}
        </p>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        <section className="space-y-3 border-t border-white/10 pt-6">
          <h2 className="font-display text-2xl text-mist">Resume & skills</h2>
          <p className="text-sm text-ink-300">
            Choose auto (from resume) or manual skills for ranking digests.
          </p>
          {data.resume ? (
            <div className="text-sm text-ink-200">
              <p>
                Saved · {data.resume.characters} chars ·{" "}
                {new Date(data.resume.updatedAt).toLocaleString()}
              </p>
              <p className="mt-2 text-xs text-ink-400">
                Resume skills: {data.resume.skills.join(", ") || "none detected"}
              </p>
            </div>
          ) : (
            <p className="text-sm text-ink-400">No resume uploaded yet.</p>
          )}
          <form onSubmit={uploadResume} className="space-y-2">
            <textarea
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              rows={3}
              placeholder="Paste highlights (optional)"
              className="w-full rounded-lg border border-white/10 bg-ink-950/50 px-3 py-2 text-sm text-mist"
            />
            <input
              name="resume"
              type="file"
              accept=".pdf,.txt,.md,application/pdf,text/plain"
              className="block w-full text-sm text-ink-300"
            />
            <button
              type="submit"
              className="rounded-lg border border-signal/40 px-4 py-2 text-sm text-signal"
            >
              Save resume
            </button>
          </form>
        </section>

        <section className="space-y-3 border-t border-white/10 pt-6">
          <h2 className="font-display text-2xl text-mist">Daily search prefs</h2>
          <form onSubmit={savePrefs} className="grid gap-2 sm:grid-cols-2">
            <label className="text-xs text-ink-400 sm:col-span-2">
              Roles (comma-separated, up to 5)
              <input
                value={rolesText}
                onChange={(e) => setRolesText(e.target.value)}
                placeholder="Software Engineer, Backend Developer"
                className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950/50 px-3 py-2 text-sm text-mist"
              />
            </label>
            <label className="text-xs text-ink-400 sm:col-span-2">
              Location
              <input
                value={prefs.location}
                onChange={(e) => setPrefs({ ...prefs, location: e.target.value })}
                className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950/50 px-3 py-2 text-sm text-mist"
              />
            </label>
            <label className="text-xs text-ink-400 sm:col-span-2">
              Skills matching
              <select
                value={prefs.skillsMode}
                onChange={(e) =>
                  setPrefs({
                    ...prefs,
                    skillsMode: e.target.value as "auto" | "manual",
                  })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950/50 px-3 py-2 text-sm text-mist"
              >
                <option value="auto">Auto from resume</option>
                <option value="manual">Manual skills list</option>
              </select>
            </label>
            {prefs.skillsMode === "manual" && (
              <label className="text-xs text-ink-400 sm:col-span-2">
                Manual skills (comma-separated)
                <input
                  value={manualSkillsText}
                  onChange={(e) => setManualSkillsText(e.target.value)}
                  placeholder="React, Node.js, PostgreSQL, TypeScript"
                  className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950/50 px-3 py-2 text-sm text-mist"
                />
              </label>
            )}
            <label className="text-xs text-ink-400">
              Work mode
              <select
                value={prefs.workMode}
                onChange={(e) => setPrefs({ ...prefs, workMode: e.target.value })}
                className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950/50 px-3 py-2 text-sm text-mist"
              >
                <option value="any">Any</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </label>
            <label className="text-xs text-ink-400">
              Top N fresh jobs
              <input
                type="number"
                min={1}
                max={10}
                value={prefs.topN}
                onChange={(e) =>
                  setPrefs({ ...prefs, topN: Number(e.target.value) || 5 })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950/50 px-3 py-2 text-sm text-mist"
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-ink-200 sm:col-span-2">
              <input
                type="checkbox"
                checked={prefs.alertsEnabled}
                onChange={(e) =>
                  setPrefs({ ...prefs, alertsEnabled: e.target.checked })
                }
              />
              Enable 5 AM Telegram digests (skips already-sent jobs)
            </label>
            <button
              type="submit"
              className="rounded-lg bg-signal px-4 py-2 text-sm font-semibold text-ink-950 sm:col-span-2"
            >
              Save preferences
            </button>
          </form>
        </section>

        <section className="space-y-3 border-t border-white/10 pt-6">
          <h2 className="font-display text-2xl text-mist">Telegram</h2>
          <p className="text-sm text-ink-300">
            {data.telegram.linked
              ? `Linked${data.telegram.username ? ` (@${data.telegram.username})` : ""}${data.telegram.chatId ? ` · chat ${data.telegram.chatId}` : ""}`
              : "Not linked yet"}
          </p>
          {!data.telegram.botConfigured && (
            <p className="text-xs text-amber-200">
              Set TELEGRAM_BOT_TOKEN on Railway (username is auto-detected).
            </p>
          )}
          {data.telegram.botUsername && (
            <p className="text-xs text-ink-400">Bot: @{data.telegram.botUsername}</p>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void connectTelegram()}
              className="rounded-lg border border-signal/40 px-4 py-2 text-sm text-signal"
            >
              {data.telegram.linked ? "Relink Telegram" : "Connect Telegram"}
            </button>
            {data.telegram.linked && (
              <button
                type="button"
                onClick={async () => {
                  await portalApi.unlinkTelegram();
                  setStatus("Telegram unlinked");
                  await load();
                }}
                className="rounded-lg border border-white/15 px-4 py-2 text-sm text-ink-200"
              >
                Unlink
              </button>
            )}
            <button
              type="button"
              onClick={() => void runDigestNow()}
              className="rounded-lg border border-white/15 px-4 py-2 text-sm text-ink-200"
            >
              Send test digest now
            </button>
          </div>
          {tgLink && (
            <a
              href={tgLink}
              target="_blank"
              rel="noreferrer"
              className="inline-block text-sm text-signal underline-offset-2 hover:underline"
            >
              Open Telegram bot to confirm →
            </a>
          )}
          {tgToken && !data.telegram.linked && (
            <p className="text-xs text-ink-400">
              Or message the bot:{" "}
              <code className="text-mist">/start {tgToken}</code>
            </p>
          )}
          <form onSubmit={connectByChatId} className="space-y-2 pt-2">
            <p className="text-xs text-ink-400">
              Fallback: get your Chat ID from @userinfobot, then paste it here.
            </p>
            <div className="flex gap-2">
              <input
                value={chatIdInput}
                onChange={(e) => setChatIdInput(e.target.value)}
                placeholder="Telegram chat ID"
                className="min-w-0 flex-1 rounded-lg border border-white/10 bg-ink-950/50 px-3 py-2 text-sm text-mist"
              />
              <button
                type="submit"
                className="rounded-lg border border-white/15 px-3 py-2 text-sm text-ink-200"
              >
                Link ID
              </button>
            </div>
          </form>
        </section>

        <section className="space-y-3 border-t border-white/10 pt-6">
          <h2 className="font-display text-2xl text-mist">Recent digests</h2>
          {data.recentRuns.length === 0 ? (
            <p className="text-sm text-ink-400">No runs yet.</p>
          ) : (
            <ul className="divide-y divide-white/10 text-sm">
              {data.recentRuns.map((run) => (
                <li key={run.id} className="py-3">
                  <p className="text-mist">
                    {new Date(run.ranAt).toLocaleString()} · {run.status} ·{" "}
                    {run.jobsSent} jobs
                  </p>
                  {run.message && (
                    <p className="text-xs text-ink-400">{run.message}</p>
                  )}
                  {run.preview && run.preview.length > 0 && (
                    <p className="mt-1 text-xs text-ink-300">
                      {run.preview
                        .slice(0, 3)
                        .map((j) => `${j.title} @ ${j.company}`)
                        .join(" · ")}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
