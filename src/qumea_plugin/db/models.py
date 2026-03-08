from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func, Column, Text, UniqueConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship
from enum import Enum

from .database import Base

# -------------------------
# Enums (als Strings in DB)
# -------------------------

class EventStatus(str, Enum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    WAITING = "WAITING"   # z.B. wartet auf SSH confirm
    DONE = "DONE"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    user_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        default="admin",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    room_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    ascom_device_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    qumea_roomId: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )


class ServiceConfig(Base):
    __tablename__ = "service_config"
    id = Column(Integer, primary_key=True)
    key = Column(String(128), nullable=False, unique=True)
    value = Column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("key", name="uq_plugin_config_key"),)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Korrelation über room + alert_type, weil SSH keine ID liefert
    room_name = Column(String(255), nullable=False, index=True)

    # Status des gesamten Events
    status = Column(String(32), nullable=False, default=EventStatus.NEW.value, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Qumea-spezifische Felder (optional, je nach Event-Typ)
    qumea_roomId = Column(Integer, nullable=True)
    qumea_alertType = Column(Integer, nullable=True)
    qumea_activeAlertId = Column(String(64), nullable=False, index=True)

    __table_args__ = (
        Index("ix_events_room_alert_status", "room_name", "qumea_alertType", "status"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
