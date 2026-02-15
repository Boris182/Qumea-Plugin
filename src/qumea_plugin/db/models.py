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


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"   # wartet auf externes Signal (SSH)
    OK = "OK"
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

    ascom_rc_ip: Mapped[str] = mapped_column(
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
    alert_type = Column(String(64), nullable=False, index=True)  # z.B. "call"

    # Status des gesamten Events
    status = Column(String(32), nullable=False, default=EventStatus.NEW.value, index=True)

    # Original-MQTT Payload als JSON-String (einfach & SQLite-freundlich)
    payload_json = Column(Text, nullable=True)

    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship zu StageRuns
    stage_runs = relationship(
        "EventStageRun",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_events_room_alert_status", "room_name", "alert_type", "status"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()



class EventStageRun(Base):
    __tablename__ = "event_stage_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)

    stage_name = Column(String(128), nullable=False, index=True)  # z.B. "http_trigger", "wait_ssh_confirm"
    status = Column(String(32), nullable=False, default=StageStatus.PENDING.value, index=True)

    attempt = Column(Integer, nullable=False, default=1)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)

    # Optional: sehr hilfreich fürs Debugging von HTTP
    http_method = Column(String(16), nullable=True)
    http_url = Column(Text, nullable=True)
    http_status = Column(Integer, nullable=True)

    error = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    event = relationship("Event", back_populates="stage_runs")

    __table_args__ = (
        Index("ix_stage_room_alert_join_helper", "stage_name", "status"),
    )

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
