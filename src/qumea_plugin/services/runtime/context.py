from dataclasses import dataclass
import httpx
from sqlalchemy.orm import sessionmaker

@dataclass
class RuntimeContext:
    SessionLocal: sessionmaker
    http: httpx.AsyncClient

    # optional: logger, metrics, settings-cache
    # optional: state values (last_keepalive_ts etc.) -> besser im Manager