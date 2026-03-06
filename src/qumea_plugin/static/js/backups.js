function downloadLatestBackup() {
  authFetch("/api/backups/db/download-latest", {
    method: "GET"
  })
    .then(res => {
      if (!res.ok) throw new Error("Download fehlgeschlagen");

      const disposition = res.headers.get("Content-Disposition");
      let filename = "app.db"; // fallback
      const match = disposition && disposition.match(/filename="(.+)"/);
      if (match && match[1]) {
        filename = match[1];
      }

      return res.blob().then(blob => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename; 
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    })
    .catch(err => {
      console.error("Backup-Download fehlgeschlagen:", err);
      alert("Fehler beim Herunterladen des Backups.");
    });
}

async function downloadBackup() {
  try {
    // 1. Passwort abfragen
    const password = prompt("Bitte Passwort für das Backup eingeben:");
    if (!password) {
      alert("Backup abgebrochen – kein Passwort angegeben.");
      return;
    }

    // 2. Anfrage an den Server (POST mit JSON-Body)
    const res = await authFetch("/api/backups/db/backup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ password })
    });

    if (!res.ok) {
      throw new Error(`Serverfehler: ${res.status}`);
    }

    // 3. Dateiname aus dem Header extrahieren
    const disposition = res.headers.get("Content-Disposition");
    let filename = "backup.db.enc";
    const match = disposition && disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }

    // 4. Datei herunterladen
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    console.log("Backup erfolgreich heruntergeladen:", filename);
  } catch (err) {
    console.error("Backup-Download fehlgeschlagen:", err);
    alert("Fehler beim Herunterladen des Backups: " + err.message);
  }
}


async function restoreBackup() {
  const input = document.getElementById("inputDB");
  if (!input || input.files.length === 0) {
    alert("Bitte wählen Sie eine .db oder .db.enc Datei aus.");
    return;
  }

  const file = input.files[0];
  const name = file.name || "";
  const isEncrypted = /\.db\.enc$/i.test(name);

  // Für verschlüsselte Backups Passwort abfragen
  let password = null;
  if (isEncrypted) {
    password = prompt("Passwort für das verschlüsselte Backup eingeben:");
    if (!password) {
      alert("Wiederherstellung abgebrochen – kein Passwort angegeben.");
      input.value = "";
      return;
    }
  } else {
    // Optional: Nur .db erlauben
    if (!/\.db$/i.test(name)) {
      const proceed = confirm("Dateiendung ist nicht .db oder .db.enc. Trotzdem versuchen?");
      if (!proceed) {
        input.value = "";
        return;
      }
    }
  }

  const formData = new FormData();
  formData.append("file", file);
  if (password !== null) {
    // Backend erwartet "password" als Form-Field, wenn .enc hochgeladen wird
    formData.append("password", password);
  }

  try {
    const res = await authFetch("/api/backups/db/restore", {
      method: "POST",
      body: formData
    });

    // Fehlermeldung des Backends möglichst anzeigen
    if (!res.ok) {
      let msg = "Wiederherstellung fehlgeschlagen";
      try {
        const ct = res.headers.get("Content-Type") || "";
        if (ct.includes("application/json")) {
          const data = await res.json();
          if (data?.detail) msg = data.detail;
        } else {
          const text = await res.text();
          if (text) msg = text;
        }
      } catch { /* ignore parsing errors */ }
      throw new Error(msg);
    }

    alert("Datenbank erfolgreich wiederhergestellt. Bitte System neustarten.");
    // Session sauber schließen und zur Login-Seite
    try { await logout(); } catch {}
    window.location.href = "/static/sites/login.html";
  } catch (err) {
    console.error("Fehler bei der Wiederherstellung:", err);
    alert("Fehler beim Wiederherstellen der Datenbank: " + (err?.message || err));
  } finally {
    // File-Input zurücksetzen
    input.value = "";
  }
}

function backupDatabase() {
  authFetch("/api/backups/db/backup", {
    method: "GET"
  })
    .then(res => {
      if (!res.ok) throw new Error("Backup fehlgeschlagen");
      return res.json();
    }).then(data => {
      console.log("Backup Status:", data.status);
      const el = document.getElementById("lastBackup");
      if (el && data.timestamp) {
        el.innerText = "app_backup_" + data.timestamp + ".db";
      }
    })
    .catch(err => console.error("Fehler:", err));
}

function getDatabaseStatus() {
  authFetch("/api/backups/db/status", {
    method: "GET"
  })
    .then(res => {
      if (!res.ok) throw new Error("Backup fehlgeschlagen");
      return res.json();
    }).then(data => {
      console.log("Backup Status:", data);
        document.getElementById("lastBackup").innerText = data.latest_backup;
        document.getElementById("databaseSize").innerText = data.db_size_formatted;
    })
    .catch(err => console.error("Fehler:", err));
}

// CSV Up und Download Buttons mappen
function wireDbButtons() {
  const inputDB = document.getElementById('inputDB');
  if (inputDB) inputDB.addEventListener('change', (e) => restoreBackup(e.target.files?.[0]));
}



getDatabaseStatus();
wireDbButtons();