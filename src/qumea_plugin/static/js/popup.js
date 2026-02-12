// popup.js
(() => {
  // ---- CSS einmalig injizieren ----
  const styleId = "global-popup-toasts-style";
  if (!document.getElementById(styleId)) {
    const css = `
:root {
  --toast-bg: #1f2937;           /* neutral */
  --toast-fg: #ffffff;
  --toast-success: #0ea5e9;      /* cyan-ish accent for success border */
  --toast-info:    #3b82f6;      /* blue */
  --toast-warn:    #f59e0b;      /* amber */
  --toast-error:   #ef4444;      /* red */
  --toast-radius:  14px;
  --toast-shadow:  0 10px 30px rgba(0,0,0,.25);
  --toast-gap:     12px;
  --toast-maxw:    380px;
  --toast-zi:      99999;
  --toast-progress-h: 3px;
}

#global-popup-container {
  position: fixed;
  top: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: var(--toast-gap);
  z-index: var(--toast-zi);
  pointer-events: none; /* Container lässt Klicks durch, Toasts selbst sind klickbar */
}

.toast {
  pointer-events: auto;
  box-sizing: border-box;
  width: min(92vw, var(--toast-maxw));
  background: var(--toast-bg);
  color: var(--toast-fg);
  border-left: 4px solid var(--toast-info);
  border-radius: var(--toast-radius);
  box-shadow: var(--toast-shadow);
  padding: 12px 14px 12px 14px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px 12px;
  opacity: 0;
  transform: translateY(-8px);
  animation: toast-in .18s ease-out forwards;
}

.toast[data-type="success"] { border-color: var(--toast-success); }
.toast[data-type="info"]    { border-color: var(--toast-info); }
.toast[data-type="warn"]    { border-color: var(--toast-warn); }
.toast[data-type="error"]   { border-color: var(--toast-error); }

.toast__title {
  font-weight: 700;
  font-size: 0.95rem;
  line-height: 1.25rem;
  margin: 0;
}
.toast__msg {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.25rem;
  opacity: .95;
}

.toast__close {
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 1rem;
  line-height: 1;
  padding: 4px;
  margin: -4px -4px 0 0;
  cursor: pointer;
  border-radius: 8px;
}
.toast__close:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

.toast__progress {
  grid-column: 1 / -1;
  height: var(--toast-progress-h);
  background: rgba(255,255,255,.18);
  border-radius: 999px;
  overflow: hidden;
}
.toast__progress > div {
  height: 100%;
  width: 100%;
  transform-origin: left center;
  animation-timing-function: linear;
}

.toast:hover { filter: brightness(1.02); }

@keyframes toast-in {
  to { opacity: 1; transform: translateY(0); }
}
@keyframes toast-out {
  to { opacity: 0; transform: translateY(-8px); }
}

@media (max-width: 480px) {
  #global-popup-container {
    right: 12px;
    left: 12px;
    top: 12px;
    align-items: flex-end;
  }
  .toast {
    width: 100%;
  }
}
    `.trim();
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = css;
    document.head.appendChild(style);
  }

  // ---- Container anlegen (einmalig) ----
  const ensureContainer = () => {
    let c = document.getElementById("global-popup-container");
    if (!c) {
      c = document.createElement("div");
      c.id = "global-popup-container";
      document.body.appendChild(c);
    }
    return c;
  };

  /**
   * ShowPopUp(title, message, options)
   * options:
   * - type: "info" | "success" | "warn" | "error" (default: "info")
   * - timeout: number in ms (default: 4000). Bei important true wird ignoriert.
   * - important: boolean (default: false) -> bleibt stehen bis Klick (kein Timeout)
   * - ariaLive: "polite"|"assertive" (default: automatisch: assertive bei error/warn, sonst polite)
   * - id: string (optional) -> gleiche ID ersetzt bestehenden Toast (praktisch für Statusmeldungen)
   * - showProgress: boolean (default: true wenn timeout gesetzt)
   */
  function ShowPopUp(title, message, options = {}) {
    const {
      type = "info",
      timeout = 4000,
      important = false,
      ariaLive,
      id,
      showProgress
    } = options;

    const container = ensureContainer();

    // Falls id vorhanden: existierenden ersetzen
    if (id) {
      const existing = container.querySelector(`.toast[data-id="${CSS.escape(id)}"]`);
      if (existing) {
        existing.remove(); // ersetzen
      }
    }

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.dataset.type = type;
    if (id) toast.dataset.id = id;

    // ARIA / A11y
    const live = ariaLive ?? (type === "error" || type === "warn" ? "assertive" : "polite");
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", live);
    toast.setAttribute("aria-atomic", "true");

    // Inhalte
    const h = document.createElement("p");
    h.className = "toast__title";
    h.textContent = title ?? (type[0].toUpperCase() + type.slice(1));

    const close = document.createElement("button");
    close.className = "toast__close";
    close.setAttribute("aria-label", "Benachrichtigung schließen");
    close.innerHTML = "✕";

    const p = document.createElement("p");
    p.className = "toast__msg";
    p.textContent = message ?? "";

    // Progress-Bar optional (nur sinnvoll mit Timeout)
    let progressWrap = null;
    let progressBar = null;
    const willAutoClose = !important && typeof timeout === "number" && timeout > 0;
    const wantProgress = showProgress ?? willAutoClose;

    if (wantProgress) {
      progressWrap = document.createElement("div");
      progressWrap.className = "toast__progress";
      progressBar = document.createElement("div");
      progressWrap.appendChild(progressBar);
    }

    toast.appendChild(h);
    toast.appendChild(close);
    toast.appendChild(p);
    if (progressWrap) toast.appendChild(progressWrap);

    // Ins DOM (oben einfügen, neueste zuerst)
    container.prepend(toast);

    // Schließen-Logik
    const removeToast = () => {
      toast.style.animation = "toast-out .14s ease-in forwards";
      const t = setTimeout(() => toast.remove(), 160);
      // Safety: falls mehrfach aufgerufen
      removeToast._tid = t;
    };

    close.addEventListener("click", removeToast);

    // Auto-Close + Progress
    let remaining = willAutoClose ? timeout : null;
    let startTs = null;
    let rafId = null;

    function tick(ts) {
      if (!startTs) startTs = ts;
      const elapsed = ts - startTs;
      const left = Math.max(timeout - elapsed, 0);
      if (progressBar) {
        const pct = Math.max(0, Math.min(1, left / timeout));
        progressBar.style.transform = `scaleX(${pct})`;
      }
      if (left <= 0) {
        cancelAnimationFrame(rafId);
        removeToast();
        return;
      }
      rafId = requestAnimationFrame(tick);
    }

    // Pause/Resume bei Hover
    let paused = false;
    let pauseTs = 0;
    function pause() {
      if (!willAutoClose || paused) return;
      paused = true;
      cancelAnimationFrame(rafId);
      // Zeit berechnen
      const now = performance.now();
      pauseTs = now;
      if (startTs) {
        const elapsed = now - startTs;
        remaining = Math.max(timeout - elapsed, 0);
      }
    }
    function resume() {
      if (!willAutoClose || !paused) return;
      paused = false;
      startTs = performance.now();
      if (typeof remaining === "number") {
        // Neustart mit remaining als neues timeout
        if (progressBar) {
          progressBar.style.transform = `scaleX(${remaining / timeout})`;
        }
        (function animateLeft(left) {
          const base = performance.now();
          function frame(ts) {
            const elapsed = ts - base;
            const leftNow = Math.max(left - elapsed, 0);
            if (progressBar) {
              progressBar.style.transform = `scaleX(${leftNow / timeout})`;
            }
            if (leftNow <= 0) {
              removeToast();
              return;
            }
            rafId = requestAnimationFrame(frame);
          }
          rafId = requestAnimationFrame(frame);
        })(remaining);
      } else {
        rafId = requestAnimationFrame(tick);
      }
    }

    if (willAutoClose) {
      rafId = requestAnimationFrame(tick);
      toast.addEventListener("mouseenter", pause);
      toast.addEventListener("mouseleave", resume);
      // Auf Fokus auch pausieren
      toast.addEventListener("focusin", pause);
      toast.addEventListener("focusout", resume);
    }

    return toast; // falls du später direkt darauf zugreifen möchtest
  }

  // global verfügbar machen
  window.ShowPopUp = ShowPopUp;
})();
