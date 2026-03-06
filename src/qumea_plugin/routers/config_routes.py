import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ..db.database import get_db
from ..db.crud import config as config_crud
from ..routers.api_models import MqttConfigDto, ServiceConfigDto, SshConfigDto, HttpClientConfigDto
from ..services.service_config_defaults import (
    DEFAULT_MQTT_CONFIG,
    DEFAULT_SSH_CONFIG,
    DEFAULT_HTTP_CONFIG,
    DEFAULT_SERVICE_CONFIG,
    merge_with_defaults,
)
from ..services.http.client import create_http_client

router = APIRouter(prefix="/api/config", tags=["Configuration"])


def _load_section(db: Session, key: str, default: dict) -> dict:
    raw = config_crud.get_value(db, key)
    if not raw:
        return default.copy()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}
    return merge_with_defaults(parsed, default)


def _persist_section(
    db: Session,
    key: str,
    default: dict,
    data: dict,
    sensitive_fields: tuple[str, ...] = (),
) -> dict:
    """
    Write config back; drops sensitive fields so they are never stored in DB.
    """
    sanitized = {k: v for k, v in data.items() if k not in sensitive_fields}
    merged = merge_with_defaults(sanitized, default)
    config_crud.set_value(db, key, json.dumps(merged))
    return merged


@router.get("/mqtt", response_model=MqttConfigDto)
def get_mqtt_config(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = _load_section(db, "mqtt", DEFAULT_MQTT_CONFIG)
    return cfg


@router.put("/mqtt", response_model=MqttConfigDto)
def update_mqtt_config(
    payload: MqttConfigDto,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = _persist_section(
        db,
        "mqtt",
        DEFAULT_MQTT_CONFIG,
        payload.model_dump(),
        sensitive_fields=("username", "password"),
    )
    return cfg


@router.get("/ssh", response_model=SshConfigDto)
def get_ssh_config(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = _load_section(db, "ssh", DEFAULT_SSH_CONFIG)
    return cfg


@router.put("/ssh", response_model=SshConfigDto)
def update_ssh_config(
    payload: SshConfigDto,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = _persist_section(
        db,
        "ssh",
        DEFAULT_SSH_CONFIG,
        payload.model_dump(),
        sensitive_fields=("username", "password"),
    )
    return cfg


@router.get("/http", response_model=HttpClientConfigDto)
def get_http_config(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = _load_section(db, "http", DEFAULT_HTTP_CONFIG)
    return cfg


@router.put("/http", response_model=HttpClientConfigDto)
def update_http_config(
    payload: HttpClientConfigDto,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = _persist_section(db, "http", DEFAULT_HTTP_CONFIG, payload.model_dump())
    return cfg

@router.get("/service")
def get_service_config(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = _load_section(db, "service", DEFAULT_SERVICE_CONFIG)
    return cfg

@router.put("/service")
def update_service_config(
    payload: ServiceConfigDto,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = _persist_section(db, "service", DEFAULT_SERVICE_CONFIG, payload.model_dump())
    return cfg

@router.post("/reload")
async def reload_services(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    app = request.app
    mgr = app.state.service_manager

    # Stop running tasks
    await mgr.stop()

    # Recreate HTTP client based on latest config
    http_cfg = _load_section(db, "http", DEFAULT_HTTP_CONFIG)
    await mgr.ctx.http.aclose()
    mgr.ctx.http = create_http_client(http_cfg)

    # Restart services with new config
    await mgr.start()
    return mgr.get_status()
