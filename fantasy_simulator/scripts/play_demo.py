#!/usr/bin/env python3
"""Eldoria live play demo — API + sim clock + siege + commanders.

Usage:
  # Terminal A
  ELDORIA_DEMO=1 uvicorn api.server:app --host 127.0.0.1 --port 8765

  # Terminal B
  python3 scripts/play_demo.py --live

  # Or in-process (no server):
  python3 scripts/play_demo.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8765"


def _print(title: str, payload: dict) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:4000])


def _run_live() -> int:
    import urllib.error
    import urllib.request

    def req(method: str, path: str, body: dict | None = None) -> dict:
        url = BASE + path
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {path}: {detail}") from exc

    print("▶ API 헬스 체크")
    health = req("GET", "/v1/health")
    _print("health", health)

    print("\n▶ 새 게임 (hybrid · precision · seed 42)")
    sess = req(
        "POST",
        "/v1/session/new",
        {
            "mode": "rule",
            "temporal_mode": "precision",
            "game_mode": "hybrid",
            "seed": 42,
        },
    )
    sid = sess["session_id"]
    _print("session", sess)

    print("\n▶ 데모 부트스트랩 (왕국 + 군대 + 공성 개시)")
    boot = req("POST", "/v1/demo/bootstrap", {"session_id": sid})
    _print("bootstrap", boot)

    print("\n▶ 시뮬 시계 상태")
    sim = req("GET", f"/v1/sim/status?session_id={sid}")
    _print("sim_clock", sim.get("sim_clock", sim))

    print("\n▶ 지휘관 로스터 (5명)")
    cmds = req("GET", f"/v1/kingdom/commanders?session_id={sid}")
    _print("commanders", cmds)

    war_id = boot.get("war_id", "")
    if war_id:
        print("\n▶ 수성 명령: 지휘관 호위 + 성벽 뒤")
        cmd = req(
            "POST",
            "/v1/kingdom/war/command",
            {
                "session_id": sid,
                "war_id": war_id,
                "doctrine": "protect_commanders",
                "posture": "behind_wall",
            },
        )
        _print("war_command", cmd)

    print("\n▶ 실시간 sim tick ×12 (5초 × 8회 ≈ 8 sim 분)")
    for i in range(8):
        tick = req("POST", "/v1/sim/tick", {"session_id": sid, "dt_real_ms": 5000})
        live = tick.get("siege_live") or {}
        cmd_view = live.get("command", {}).get("defender", {})
        clock = tick.get("world", {})
        mod = int(clock.get("minute_of_day", 0))
        hh, mm = divmod(mod, 60)
        events = tick.get("new_siege_events", [])
        print(
            f"  tick {i + 1}: D{clock.get('day', '?')} {hh:02d}:{mm:02d} "
            f"라운드 {live.get('round', 0)} "
            f"결계 {live.get('barrier_hp', '?')} "
            f"지휘 {cmd_view.get('alive_count', '?')}/5 "
            f"{'[자율교전]' if cmd_view.get('autonomous') else cmd_view.get('doctrine_label', '')} "
            f"이벤트 {len(events)}"
        )
        if events:
            print(f"    → {events[0].get('text', events[0].get('kind'))}")
        if live.get("status") != "active":
            print(f"  공성 종료: {live.get('outcome')}")
            break
        time.sleep(0.3)

    print("\n▶ 탐험 턴 (공성 스킵 없어야 함 — sim tick 전용)")
    turn = req(
        "POST",
        "/v1/turn",
        {
            "session_id": sid,
            "action": "explore",
            "temporal_mode": "precision",
            "position": {
                "map_id": "ashpoint_01",
                "x": 40,
                "y": 48,
                "facing": "south",
                "allow_map_transition": False,
            },
        },
    )
    lines = turn.get("lines", [])[:5]
    _print("explore_turn", {"lines": lines, "clock": turn.get("clock")})

    wars = req("GET", f"/v1/kingdom/wars?session_id={sid}")
    _print("final_wars", {
        "siege_live": wars.get("siege_live"),
        "active": len(wars.get("active_sieges", [])),
    })

    print("\n✅ 데모 완료 — Godot: client/godot → F5 (API 8765 실행 중이어야 함)")
    print(f"   session_id (디버그): {sid}")
    return 0


def _run_inprocess() -> int:
    import os

    from fastapi.testclient import TestClient

    from api.server import app

    os.environ["ELDORIA_DEMO"] = "1"
    client = TestClient(app)
    r = client.post(
        "/v1/session/new",
        json={
            "mode": "rule",
            "temporal_mode": "precision",
            "game_mode": "hybrid",
            "seed": 42,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]

    boot = client.post("/v1/demo/bootstrap", json={"session_id": sid})
    assert boot.status_code == 200, boot.text
    print(json.dumps(boot.json(), ensure_ascii=False, indent=2))

    for _ in range(4):
        t = client.post("/v1/sim/tick", json={"session_id": sid, "dt_real_ms": 5000})
        assert t.status_code == 200, t.text
        live = t.json().get("siege_live") or {}
        print(f"tick round={live.get('round')} barrier={live.get('barrier_hp')}")

    print("OK in-process demo")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Eldoria play demo")
    parser.add_argument("--live", action="store_true", help="Hit uvicorn on :8765")
    args = parser.parse_args()
    try:
        return _run_live() if args.live else _run_inprocess()
    except Exception as exc:
        print(f"\n❌ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
