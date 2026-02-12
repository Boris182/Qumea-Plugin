import os
import logging
import secrets
from pathlib import Path
from . import __version__
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from contextlib import asynccontextmanager
from .routers import public_routes, auth_routes, backup_routes, maintenance_routes
from .logging_conf import setup_logging
from .config import get_settings
from .db.database import engine, Base
from .db import models
from .ws import logs_socket

# Logger anlegen für Applikation
logger = logging.getLogger(__name__)

# Verzeichnisse anlegen
database_dir = "database"
backup_dir = "backup"
os.makedirs(database_dir, exist_ok=True)
os.makedirs(backup_dir, exist_ok=True)


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Startup: %s v%s", settings.app_name, __version__)
        # JWT Secret erzeugen, bleibt solange Porgramm läuft.
        app.state.jwt_secret = secrets.token_urlsafe(64)
        Base.metadata.create_all(bind=engine)
        yield
        logger.info("Shutdown: bye")
        # Beispiel: Cleanup:
        # await app.state.db.close()
        # await app.state.nats.close()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=settings.app_description,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_tags=[
            {"name": "Authentication", "description": "Endpoints for user authentication."}
        ],
        lifespan=lifespan,
    )

    # --- STATIC FILES ---
    BASE_DIR = Path(__file__).resolve().parent
    app.mount(
        "/static",
        StaticFiles(directory="src/qumea_plugin/static", html=True),
        name="static",
    )

    @app.get("/")
    async def root():
        return RedirectResponse("/static/")
    
     # --- ROUTER ---
    app.include_router(auth_routes.router)
    app.include_router(public_routes.router)
    app.include_router(logs_socket.router)
    app.include_router(backup_routes.router)
    app.include_router(maintenance_routes.router)

    return app

app = create_app()