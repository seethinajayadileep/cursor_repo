const form = document.getElementById("form");
const fileInput = document.getElementById("file");
const runBtn = document.getElementById("run");
const statusEl = document.getElementById("status");
const results = document.getElementById("results");
const countsEl = document.getElementById("counts");
const metricsEl = document.getElementById("metrics");
const previewEl = document.getElementById("preview");
const docxLink = document.getElementById("docx");
const reportLink = document.getElementById("report");
const fileLabel = document.querySelector(".file span");

fileInput.addEventListener("change", () => {
  fileLabel.textContent = fileInput.files[0]
    ? fileInput.files[0].name
    : "Choose a PDF or .txt file";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files[0]) return;

  const data = new FormData();
  data.append("file", fileInput.files[0]);

  runBtn.disabled = true;
  statusEl.hidden = false;
  statusEl.textContent = "Extracting and redacting…";
  results.hidden = true;

  try {
    const response = await fetch("/redact", { method: "POST", body: data });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || "Redaction failed");
    }
    const payload = await response.json();
    countsEl.innerHTML = "";
    const counts = payload.counts || {};
    if (!Object.keys(counts).length) {
      countsEl.innerHTML = "<li>No PII detected</li>";
    } else {
      Object.keys(counts)
        .sort()
        .forEach((key) => {
          const li = document.createElement("li");
          li.textContent = `${key}: ${counts[key]}`;
          countsEl.appendChild(li);
        });
    }
    if (payload.metrics) {
      const m = payload.metrics;
      metricsEl.textContent =
        `Eval sample — precision ${m.precision.toFixed(3)}, ` +
        `recall ${m.recall.toFixed(3)}, accuracy ${m.accuracy.toFixed(3)}`;
    } else {
      metricsEl.textContent = "";
    }
    previewEl.textContent = JSON.stringify(payload.mapping_preview, null, 2);
    docxLink.href = `/download/docx/${payload.job_id}`;
    reportLink.href = `/download/report/${payload.job_id}`;
    results.hidden = false;
    statusEl.textContent = "Done.";
  } catch (error) {
    statusEl.textContent = error.message;
  } finally {
    runBtn.disabled = false;
  }
});
