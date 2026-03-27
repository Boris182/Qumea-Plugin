from datetime import datetime
import sys
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body, Form
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse
from pathlib import Path
from qumea_plugin.db.database import get_db
from qumea_plugin.deps import get_current_user
from qumea_plugin.routers.api_models import BackupRequest
from qumea_plugin.config import get_settings
import logging
import os
import io
import shutil
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Backups"], prefix="/api/backups")

#### Verschlüsselungs-Helper ###
MAGIC = b"SL3BKUP"     
VERSION = b"\x01"       
ASSOCIATED_DATA = b"sqlite-backup"  

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(password.encode("utf-8"))

def encrypt_bytes(plaintext: bytes, password: str) -> bytes:
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    aes = AESGCM(key)
    nonce = os.urandom(12) 
    ciphertext = aes.encrypt(nonce, plaintext, ASSOCIATED_DATA)
    return MAGIC + VERSION + salt + nonce + ciphertext

def is_encrypted(payload: bytes) -> bool:
    return payload.startswith(MAGIC + VERSION)

def decrypt_bytes(payload: bytes, password: str) -> bytes:
    if not is_encrypted(payload):
        raise ValueError("Datei ist nicht im erwarteten verschlüsselten Format.")
    off = len(MAGIC) + len(VERSION)
    salt = payload[off:off+16]; off += 16
    nonce = payload[off:off+12]; off += 12
    ciphertext = payload[off:]
    key = _derive_key(password, salt)
    aes = AESGCM(key)
    return aes.decrypt(nonce, ciphertext, ASSOCIATED_DATA)

### Helper Funktion für Größe des Backups ###
def format_size(bytes_size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


### Create Backup ###
@router.get("/db/backup", description="Erstellt ein lokales Backup der SQLite-Datenbank")
def db_backup(user=Depends(get_current_user)):
    db_file = Path("./database/app.db")
    if not db_file.exists():
        logger.info(f"SQLite DB nicht gefunden")
        raise HTTPException(status_code=500, detail="app.db nicht gefunden")

    backup_path = Path("backup")
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
        raise HTTPException(status_code=500, detail="Fehler beim Erstellen des Backup")
    
### Zeige Backup Status###
@router.get("/db/status", description="Check the status of the SQLite database.")
def db_status(user=Depends(get_current_user)):
    db_file = Path("./database/app.db")
    backup_dir = Path("./backup")
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

### Download verschlüsseltes Backup ###
@router.post("/db/backup", description="Erstellt ein verschlüsseltes Backup der SQLite-Datenbank und liefert die .db.enc-Datei.")
def db_backup(req: BackupRequest = Body(...), user=Depends(get_current_user)):
    db_file = Path("./database/app.db")
    if not db_file.exists():
        logger.info("SQLite DB nicht gefunden")
        raise HTTPException(status_code=500, detail="app.db nicht gefunden")

    backup_path = Path("backup")
    backup_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_plain = backup_path / f"app_backup_{timestamp}.db"
    enc_file = backup_path / f"app_backup_{timestamp}.db.enc"

    try:
        # 1) unverschlüsselte Kopie erstellen (kurzzeitig)
        shutil.copy2(db_file, tmp_plain)
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        ts = dt.timestamp()
        os.utime(tmp_plain, (ts, ts))

        # 2) einlesen & verschlüsseln
        plaintext = tmp_plain.read_bytes()
        enc_bytes = encrypt_bytes(plaintext, req.password)

        # 3) persistieren (optional) und unverschlüsselte temporäre Kopie entfernen
        enc_file.write_bytes(enc_bytes)
        os.utime(enc_file, (ts, ts))
        try:
            tmp_plain.unlink(missing_ok=True)
        except Exception:
            pass  # falls auf Windows gesperrt etc.

        logger.info(f"Verschlüsseltes SQLite-Backup erstellt: {enc_file}")

        # 4) als Download streamen
        return StreamingResponse(
            io.BytesIO(enc_bytes),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{enc_file.name}"'}
        )

    except Exception as e:
        logger.error(f"Fehler beim Backup: {e}")
        # Aufräumen
        try: tmp_plain.unlink(missing_ok=True)
        except Exception: pass
        raise HTTPException(status_code=500, detail="Fehler beim Erstellen des Backup")

### Restore Backup ###
@router.post("/db/restore", description="Stellt die SQLite-Datenbank aus einem (ggf. verschlüsselten) Backup wieder her.")
async def restore_backup(
    file: UploadFile = File(...),
    password: str | None = Form(None),
    user=Depends(get_current_user),
):
    db_file = Path("./database/app.db")
    if not db_file.exists():
        logger.info("SQLite DB nicht gefunden")
        raise HTTPException(status_code=500, detail="app.db nicht gefunden")

    backup_path = Path("backup")
    backup_path.mkdir(parents=True, exist_ok=True)

    try:
        # 1) Datei einlesen
        content = await file.read()

        # 2) ggf. entschlüsseln
        if content.startswith(b"SL3BKUP\x01"):
            if not password:
                raise HTTPException(status_code=400, detail="Passwort wird für verschlüsselte Backup benötigt")
            try:
                content = decrypt_bytes(content, password)
            except Exception:
                raise HTTPException(status_code=400, detail="Entschlüsselung fehlgeschlagen (falsches Passwort oder beschädigte Datei)")
        else:
            # optional: nur .db erlauben
            if not file.filename.lower().endswith(".db"):
                raise HTTPException(status_code=400, detail="Bitte eine .db oder .db.enc-Datei hochladen")

        # 3) temporär speichern
        temp_backup_file = backup_path / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        temp_backup_file.write_bytes(content)

        # 4) Validieren (echte SQLite-DB?)
        import sqlite3
        try:
            conn = sqlite3.connect(temp_backup_file)
            conn.execute("PRAGMA integrity_check;")
            conn.close()
        except sqlite3.DatabaseError:
            temp_backup_file.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Hochgeladene Datei ist keine gültige SQLite-Datenbank")

        # 5) aktuelle DB sichern
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_backup_file = backup_path / f"app_db_before_restore_{timestamp}.db"
        shutil.copy2(db_file, current_backup_file)
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S"); ts = dt.timestamp()
        os.utime(current_backup_file, (ts, ts))
        logger.info(f"Aktuelle DB gesichert: {current_backup_file}")

        # 6) ersetzen
        shutil.copy2(temp_backup_file, db_file)
        logger.info(f"Datenbank wiederhergestellt von: {temp_backup_file}")

        # 7) aufräumen
        temp_backup_file.unlink(missing_ok=True)

        return {"status": "success", "restored_from": file.filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Wiederherstellen: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Wiederherstellen des Backup")