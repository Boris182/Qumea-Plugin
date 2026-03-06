from datetime import datetime
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text as sqltext
from qumea_plugin.db.database import get_db
from qumea_plugin.deps import get_current_user
from qumea_plugin.routers.api_models import *
from qumea_plugin.config import get_settings
import logging
import io

import os
import zipfile

router = APIRouter(tags=["Maintenance"], prefix="/api/maintenance")
settings = get_settings()

# Root logger (global)
root_logger = logging.getLogger()
logger = logging.getLogger(__name__)



LEVELS = {"CRITICAL": 50, "ERROR": 40, "WARNING": 30, "INFO": 20, "DEBUG": 10, "NOTSET": 0}

# Alle Logger auf ein bestimmtes Level setzen (z.B. DEBUG, INFO, WARNING, ERROR, CRITICAL)
def set_all_loggers_level(numeric: int) -> None:
    root = logging.getLogger()
    root.setLevel(numeric)

    for h in root.handlers:
        h.setLevel(numeric)

    for name, obj in logging.Logger.manager.loggerDict.items():
        if isinstance(obj, logging.Logger):
            obj.setLevel(numeric)
            for h in obj.handlers:
                h.setLevel(numeric)

# Log-Pfade aus Settings
LOG_PATH = Path(settings.log_dir)
LOG_FILE = LOG_PATH / settings.log_file

###### System ######-----------------------------------------------------------------------------------
@router.post("/restart")
def restart(user=Depends(get_current_user)):
    logger.warning("SYSTEM REBOOT requested by %s", getattr(user, "user_name", "unknown"))
    python = sys.executable
    os.execl(python, python, *sys.argv)

###### LOGS ######-----------------------------------------------------------------------------------
### Get the Logs ###
@router.get("/logs", description="Gibt die letzten 20 Log-Zeilen zurück")
def get_logs(user=Depends(get_current_user)):
    if not LOG_FILE.exists():
        raise HTTPException(status_code=404, detail="Log-Datei nicht gefunden")

    with LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    return {"logs": [line.rstrip("\n") for line in lines[-20:]]}

### Download the Logs ###
@router.get("/logsDownload", description="Alle Logs als ZIP herunterladen")
def download_logs(user=Depends(get_current_user)):
    if not LOG_PATH.exists() or not LOG_PATH.is_dir():
        raise HTTPException(status_code=404, detail="Logs-Verzeichnis nicht gefunden")

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in LOG_PATH.rglob("*"):
            if file_path.is_file():
                zip_file.write(file_path, file_path.relative_to(LOG_PATH))

    zip_buffer.seek(0)
    filename = f"logs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



### Get the Log Level ###
@router.get("/getLogLevel", description="Return the effective log level of the application.")
def get_log_level(user=Depends(get_current_user)):
    lvl = root_logger.getEffectiveLevel()
    return {"logLevel": logging.getLevelName(lvl)}

### Set the Log Level ###
@router.get("/setLogLevel/{logLevel}")
def set_log_level(logLevel: str, user=Depends(get_current_user)):
    key = logLevel.upper()
    numeric = LEVELS.get(key)
    if numeric is None:
        raise HTTPException(status_code=400, detail=f"Ungültiger Log-Level: {logLevel}")

    set_all_loggers_level(numeric)
    logging.getLogger(__name__).warning("Log level changed to %s", key)
    return {"logLevel": key}
