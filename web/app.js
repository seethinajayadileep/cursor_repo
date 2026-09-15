const TOKEN_KEY = "cursor-pocket-token";
const MODE_KEY = "cursor-pocket-mode";
const CHAT_KEY = "cursor-pocket-chat";
const state = {
  token: localStorage.getItem(TOKEN_KEY) || "",
  laptop: "",
  workspaces: [],
  jobs: [],
  activeId: "",
  events: [],
  source: null,
  wakeLock: null,
  announced: new Set(),
  healthTimer: 0,
};

const $ = (id) => document.getElementById(id);

const pairScreen = $("pair-screen");
const mainScreen = $("main-screen");
const pairForm = $("pair-form");
const pairError = $("pair-error");
const composer = $("composer");
const savedMode = localStorage.getItem(MODE_KEY);
if (["agent", "cloud", "ask", "plan"].includes(savedMode)) {
  const radio = document.querySelector(`input[name=mode][value="${savedMode}"]`);
  if (radio) radio.checked = true;
}
const banner = $("banner");
const historyEl = $("history");
const logEl = $("log");
const activeEl = $("active");
const followForm = $("follow-form");

function headers(json) {
  const out = {};
  if (json) out["Content-Type"] = "application/json";
  if (state.token) out.Authorization = `Bearer ${state.token}`;
  return out;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { ...headers(Boolean(options.body)), ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || response.statusText);
    error.status = response.status;
    throw error;
  }
  return data;
}

function showBanner(text, ok) {
  banner.hidden = !text;
  banner.textContent = text || "";
  banner.classList.toggle("ok", Boolean(ok));
}

function setPaired(on) {
  pairScreen.hidden = on;
  mainScreen.hidden = !on;
}

pairForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  pairError.hidden = true;
  $("pair-btn").disabled = true;
  try {
    const data = await api("/api/pair", {
      method: "POST",
      body: JSON.stringify({ pin: $("pin").value }),
    });
    state.token = data.token;
    localStorage.setItem(TOKEN_KEY, data.token);
    await boot();
  } catch (err) {
    pairError.hidden = false;
    pairError.textContent = err.message;
  } finally {
    $("pair-btn").disabled = false;
  }
});

$("unpair-btn").addEventListener("click", async () => {
  try {
    await api("/api/unpair", { method: "POST", body: "{}" });
  } catch {
    /* still clear local token */
  }
  localStorage.removeItem(TOKEN_KEY);
  state.token = "";
  closeStream();
  setPaired(false);
});

composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = $("prompt").value.trim();
  if (!prompt) return;
  $("send-btn").disabled = true;
  try {
    const mode = document.querySelector("input[name=mode]:checked").value;
    localStorage.setItem(MODE_KEY, mode);
    const data = await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify({
        prompt,
        workspace: $("workspace").value,
        mode,
        chat: mode === "cloud" ? $("chat").value : "current",
      }),
    });
    $("prompt").value = "";
    maybeNotifyPermission();
    openJob(data.job.id);
    await refreshJobs();
  } catch (err) {
    showBanner(err.message);
  } finally {
    $("send-btn").disabled = false;
  }
});

$("cancel-btn").addEventListener("click", async () => {
  if (!state.activeId) return;
  try {
    await api(`/api/jobs/${state.activeId}/cancel`, { method: "POST", body: "{}" });
  } catch (err) {
    showBanner(err.message);
  }
});

followForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = $("follow-up").value.trim();
  if (!prompt || !state.activeId) return;
  try {
    const data = await api(`/api/jobs/${state.activeId}/follow-up`, {
      method: "POST",
      body: JSON.stringify({ prompt }),
    });
    $("follow-up").value = "";
    openJob(data.job.id);
    await refreshJobs();
  } catch (err) {
    showBanner(err.message);
  }
});

async function boot() {
  try {
    const status = await api("/api/status");
    state.laptop = status.laptop;
    state.workspaces = status.workspaces || [];
    $("laptop-label").textContent = status.laptop || "Laptop";
    const badge = $("mode-badge");
    badge.textContent = status.demo ? "demo" : "live";
    badge.classList.toggle("demo", Boolean(status.demo));
    fillWorkspaces();
    setPaired(true);
    refreshNotifyUi();
    syncChatRow();
    if (status.demo) {
      showBanner("Demo mode: Cursor will not run. On the Mac, Ctrl+C and start Pocket without --demo.");
    } else {
      showBanner("");
    }
    await refreshJobs();
    const running = state.jobs.find((job) => job.status === "running" || job.status === "queued");
    if (running) openJob(running.id);
    pingHealth();
  } catch (err) {
    if (err.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      state.token = "";
      setPaired(false);
      return;
    }
    showBanner(err.message);
    setPaired(Boolean(state.token));
  }
}

function fillWorkspaces() {
  const select = $("workspace");
  select.innerHTML = "";
  for (const item of state.workspaces) {
    const option = document.createElement("option");
    option.value = item.path;
    option.textContent = item.name;
    select.appendChild(option);
  }
}

function currentMode() {
  const radio = document.querySelector("input[name=mode]:checked");
  return radio ? radio.value : "agent";
}

