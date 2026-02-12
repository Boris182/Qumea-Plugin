// settings.js
window.pageInit = function () {
  const btn = document.getElementById('btn-save');
  if (btn) {
    btn.addEventListener('click', () => {
      alert("Einstellungen gespeichert!");
    });
  }
};

function save_ofelia_3cx_settings() {
  const service_name = document.getElementById("ofelia_3cx_service_name").value;
  const service_type = document.getElementById("ofelia_3cx_service_type").value;
  const service_enabled = document.getElementById("ofelia_3cx_service_enabled").checked;
  const ofelia_base_url = document.getElementById("ofelia_base_url").value;
  const ofelia_number_regex = document.getElementById("ofelia_number_regex").value;
  const ofelia_medias_path = document.getElementById("ofelia_medias_path").value;
  const threecx_base_url = document.getElementById("threecx_base_url").value;
  const poll_intervall_seconds = document.getElementById("poll_intervall_seconds").value;
  const timeout_seconds = document.getElementById("timeout_seconds").value;


  const updatedServiceData = {
    name: service_name,
    type: service_type,
    enabled: service_enabled,
    config: {
      ofelia_base_url: ofelia_base_url,
      ofelia_number_regex: ofelia_number_regex,
      ofelia_medias_path: ofelia_medias_path,
      threecx_base_url: threecx_base_url,
      poll_intervall_seconds: parseInt(poll_intervall_seconds),
      timeout_seconds: parseInt(timeout_seconds)
    }
  };
  console.log("Speichere Service Einstellungen:", updatedServiceData);
  changeOfelia3cxConfig(service_name, updatedServiceData);


}

function changeOfelia3cxConfig(service_name, updated_config) {
  const token = localStorage.getItem('auth_token');

  authFetch(`/services/ofelia3cx/${service_name}/config`, {
    method: "PUT", 
    body: JSON.stringify(updated_config)
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert oder Fehler beim Ändern");
      return res.json();
    })
    .then(data => {
      console.log("Config Aktualisiert", data);
      get_ofelia_3cx_settings(); // Aktualisieren
    })
    .catch(err => console.error("Fehler:", err));
}

function get_ofelia_3cx_settings() {
  authFetch("/services/ofelia3cx/ofelia_3cx/config", {
    method: "GET"
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Laden der Einstellungen");
      return res.json();
    }).then(data => {
      console.log("Service Daten:", data);
        document.getElementById("ofelia_3cx_service_name").value = data.name;
        document.getElementById("ofelia_3cx_service_type").value = data.type;
        document.getElementById("ofelia_3cx_service_enabled").checked = data.enabled;
        document.getElementById("ofelia_base_url").value = data.config.ofelia_base_url || "";
        document.getElementById("ofelia_number_regex").value = data.config.ofelia_number_regex || "";
        document.getElementById("ofelia_medias_path").value = data.config.ofelia_medias_path || "";
        document.getElementById("threecx_base_url").value = data.config.threecx_base_url || "";
        document.getElementById("timeout_seconds").value = data.config.timeout_seconds || "";
        document.getElementById("poll_intervall_seconds").value = data.config.poll_intervall_seconds || "";
        

        const status_label = document.querySelector('label[for="ofelia_3cx_service_enabled"]');

        if (data.enabled) {
          status_label.textContent = "Aktiviert";
        } else {
          status_label.textContent = "Deaktiviert";
        } 
    })
    .catch(err => console.error("Fehler:", err));

}

get_ofelia_3cx_settings();