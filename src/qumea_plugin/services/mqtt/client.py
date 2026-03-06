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
    def alert_topic(self) -> str:
        return f"qumea/tenant/{self.tenant_id}/public/v1/alert/+/type/+"

    @property
    def keepalive_in_topic(self) -> str:
        return f"qumea/tenant/{self.tenant_id}/public/v1/keepalive/in"

    @property
    def keepalive_out_topic(self) -> str:
        return f"qumea/tenant/{self.tenant_id}/public/v1/keepalive/out"


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
            topic = f"qumea/tenant/{self.cfg.tenant_id}/public/v1/integration/{self.cfg.integrationId}/alive"
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
                    "resolverName": "axelion",
                }
            )
            topic = f"qumea/tenant/{self.cfg.tenant_id}/public/v1/alert/{qumea_activeAlertId}/resolve"
            self._client.publish(topic, payload=payload)

    async def run(self):
        # asyncio-loop merken, damit wir aus dem MQTT-Thread sicher reinposten können
        self._loop = asyncio.get_running_loop()

        client = paho.Client(client_id=self.cfg.client_id, protocol=paho.MQTTv311)
        self._client = client

        if self.cfg.username is not None:
            client.username_pw_set(self.cfg.username, self.cfg.password)

        def on_connect(cl, userdata, flags, rc, properties=None):
            # rc == 0 => ok
            print("MQTT connected rc=", rc)
            # Alert-Topic abonnieren, damit wir die Events empfangen können
            cl.subscribe(self.cfg.alert_topic)
            # Keepalive-Topic abonnieren, damit wir wissen, dass die Verbindung zum Broker noch steht (der Broker veröffentlicht dort regelmäßig Nachrichten)
            cl.subscribe(self.cfg.keepalive_in_topic)

        def on_disconnect(cl, userdata, rc, properties=None):
            print("MQTT disconnected rc=", rc)

        def on_message(cl, userdata, msg):
            topic = msg.topic
            payload = msg.payload.decode(errors="replace")
            print(f"MQTT message topic={topic} payload={payload}")

            # ins asyncio sicher reinreichen
            def handle():
                # keepalive
                if topic == self.cfg.keepalive_in_topic:
                    self.ka_queue.put_nowait(time.time())
                    return

                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    return

                if self.cfg.events_to_handle:
                    ev_type = data.get("alertType")
                    if ev_type is None:
                        return
                    if not self.cfg.events_to_handle.get(ev_type, False):
                        return

                self.mqtt_queue.put_nowait(data)

            self._loop.call_soon_threadsafe(handle)

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        print(f"Connecting MQTT {self.cfg.host}:{self.cfg.port} id={self.cfg.client_id} user={self.cfg.username}")
        client.connect(self.cfg.host, self.cfg.port, keepalive=30)

        # startet Netzwerkloop in eigenem Thread
        client.loop_start()

        # asyncio-task bleibt “am Leben” bis stop
        await self._stop.wait()