function syncChatRow() {
  const row = $("chat-row");
  if (!row) return;
  const on = currentMode() === "cloud";
  row.hidden = !on;
  if (on) refreshChats().catch(() => {});
}

async function refreshChats() {
  const select = $("chat");
  if (!select) return;
  const previous = select.value || localStorage.getItem(CHAT_KEY) || "current";
  let titles = [];
  try {
    const data = await api("/api/chats");
    titles = (data.chats || []).map((item) => item.title).filter(Boolean);
  } catch {
    titles = [];
  }
  select.innerHTML = "";
  const add = (value, label) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  };
  add("current", "This chat (already open)");
  add("new", "New chat");
  for (const title of titles) {
    add(title, title);
  }
  const allowed = ["current", "new", ...titles];
  select.value = allowed.includes(previous) ? previous : "current";
  localStorage.setItem(CHAT_KEY, select.value);
}

document.querySelectorAll("input[name=mode]").forEach((radio) => {
  radio.addEventListener("change", () => {
    localStorage.setItem(MODE_KEY, currentMode());
    syncChatRow();
  });
});

$("refresh-chats").addEventListener("click", () => {
  refreshChats().catch((err) => showBanner(err.message));
});

$("chat").addEventListener("change", () => {
  localStorage.setItem(CHAT_KEY, $("chat").value);
});

async function refreshJobs() {
  const data = await api("/api/jobs");
  state.jobs = data.jobs || [];
  renderHistory();
}

function renderHistory() {
  historyEl.innerHTML = "";
  const rest = state.jobs.filter((job) => job.id !== state.activeId);
  if (!rest.length) {
    const empty = document.createElement("li");
    empty.className = "hint";
    empty.textContent = "No earlier runs yet.";
    historyEl.appendChild(empty);
    return;
  }
  for (const job of rest) {
    const li = document.createElement("li");
    li.className = "history-item";
    li.innerHTML = `<div><strong>${escapeHtml(job.workspace_name)}</strong><p>${escapeHtml(job.prompt)}</p></div><span class="status-pill ${job.status}">${job.status}</span>`;
    li.addEventListener("click", () => openJob(job.id));
    historyEl.appendChild(li);
  }
}

function openJob(jobId, opts = {}) {
  state.activeId = jobId;
  state.events = [];
  activeEl.hidden = false;
  followForm.hidden = true;
  closeStream();
  const job = state.jobs.find((item) => item.id === jobId);
  $("active-prompt").textContent = job ? job.prompt : "";
  $("active-title").textContent = job ? titleFor(job) : "Run";
  logEl.innerHTML = "";
  const token = encodeURIComponent(state.token);
  const source = new EventSource(`/api/jobs/${jobId}/events?token=${token}`);
  state.source = source;
  source.onmessage = (message) => {
    let payload;
    try {
      payload = JSON.parse(message.data);
    } catch {
      return;
    }
    if (payload.kind === "snapshot" && payload.job) {
      state.events = payload.job.events || [];
      updateActive(payload.job);
      renderLog();
      return;
    }
    if (payload.kind === "end" && payload.job) {
      updateActive(payload.job);
      onTerminal(payload.job);
      closeStream();
      refreshJobs().catch(() => {});
      return;
    }
    pushEvent(payload);
  };
  source.onerror = () => {
    /* browser retries; banner only if we lost the laptop */
  };
  renderHistory();
}

function pushEvent(event) {
  if (event.kind === "assistant") {
    const last = state.events[state.events.length - 1];
    if (last && last.kind === "assistant") {
      if (event.delta) {
        last.text = event.text.startsWith(last.text) ? event.text : last.text + event.text;
      } else {
        last.text = event.text;
      }
      renderLog();
      return;
    }
  }
  state.events.push(event);
  if (event.kind === "status" && event.status) {
    $("active-title").textContent = titleFor({ status: event.status, prompt: $("active-prompt").textContent });
    if (["done", "error", "canceled"].includes(event.status)) {
      const known = state.jobs.find((item) => item.id === state.activeId) || {};
      const job = {
        ...known,
        id: state.activeId,
        status: event.status,
        prompt: $("active-prompt").textContent || known.prompt,
        error: event.text,
      };
      onTerminal(job);
    }
  }
  renderLog();
}

function updateActive(job) {
  $("active-title").textContent = titleFor(job);
  $("active-prompt").textContent = job.prompt || "";
  $("cancel-btn").hidden = ["done", "error", "canceled"].includes(job.status);
  followForm.hidden = !(job.status === "done" && job.session_id);
  if (["running", "queued"].includes(job.status)) keepAwake();
  else releaseAwake();
}

function onTerminal(job, opts = {}) {
  $("cancel-btn").hidden = true;
  followForm.hidden = job.status !== "done";
  releaseAwake();
  refreshJobs().catch(() => {});
  const id = job.id || state.activeId;
  if (!opts.quiet && id && !state.announced.has(id)) {
    state.announced.add(id);
    announce(job);
  }
}

function titleFor(job) {
  if (job.status === "queued") return "Queued on laptop";
  if (job.status === "running") return "Running on laptop";
  if (job.status === "done") return "Finished";
  if (job.status === "canceled") return "Canceled";
  return "Failed";
}

