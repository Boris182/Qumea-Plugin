console.log("Dashboard JS geladen");

function getServices() {
  const ofelia3cx_status = document.getElementById("ofelia3cx_status");
  const token = localStorage.getItem("auth_token");
  fetch("/services", {
    method: "GET",
    headers: {
      "Authorization": "Bearer " + token
    }
  })
  .then(res => res.json())
  .then(data => {
    console.log(data.services[0]);
    if (data.services) {
      ofelia3cx_status.textContent = data.services[0].running ? "Läuft" : "Gestoppt";
    }
})
.catch(err => {
  console.log("[Fehler beim Laden der Services]");
});
}



getServices();
