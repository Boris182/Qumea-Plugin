from sqlalchemy.orm import Session
from .. import models

def get_value(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.query(models.PluginConfig).filter(models.PluginConfig.key == key).first()
    return row.value if row else default

def set_value(db: Session, key: str, value: str) -> None:
    row = db.query(models.PluginConfig).filter(models.PluginConfig.key == key).first()
    if row:
        row.value = value
    else:
        db.add(models.PluginConfig(key=key, value=value))
    db.commit()