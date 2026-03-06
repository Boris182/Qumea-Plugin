# src/qumea_plugin/services/runtime/manager.py
import asyncio
import json
import time
from dataclasses import dataclass
from typing import Optional
import logging

from .context import RuntimeContext
from ..mqtt.client import MqttWorker, MqttConfig
from ..ssh.listener import SshListener, SshConfig
from ..service_config_defaults import (
    DEFAULT_MQTT_CONFIG,
    DEFAULT_SSH_CONFIG,
    merge_with_defaults,
)
from ...db.crud import config as config_crud
from ...db.models import Room
from ...db.models import Event

logger = logging.getLogger(__name__)

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

        self.mqtt_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)
        self.ssh_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)
        self.ka_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        self.status = ServiceStatus(False, None, None, None)

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
        room_id = event.get("room_id")
        if not room_id:
            return None

        db = ctx.SessionLocal()
        try:
            room = db.query(Room).filter(Room.id == room_id).first()
            if not room:
                return None
            return f"http://baseurl/?room_id={room.id}"
        finally:
            db.close()

    async def start(self):
        if self.status.running:
            logger.warning("ServiceManager is already running")
            return
        logger.info("Starting ServiceManager...")
        settings = self.ctx.settings
        mqtt_dict = self._load_config("mqtt", DEFAULT_MQTT_CONFIG)
        mqtt_dict["username"] = settings.mqtt_username
        mqtt_dict["password"] = settings.mqtt_password

        ssh_dict = self._load_config("ssh", DEFAULT_SSH_CONFIG)
        ssh_dict["username"] = settings.ssh_username or "user"
        ssh_dict["password"] = settings.ssh_password

        mqtt_cfg = MqttConfig(**mqtt_dict)
        ssh_cfg = SshConfig(**ssh_dict)

        self._mqtt = MqttWorker(mqtt_cfg, self.mqtt_queue, self.ka_queue)
        self._ssh = SshListener(ssh_cfg, self.ssh_queue)

        self.status.running = True
        self.status.started_at = time.time()
        self.status.last_error = None

        self._tasks = [
            asyncio.create_task(self._mqtt.run(), name="mqtt-subscribe"),
            asyncio.create_task(self._ssh.run(), name="ssh-listener"),
            asyncio.create_task(self._mqtt_event_loop(), name="mqtt-event-loop"),
            asyncio.create_task(self._ssh_event_loop(), name="ssh-event-loop"),
            asyncio.create_task(self._healthcheck_loop(), name="healthcheck-loop"),
        ]

    async def stop(self):
        if not self.status.running:
            logger.warning("ServiceManager is not running")
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
        logger.info("ServiceManager stopped successfully")

    # Hier wird die Logik implementiert, wenn eine MQTT oder SSH Nachricht reinkommt.
    async def _mqtt_event_loop(self):
        while self.status.running:
            event = await self.mqtt_queue.get()
            try:
                logger.debug(f"Received event in MQTT Queue: {event}")
                await self._handle_mqtt_event(self.ctx, event)
            except Exception as e:
                self.status.last_error = str(e)

    async def _ssh_event_loop(self):
        while self.status.running:
            event = await self.ssh_queue.get()
            try:
                logger.debug(f"Received event in SSH Queue: {event}")
                await self._handle_ssh_event(self.ctx, event)
            except Exception as e:
                self.status.last_error = str(e)

    async def _handle_mqtt_event(self, ctx: RuntimeContext, event: dict):
        logger.debug(f"Handling MQTT event: {event}")
        await self._mqtt.publish_resolve(qumea_activeAlertId=123, qumea_roomId="room-1")
        logger.debug("Published resolve message to MQTT")
        baseURL = ctx.http.base_url
        logger.debug(f"Making HTTP GET request to {baseURL}/resolve")
        await ctx.http.get(f"{baseURL}/resolve")


    async def _handle_ssh_event(self, ctx: RuntimeContext, event: dict):
        logger.debug(f"Handling SSH event: {event}")
        await self._mqtt.publish_resolve(qumea_activeAlertId=123, qumea_roomId="room-1")
        logger.debug("Published resolve message to MQTT")
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
