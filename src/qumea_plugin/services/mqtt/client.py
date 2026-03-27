import asyncio
import json
import time
from dataclasses import dataclass

import paho.mqtt.client as paho


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
            self._client.publish(topic, payload=payload)

    # Sende Quittierung auf Event Topic
    async def publish_resolve(self, qumea_activeAlertId: int, qumea_roomId: str):
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

        client = paho.Client(client_id=self.cfg.client_id, protocol=paho.MQTTv311)
        self._client = client

        if self.cfg.username is not None:
            client.username_pw_set(self.cfg.username, self.cfg.password)

        def on_connect(cl, userdata, flags, rc, properties=None):
            # rc == 0 => ok
            print("MQTT connected rc=", rc)
            # Alert-Topic
            cl.subscribe(self.cfg.alert_in_topic)
            # Keepalive-Topic
            cl.subscribe(self.cfg.keepalive_in_topic)
            # Confirm-Topic
            cl.subscribe(self.cfg.confirm_in_topic)
            # Resolve-Topic
            cl.subscribe(self.cfg.resolve_in_topic)

        def on_disconnect(cl, userdata, rc, properties=None):
            print("MQTT disconnected rc=", rc)

        def on_message(cl, userdata, msg):
            topic = msg.topic
            payload = msg.payload.decode(errors="replace")
            print(f"MQTT message topic={topic} payload={payload}")

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
                    return

                data["msg_type"] = msg_type

                if msg_type == "alert":
                    print(f"Parsed MQTT alert event: {data}")

                    events_filter = self.cfg.events_to_handle
                    if events_filter:
                        ev_type = data.get("alertType")
                        if ev_type is None or not events_filter.get(ev_type, False):
                            return

                self.mqtt_queue.put_nowait(data)

            # MQTT Callback läuft in eigenem Thread, daher call_soon_threadsafe um in den asyncio Loop zu wechseln
            self._loop.call_soon_threadsafe(handle)

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        print(f"Connecting MQTT {self.cfg.host}:{self.cfg.port} id={self.cfg.client_id} user={self.cfg.username}")
        client.connect(self.cfg.host, self.cfg.port, keepalive=30)

        # startet Netzwerkloop in eigenem Thread
        client.loop_start()

        # Läuft bis stop
        await self._stop.wait()