function renderLog() {
  logEl.innerHTML = "";
  for (const event of state.events) {
    if (!event || event.kind === "snapshot") continue;
    const div = document.createElement("div");
    div.className = "item";
    if (event.kind === "tool") div.classList.add("tool");
    if (event.kind === "error" || event.error) div.classList.add("error-line");
    if (event.kind === "result") div.classList.add("result");
    if (event.kind === "changes") div.classList.add("result");
    const kind = document.createElement("div");
    kind.className = "kind";
    kind.textContent = event.kind === "changes" ? "what was fixed" : event.kind || "log";
    const text = document.createElement("div");
    text.textContent = event.text || "";
    div.append(kind, text);
    logEl.appendChild(div);
  }
  logEl.scrollTop = logEl.scrollHeight;
}

function closeStream() {
  if (state.source) {
    state.source.close();
    state.source = null;
  }
}

function announce(job) {
  const notice = noticeFor(job);
  showBanner(notice.ok ? "Cursor finished on the laptop." : job.error || "Run ended.", notice.ok);
  document.title = notice.ok ? "Done · Cursor Pocket" : "Cursor Pocket";
  if (navigator.vibrate) navigator.vibrate(notice.ok ? [40, 30, 80] : [120, 60, 120]);
  playChime(notice.ok);
  const native = window.PocketNative && typeof window.PocketNative.notifyDone === "function";
  if (native) {
    window.PocketNative.notifyDone(notice.title, notice.body);
  } else if ("Notification" in window && Notification.permission === "granted") {
    new Notification(notice.title, {
      body: notice.body,
      tag: job.id || "cursor-pocket",
      icon: "/icons/icon-192.png",
    });
  }
  refreshNotifyUi();
}

function noticeFor(job) {
  const ok = job.status === "done";
  let title = "Cursor finished";
  if (job.status === "canceled") title = "Cursor canceled";
  else if (!ok) title = "Cursor failed";
  else if (job.mode === "cloud") title = "Cloud Agent finished";
  const body = String(job.prompt || job.error || "Done").slice(0, 140);
  return { title, body, ok };
}

function refreshNotifyUi() {
  const btn = $("notify-btn");
  const status = $("notify-status");
  if (!btn || !status) return;
  const nativeOn =
    window.PocketNative &&
    typeof window.PocketNative.notificationsReady === "function" &&
    window.PocketNative.notificationsReady();
  if (nativeOn) {
    btn.hidden = true;
    status.textContent = "Phone alerts are on (Android app). The Mac also banners when a run ends.";
    return;
  }
  if (!("Notification" in window)) {
    btn.hidden = true;
    status.textContent = "This browser cannot show banners. Install the Android APK for lock-screen alerts.";
    return;
  }
  if (Notification.permission === "granted") {
    btn.hidden = true;
    status.textContent = "Notifications on. You’ll get a banner when Cursor or Cloud Agent finishes.";
    return;
  }
  btn.hidden = false;
  if (Notification.permission === "denied") {
    status.textContent = "Notifications blocked. Click Enable, or the lock icon → Site settings → Notifications → Allow. The Android APK always alerts.";
    return;
  }
  status.textContent = "Turn on notifications so you hear when Cloud / Cursor finishes.";
}

$("notify-btn").addEventListener("click", async () => {
  if (!("Notification" in window)) return;
  try {
    await Notification.requestPermission();
  } catch {
    /* some WebViews throw */
  }
  refreshNotifyUi();
});

function maybeNotifyPermission() {
  if (!("Notification" in window)) return;
  if (Notification.permission === "default") Notification.requestPermission().catch(() => {});
}

function playChime(ok) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = ok ? 880 : 220;
    gain.gain.value = 0.04;
    osc.start();
    osc.stop(ctx.currentTime + 0.18);
  } catch {
    /* autoplay may be blocked on some browsers until a gesture; send is a gesture */
  }
}

async function keepAwake() {
  try {
    if (navigator.wakeLock) state.wakeLock = await navigator.wakeLock.request("screen");
  } catch {
    /* not a secure context on plain LAN HTTP */
  }
}

function releaseAwake() {
  try {
    state.wakeLock?.release();
  } catch {
    /* ignore */
  }
  state.wakeLock = null;
}

function pingHealth() {
  if (state.healthTimer) return;
  state.healthTimer = setInterval(async () => {
    try {
      await fetch("/api/health").then((r) => r.json());
    } catch {
      showBanner("Cannot reach the laptop. Is Cursor Pocket still running?");
    }
  }, 8000);
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function registerPwa() {
  const secure = location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (secure && "serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

registerPwa();
showApkDownload();
if (state.token) boot();
else setPaired(false);

function showApkDownload() {
  fetch("/api/health")
    .then((r) => r.json())
    .then((data) => {
      const link = $("apk-link");
      const hint = $("apk-hint");
      if (!link) return;
      const on = Boolean(data && data.apk);
      link.hidden = !on;
      if (hint) hint.hidden = !on;
    })
    .catch(() => {});
}
