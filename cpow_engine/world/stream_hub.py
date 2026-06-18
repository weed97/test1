"""월드 스트림 이벤트 — WebSocket AOI delta."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from queue import Empty, Full, Queue
from typing import Any


@dataclass
class StreamSubscription:
    connection_id: str
    area_id: str
    actor_id: str
    x: float
    z: float
    radius_m: float = 128.0
    queue: Queue = field(default_factory=Queue)

    def matches_aoi(self, event: dict[str, Any]) -> bool:
        from cpow_engine.world.aoi import in_aoi

        ex = float(event.get("x", self.x))
        ez = float(event.get("z", self.z))
        if event.get("type") == "inventory_delta":
            return str(event.get("actor_id", "")) == self.actor_id
        return in_aoi(self.x, self.z, ex, ez, self.radius_m)


class WorldStreamHub:
    """에리어별 구독 — delta만 푸시 (thread-safe queue)."""

    def __init__(self) -> None:
        self._subs: dict[str, StreamSubscription] = {}

    async def subscribe(self, sub: StreamSubscription) -> None:
        self._subs[sub.connection_id] = sub

    async def unsubscribe(self, connection_id: str) -> None:
        self._subs.pop(connection_id, None)

    async def update_pose(
        self,
        connection_id: str,
        x: float,
        z: float,
        radius_m: float | None = None,
    ) -> None:
        sub = self._subs.get(connection_id)
        if sub is None:
            return
        sub.x = x
        sub.z = z
        if radius_m is not None:
            sub.radius_m = radius_m

    def publish_sync(self, area_id: str, event: dict[str, Any]) -> int:
        event = {**event, "ts": time.time()}
        sent = 0
        for sub in self._subs.values():
            if sub.area_id != area_id or not sub.matches_aoi(event):
                continue
            try:
                sub.queue.put_nowait(event)
                sent += 1
            except Full:
                pass
        return sent

    async def drain(self, connection_id: str, timeout: float = 25.0) -> dict[str, Any] | None:
        sub = self._subs.get(connection_id)
        if sub is None:
            return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                return sub.queue.get_nowait()
            except Empty:
                await asyncio.sleep(0.05)
        return {"type": "ping", "ts": time.time()}

    @staticmethod
    def dumps(event: dict[str, Any]) -> str:
        return json.dumps(event, ensure_ascii=False)


_HUB = WorldStreamHub()


def get_stream_hub() -> WorldStreamHub:
    return _HUB
