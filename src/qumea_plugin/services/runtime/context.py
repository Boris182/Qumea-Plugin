from dataclasses import dataclass
import httpx
from sqlalchemy.orm import sessionmaker
from ...config import Settings

@dataclass
class RuntimeContext:
    SessionLocal: sessionmaker
    http: httpx.AsyncClient
    settings: Settings

    # optional: logger, metrics, settings-cache
    # optional: state values (last_keepalive_ts etc.) -> besser im Manager
