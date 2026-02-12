
function restartSystem() {

  authFetch(`/restart`, {
    method: "POST", // oder PATCH, je nach API
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
    logout()
}

