from sqlalchemy.orm import Session
from ..models import ServiceConfig


def get_value(db: Session, key: str, default: str | None = None) -> str | None:
    """
    Fetch a config value by key; return default if absent.
    """
    row = db.query(ServiceConfig).filter(ServiceConfig.key == key).first()
    return row.value if row else default


def set_value(db: Session, key: str, value: str) -> None:
    """
    Upsert a config value.
    """
    row = db.query(ServiceConfig).filter(ServiceConfig.key == key).first()
    if row:
        row.value = value
    else:
        db.add(ServiceConfig(key=key, value=value))
    db.commit()
