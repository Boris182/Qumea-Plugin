import asyncio
import json
import time
from dataclasses import dataclass
import logging
import paho.mqtt.client as paho
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes
import ssl

logger = logging.getLogger(__name__)

@dataclass
class MqttConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    tenant_id: str
    client_id: str
    integrationId: str
    events_to_handle: dict | None

    @property
    def alert_in_topic(self) -> str:
        return f"qumea/tenant/{self.tenant_id}/public/v1/alert/+/type/+"
    
    @property
    def confirm_in_topic(self) -> str:
        return f"qumea/tenant/{self.tenant_id}/public/v1/alert/confirm/+"
    
    @property
    def resolve_in_topic(self) -> str:
        return f"qumea/tenant/{self.tenant_id}/public/v1/alert/+/resolved"

    @property
    def keepalive_in_topic(self) -> str:
        return f"qumea/tenant/{self.tenant_id}/public/v1/alive"

    @property
    def keepalive_out_topic(self) -> str:
        return f"qumea/tenant/{self.tenant_id}/public/v1/integration/{self.integrationId}/alive"


class MqttWorker:
    def __init__(self, cfg: MqttConfig, event_queue: asyncio.Queue, ka_queue: asyncio.Queue):
        self.cfg = cfg
        self.mqtt_queue = event_queue
        self.ka_queue = ka_queue
        self._stop = asyncio.Event()

        self._client: paho.Client | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def stop(self):
        self._stop.set()
        if self._client is not None:
            try:
                self._client.disconnect()
                self._client.loop_stop()
            except Exception:
                pass
    
    # Publish Keep Alive
    async def publish_integration_keepalive(self, issueActive: bool, issues: list[dict]):
        if self._client is not None:
            payload = json.dumps(
                {
                    "timestamp": time.time(),
                    "tenant": self.cfg.tenant_id,
                    "integrationId": self.cfg.integrationId,
                    "issueActive": issueActive,
                    "issues": issues if issueActive else [],
                }
            )
            topic = self.cfg.keepalive_out_topic
            logger.debug(f"Send Keepalive with payload: {payload}")
            self._client.publish(topic, payload=payload)

    # Sende Quittierung auf Event Topic
    async def publish_resolve(self, qumea_activeAlertId: int, qumea_roomId: str):
        logger.debug(f"Notifying Qumea of resolved alertId={qumea_activeAlertId} roomId={qumea_roomId}")
        if self._client is not None:
            payload = json.dumps(
                {
                    "roomId": qumea_roomId,
                    "activeAlertId": qumea_activeAlertId,
                    "tenant": self.cfg.tenant_id,
                    "resolveAllAlertsInRoom": True,
                    "resolverName": self.cfg.integrationId,
                }
            )
            topic = f"qumea/tenant/{self.cfg.tenant_id}/public/v1/alert/{qumea_activeAlertId}/resolve"
            self._client.publish(topic, payload=payload)

    async def run(self):
        self._loop = asyncio.get_running_loop()

        client = paho.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=self.cfg.client_id,
            protocol=paho.MQTTv5,
            transport="tcp",
        )
        self._client = client

        if self.cfg.username:
            client.username_pw_set(self.cfg.username, self.cfg.password)

        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        client.tls_insecure_set(False)

        client.enable_logger(logger)

        def on_connect(cl, userdata, flags, reason_code, properties):
            logger.info(
                "MQTT connected: reason_code=%s flags=%s properties=%s",
                reason_code, flags, properties
            )

            for topic in [
                self.cfg.alert_in_topic,
                self.cfg.keepalive_in_topic,
                self.cfg.confirm_in_topic,
                self.cfg.resolve_in_topic,
            ]:
                res, mid = cl.subscribe(topic, qos=0)
                logger.info("Subscribe sent: topic=%s result=%s mid=%s", topic, res, mid)

        def on_disconnect(cl, userdata, disconnect_flags, reason_code, properties):
            logger.error(
                "MQTT disconnected: reason_code=%s disconnect_flags=%s properties=%s",
                reason_code, disconnect_flags, properties
            )

        def on_subscribe(cl, userdata, mid, reason_code_list, properties):
            logger.info(
                "SUBACK: mid=%s reason_codes=%s properties=%s",
                mid, reason_code_list, properties
            )

        def on_message(cl, userdata, msg):
            topic = msg.topic
            payload = msg.payload.decode(errors="replace")
            logger.debug("MQTT message topic=%s payload=%s", topic, payload)

            def handle():
                if topic == self.cfg.keepalive_in_topic:
                    self.ka_queue.put_nowait(time.time())
                    return

                if "/alert/confirm" in topic:
                    msg_type = "confirm"
                elif topic.endswith("/resolved"):
                    msg_type = "resolved"
                elif "/alert/" in topic:
                    msg_type = "alert"
                else:
                    return

                try:
                    data = json.loads(payload)
                    if not isinstance(data, dict):
                        return
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON payload on topic=%s", topic)
                    return

                data["msg_type"] = msg_type

                if msg_type == "alert":
                    events_filter = self.cfg.events_to_handle
                    if events_filter:
                        ev_type = data.get("alertType")
                        if ev_type is None or not events_filter.get(ev_type, False):
                            return

                self.mqtt_queue.put_nowait(data)

            self._loop.call_soon_threadsafe(handle)

        def on_log(cl, userdata, level, buf):
            logger.debug("PAHO LOG level=%s: %s", level, buf)

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_subscribe = on_subscribe
        client.on_message = on_message
        client.on_log = on_log

        # MQTT v5: leer wie in Node-RED "Session-Zeitablauf" leer
        connect_props = Properties(PacketTypes.CONNECT)
        # Nicht setzen = Broker-Default / keine explizite Session Expiry

        logger.info(
            "Connecting MQTT v5 to host=%s port=%s client_id=%s",
            self.cfg.host,
            self.cfg.port,
            self.cfg.client_id,
        )

        client.connect(
            host=self.cfg.host,          # nur mqtt.qumea.cloud
            port=self.cfg.port,          # 8883
            keepalive=60,                # wie Node-RED
            clean_start=True,            # "Bereinigter Start"
            properties=connect_props,
        )

        client.loop_start()
        await self._stop.wait()