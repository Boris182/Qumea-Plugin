from datetime import datetime
import sys
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path
from qumea_plugin.db.database import get_db
from qumea_plugin.deps import get_current_user
from qumea_plugin.routers.api_models import *
from qumea_plugin.config import get_settings
import logging
import os
import shutil

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Backups"])

###### Helper Funktionen ######
def format_size(bytes_size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


### Create Backup ###
@router.get("/api/maintenance/db/backup", description="Make a backup of the SQLite database.")
def db_backup(user=Depends(get_current_user)):
    db_file = Path("./database/app.db")
    if not db_file.exists():
        logger.info(f"SQLite DB nicht gefunden")
        raise HTTPException(status_code=500, detail="app.db nicht gefunden")

    backup_path = Path("backups")
    backup_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"app_backup_{timestamp}.db"

    try:
        shutil.copy2(db_file, backup_file)
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        ts = dt.timestamp()
        os.utime(backup_file, (ts, ts))
        logger.info(f"SQLite-Backup erstellt unter: {backup_file}")
        return {"status": "success", "backup_file": str(backup_file), "timestamp": timestamp}
    except Exception as e:
        logger.error(f"Fehler beim Backup: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Erstellen des Backups")

### Restore Backup ###
@router.post("/api/maintenance/db/restore", description="Restore the SQLite database from an uploaded backup file.")
async def restore_backup(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.filename.lower().endswith(".db"):
        raise HTTPException(status_code=400, detail="Bitte eine .db-Datei hochladen")

    db_file = Path("./database/app.db")
    if not db_file.exists():
        logger.info(f"SQLite DB nicht gefunden")
        raise HTTPException(status_code=500, detail="app.db nicht gefunden")

    backup_path = Path("backups")
    backup_path.mkdir(parents=True, exist_ok=True)

    try:
        # Temporäre Datei im Backup-Verzeichnis speichern
        temp_backup_file = backup_path / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        with temp_backup_file.open("wb") as out_file:
            content = await file.read()
            out_file.write(content)

        # Validierung: Prüfen, ob die Datei eine gültige SQLite-Datenbank ist
        try:
            import sqlite3
            conn = sqlite3.connect(temp_backup_file)
            conn.execute("PRAGMA integrity_check;")
            conn.close()
        except sqlite3.DatabaseError:
            temp_backup_file.unlink(missing_ok=True)  # Temporäre Datei löschen
            raise HTTPException(status_code=400, detail="Hochgeladene Datei ist keine gültige SQLite-Datenbank")

        # Aktuelle Datenbank sichern (optional)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_backup_file = backup_path / f"app_db_before_restore_{timestamp}.db"
        shutil.copy2(db_file, current_backup_file)
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        ts = dt.timestamp()
        os.utime(current_backup_file, (ts, ts))
        logger.info(f"Aktuelle Datenbank gesichert unter: {current_backup_file}")

        # Temporäre Datei als neue Datenbank kopieren
        shutil.copy2(temp_backup_file, db_file)
        logger.info(f"Datenbank wiederhergestellt von: {temp_backup_file}")

        # Temporäre Datei löschen
        temp_backup_file.unlink(missing_ok=True)

        return {"status": "success", "restored_from": file.filename}
    except Exception as e:
        logger.error(f"Fehler beim Wiederherstellen des Backups: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Wiederherstellen des Backups") 

### Download the latest Backup ###
@router.get("/api/maintenance/db/download-latest", description="Download the most recent SQLite backup.")
def download_latest_backup(user=Depends(get_current_user)):
    backup_dir = Path("backups")
    if not backup_dir.exists() or not backup_dir.is_dir():
        raise HTTPException(status_code=404, detail="Kein Backup-Verzeichnis gefunden")

    # Alle Dateien mit .db-Endung im Backup-Ordner
    backup_files = list(backup_dir.glob("app_backup_*.db"))
    if not backup_files:
        raise HTTPException(status_code=404, detail="Keine Backups gefunden")

    # Neueste Datei anhand Änderungszeit
    latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)

    return FileResponse(
        path=latest_backup,
        filename=latest_backup.name,
        media_type='application/octet-stream',
        headers={
            "Content-Disposition": f'attachment; filename="{latest_backup.name}"'
        }
    )

### Get the DB State ###
@router.get("/api/maintenance/db/status", description="Check the status of the SQLite database.")
def db_status(user=Depends(get_current_user)):
    db_file = Path("./database/app.db")
    backup_dir = Path("./backups")
    backup_files = list(backup_dir.glob("app_backup_*.db"))

    if not db_file.exists():
        raise HTTPException(status_code=404, detail="app.db nicht gefunden")

    # Ermittle Backup-Dateiname
    backup_name = None
    if backup_files:
        latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
        backup_name = latest_backup.name

    # Ermittle Dateigröße
    try:
        db_size = db_file.stat().st_size  # in Bytes
        with db_file.open("rb") as f:
            f.read(1)  # Teste, ob die Datei lesbar ist
        return {
            "status": "ok",
            "message": "Datenbank ist erreichbar",
            "db_size_bytes": db_size,
            "db_size_formatted": format_size(db_size),
            "latest_backup": backup_name
        }
    except Exception as e:
        logger.error(f"Fehler beim Zugriff auf die Datenbank: {e}")
        raise HTTPException(status_code=500, detail="Datenbank ist nicht erreichbar")
