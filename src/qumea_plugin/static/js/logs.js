

// 1. Letzte 20 Zeilen per HTTP abrufen
function getLogs() {
    const logBox = document.getElementById("logOutput");
const token = localStorage.getItem("auth_token");
    fetch("/api/maintenance/logs", {
  method: "GET",
  headers: {
    "Authorization": "Bearer " + token
  }
})
.then(res => res.json())
.then(data => {
  if (data.logs) {
    logBox.textContent = data.logs.join("\n") + "\n";
    logBox.scrollTop = logBox.scrollHeight;
  }

  // 2. WebSocket starten
  startLogWebSocket();
})
.catch(err => {
  logBox.textContent = "[Fehler beim Laden der Logs]";
});
}
// 3. WebSocket-Stream-Funktion mit Token in URL
function startLogWebSocket() {
    const logBox = document.getElementById("logOutput");
const token = localStorage.getItem("auth_token");
  const ws = new WebSocket("ws://" + location.host + "/ws/logs?token=" + token);

  ws.onmessage = function(event) {
    logBox.textContent += event.data;
    logBox.scrollTop = logBox.scrollHeight;
  };

  ws.onclose = function() {
    logBox.textContent += "\n[Verbindung getrennt]";
  };
}

function updateLogLevel() {
  const selectedLevel = document.getElementById("logLevelInput").value;

  authFetch(`/api/maintenance/setLogLevel/${selectedLevel}`) 
    .then(res => {
      if (!res.ok) throw new Error("Fehler beim Setzen des Log-Levels");
      return res.json();
    })
    .then(data => {
      console.log("Log-Level aktualisiert:", data);
      getlogLevel();
    })
    .catch(err => {
      console.error("Fehler:", err);
    });
}
function getlogLevel() {

  authFetch(`/api/maintenance/getLogLevel`, {
    method: "GET", // oder PATCH, je nach API
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert oder Fehler beim Ändern");
      return res.json();
    })
    .then(data => {
      console.log("Log Level:", data);
      const el = document.getElementById("currentLogLevel");
      if (el && data.logLevel) {
        el.innerText = data.logLevel;
      }
    })
    .catch(err => console.error("Fehler:", err));
}

function downloadLogs() {
  authFetch('/api/maintenance/logsDownload', {
    method: 'GET',
  }).then(response => {
    if (!response.ok) {
      throw new Error('Fehler beim Herunterladen der Logs');
    } return response.blob();
  })
  .then(blob => {
    const url = window.URL.createObjectURL(new Blob([blob]));
    const link = document.createElement('a'); 
    link.href = url;
    link.download = "logs.zip";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  })
  .catch(err => {
    console.error("Fehler beim Herunterladen der Logs:", err);
  });
}

getLogs();
getlogLevel()