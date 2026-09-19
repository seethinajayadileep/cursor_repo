import { useEffect, useState } from "react";
import { useAuth } from "../state/auth";
import { api } from "../lib/api";
import { BILLING_PLANS } from "@interviewpilot/shared";

export function SettingsPage() {
  const { token, demoMode } = useAuth();
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null);
  const [privacy, setPrivacy] = useState<Record<string, unknown> | null>(null);
  const [diag, setDiag] = useState<Record<string, unknown> | null>(null);
  const [section, setSection] = useState("general");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) return;
    void (async () => {
      const s = await api.get<{ settings: Record<string, unknown> }>("/api/settings", token);
      const p = await api.get<Record<string, unknown>>("/api/settings/privacy", token);
      const d = await api.get<Record<string, unknown>>("/api/diagnostics", token);
      setSettings(s.settings);
      setPrivacy(p);
      setDiag(d);
    })();
  }, [token]);

  async function save(patch: Record<string, unknown>) {
    if (!token) return;
    const res = await api.put<{ settings: Record<string, unknown> }>("/api/settings", patch, token);
    setSettings(res.settings);
    setMessage("Settings saved");
  }

  if (!settings) return <div className="text-mist">Loading settings…</div>;

  const nav = ["general", "audio", "speech", "ai", "language", "shortcuts", "privacy", "appearance", "notifications", "account", "diagnostics"];

  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr] animate-fadeUp">
      <aside className="panel h-fit p-3">
        <nav className="flex flex-col gap-1" aria-label="Settings sections">
          {nav.map((n) => (
            <button
              key={n}
              type="button"
              className={`rounded-md px-3 py-2 text-left text-sm capitalize ${section === n ? "bg-white/10 text-foam" : "text-mist hover:text-foam"}`}
              onClick={() => setSection(n)}
            >
              {n}
            </button>
          ))}
        </nav>
      </aside>
      <section className="panel space-y-4 p-6">
        <h1 className="font-display text-3xl capitalize">{section}</h1>
        {message && <p className="text-sm text-accent">{message}</p>}

        {section === "general" && (
          <div className="space-y-3">
            <p className="text-sm text-mist">Processing mode currently: {String(settings.processingMode)} {demoMode ? "(DEMO MODE)" : ""}</p>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(settings.alwaysOnTop)}
                onChange={(e) => void save({ alwaysOnTop: e.target.checked })}
              />
              Always-on-top assistant panel (desktop)
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(settings.compactMode)}
                onChange={(e) => void save({ compactMode: e.target.checked })}
              />
              Compact mode
            </label>
          </div>
        )}

        {section === "audio" && (
          <p className="text-sm text-mist">
            Audio sources are abstracted (microphone, browser/tab, desktop system audio). Capability detection explains
            unsupported paths instead of breaking the session.
          </p>
        )}

        {section === "speech" && (
          <div>
            <label className="label">STT provider</label>
            <select
              className="input max-w-sm"
              value={String(settings.sttProvider)}
              onChange={(e) => void save({ sttProvider: e.target.value })}
            >
              {["demo", "browser", "local", "cloud"].map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        )}

        {section === "ai" && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label">AI provider preference</label>
              <select className="input" value={String(settings.aiProvider)} onChange={(e) => void save({ aiProvider: e.target.value })}>
                {["demo", "openai", "anthropic", "google", "local"].map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Default response mode</label>
              <select className="input" value={String(settings.responseMode)} onChange={(e) => void save({ responseMode: e.target.value })}>
                {["fast", "balanced", "detailed"].map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {section === "language" && (
          <div>
            <label className="label">UI / session language</label>
            <select className="input max-w-sm" value={String(settings.language)} onChange={(e) => void save({ language: e.target.value })}>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="te">Telugu</option>
            </select>
          </div>
        )}

        {section === "shortcuts" && (
          <div className="space-y-2 text-sm">
            {Object.entries((settings.shortcuts as Record<string, string>) || {}).map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-line/60 py-2">
                <span className="capitalize text-mist">{k.replace(/([A-Z])/g, " $1")}</span>
                <code className="text-foam">{v}</code>
              </div>
            ))}
          </div>
        )}

        {section === "privacy" && privacy && (
          <div className="space-y-3 text-sm">
            <p>{String(privacy.notice)}</p>
            <ul className="space-y-1 text-mist">
              <li>AI provider: {String(privacy.aiProvider)}</li>
              <li>Cloud processing: {String(privacy.cloudProcessing)}</li>
              <li>Local processing: {String(privacy.localProcessing)}</li>
              <li>Storage mode: {String(privacy.dataStorageMode)}</li>
            </ul>
            <button
              className="btn-secondary"
              type="button"
              onClick={async () => {
                await api.post("/api/settings/privacy/clear-local", {}, token);
                setMessage("Local session/document data cleared");
              }}
            >
              Clear local data
            </button>
          </div>
        )}

        {section === "appearance" && (
          <div>
            <label className="label">Theme</label>
            <select className="input max-w-sm" value={String(settings.theme)} onChange={(e) => void save({ theme: e.target.value })}>
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="system">System</option>
            </select>
          </div>
        )}

        {section === "notifications" && (
          <p className="text-sm text-mist">Desktop notifications are available in the Electron app for session start/stop events.</p>
        )}

        {section === "account" && (
          <button
            className="btn-secondary text-danger"
            type="button"
            onClick={async () => {
              if (!confirm("Delete account and all data? This cannot be undone.")) return;
              await api.delete("/api/auth/account", token);
              localStorage.removeItem("ip_token");
              window.location.href = "/";
            }}
          >
            Delete account
          </button>
        )}

        {section === "diagnostics" && diag && (
          <pre className="overflow-x-auto rounded-lg bg-ink p-4 text-xs text-mist">{JSON.stringify(diag, null, 2)}</pre>
        )}
      </section>
    </div>
  );
}

