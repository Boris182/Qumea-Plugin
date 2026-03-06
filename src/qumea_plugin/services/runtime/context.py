from dataclasses import dataclass
import httpx
from sqlalchemy.orm import sessionmaker
from ...config import Settings

# Runtime-Kontext, der wichtige Ressourcen und Konfigurationen für die gesamte Anwendung bereitstellt
@dataclass
class RuntimeContext:
    SessionLocal: sessionmaker
    http: httpx.AsyncClient
    settings: Settings

