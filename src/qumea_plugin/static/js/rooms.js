function get3cxDevices(){
  const token = localStorage.getItem('auth_token');
  authFetch("/api/3cx/devices", {
    method: "GET"
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert");
      return res.json();
    })
    .then(data => {
      console.log("Devices:", data);
      render3cxDevices(data)
    })
    .catch(err => console.error("Fehler:", err));
}

function add3cxDevice(device) {
  const token = localStorage.getItem('auth_token');

  authFetch("/api/3cx/device", {
    method: "POST",
    body: JSON.stringify(device)
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert oder Fehler beim Hinzufügen");
      return res.json();
    })
    .then(data => {
      console.log("Gerät hinzugefügt:", data);
      get3cxDevices(); // aktualisiere Liste
    })
    .catch(err => console.error("Fehler:", err));
}

function change3cxDevice(deviceId, updatedData) {
  const token = localStorage.getItem('auth_token');

  authFetch(`/api/3cx/device/${deviceId}`, {
    method: "PUT", 
    body: JSON.stringify(updatedData)
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert oder Fehler beim Ändern");
      return res.json();
    })
    .then(data => {
      console.log("Gerät geändert:", data);
      get3cxDevices(); // Aktualisieren
    })
    .catch(err => console.error("Fehler:", err));
}

function delete3cxDevice(deviceId) {
  if (!confirm("Bist du sicher, dass du dieses Gerät löschen möchtest?")) {
    return; // abbrechen
  }
  
  const token = localStorage.getItem('auth_token'); 
  authFetch(`/api/3cx/device/${deviceId}`, {
    method: "DELETE"
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert oder Fehler beim Löschen");
      return res.json();
    })
    .then(data => {
      console.log("Gerät Gelöscht:", data);
      get3cxDevices(); // Aktualisieren
    })
    .catch(err => console.error("Fehler:", err));
}


function submit3cxDevice() {
  const number = document.getElementById("add_number").value;
  const default_first_name = document.getElementById("add_default_first_name").value;
  const default_last_name = document.getElementById("add_default_last_name").value;
  const default_group_name = document.getElementById("add_default_group_name").value;

  const device = {
    number: number,
    default_first_name: default_first_name,
    default_last_name: default_last_name,
    default_group_name: default_group_name
  };

  add3cxDevice(device);

  // Modal schließen
  const modalElement = document.getElementById('add3cxDeviceModal');
  document.activeElement.blur(); 
  const modal = bootstrap.Modal.getInstance(modalElement);
  modal.hide();

  // Formular zurücksetzen
  document.getElementById("add_number").value = '';
  document.getElementById("add_default_first_name").value = '';
  document.getElementById("add_default_last_name").value = '';
  document.getElementById("add_default_group_name").value = '';
}

function submit3cxDeviceEdit() {
  const deviceId = document.getElementById("edit_id").value;
  const number = document.getElementById("edit_number").value;
  const default_first_name = document.getElementById("edit_default_first_name").value;
  const default_last_name = document.getElementById("edit_default_last_name").value;
  const default_group_name = document.getElementById("edit_default_group_name").value;

  const updatedData = {
    number: number,
    default_first_name: default_first_name,
    default_last_name: default_last_name,
    default_group_name: default_group_name
  };

  change3cxDevice(deviceId, updatedData);

  // Modal schließen
  const modalElement = document.getElementById('editDeviceModal');
  document.activeElement.blur(); 
  const modal = bootstrap.Modal.getInstance(modalElement);
  modal.hide();
}


function render3cxDevices(devices) {
  const table = $('#devices3cxTable');

  // Falls DataTable aktiv ist → zerstören und DOM zurücksetzen
  if ($.fn.dataTable.isDataTable('#devices3cxTable')) {
    table.DataTable().clear().destroy();
  }

  const tbody = document.getElementById("devices3cx-table-body");
  tbody.innerHTML = ""; // alte Einträge entfernen

  // Neue Zeilen hinzufügen
  devices.forEach(device => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${device.id}</td>
      <td>${device.number}</td>
      <td>${device.default_first_name}</td>
      <td>${device.default_last_name}</td>
      <td>${device.default_group_name}</td>
      <td class="text-end">
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-sm btn-warning" onclick='open3cxEditModal(${device.id}, "${device.number}", "${device.default_first_name}", "${device.default_last_name}", "${device.default_group_name}")'>
            Bearbeiten
          </button>
          <button type="button" class="btn btn-sm btn-danger" onclick='delete3cxDevice(${device.id})'>
            Delete
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  // Nach DOM-Update → DataTable neu aufbauen
  $('#devices3cxTable').DataTable({
  destroy: true,
  responsive: { details: { type: 'inline', target: 'tr' } },
  autoWidth: false,
  scrollX: false,
  paging: true,
  searching: true,
  language: { url: "/static/datatables/i18n/de-DE.json" },
  layout: { topStart: 'info' },
  columnDefs: [
    { responsivePriority: 1, targets: 1 },
    { responsivePriority: 2, targets: -1 }
  ]
  });
}

function open3cxEditModal(id, number, default_first_name, default_last_name, default_group_name) {
  document.getElementById("edit_id").value = id;
  document.getElementById("edit_number").value = number;
  document.getElementById("edit_default_first_name").value = default_first_name;
  document.getElementById("edit_default_last_name").value = default_last_name;
  document.getElementById("edit_default_group_name").value = default_group_name

  const modal = new bootstrap.Modal(document.getElementById("editDeviceModal"));
  modal.show();
}

// Export CSV – mit Auth-Header via fetch -> Blob-Download
function export3cxCsv() {
  authFetch('/api/3cx/devices/export')
    .then(res => {
      if (!res.ok) throw new Error('Export fehlgeschlagen');
      return res.blob();
    })
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'devices3cx.csv';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    })
    .catch(err => console.error(err));
}


// Import CSV – bestätigt Überschreiben, sendet Multipart und lädt neu
function import3cxCsv(file) {
  if (!file) return;
  if (!confirm('Achtung: Alle Einträge werden überschrieben. Fortfahren?')) return;


  const fd = new FormData();
  fd.append('file', file, file.name || 'devices3cx.csv');


  authFetch('/api/3cx/devices/import', { method: 'POST', body: fd })
    .then(res => res.json())
    .then(json => {
      if (json.status !== 'ok') throw new Error(json.detail || 'Import fehlgeschlagen');
      // Nach Import Tabelle neu laden
      if (typeof get3cxDevices === 'function') {
        get3cxDevices();
      } else if ($.fn.DataTable.isDataTable('#devices3cxTable')) {
        $('#devices3cxTable').DataTable().ajax?.reload(null, false);
      }
      alert(`Import OK – ${json.imported} Einträge`);
      document.getElementById('inputCsv').value = '';
    })
    .catch(err => alert(err.message || String(err)));
}


// CSV Up und Download Buttons mappen
function wireCsvButtons() {
  const btnExport = document.getElementById('btnExportCsv');
  const inputCsv = document.getElementById('inputCsv');
  if (btnExport) btnExport.addEventListener('click', export3cxCsv);
  if (inputCsv) inputCsv.addEventListener('change', (e) => import3cxCsv(e.target.files?.[0]));
}


get3cxDevices()
wireCsvButtons()