export function BillingPage() {
  const { token, user, refresh } = useAuth();
  const [usage, setUsage] = useState<Record<string, unknown> | null>(null);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!token) return;
    void api.get<{ usage: Record<string, unknown>; plan: string }>("/api/billing/usage", token).then(setUsage);
  }, [token]);

  return (
    <div className="space-y-6 animate-fadeUp">
      <div>
        <h1 className="font-display text-4xl">Billing</h1>
        <p className="mt-2 text-mist">Current plan: <strong className="text-foam">{user?.plan}</strong>. Payment providers are configurable; simulator is DEV ONLY.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {BILLING_PLANS.map((plan) => (
          <div key={plan.id} className="panel p-5">
            <div className="font-semibold">{plan.name}</div>
            <div className="mt-1 text-2xl">${plan.priceMonthly}/mo</div>
            <ul className="mt-3 space-y-1 text-sm text-mist">
              {plan.features.map((f) => <li key={f}>• {f}</li>)}
            </ul>
            <button
              className="btn-secondary mt-4"
              type="button"
              onClick={async () => {
                const res = await api.post<{ label: string }>("/api/billing/dev-simulate", { plan: plan.id }, token);
                setNote(res.label);
                await refresh();
              }}
            >
              DEV simulate
            </button>
          </div>
        ))}
      </div>
      {note && <p className="text-sm text-warn">{note}</p>}
      {usage && <pre className="panel overflow-x-auto p-4 text-xs text-mist">{JSON.stringify(usage, null, 2)}</pre>}
    </div>
  );
}

export function HelpPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-4 animate-fadeUp">
      <h1 className="font-display text-4xl">Help</h1>
      <p className="text-mist">
        InterviewPilot AI is a productivity and preparation tool. Some interviews prohibit AI assistance — follow the
        rules of each process. Obtain consent before recording conversations.
      </p>
      <div className="panel space-y-3 p-5 text-sm">
        <p><strong>Demo login after seed:</strong> demo@interviewpilot.ai / demo12345</p>
        <p><strong>Shortcuts:</strong> Ctrl+Shift+S start/stop · Ctrl+Shift+C copy latest answer</p>
        <p><strong>Docs:</strong> see /docs in the repository for architecture, audio, security, and deployment.</p>
      </div>
    </div>
  );
}
