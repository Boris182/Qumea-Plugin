# Qumea Plugin

Middleware zwischen Qumea und Ascom TelecareIP mit Web-UI, REST-API, Authentifizierung, Konfigurationsverwaltung, Backup/Restore und Hintergrunddiensten (MQTT/SSH).

## Inhaltsverzeichnis

1. [Ueberblick](#ueberblick)
2. [Funktionsumfang](#funktionsumfang)
3. [Architektur](#architektur)
4. [Voraussetzungen](#voraussetzungen)
5. [Installation](#installation)
6. [Starten der Anwendung](#starten-der-anwendung)
7. [Konfiguration](#konfiguration)
8. [Web-Oberflaeche](#web-oberflaeche)
9. [API-Endpunkte](#api-endpunkte)
10. [Datenbankmodell](#datenbankmodell)
11. [Logging](#logging)
12. [Sicherheit](#sicherheit)
13. [Backup- und Restore-Format](#backup--und-restore-format)
14. [Entwicklung](#entwicklung)
15. [Troubleshooting](#troubleshooting)

## Ueberblick

Das Qumea Plugin ist ein FastAPI-Dienst mit:

- REST-API fuer Auth, Konfiguration, Raeume, Wartung und Service-Steuerung
- Web-UI unter `/static/`
- SQLite-Datenbank fuer Benutzer, Raeume und Konfigurationswerte
- Laufzeit-Service-Manager fuer MQTT- und SSH-Worker
- JWT-basierter Authentifizierung
- WebSocket-Logstream fuer Admins

## Funktionsumfang

- Benutzerregistrierung (ein initialer Benutzer) und Login
- Token-basierter Zugriff auf geschuetzte API-Routen
- Persistente Konfiguration fuer MQTT, SSH, HTTP-Client und Service-Verhalten
- Start, Stop und Status der Hintergrundservices
- Datenbank-Backups lokal oder verschluesselt als Download
- Restore aus `.db` oder `.db.enc`
- Log-Verwaltung mit Live-Stream, Download und Log-Level-Steuerung
- Raumverwaltung (CRUD)

## Architektur

### Backend

- Framework: FastAPI
- Einstiegspunkte:
- `src/qumea_plugin/__main__.py` (Uvicorn-Start)
- `src/qumea_plugin/app.py` (App-Factory + Lifespan)
- Datenbank: SQLite via SQLAlchemy
- Auth: JWT (`python-jose`) + Passwort-Hashing (`bcrypt`)
- HTTP-Client: `httpx.AsyncClient`
- Worker:
- MQTT-Worker (`paho-mqtt`)
- SSH-Listener (`asyncssh`)
- Frontend: statische HTML/CSS/JS-Dateien unter `src/qumea_plugin/static`

### Laufzeitablauf (vereinfacht)

1. App startet und initialisiert Logging.
2. JWT-Secret wird pro Prozesslauf neu erzeugt.
3. DB-Tabellen werden erstellt.
4. Konfigurationen (`http`, `service`, usw.) werden aus DB geladen.
5. HTTP-Client und `ServiceManager` werden initialisiert.
6. Optionaler Auto-Start ueber `run_services_on_startup`.

## Voraussetzungen

- Python `>=3.13`
- Zugriff auf Dateisystem fuer `database/`, `backups/`, `logs/`
- Erreichbarer MQTT-Broker
- Erreichbares SSH-Zielsystem
- Optionales HTTP-Zielsystem (z. B. Node-RED)

## Installation

### Option A: mit `uv` (empfohlen)

```powershell
uv sync
```

### Option B: mit `pip`

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

## Starten der Anwendung

### Ueber den Projekt-Entry-Point

```powershell
qumea-plugin
```

### Direkt mit Python

```powershell
python -m qumea_plugin
```

### Umgebungsvariablen zur Laufzeit

- `HOST` (Standard: `0.0.0.0`)
- `PORT` (Standard: `8000`)
- `RELOAD` (`true/false`, Standard: `false`)

Nach dem Start:

- Web-UI: `http://<host>:<port>/static/`
- Swagger: `http://<host>:<port>/docs`
- ReDoc: `http://<host>:<port>/redoc`
- Health: `http://<host>:<port>/health`

## Konfiguration

Die App nutzt `pydantic-settings` mit `.env`-Unterstuetzung.

Wichtige Defaults aus `config.py`:

- `app_name`: `Qumea Plugin`
- `app_description`: `Middleware zwischen Qumea und Ascom TelecareIP`
- `db_path`: `database/app.db`
- `log_dir`: `logs`
- `log_file`: `app.log`
- `jwt_alg`: `HS256`
- `jwt_expire_min`: `60`

Credentials werden aus Umgebungsvariablen geladen und nicht in der DB gespeichert:

- `mqtt_username`
- `mqtt_password`
- `ssh_username`
- `ssh_password`

Persistente Service-Konfiguration liegt als JSON in `service_config` unter den Keys:

- `mqtt`
- `ssh`
- `http`
- `service`

## Web-Oberflaeche

Die UI ist eine statische Navigation mit dynamisch geladenen Teilseiten.

Hauptbereiche:

- Dashboard
- Settings
- Administration / Rooms
- Maintenance / Backups
- Maintenance / Logs
- Maintenance / System

Authentifizierung im Frontend erfolgt ueber Bearer-Token im `localStorage`.

## API-Endpunkte

### Public

- `GET /` -> Redirect auf `/static/`
- `GET /health` -> Dienststatus und Version

### Auth

- `POST /register` -> Initialen Benutzer anlegen
- `POST /login` -> JWT ausstellen
- `GET /auth/check` -> Token pruefen
- `GET /registerCheck` -> Pruefen, ob Benutzer existiert

### Konfiguration (`/api/config`)

- `GET /mqtt`
- `PUT /mqtt`
- `GET /ssh`
- `PUT /ssh`
- `GET /http`
- `PUT /http`
- `GET /service`
- `PUT /service`
- `POST /reload` -> Services stoppen, HTTP-Client neu erstellen, Services neu starten

### Service (`/api/service`)

- `POST /start`
- `POST /stop`
- `GET /status`
- `GET /health`

### Raeume (`/api/room`)

- `GET /`
- `POST /create`
- `PUT /{room_id}`
- `DELETE /{room_id}`

### Backups (`/api/backups`)

- `GET /db/status` -> DB-Status + letztes Backup
- `GET /db/backup` -> Lokales Backup auf Server erstellen
- `POST /db/backup` -> Verschluesseltes Backup als Download liefern
- `POST /db/restore` -> Restore aus Upload (`.db` oder `.db.enc`)

### Maintenance (`/api/maintenance`)

- `POST /restart` -> Prozess-Neustart
- `GET /logs` -> Letzte 20 Logzeilen
- `GET /logsDownload` -> Logs als ZIP
- `GET /getLogLevel` -> Effektiven Log-Level lesen
- `GET /setLogLevel/{logLevel}` -> Log-Level setzen

### WebSocket

- `WS /ws/logs?token=<JWT>` -> Live-Logstream (Admin-Rolle erforderlich)

## Datenbankmodell

Tabellen:

- `users`: Benutzername, Passwort-Hash, Rolle, Zeitstempel
- `rooms`: Raumname und Ascom Device ID (jeweils eindeutig)
- `service_config`: Key/Value fuer JSON-Konfiguration
- `events`: Event-Metadaten (Status, Raum, Qumea-Felder)

Standard-Pfad der SQLite-Datei: `database/app.db`.

## Logging

- Rotierendes File-Logging (`RotatingFileHandler`)
- Zusaetzlich Konsolen-Logging
- Standard-Logdatei: `logs/app.log`
- Log-Level zur Laufzeit ueber Maintenance-API aenderbar

## Sicherheit

- Passwort-Hashing mit `bcrypt`
- JWT mit konfigurierbarem Algorithmus und Ablaufzeit
- JWT-Secret wird beim Start neu erzeugt
- Tokens werden damit nach jedem Neustart ungueltig
- Rollenpruefung fuer sensible Funktionen (z. B. WS-Logstream nur `admin`)
- Sensitive Credentials werden nur aus Umgebungsvariablen geladen

## Backup- und Restore-Format

Verschluesseltes Backup (`POST /api/backups/db/backup`) verwendet:

- Magic Header: `SL3BKUP`
- Version: `0x01`
- KDF: `Scrypt` (32 Byte Key)
- Verschluesselung: `AES-GCM`
- AAD: `sqlite-backup`

Restore akzeptiert:

- Unverschluesselte `.db`
- Verschluesselte `.db.enc` (mit Passwort)

Vor Restore wird die aktuelle DB als Sicherheitskopie in `backups/` gesichert.

## Entwicklung

Projektstruktur (Kurzform):

```text
src/qumea_plugin/
  app.py
  config.py
  deps.py
  security.py
  routers/
  services/
  db/
  ws/
  static/
```

## Troubleshooting

- Login funktioniert nicht: pruefen, ob ein Benutzer via `/register` angelegt wurde.
- Services starten nicht: Konfiguration unter `/api/config/*` pruefen und `POST /api/config/reload` aufrufen.
- Keine Logs sichtbar: Existenz von `logs/app.log` pruefen.
- Backup/Restore schlaegt fehl: Dateiformat und Passwort pruefen.
- Token nach Neustart ungueltig: erwartetes Verhalten wegen neuem JWT-Secret.

## Hinweise

- Im Code werden `paho-mqtt` (MQTT-Worker) und `cryptography` (Backup-Verschluesselung) verwendet.
- Falls diese Pakete in der Umgebung fehlen, bitte zusaetzlich installieren.
