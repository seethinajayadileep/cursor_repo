async function main() {
  const error = document.getElementById("host-error");
  const pin = document.getElementById("host-pin");
  const urlEl = document.getElementById("phone-url");
  const nameEl = document.getElementById("laptop-name");
  const meta = document.getElementById("meta");
  const modeLine = document.getElementById("mode-line");
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
    const lan = (data.urls || []).find((url) => !url.includes("127.0.0.1")) || (data.urls || [])[0];
    const phone = data.online_url || lan;
    urlEl.textContent = phone || "";
    const target = data.demo ? "demo mode" : data.target === "desktop" ? "Cursor desktop" : "Cursor CLI";
    const folders = (data.workspaces || []).map((item) => item.name).join(", ");
    meta.textContent = `${target} · ${folders}`;
    if (modeLine) {
      modeLine.textContent = data.online_url
        ? "Internet URL (phone can be on another network). PIN stays on this laptop page."
        : "LAN URL. For another network, restart with --online.";
    }
    const apk = document.getElementById("apk-link");
    if (apk) apk.hidden = !data.apk;
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
