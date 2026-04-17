# src/qumea_plugin/services/runtime/manager.py
import asyncio
import json
import time
from dataclasses import dataclass
from typing import Optional
import logging
from sqlalchemy.exc import IntegrityError

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
from ...db.models import EventStatus

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
            print(f"Ater Handled: {event}")

    async def _ssh_event_loop(self):
        while self.status.running:
            event = await self.ssh_queue.get()
            try:
                logger.debug(f"Received event in SSH Queue: {event}")
                await self._handle_ssh_event(self.ctx, event)
            except Exception as e:
                self.status.last_error = str(e)

    async def _handle_mqtt_event(self, ctx: RuntimeContext, event: dict):
        logger.debug("Handling MQTT event: %s", event)

        db = ctx.SessionLocal()
        baseURL = ctx.http.base_url
        ascom_id = None

        def send_http_alert_request(event):
            success = ctx.http.get(f"{baseURL}/sendUCM?ascom_id={ascom_id}", timeout=5.0)
            if success:
                return True
            else:
                return False
            

        def handle_alert(event):
            try:
                room: Room | None = db.query(Room).filter(Room.room_name == event.get("roomName")).first()
                if not room:
                    logger.warning("Room not found for event: %s", event.get("roomName"))
                    return
               
                logger.debug("Found room in DB: %s with ASCOM ID: %s", room.room_name, room.ascom_device_id)
                
                # Set Room ID from Message
                room.qumea_roomId = event.get("roomId")

                active_alert_id = event.get("activeAlertId")

                if not active_alert_id:
                    logger.warning("Missing activeAlertId in event: %s", event)
                    db.commit()
                    return

                existing_open_event: Event | None = (
                    db.query(Event)
                    .filter(
                        Event.qumea_activeAlertId == active_alert_id,
                        Event.status.notin_([
                            EventStatus.DONE.value,
                            EventStatus.FAILED.value,
                            EventStatus.TIMEOUT.value,
                        ]),
                    )
                    .first()
                )

                logger.debug("Existing open event for activeAlertId %s: %s", active_alert_id, existing_open_event)

                if existing_open_event is None:
                    new_event = Event(
                        room_name=event.get("roomName"),
                        status=EventStatus.NEW.value,
                        qumea_alertType=event.get("alertType"),
                        qumea_activeAlertId=active_alert_id,
                        qumea_roomId=event.get("roomId"),
                    )
                    db.add(new_event)
                    logger.info("Created new event for activeAlertId=%s", active_alert_id)
                else:
                    existing_open_event.touch()
                    logger.info("Open event already exists for activeAlertId=%s, skipping insert", active_alert_id)
                
                db.commit()

                # Make Action to Telecare via HTTP
                try:
                    ascom_id = (
                        db.query(Room.ascom_device_id)
                        .filter(Room.room_name == event.get("roomName"))
                        .scalar()
                    )
                except Exception:
                    logger.exception("Error while querying ASCOM device ID for room: %s", event.get("roomName"))
                    ascom_id = None

                if ascom_id is None:
                    logger.warning("ASCOM device ID not found for room: %s", event.get("roomName"))
                    return

            except Exception:
                db.rollback()
                logger.exception("Error while handling MQTT event")
                return

            finally:
                logger.debug("Ascom ID found. {ascom_id}")

            if ascom_id:
                try:
                    existing_open_event: Event | None = (
                        db.query(Event)
                        .filter(
                            Event.qumea_activeAlertId == active_alert_id,
                            Event.status.notin_([
                                EventStatus.DONE.value,
                                EventStatus.FAILED.value,
                                EventStatus.TIMEOUT.value,
                            ]),
                        )
                        .first()
                    )

                    if existing_open_event is None:
                        logger.debug("No existing Event found with active alertID: {active_alert_id}")
                        return


                    if existing_open_event(Event.status) == EventStatus.NEW.value:
                        request = send_http_alert_request(event=event)
                    
                    elif existing_open_event(Event.status) == EventStatus.WAITING_SSH_CONFIRM.value:
                        request = send_http_alert_request(event=event)
                    
                    else:
                        logger.debug(f"Alert already created in Telecare for Device: {ascom_id}")

                    if request:
                        existing_open_event.status = EventStatus.WAITING_SSH_CONFIRM.value
                        logger.debug(f"Alert send successfully via HTTP to UCM")
                    else:
                        logger.error(f"HTTP Request to UCM Failed")

                except Exception:
                    logger.exception("Error while updating event status for activeAlertId=%s", active_alert_id)
            else:
                logger.debug("No ascom_id found")
            db.commit()


        def handle_confirm(event):
            logger.debug("Handle Confirm Event")
            active_alert_id = event.get("activeAlertId")
            try:
                room: Room | None = db.query(Room).filter(Room.room_name == event.get("roomName")).first()
                if not room:
                    logger.warning("Room not found for event: %s", event.get("roomName"))
                    return
               
                logger.debug("Found room in DB: %s with ASCOM ID: %s", room.room_name, room.ascom_device_id)

                existing_open_event: Event | None = (
                        db.query(Event)
                        .filter(
                            Event.qumea_activeAlertId == active_alert_id,
                            Event.status.in_([
                                EventStatus.WAITING_MQTT_RESOLVE.value,
                            ]),
                        )
                        .first()
                    )
                
                if existing_open_event is None:
                    logger.warning(f"No Waiting MQTT Event found for Alert ID: {active_alert_id}")
                    return
                else:
                    existing_open_event.status = EventStatus.DONE.value
                    db.commit()
                    logger.info(f"Alert ID: {active_alert_id} successfully resolved")

            except Exception:
                logger.exception(Exception)

        def handle_resolved(event):
            logger.debug("Handle Resolve Event")
            active_alert_id = event.get("activeAlertId")
            try:
                room: Room | None = db.query(Room).filter(Room.room_name == event.get("roomName")).first()
                if not room:
                    logger.warning("Room not found for event: %s", event.get("roomName"))
                    return
               
                logger.debug("Found room in DB: %s with ASCOM ID: %s", room.room_name, room.ascom_device_id)

                existing_open_event: Event | None = (
                        db.query(Event)
                        .filter(
                            Event.qumea_activeAlertId == active_alert_id,
                            Event.status.notin_([
                                EventStatus.DONE.value,
                                EventStatus.FAILED.value,
                                EventStatus.TIMEOUT.value,
                            ]),
                        )
                        .first()
                    )
                
                if existing_open_event is None:
                    logger.warning(f"No Waiting MQTT Event found for Alert ID: {active_alert_id}")
                    return
                else:
                    existing_open_event.status = EventStatus.DONE.value
                    db.commit()
                    logger.info(f"Alert ID: {active_alert_id} successfully resolved")

            except Exception:
                logger.exception(Exception)

        handlers = {
            "alert": handle_alert,
            "confirm": handle_confirm,
            "resolved": handle_resolved

        }

        msg_type = event.get("msg_type")
        handler = handlers.get(msg_type)
        if handler:
            # start specific handler from handlers
            handler(event)
        else:
            logger.debug(f"Unknown event type: {msg_type}")
        
        db.close()


       


    async def _handle_ssh_event(self, ctx: RuntimeContext, event: dict):
        logger.debug("Handling SSH event: %s", event)

        db = ctx.SessionLocal()

        def get_active_event_from_db(room_name: str) -> Optional[Event]:
            return db.query(Event).filter(
                Event.room_name == room_name,
                Event.status.notin_([
                    EventStatus.DONE.value,
                    EventStatus.FAILED.value,
                    EventStatus.TIMEOUT.value,
                    EventStatus.WAITING_MQTT_RESOLVE.value
                ]),
            ).first()
        
        def resolve_action(active_event):
            qumea_roomId = active_event(Event.qumea_roomId)
            qumea_activeAlertId = active_event(Event.qumea_activeAlertId)
            room_name = active_event(Event.room_name)
            self._mqtt.publish_resolve(qumea_activeAlertId=qumea_activeAlertId, qumea_roomId=qumea_roomId)
            active_event.status = EventStatus.WAITING_MQTT_RESOLVE.value
            db.commit()
            logger.info(f"Event change to WAITING_MQTT_RESOLVE: {room_name}")


        def handle_fall(event):
            logger.debug("Make Fall Action for event: %s", event)
            active_event = get_active_event_from_db(event.get("location"))
            if not active_event:
                logger.debug(f"No active event found in DB for room: {event.get('location')}. Cannot process BedCancel.")
                return
            active_event.status = EventStatus.RUNNING.value
            db.commit()
            logger.info(f"Event change to RUNNING: {event.get('location')}")
            


        def handle_bed(event):
            logger.debug("Make Bed Action for event: %s", event)
            active_event = get_active_event_from_db(event.get("location"))
            if not active_event:
                logger.debug(f"No active event found in DB for room: {event.get('location')}. Cannot process BedCancel.")
                return
            active_event.status = EventStatus.RUNNING.value
            db.commit()
            logger.info(f"Event change to RUNNING: {event.get('location')}")

        def handle_no_return(event):
            logger.debug("Make No Return Action for event: %s", event)
            active_event = get_active_event_from_db(event.get("location"))
            if not active_event:
                logger.debug(f"No active event found in DB for room: {event.get('location')}. Cannot process BedCancel.")
                return
            active_event.status = EventStatus.RUNNING.value
            db.commit()
            logger.info(f"Event change to RUNNING: {event.get('location')}")
       
        def handle_fall_cancel(event):
            logger.debug("Make Fall Cancel Action for event: %s", event)
            active_event = get_active_event_from_db(event.get("location"))
            if not active_event:
                logger.debug(f"No active event found in DB for room: {event.get('location')}. Cannot process FallCancel.")
                return
            logger.debug("Make Resolve Action for event: %s", active_event)
            resolve_action(active_event)



       
        def handle_bed_cancel(event):
            logger.debug("Make Bed Cancel Action for event: %s", event)
            active_event = get_active_event_from_db(event.get("location"))
            if not active_event:
                logger.debug(f"No active event found in DB for room: {event.get('location')}. Cannot process FallCancel.")
                return
            logger.debug("Make Resolve Action for event: %s", active_event)
            resolve_action(active_event)
       
        def handle_no_return_cancel(event):
            logger.debug("Make No Return Cancel Action for event: %s", event)
            active_event = get_active_event_from_db(event.get("location"))
            if not active_event:
                logger.debug(f"No active event found in DB for room: {event.get('location')}. Cannot process FallCancel.")
                return
            logger.debug("Make Resolve Action for event: %s", active_event)
            resolve_action(active_event)


        def handle_call(event):
            eventtext = event.get("eventtext", "")
            call_handler = call_handlers.get(eventtext)
            if call_handler:
                # start specific call handle from call_handlers
                call_handler(event)
            else:
                logger.debug(f"Unknown Call eventtext: {eventtext}")

        def handle_call_cancel(event):
            eventtext = event.get("eventtext", "")
            call_cancel_handler = call_cancel_handlers.get(eventtext)
            if call_cancel_handler:
                # start specific call cancel handle from call_cancel_handlers
                call_cancel_handler(event)
            else:
                logger.debug(f"Unknown CallCancel eventtext: {eventtext}")

        def handle_nurse_present(event):
            logger.debug("Make Nurse Presence Action for event: %s", event)
            active_event = get_active_event_from_db(event.get("location"))
            if not active_event:
                logger.debug(f"No active event found in DB for room: {event.get('location')}. Cannot process Nurse Presence Action.")
                return
            logger.debug("Make Resolve Action for event: %s", active_event)
            resolve_action(active_event)

        def handle_nurse_present_cancel(event):
            active_event = get_active_event_from_db(event.get("location"))
            if not active_event:
                logger.debug(f"No active event found in DB for room: {event.get('location')}. Cannot process NursePresentCancel.")
                return
            logger.debug("Make Nurse Presence Cancel Action for event: %s", active_event)
            resolve_action(active_event)
       

        # Handlers
        handlers = {
            "Call": handle_call,
            "CallCancel": handle_call_cancel,
            "NursePresent": handle_nurse_present,
            "NursePresentCancel": handle_nurse_present_cancel,
        }

        call_handlers = {
            "Fall": handle_fall,
            "Bed": handle_bed,
            "NoReturn": handle_no_return
        }

        call_cancel_handlers = {
            "Fall": handle_fall_cancel,
            "Bed": handle_bed_cancel,
            "NoReturn": handle_no_return_cancel    
        }

        event_type = event.get("type")
        handler = handlers.get(event_type)

        if handler:
            # start specific handler from handlers
            handler(event)
        else:
            logger.debug(f"Unknown event type: {event_type}")
        db.close()


    async def _healthcheck_loop(self):
        last_60s_task = time.time()
        baseURL = self.ctx.http.base_url

        while self.status.running:
            now = time.time()

            # --- Queue leeren ---
            while True:
                try:
                    ts = self.ka_queue.get_nowait()
                    self.status.last_broker_keepalive = ts
                except asyncio.QueueEmpty:
                    break

            # --- 120s Check ---
            last = self.status.last_broker_keepalive
            if last is not None and (now - last) > 120.0:
                try:
                    await self.ctx.http.get(f"{baseURL}/sendUCM?ascom_id=stoerung", timeout=5.0)
                except Exception as e:
                    self.status.last_error = str(e)

            # --- 60s Task ---
            if (now - last_60s_task) > 60.0:
                try:
                    self._mqtt.publish_integration_keepalive()
                except Exception as e:
                    self.status.last_error = str(e)
                last_60s_task = now

            await asyncio.sleep(5.0)

    def get_status(self) -> dict:
        return {
            "running": self.status.running,
            "started_at": self.status.started_at,
            "last_broker_keepalive": self.status.last_broker_keepalive,
            "last_error": self.status.last_error,
            "tasks": [t.get_name() for t in self._tasks if not t.done()],
        }
