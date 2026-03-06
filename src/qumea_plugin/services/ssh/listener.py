import asyncio
import contextlib
from dataclasses import dataclass

@dataclass
class SshConfig:
    host: str
    port: int
    username: str
    password: str | None = None

class SshListener:
    def __init__(self, cfg: SshConfig, ssh_queue: asyncio.Queue):
        self.cfg = cfg
        self.ssh_queue = ssh_queue
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
            known_hosts=None,
        ) as conn:
            # Startet eine Login-Shell auf dem Remote-Host
            process = await conn.create_process(
                term_type="xterm",
                encoding="utf-8",
            )

            try:
                while not self._stop.is_set():
                    # Shell gibt oft erst nach Prompt/Newline aus
                    line = await process.stdout.readline()
                    if not line:
                        await asyncio.sleep(0.2)
                        continue

                    line = line.rstrip("\r\n")

                    # TODO: parse stdout line -> event
                    # event = {"source": "ssh", "line": line}
                    # await self.ssh_queue.put(event)

            finally:
                # Shell sauber beenden
                if process.stdin:
                    process.stdin.write("exit\n")
                    await process.stdin.drain()
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(process.wait(), timeout=2)
                if process.exit_status is None:
                    process.terminate()