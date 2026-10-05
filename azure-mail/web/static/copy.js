(function () {
  function copyText(text) {
    text = text || "";
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "0";
    ta.style.left = "0";
    ta.style.width = "2em";
    ta.style.height = "2em";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    ta.setSelectionRange(0, text.length);
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
    return Promise.resolve();
  }

  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("[data-copy-text]");
    if (!b) return;
    ev.preventDefault();
    var t = b.getAttribute("data-copy-text") || "";
    copyText(t).then(function () {
      var old = b.getAttribute("data-label") || b.textContent;
      b.setAttribute("data-label", old);
      b.textContent = "Copied";
      setTimeout(function () { b.textContent = old; }, 1500);
    });
  });

  document.addEventListener("focus", function (ev) {
    if (ev.target && ev.target.classList && ev.target.classList.contains("copy-field")) {
      ev.target.select();
    }
  }, true);
})();
