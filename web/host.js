async function main() {
  const error = document.getElementById("host-error");
  const pin = document.getElementById("host-pin");
  const urlEl = document.getElementById("phone-url");
  const nameEl = document.getElementById("laptop-name");
  const meta = document.getElementById("meta");
  try {
    const response = await fetch("/api/host");
    const data = await response.json();
    if (!response.ok) {
      error.hidden = false;
      error.textContent = data.error || "Open this page on the laptop (localhost).";
      return;
    }
    pin.textContent = data.pin;
    nameEl.textContent = data.laptop || "";
    const phone = (data.urls || []).find((url) => !url.includes("127.0.0.1")) || (data.urls || [])[0];
    urlEl.textContent = phone || "";
    const demo = data.demo ? "demo mode" : "live Cursor CLI";
    const folders = (data.workspaces || []).map((item) => item.name).join(", ");
    meta.textContent = `${demo} · ${folders}`;
    if (phone && window.QRCode) {
      const mount = document.getElementById("qr");
      mount.innerHTML = "";
      new QRCode(mount, {
        text: phone,
        width: 192,
        height: 192,
        colorDark: "#111111",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.M,
      });
    }
  } catch (err) {
    error.hidden = false;
    error.textContent = err.message;
  }
}

main();
