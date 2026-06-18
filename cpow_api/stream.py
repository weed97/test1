"""WebSocket — /v1/world/stream AOI delta."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import WebSocket, WebSocketDisconnect

from cpow_engine.world.service import get_world_service
from cpow_engine.world.stream_hub import StreamSubscription, get_stream_hub


async def world_stream_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    hub = get_stream_hub()
    conn_id = f"ws_{uuid.uuid4().hex[:10]}"
    sub: StreamSubscription | None = None

    async def wait_subscribe() -> StreamSubscription:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if str(msg.get("type", "")).lower() != "subscribe":
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "reason": "expected_subscribe",
                }))
                continue
            area_id = str(msg.get("area_id", ""))
            if not area_id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "reason": "missing_area_id",
                }))
                continue
            subscription = StreamSubscription(
                connection_id=conn_id,
                area_id=area_id,
                actor_id=str(msg.get("actor_id", "anonymous")),
                x=float(msg.get("x", 0.0)),
                z=float(msg.get("z", 0.0)),
                radius_m=float(msg.get("radius_m", 128.0)),
            )
            await hub.subscribe(subscription)
            svc = get_world_service()
            await websocket.send_text(json.dumps({
                "type": "subscribed",
                "connection_id": conn_id,
                "area_id": area_id,
                "inventory": svc.get_inventory(area_id, subscription.actor_id).get("inventory", {}),
                "drops": svc.drops_in_aoi(
                    area_id, subscription.x, subscription.z, subscription.radius_m,
                ).get("drops", []),
            }, ensure_ascii=False))
            return subscription

    async def reader() -> None:
        nonlocal sub
        assert sub is not None
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            mtype = str(msg.get("type", "")).lower()
            if mtype == "pose":
                await hub.update_pose(
                    conn_id,
                    float(msg.get("x", sub.x)),
                    float(msg.get("z", sub.z)),
                    float(msg["radius_m"]) if "radius_m" in msg else None,
                )
                sub.x = float(msg.get("x", sub.x))
                sub.z = float(msg.get("z", sub.z))
            elif mtype == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    async def writer() -> None:
        while True:
            event = await hub.drain(conn_id, timeout=25.0)
            if event:
                await websocket.send_text(json.dumps(event, ensure_ascii=False))

    try:
        sub = await wait_subscribe()
        await asyncio.gather(reader(), writer())
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        await hub.unsubscribe(conn_id)
