console.log("Dashboard JS geladen");

function formatDuration(seconds) {
  if (!isFinite(seconds) || seconds < 0) return "—";
  const s = Math.floor(seconds);
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const mins = Math.floor((s % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

function formatTime(tsSeconds) {
  if (tsSeconds === null || tsSeconds === undefined) return "—";
  // API liefert vermutlich Unix Sekunden (float)
  const d = new Date(tsSeconds * 1000);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

function setBadge(el, text, type) {
  // type: success | danger | warning | secondary | info | primary
  el.textContent = text;
  el.className = `badge rounded-pill text-bg-${type}`;
}

function renderTasks(tasks) {
  const container = document.getElementById("tasks_container");
  const count = document.getElementById("task_count");

  container.innerHTML = "";
  const list = Array.isArray(tasks) ? tasks : [];
  count.textContent = `${list.length}`;

  if (list.length === 0) {
    const empty = document.createElement("div");
    empty.className = "text-muted small";
    empty.textContent = "Keine Tasks gemeldet";
    container.appendChild(empty);
    return;
  }

  list.forEach(t => {
    const badge = document.createElement("span");
    badge.className = "badge text-bg-light border";
    badge.textContent = t;
    container.appendChild(badge);
  });
}

function getHealth(manual = false) {
  const token = localStorage.getItem("auth_token");

  fetch("/api/service/health", {
    method: "GET",
    headers: { "Authorization": "Bearer " + token }
  })
    .then(res => {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(data => {
      // Elements
      const service_status = document.getElementById("service_status");
      const service_uptime = document.getElementById("service_uptime");
      const last_keepalive = document.getElementById("last_keepalive");
      const last_update = document.getElementById("last_update");

      const okBadge = document.getElementById("service_ok_badge");
      const runningBadge = document.getElementById("service_running_badge");
      const icon = document.getElementById("service_icon");

      const errorBox = document.getElementById("error_box");
      const lastError = document.getElementById("last_error");

      // Data
      const running = !!data.running;
      const ok = !!data.ok;

      // Status text
      service_status.textContent = running ? "Läuft" : "Gestoppt";

      // Badges
      setBadge(okBadge, ok ? "ok" : "not ok", ok ? "success" : "danger");
      setBadge(runningBadge, running ? "running" : "stopped", running ? "success" : "secondary");

      // Icon (optional: setz deine eigenen Bilder)
      // Wenn du nur ein GIF hast, kannst du das auch einfach lassen.
      // icon.src = running ? "/static/assets/icons/running.gif" : "/static/assets/icons/stopped.png";

      // Uptime
      const startedAt = data.started_at; // seconds (float)
      const now = Date.now() / 1000;
      const uptimeSec = (typeof startedAt === "number") ? (now - startedAt) : NaN;
      service_uptime.textContent = formatDuration(uptimeSec);

      // Keepalive
      last_keepalive.textContent = formatTime(data.last_broker_keepalive);

      // Error
      const err = data.last_error;
      if (err && String(err).trim().length > 0) {
        errorBox.classList.remove("d-none");
        lastError.textContent = String(err);
      } else {
        errorBox.classList.add("d-none");
        lastError.textContent = "—";
      }

      // Tasks
      renderTasks(data.tasks);

      // Update timestamp
      last_update.textContent = new Date().toLocaleString();

      if (manual) console.log("[Dashboard] Health updated", data);
    })
    .catch(err => {
      console.log("[Fehler beim Laden der Health]", err);

      // Optional: UI auf Fehler setzen
      const service_status = document.getElementById("service_status");
      const okBadge = document.getElementById("service_ok_badge");
      const runningBadge = document.getElementById("service_running_badge");
      const last_update = document.getElementById("last_update");

      if (service_status) service_status.textContent = "Nicht erreichbar";
      if (okBadge) setBadge(okBadge, "error", "danger");
      if (runningBadge) setBadge(runningBadge, "—", "secondary");
      if (last_update) last_update.textContent = new Date().toLocaleString();
    });
}

// Initial load
getHealth();

// Auto refresh (z.B. alle 5 Sekunden)
setInterval(getHealth, 5000);