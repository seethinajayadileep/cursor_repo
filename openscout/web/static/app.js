const $ = (id) => document.getElementById(id);

async function loadSample() {
  const response = await fetch("/api/sample-journey");
  const data = await response.json();
  $("journey").value = data.text;
}

$("sample").addEventListener("click", loadSample);

$("run").addEventListener("click", async () => {
  const mode = document.querySelector("input[name=mode]:checked").value;
  $("status").textContent = "Running OpenScout…";
  $("run").disabled = true;
  $("stats").hidden = true;
  $("findings").innerHTML = "";
  $("steps").innerHTML = "";
  $("generated").hidden = true;
  try {
    const started = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: $("url").value.trim(),
        mode,
        journey: $("journey").value,
        max_steps: Number($("max-steps").value) || 18,
      }),
    });
    if (!started.ok) {
      throw new Error(await started.text());
    }
    const { id } = await started.json();
    const job = await poll(id);
    render(job);
  } catch (error) {
    $("status").textContent = String(error);
  } finally {
    $("run").disabled = false;
  }
});

async function poll(id) {
  for (;;) {
    const response = await fetch(`/api/runs/${id}`);
    const job = await response.json();
    if (job.status && job.status !== "running") {
      return job;
    }
    await new Promise((resolve) => setTimeout(resolve, 800));
  }
}

function render(job) {
  if (job.error && !job.report) {
    $("status").textContent = job.error;
    return;
  }
  const report = job.report;
  const summary = report.summary;
  $("status").textContent = `Run ${report.id} finished with status ${report.status}.`;
  $("stats").hidden = false;
  $("stats").innerHTML = [
    stat("Status", report.status, report.status === "passed" ? "ok" : "bad"),
    stat("Steps", `${summary.passed_steps}/${summary.steps}`),
    stat("Findings", String(summary.findings)),
    stat("Critical", String(summary.critical)),
  ].join("");

  $("findings").innerHTML = "<h2>Findings</h2>" + (
    report.findings.length
      ? report.findings.map((finding) => card(finding, report.run_folder, true)).join("")
      : "<p class='muted'>No findings.</p>"
  );
  $("steps").innerHTML = "<h2>Steps</h2>" + report.steps.map((step) => stepCard(step, report.run_folder)).join("");
  if (report.generated_test) {
    $("generated").hidden = false;
    $("generated").textContent = report.generated_test;
  }
}

function stat(label, value, cls) {
  return `<div class="stat"><span>${label}</span><b class="${cls || ""}">${value}</b></div>`;
}

function shot(folder, path) {
  if (!folder || !path) return "";
  return `<img class="thumb" src="/runs/${folder}/${path}" alt="run screenshot" />`;
}

function card(finding, folder) {
  return `<article class="card ${finding.severity}">
    <span class="pill">${finding.severity}</span><strong>${escapeHtml(finding.title)}</strong>
    <p>${escapeHtml(finding.detail)}</p>
    <p class="muted">${escapeHtml(finding.kind)} · ${escapeHtml(finding.url)}</p>
    ${shot(folder, finding.screenshot)}
  </article>`;
}

function stepCard(step, folder) {
  const raw = step.raw || step.action.type;
  return `<article class="card ${step.status === "passed" ? "pass" : "fail"}">
    <span class="pill">${step.status}</span><code>${escapeHtml(raw)}</code>
    <p>${escapeHtml(step.message)}</p>
    ${shot(folder, step.screenshot)}
  </article>`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

loadSample();
