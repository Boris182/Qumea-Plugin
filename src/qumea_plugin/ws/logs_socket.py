import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db.database import get_db
from ..services.auth_service import get_user_from_token, require_role

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

# Besser: Logfile-Pfad aus deinen Settings ableiten (wenn du log_dir/log_file hast)
LOG_PATH = Path(getattr(settings, "log_dir", "logs")) / getattr(settings, "log_file", "app.log")


@router.websocket("/ws/logs")
async def websocket_log_stream(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    try:
        # 1) JWT-Secret aus app.state (wird in lifespan gesetzt)
        secret = websocket.app.state.jwt_secret

        # 2) User aus Token holen (DB + JWT verify)
        user = get_user_from_token(
            raw_token=token,
            db=db,
            secret=secret,
            algorithm=settings.jwt_alg,
        )

        # 3) Optional: nur Admin darf Logs streamen
        require_role(user, "admin")

        await websocket.accept()
        logger.info("WS logs connected: user=%s", user.user_name)

        await send_log_tail(websocket)

    except WebSocketDisconnect:
        logger.info("WS logs disconnected")
    except Exception as e:
        logger.warning("WS logs auth/error: %s", e)
        # 1008 = Policy Violation (z.B. Auth fehlgeschlagen)
        await websocket.close(code=1008)


async def send_log_tail(websocket: WebSocket):
    last_size = LOG_PATH.stat().st_size if LOG_PATH.exists() else 0

    while True:
        await asyncio.sleep(1)

        if not LOG_PATH.exists():
            continue

        current_size = LOG_PATH.stat().st_size
        if current_size > last_size:
            # robust gegen Encoding-Probleme:
            with LOG_PATH.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(last_size)
                new_data = f.read()
                await websocket.send_text(new_data)
                last_size = current_size
