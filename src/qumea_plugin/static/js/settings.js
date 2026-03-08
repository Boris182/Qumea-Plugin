// settings.js
function get_events_to_handle() {
  const checkboxes = document.querySelectorAll("input.event-type[type='checkbox']");
  const events = {};

  checkboxes.forEach(checkbox => {
    events[checkbox.value] = checkbox.checked;
  });

  console.log("Events to handle:", events);
  return events;
}



function save_settings() {
  const mqtt_settings = {
    tenant_id: document.getElementById("qumea_tenant_id").value,
    host: document.getElementById("qumea_mqtt_host").value,
    port: parseInt(document.getElementById("qumea_mqtt_port").value),
    client_id: document.getElementById("qumea_client_id").value,
    integrationId: document.getElementById("qumea_integration_id").value,
    events_to_handle: get_events_to_handle()
  };

  const ssh_settings = {
    host: document.getElementById("ssh_host").value,
    port: parseInt(document.getElementById("ssh_port").value)
  };

  const http_settings = {
    timeout: parseFloat(document.getElementById("http_timeout").value),
    http_base_url: document.getElementById("http_base_url").value,
    verify_ssl: document.getElementById("http_verify_ssl").checked
  };

  const service_settings = {
    run_services_on_startup: document.getElementById("service_enabled").checked
  };

  set_mqtt_settings(mqtt_settings);
  set_ssh_settings(ssh_settings);
  set_http_settings(http_settings);
  set_service_settings(service_settings);

  alert("Einstellungen gespeichert!");
};




function get_mqtt_settings() {
  authFetch("/api/config/mqtt", {
    method: "GET"
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Laden der MQTT Einstellungen");
      return res.json();
    }).then(data => {
      console.log("MQTT Einstellungen:", data);
        document.getElementById("qumea_tenant_id").value = data.tenant_id || "";
        document.getElementById("qumea_mqtt_host").value = data.host|| "";
        document.getElementById("qumea_mqtt_port").value = data.port || "";
        document.getElementById("qumea_client_id").value = data.client_id || "";
        document.getElementById("qumea_integration_id").value = data.integrationId || "";
        if (data.events_to_handle) {
          for (const [event, handle] of Object.entries(data.events_to_handle)) {
            const checkbox = document.querySelector(`input.event-type[type='checkbox'][value='${event}']`);
            if (checkbox) {
              checkbox.checked = handle;
            }
          }
        }
    })
    .catch(err => console.error("Fehler:", err));
};

function get_ssh_settings() {
  authFetch("/api/config/ssh", {
    method: "GET"
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Laden der SSH Einstellungen");
      return res.json();
    }).then(data => {
      console.log("SSH Einstellungen:", data);
        document.getElementById("ssh_host").value = data.host || "";
        document.getElementById("ssh_port").value = data.port || "";
    })
    .catch(err => console.error("Fehler:", err));
};

function get_http_settings() {
  authFetch("/api/config/http", {
    method: "GET"
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Laden der HTTP Client Einstellungen");
      return res.json();
    }).then(data => {
      console.log("HTTP Client Einstellungen:", data);
        document.getElementById("http_base_url").value = data.http_base_url || "";
        document.getElementById("http_timeout").value = data.timeout || "";
        const httpVerifySslCheckbox = document.getElementById("http_verify_ssl");
        httpVerifySslCheckbox.checked = data.verify_ssl || false;
        const label = httpVerifySslCheckbox.nextElementSibling;
        if (label) {
          label.textContent = httpVerifySslCheckbox.checked ? "Aktiviert" : "Deaktiviert";
        }
    })
    .catch(err => console.error("Fehler:", err));
};

function get_service_settings() {
  authFetch("/api/config/service", {
    method: "GET"
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Laden der Service Einstellungen");
      return res.json();
    }).then(data => {
      console.log("Service Einstellungen:", data);
        const serviceEnabledCheckbox = document.getElementById("service_enabled");
        serviceEnabledCheckbox.checked = data.run_services_on_startup || false;
        const label = serviceEnabledCheckbox.nextElementSibling;
        if (label) {
          label.textContent = serviceEnabledCheckbox.checked ? "Aktiviert" : "Deaktiviert";
        }
    })
    .catch(err => console.error("Fehler:", err));
};  

function set_mqtt_settings(mqtt_settings) {
  authFetch("/api/config/mqtt", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(mqtt_settings)
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Speichern der MQTT Einstellungen");
    })
    .catch(err => console.error("Fehler:", err));
};

function set_http_settings(http_settings) {
  authFetch("/api/config/http", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(http_settings)
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Speichern der HTTP Client Einstellungen");
    })
    .catch(err => console.error("Fehler:", err));
};

function set_ssh_settings(ssh_settings) {
  authFetch("/api/config/ssh", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(ssh_settings)
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Speichern der SSH Einstellungen");
    })
    .catch(err => console.error("Fehler:", err));
}; 

function set_service_settings(service_settings) {
  authFetch("/api/config/service", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(service_settings)
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Speichern der Service Einstellungen");
    })
    .catch(err => console.error("Fehler:", err));
};


function reload_settings() {
  authFetch("/api/config/reload", {
    method: "POST"
  }).then(res => {
      if (!res.ok) throw new Error("Fehler beim Neuladen der Einstellungen");
      alert("Einstellungen neu geladen!");
    })
    .catch(err => console.error("Fehler:", err));
};


get_mqtt_settings();
get_ssh_settings();
get_http_settings();
get_service_settings();

