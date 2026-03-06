function getRooms(){
  const token = localStorage.getItem('auth_token');
  authFetch("/api/room", {
    method: "GET"
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert");
      return res.json();
    })
    .then(data => {
      console.log("Rooms:", data);
      renderRooms(data)
    })
    .catch(err => console.error("Fehler:", err));
}

function addRoom(room) {
  const token = localStorage.getItem('auth_token');

  authFetch("/api/room/create", {
    method: "POST",
    body: JSON.stringify(room)
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert oder Fehler beim Hinzufügen");
      return res.json();
    })
    .then(data => {
      console.log("Room hinzugefügt:", data);
      getRooms(); // aktualisiere Liste
    })
    .catch(err => console.error("Fehler:", err));
}

function changeRoom(roomId, updatedData) {
  const token = localStorage.getItem('auth_token');

  authFetch(`/api/room/${roomId}`, {
    method: "PUT", 
    body: JSON.stringify(updatedData)
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert oder Fehler beim Ändern");
      return res.json();
    })
    .then(data => {
      console.log("Room geändert:", data);
      getRooms(); // Aktualisieren
    })
    .catch(err => console.error("Fehler:", err));
}

function deleteRoom(roomId) {
  if (!confirm("Bist du sicher, dass du dieses Room löschen möchtest?")) {
    return; // abbrechen
  }
  
  const token = localStorage.getItem('auth_token'); 
  authFetch(`/api/room/${roomId}`, {
    method: "DELETE"
  })
    .then(res => {
      if (!res.ok) throw new Error("Nicht autorisiert oder Fehler beim Löschen");
      return res.json();
    })
    .then(data => {
      console.log("Room Gelöscht:", data);
      getRooms(); // Aktualisieren
    })
    .catch(err => console.error("Fehler:", err));
}


function submitRoom() {
  const room_name = document.getElementById("add_room_name").value;
  const ascom_device_id = document.getElementById("add_ascom_device_id").value;

  const room = {
    room_name: room_name,
    ascom_device_id: ascom_device_id
  };

  addRoom(room);

  // Modal schließen
  const modalElement = document.getElementById('addRoomModal');
  document.activeElement.blur(); 
  const modal = bootstrap.Modal.getInstance(modalElement);
  modal.hide();

  // Formular zurücksetzen
  document.getElementById("add_room_name").value = '';
  document.getElementById("add_ascom_device_id").value = '';
}

function submitRoomEdit() {
  const roomId = document.getElementById("edit_id").value;
  const room_name = document.getElementById("edit_room_name").value;
  const ascom_device_id = document.getElementById("edit_ascom_device_id").value;

  const updatedData = {
    room_name: room_name,
    ascom_device_id: ascom_device_id
  };

  changeRoom(roomId, updatedData);

  // Modal schließen
  const modalElement = document.getElementById('editRoomModal');
  document.activeElement.blur(); 
  const modal = bootstrap.Modal.getInstance(modalElement);
  modal.hide();
}


function renderRooms(rooms) {
  const table = $('#roomsTable');

  // Falls DataTable aktiv ist → zerstören und DOM zurücksetzen
  if ($.fn.dataTable.isDataTable('#roomsTable')) {
    table.DataTable().clear().destroy();
  }

  const tbody = document.getElementById("rooms-table-body");
  tbody.innerHTML = ""; // alte Einträge entfernen

  // Neue Zeilen hinzufügen
  rooms.forEach(room => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${room.id}</td>
      <td>${room.room_name}</td>
      <td>${room.ascom_device_id}</td>
      <td class="text-end">
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-sm btn-warning" onclick='openRoomEditModal(${room.id}, "${room.room_name}", "${room.ascom_device_id}")'>
            Bearbeiten
          </button>
          <button type="button" class="btn btn-sm btn-danger" onclick='deleteRoom(${room.id})'>
            Delete
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  // Nach DOM-Update → DataTable neu aufbauen
  $('#roomsTable').DataTable({
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

function openRoomEditModal(id, room_name, ascom_device_id) {
  document.getElementById("edit_id").value = id;
  document.getElementById("edit_room_name").value = room_name;
  document.getElementById("edit_ascom_device_id").value = ascom_device_id;

  const modal = new bootstrap.Modal(document.getElementById("editRoomModal"));
  modal.show();
}

// Export CSV – mit Auth-Header via fetch -> Blob-Download
function exportRoomsCsv() {
  authFetch('/api/room/export')
    .then(res => {
      if (!res.ok) throw new Error('Export fehlgeschlagen');
      return res.blob();
    })
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'rooms.csv';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    })
    .catch(err => console.error(err));
}


// Import CSV – bestätigt Überschreiben, sendet Multipart und lädt neu
function importRoomsCsv(file) {
  if (!file) return;
  if (!confirm('Achtung: Alle Einträge werden überschrieben. Fortfahren?')) return;


  const fd = new FormData();
  fd.append('file', file, file.name || 'rooms.csv');


  authFetch('/api/room/import', { method: 'POST', body: fd })
    .then(res => res.json())
    .then(json => {
      if (json.status !== 'ok') throw new Error(json.detail || 'Import fehlgeschlagen');
      // Nach Import Tabelle neu laden
      if (typeof getRooms === 'function') {
        getRooms();
      } else if ($.fn.DataTable.isDataTable('#roomsTable')) {
        $('#roomsTable').DataTable().ajax?.reload(null, false);
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
  if (btnExport) btnExport.addEventListener('click', exportRoomsCsv);
  if (inputCsv) inputCsv.addEventListener('change', (e) => importRoomsCsv(e.target.files?.[0]));
}


getRooms()
wireCsvButtons()