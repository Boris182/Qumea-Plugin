# src/qumea_plugin/services/runtime/manager.py
import asyncio
import json
import time
from dataclasses import dataclass
from typing import Optional

from .context import RuntimeContext
from ..workflow.engine import WorkflowEngine
from ..workflow.stages.http_get import HttpGetStage
from ..mqtt.client import MqttWorker, MqttConfig
from ..ssh.listener import SshListener, SshConfig
from ..config_defaults import (
    DEFAULT_MQTT_CONFIG,
    DEFAULT_SSH_CONFIG,
    merge_with_defaults,
)
from ...db.crud import config as config_crud
from ...db.models import Room

@dataclass
class ServiceStatus:
    running: bool
    started_at: float | None
    last_broker_keepalive: float | None
    last_error: str | None

class ServiceManager:
    def __init__(self, ctx: RuntimeContext):
        self.ctx = ctx
        self._tasks: list[asyncio.Task] = []
        self._mqtt: MqttWorker | None = None
        self._ssh: SshListener | None = None

        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)
        self.ka_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

        self.status = ServiceStatus(False, None, None, None)

        # Pipeline (später kannst du hier dynamisch stages aus DB config bauen)
        self.engine = WorkflowEngine(
            stages=[
                HttpGetStage(url_builder=self._url_builder),
            ]
        )

    def _load_config(self, key: str, default: dict) -> dict:
        db = self.ctx.SessionLocal()
        try:
            raw = config_crud.get_value(db, key)
        finally:
            db.close()

        if not raw:
            return default.copy()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}

        return merge_with_defaults(parsed, default)

    def _url_builder(self, ctx: RuntimeContext, event: dict) -> str | None:
        """
        Hier: event auswerten + rooms aus SQLite laden + URL bauen.
        Das ist nur ein Platzhalter.
        """
        # Beispiel: event enthält room_id
        room_id = event.get("room_id")
        if not room_id:
            return None

        db = ctx.SessionLocal()
        try:
            room = db.query(Room).filter(Room.id == room_id).first()
            if not room:
                return None
            return f"http://{room.ascom_rc_ip}/action?device_id={room.ascom_device_id}&room_id={room.id}"
        finally:
            db.close()

    async def start(self):
        if self.status.running:
            return

        settings = self.ctx.settings
        mqtt_dict = self._load_config("mqtt", DEFAULT_MQTT_CONFIG)
        mqtt_dict["username"] = settings.mqtt_username
        mqtt_dict["password"] = settings.mqtt_password

        ssh_dict = self._load_config("ssh", DEFAULT_SSH_CONFIG)
        ssh_dict["username"] = settings.ssh_username or "user"
        ssh_dict["password"] = settings.ssh_password

        mqtt_cfg = MqttConfig(**mqtt_dict)
        ssh_cfg = SshConfig(**ssh_dict)

        self._mqtt = MqttWorker(mqtt_cfg, self.event_queue, self.ka_queue)
        self._ssh = SshListener(ssh_cfg, self.event_queue)

        self.status.running = True
        self.status.started_at = time.time()
        self.status.last_error = None

        self._tasks = [
            asyncio.create_task(self._mqtt.run(), name="mqtt-subscribe"),
            asyncio.create_task(self._mqtt.keepalive_publisher(), name="mqtt-keepalive-out"),
            asyncio.create_task(self._ssh.run(), name="ssh-listener"),
            asyncio.create_task(self._event_loop(), name="event-loop"),
            asyncio.create_task(self._healthcheck_loop(), name="healthcheck-loop"),
        ]

    async def stop(self):
        if not self.status.running:
            return

        self.status.running = False

        if self._mqtt:
            await self._mqtt.stop()
        if self._ssh:
            await self._ssh.stop()

        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks = []
        self._mqtt = None
        self._ssh = None

    async def _event_loop(self):
        while self.status.running:
            event = await self.event_queue.get()
            try:
                await self.engine.handle_event(self.ctx, event)
            except Exception as e:
                self.status.last_error = str(e)

    async def _healthcheck_loop(self):
        """
        - last_broker_keepalive wird über ka_queue aktualisiert
        - Wenn seit > 120s nichts kam -> HTTP GET auslösen
        """
        while self.status.running:
            now = time.time()

            # ka_queue “drain”
            drained = False
            while True:
                try:
                    ts = self.ka_queue.get_nowait()
                    self.status.last_broker_keepalive = ts
                    drained = True
                except asyncio.QueueEmpty:
                    break

            # Regel: wenn > 120s
            last = self.status.last_broker_keepalive
            if last is not None and (now - last) > 120.0:
                try:
                    await self.ctx.http.get("http://127.0.0.1:8181/broker-missing-keepalive")
                except Exception as e:
                    self.status.last_error = str(e)

            await asyncio.sleep(5.0)

    def get_status(self) -> dict:
        return {
            "running": self.status.running,
            "started_at": self.status.started_at,
            "last_broker_keepalive": self.status.last_broker_keepalive,
            "last_error": self.status.last_error,
            "tasks": [t.get_name() for t in self._tasks if not t.done()],
        }
