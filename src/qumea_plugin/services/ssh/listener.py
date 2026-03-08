import asyncio
import contextlib
from dataclasses import dataclass
import logging
import xml.etree.ElementTree as ET
import time

logger = logging.getLogger(__name__)

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
        self.deduplicator = Deduplicator(window_seconds= 5.0)
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

                    should_process, event = self.deduplicator.should_process(line)
                    if should_process and event:
                        logger.debug(f"New event parsed: {event}")
                        await self.ssh_queue.put(event)
                    else:
                        logger.debug(f"Duplicate or unprocessable line skipped: {line.strip()}")
                        pass

            finally:
                # Shell sauber beenden
                if process.stdin:
                    process.stdin.write("exit\n")
                    await process.stdin.drain()
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(process.wait(), timeout=2)
                if process.exit_status is None:
                    process.terminate()

class Deduplicator:
    def __init__(self, window_seconds: float = 5.0):
        self.window_seconds = window_seconds
        self._last_seen:dict[tuple, float] = {}

    def parse_line(self, line: str) -> dict | None:
        line = line.strip("\r\n")
        if not line:
            return None
       
        try:
            elem = ET.fromstring(line)
        except ET.ParseError:
            return None
       
        return {
            "type": elem.tag,
            **elem.attrib
        }

    def is_duplicate(self, item):
        if item in self.last_seen:
            return True
        self.last_seen.add(item)
        return False
   
    def build_key(self, event: dict) -> tuple:
        return (
            event.get("type"),
            event.get("tracelogid"),
            event.get("time"),
            event.get("device"),
            event.get("eventtext"),
        )

    def should_process(self, line: str) -> tuple[bool, dict | None]:
        event = self.parse_line(line)
        if not event:
            return False, None
       
        now = time.monotonic()
        key = self.build_key(event)

        self.last_seen = self._last_seen.get(key)
        if self.last_seen is not None and (now - self.last_seen) < self.window_seconds:
            return False, None
       
        self._last_seen[key] = now
        self._cleanup(now)
        return True, event
   
    def _cleanup(self, now: float) -> None:
        limit = now - self.window_seconds
        old_keys = [k for k, ts in self._last_seen.items() if ts < limit]
        for key in old_keys:
            del self._last_seen[key]