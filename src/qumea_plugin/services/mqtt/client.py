import asyncio
import json
import time
from dataclasses import dataclass

@dataclass
class MqttConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    subscribe_topic: str
    keepalive_in_topic: str       # topic vom broker, den du erwartest
    keepalive_out_topic: str      # topic, auf den du publishst

class MqttWorker:
    def __init__(self, cfg: MqttConfig, event_queue: asyncio.Queue, ka_queue: asyncio.Queue):
        self.cfg = cfg
        self.event_queue = event_queue
        self.ka_queue = ka_queue
        self._stop = asyncio.Event()

    async def stop(self):
        self._stop.set()

    async def run(self):
        """
        - subscribt subscribe_topic und keepalive_in_topic
        - legt Events in event_queue
        - legt KeepAlive-Timestamps in ka_queue
        """
        from asyncio_mqtt import Client, MqttError

        try:
            async with Client(
                hostname=self.cfg.host,
                port=self.cfg.port,
                username=self.cfg.username,
                password=self.cfg.password,
            ) as client:
                async with client.unfiltered_messages() as messages:
                    await client.subscribe(self.cfg.subscribe_topic)
                    await client.subscribe(self.cfg.keepalive_in_topic)

                    while not self._stop.is_set():
                        msg = await messages.get()
                        topic = str(msg.topic)
                        payload = msg.payload.decode(errors="replace")

                        if topic == self.cfg.keepalive_in_topic:
                            # signal an Manager: broker keepalive received
                            await self.ka_queue.put(time.time())
                            continue

                        if topic == self.cfg.subscribe_topic:
                            try:
                                data = json.loads(payload)
                                await self.event_queue.put(data)
                            except json.JSONDecodeError:
                                # optional: log bad payload
                                pass
        except MqttError:
            # optional: reconnect strategy (Manager kann restart triggern)
            return

    async def keepalive_publisher(self):
        """sendet jede Minute keepalive_out_topic"""
        from asyncio_mqtt import Client

        async with Client(
            hostname=self.cfg.host,
            port=self.cfg.port,
            username=self.cfg.username,
            password=self.cfg.password,
        ) as client:
            while not self._stop.is_set():
                await client.publish(self.cfg.keepalive_out_topic, payload="1", qos=0, retain=False)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=60.0)
                except asyncio.TimeoutError:
                    pass