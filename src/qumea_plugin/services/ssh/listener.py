import asyncio
from dataclasses import dataclass

@dataclass
class SshConfig:
    host: str
    port: int
    username: str
    password: str | None = None
    command: str = "tail -f /var/log/something.log"

class SshListener:
    def __init__(self, cfg: SshConfig, event_queue: asyncio.Queue):
        self.cfg = cfg
        self.event_queue = event_queue
        self._stop = asyncio.Event()

    async def stop(self):
        self._stop.set()

    async def run(self):
        import asyncssh

        async with asyncssh.connect(
            self.cfg.host,
            port=self.cfg.port,
            username=self.cfg.username,
            password=self.cfg.password,
            known_hosts=None,  # ggf. bei dir sauberer lösen
        ) as conn:
            process = await conn.create_process(self.cfg.command)

            while not self._stop.is_set():
                line = await process.stdout.readline()
                if not line:
                    await asyncio.sleep(0.2)
                    continue

                # TODO: parse stdout line -> event
                # Beispiel:
                #event = {"source": "ssh", "line": line.strip()}
                #await self.event_queue.put(event)

            process.terminate()