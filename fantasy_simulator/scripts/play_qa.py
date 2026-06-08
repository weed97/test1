#!/usr/bin/env python3
"""Extended QA playthrough — find bugs and design issues."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8765"
ISSUES: list[str] = []


def issue(severity: str, msg: str) -> None:
    ISSUES.append(f"[{severity}] {msg}")
    print(f"  ⚠ [{severity}] {msg}")


def req(method: str, path: str, body: dict | None = None) -> dict:
    url = BASE + path
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {detail}") from exc


def main() -> int:
    print("=== Eldoria QA Playthrough ===\n")

    # 1. Bootstrap
    print("1) 세션 + 데모 부트스트랩")
    try:
        req("GET", "/v1/health")
    except Exception:
        issue("BLOCKER", "API 서버 미실행 (uvicorn :8765)")
        _report()
        return 1

    sid = req(
        "POST",
        "/v1/session/new",
        {"mode": "rule", "temporal_mode": "precision", "game_mode": "hybrid", "seed": 99},
    )["session_id"]

    try:
        boot = req("POST", "/v1/demo/bootstrap", {"session_id": sid})
    except RuntimeError as exc:
        issue("BLOCKER", f"demo/bootstrap 실패 — ELDORIA_DEMO=1 필요: {exc}")
        _report()
        return 1

    war_id = boot.get("war_id", "")
    print(f"   war_id={war_id}")

    # 2. Sim clock advances
    print("\n2) Sim tick — 시계·공성 라운드")
    rounds_seen: list[int] = []
    barrier_seen: list[int] = []
    events_total = 0
    for i in range(25):
        tick = req("POST", "/v1/sim/tick", {"session_id": sid, "dt_real_ms": 5000})
        live = tick.get("siege_live") or {}
        r = int(live.get("round", 0))
        b = int(live.get("barrier_hp", 0))
        rounds_seen.append(r)
        barrier_seen.append(b)
        events_total += len(tick.get("new_siege_events", []))
        if live.get("status") != "active":
            print(f"   공성 종료 tick {i + 1}: {live.get('outcome')}")
            break

    if max(rounds_seen) == 0:
        issue(
            "MAJOR",
            f"25틱(125 real sec ≈ 25 sim 분) 후에도 공성 라운드 0 — "
            "20 sim분/라운드면 1라운드는 나와야 함",
        )
    elif max(barrier_seen) == min(barrier_seen) and max(barrier_seen) > 0:
        issue("MAJOR", "공성 라운드는 진행됐지만 결계 HP 변화 없음 (밸런스)")

    print(f"   라운드 {min(rounds_seen)}→{max(rounds_seen)}, 이벤트 {events_total}개")

    # 3. Explore should NOT advance siege round
    print("\n3) 탐험 턴이 공성 스킵하지 않는지")
    before = req("GET", f"/v1/kingdom/wars?session_id={sid}")
    live_before = before.get("siege_live") or {}
    rnd_before = int(live_before.get("round", 0))

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
    after = req("GET", f"/v1/kingdom/wars?session_id={sid}")
    live_after = after.get("siege_live") or {}
    rnd_after = int(live_after.get("round", 0))

    if rnd_after > rnd_before:
        issue("MAJOR", f"탐험 턴 후 공성 라운드 증가 {rnd_before}→{rnd_after} (스킵 버그)")
    else:
        print(f"   OK explore 후 라운드 유지 {rnd_before}")

    if not turn.get("lines"):
        issue("MINOR", "탐험 턴 lines 비어 있음")

    # 4. Command when chain intact
    print("\n4) 지휘 명령")
    if live_after.get("status") == "active":
        cmd = req(
            "POST",
            "/v1/kingdom/war/command",
            {
                "session_id": sid,
                "war_id": war_id,
                "doctrine": "coordinate_defense",
                "posture": "citadel",
            },
        )
        if not cmd.get("ok"):
            issue("MAJOR", f"지휘 명령 실패: {cmd}")
        else:
            dfn = cmd.get("command", {}).get("defender", {})
            if dfn.get("posture") != "citadel":
                issue("MAJOR", "심성 posture 반영 안 됨")
            print(f"   OK → {dfn.get('doctrine_label')} / {dfn.get('posture_label')}")

    # 5. Demo without ELDORIA_DEMO — normal new game kingdom path
    print("\n5) 데모 없이 신규 세션 (왕국 선포 불가 예상)")
    sid2 = req(
        "POST",
        "/v1/session/new",
        {"mode": "rule", "temporal_mode": "precision", "game_mode": "hybrid", "seed": 1},
    )["session_id"]
    kstatus = req("GET", f"/v1/kingdom/status?session_id={sid2}")
    if kstatus.get("is_kingdom"):
        issue("MINOR", "신규 세션에 이미 왕국 있음 (비정상)")
    gold = int(kstatus.get("party_gold", 0))
    preview = kstatus.get("founding_preview", {})
    tut = preview.get("tutorial", {})
    if gold < 1000 and not tut.get("active"):
        issue(
            "UX",
            f"신규 플레이 골드 {gold}G — 왕국 선포 비용 {preview.get('gold_cost_total', '?')} "
            "→ 정식 플레이까지 그라인딩 매우 김",
        )
    elif gold < 1000:
        print(
            f"   OK 튜토리얼 경로 활성 (80G 시작, 선포 {preview.get('gold_cost_total', '?')}G)"
        )
    sim2 = req("GET", f"/v1/sim/status?session_id={sid2}")
    if not sim2.get("sim_clock", {}).get("enabled"):
        issue("MAJOR", "hybrid 신규 세션에 sim_clock 비활성")

    # 6. bootstrap without demo flag
    print("\n6) ELDORIA_DEMO 없이 bootstrap 차단")
    demo_on = bool(req("GET", "/v1/health").get("demo_mode", False))
    if demo_on:
        print("   SKIP 서버 demo_mode=1 — 로컬은 ELDORIA_DEMO=0 으로 재검증")
    else:
        try:
            req("POST", "/v1/demo/bootstrap", {"session_id": sid2})
            issue("MINOR", "ELDORIA_DEMO 없이 bootstrap 허용됨")
        except RuntimeError as exc:
            if "403" in str(exc):
                print("   OK 403 차단")
            else:
                issue("MINOR", f"bootstrap 예상외 오류: {exc}")

    # 7. Commander kill simulation via many ticks on fresh war
    print("\n7) 장기 sim — 지휘관/명령체계")
    sid3 = req(
        "POST",
        "/v1/session/new",
        {"mode": "rule", "temporal_mode": "precision", "game_mode": "hybrid", "seed": 77},
    )["session_id"]
    req("POST", "/v1/demo/bootstrap", {"session_id": sid3})
    war_id3 = req("GET", f"/v1/kingdom/wars?session_id={sid3}").get("siege_live", {}).get(
        "war_id", ""
    )
    req(
        "POST",
        "/v1/kingdom/war/command",
        {
            "session_id": sid3,
            "war_id": war_id3,
            "side": "attacker",
            "doctrine": "focus_commander",
            "posture": "forward_command",
        },
    )
    req(
        "POST",
        "/v1/kingdom/war/command",
        {
            "session_id": sid3,
            "war_id": war_id3,
            "doctrine": "coordinate_defense",
            "posture": "forward_command",
        },
    )
    live_before7 = req("GET", f"/v1/kingdom/wars?session_id={sid3}").get("siege_live", {})
    def_cmds = (live_before7.get("command") or {}).get("defender", {}).get("commanders", [])
    cmd_hp_start = int(def_cmds[0].get("hp", 0)) if def_cmds else 0
    autonomous = False
    for _ in range(80):
        tick = req("POST", "/v1/sim/tick", {"session_id": sid3, "dt_real_ms": 5000})
        live = tick.get("siege_live") or {}
        dfn = (live.get("command") or {}).get("defender", {})
        if dfn.get("autonomous"):
            autonomous = True
            print(f"   명령체계 붕괴 감지 (라운드 {live.get('round')})")
            break
        if live.get("status") != "active":
            print(f"   공성 종료: {live.get('outcome')} 라운드 {live.get('round')}")
            break
    if not autonomous and cmd_hp_start > 0:
        live_after7 = req("GET", f"/v1/kingdom/wars?session_id={sid3}").get("siege_live", {})
        def_after = (live_after7.get("command") or {}).get("defender", {}).get("commanders", [])
        cmd_hp_end = int(def_after[0].get("hp", 0)) if def_after else 0
        if cmd_hp_end >= cmd_hp_start * 0.92:
            issue(
                "BALANCE/UX",
                "80틱(400초) + 암살 doctrine에도 최고 지휘관 HP 거의 무손 — "
                "피해 튜닝 재확인",
            )
        else:
            print(
                f"   OK 지휘관 피해 {cmd_hp_start}→{cmd_hp_end} "
                f"({100 - int(100 * cmd_hp_end / cmd_hp_start)}%)"
            )

    # 8. Non-siege gameplay loop
    print("\n8) 공성 외 플레이 — 탐험·이동·성장·도감")
    sid4 = req(
        "POST",
        "/v1/session/new",
        {"mode": "rule", "temporal_mode": "precision", "game_mode": "hybrid", "seed": 202},
    )["session_id"]

    maps = req("GET", "/v1/world/maps")
    if not maps.get("maps"):
        issue("MAJOR", "world/maps 비어 있음")

    pos = req(
        "POST",
        "/v1/world/position",
        {
            "session_id": sid4,
            "position": {
                "map_id": "ashpoint_01",
                "x": 42,
                "y": 50,
                "facing": "east",
                "allow_map_transition": True,
            },
        },
    )
    if not pos.get("ok", True):
        issue("MAJOR", f"position sync 실패: {pos}")

    agents = req("GET", f"/v1/world/agents?session_id={sid4}&map_id=ashpoint_01")
    if not agents.get("ecology_enabled"):
        issue("MAJOR", "hybrid 세션 ecology_enabled false")
    agent_count = len(agents.get("agents", []))
    print(f"   agents on map: {agent_count}")
    if agent_count == 0:
        issue("UX", "탐험 맵에 ecology agent 0 — 필드가 빈 느낌")

    kstatus4 = req("GET", f"/v1/kingdom/status?session_id={sid4}")
    tut = kstatus4.get("founding_preview", {}).get("tutorial", {})
    if not tut.get("active"):
        issue("MINOR", "신규 세션 tutorial 경로 비활성")
    gold_before = int(kstatus4.get("party_gold", 0))

    for action in ("explore", "explore", "investigate forest", "rest"):
        t = req(
            "POST",
            "/v1/turn",
            {
                "session_id": sid4,
                "action": action,
                "temporal_mode": "precision",
                "position": {
                    "map_id": "ashpoint_01",
                    "x": 42,
                    "y": 50,
                    "facing": "east",
                    "allow_map_transition": False,
                },
            },
        )
        if not t.get("lines"):
            issue("MINOR", f"턴 '{action}' lines 없음")

    kstatus4b = req("GET", f"/v1/kingdom/status?session_id={sid4}")
    gold_after = int(kstatus4b.get("party_gold", 0))
    if gold_after <= gold_before:
        issue("MAJOR", "탐험·조사·휴식 후 튜토리얼 골드 미지급")
    else:
        print(f"   tutorial gold {gold_before}→{gold_after}G")

    prog = req("GET", f"/v1/progression/status?session_id={sid4}")
    heroes = prog.get("heroes", {})
    if not heroes:
        issue("MAJOR", "progression heroes 비어 있음")
    else:
        cid = next(iter(heroes))
        tree = req(
            "GET",
            f"/v1/progression/skill_tree?session_id={sid4}&character_id={cid}",
        )
        total = tree.get("skill_tree", {}).get("counts", {}).get("job_total", 0)
        print(f"   skill_tree job_total={total}")
        if total < 100:
            issue("MINOR", f"skill_tree 작음: {total}")

    catalog = req("GET", f"/v1/catalog/items?session_id={sid4}&limit=20")
    items = catalog.get("items", [])
    if len(items) < 5:
        issue("MAJOR", "item catalog 거의 비어 있음")
    else:
        grant = req(
            "POST",
            "/v1/progression/grant_item",
            {"session_id": sid4, "item_id": items[0]["item_id"], "count": 1},
        )
        if not grant.get("ok", True):
            issue("MINOR", f"grant_item 실패: {grant}")

    settle = req("GET", f"/v1/settlement/status?session_id={sid4}")
    if "construction_level" not in str(settle):
        issue("MINOR", "settlement status 필드 부족")

    eco = req("GET", f"/v1/ecology/civilizations?session_id={sid4}")
    civs = eco.get("civilizations", eco.get("civs", []))
    if isinstance(civs, dict):
        civ_count = len(civs)
    else:
        civ_count = len(civs) if civs else 0
    print(f"   civilizations: {civ_count}")
    if civ_count == 0:
        issue("UX", "ecology civilizations 비어 있음 — 세계가 정적")

    # sim tick without kingdom — ecology only
    t0 = req("GET", f"/v1/sim/status?session_id={sid4}")
    for _ in range(3):
        req("POST", "/v1/sim/tick", {"session_id": sid4, "dt_real_ms": 5000})
    t1 = req("GET", f"/v1/sim/status?session_id={sid4}")
    if float(t1.get("sim_clock", {}).get("total_sim_minutes", 0)) <= float(
        t0.get("sim_clock", {}).get("total_sim_minutes", 0)
    ):
        issue("MAJOR", "공성 없어도 sim tick 시계가 안 감")

    wars4 = req("GET", f"/v1/kingdom/wars?session_id={sid4}")
    if wars4.get("siege_live"):
        issue("MINOR", "왕국 없는데 siege_live 존재")

    print("   OK 탐험·성장·도감·sim tick (무공성)")

    _report()
    return 0 if not any(i.startswith("[BLOCKER]") or i.startswith("[MAJOR]") for i in ISSUES) else 1


def _report() -> None:
    print("\n" + "=" * 50)
    print(f"발견 이슈 {len(ISSUES)}건")
    for i in ISSUES:
        print(f"  {i}")
    if not ISSUES:
        print("  (치명 이슈 없음)")


if __name__ == "__main__":
    raise SystemExit(main())
