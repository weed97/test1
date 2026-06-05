"""Temporal model — moment classification, Nex time advance, somatic presence."""

from __future__ import annotations

import random
from typing import Any, Literal

TemporalMode = Literal["classic", "nex", "precision"]

MomentKind = Literal[
    "glance",
    "step",
    "talk",
    "investigate",
    "explore",
    "travel",
    "rest",
    "combat",
    "unknown",
]

# Nex: base simulation-cycle steps per moment (classic always uses 1 via resolve_time_steps).
_NEX_BASE_STEPS: dict[MomentKind, int] = {
    "glance": 0,
    "step": 0,
    "talk": 1,
    "investigate": 1,
    "explore": 1,
    "travel": 1,
    "rest": 0,
    "combat": 1,
    "unknown": 1,
}

# Precision: in-world minutes per simulation beat (minimum 1 for physical acts).
_PRECISION_MINUTES: dict[MomentKind, int] = {
    "glance": 0,
    "step": 1,
    "talk": 5,
    "investigate": 8,
    "explore": 5,
    "travel": 15,
    "rest": 0,
    "combat": 3,
    "unknown": 1,
}

_SOMATIC_BY_TIME: dict[str, list[str]] = {
    "morning": [
        "아침 공기가 폐를 차갑게 채운다.",
        "먼지 냄새와 나무 연기가 섞여 코끝을 찌른다.",
    ],
    "afternoon": [
        "낮 햇빛이 뺨에 닿는 열이 느껴진다.",
        "멀리 망치 소리가 뼈 안쪽으로 울린다.",
    ],
    "evening": [
        "해질녘 바람이 목덜미를 스친다.",
        "여관 쪽에서 희미한 웃음소리가 들린다.",
    ],
    "night": [
        "밤공기가 차갑고, 숨결이 하얗게 보인다.",
        "어둠 속에서 무언가가 바스락거리는 느낌이 든다.",
    ],
}

_SOMATIC_BY_ZONE: dict[str, list[str]] = {
    "forest": [
        "나뭇잎 밑에서 냉기가 올라온다.",
        "멀리서 연기 냄새가 목을 타고 내려간다.",
    ],
    "tower": [
        "돌바닥의 진동이 발바닥으로 전해진다.",
        "귀 안쪽에 낮은 울림이 맴돈다.",
    ],
    "ashpoint": [
        "장작 냄새와 금속 냄새가 섞여 있다.",
        "발밑 돌길의 울퉁불퉁함이 느껴진다.",
    ],
}


def classify_moment(action: str) -> MomentKind:
    """Classify player input into a moment kind for time advancement."""
    lower = action.lower().strip()
    if not lower:
        return "unknown"
    if lower in ("rest", "sleep", "휴식", "수면") or "휴식" in lower:
        return "rest"
    if lower.startswith("combat") or lower == "combat":
        return "combat"
    if lower.startswith("talk") or lower.startswith("speak") or "대화" in lower:
        return "talk"
    if lower.startswith("investigate") or lower.startswith("inspect") or "조사" in lower:
        return "investigate"
    if lower in ("look", "listen", "wait", "pause", "stop") or lower.startswith(
        ("look ", "listen ", "wait ")
    ):
        return "glance"
    if "forest" in lower or "숲" in lower or "investigate" in lower:
        return "travel"
    if lower == "explore" or "explore" in lower or "탐험" in lower:
        return "explore"
    if lower in ("go", "move", "walk", "이동"):
        return "step"
    return "unknown"


def resolve_time_steps(
    action: str,
    *,
    temporal_mode: TemporalMode = "classic",
    time_scale: float = 1.0,
) -> tuple[int, MomentKind, bool]:
    """Return (cycle_steps, kind, rest_until_morning).

    classic: always 1 cycle step (legacy turn feel).
    nex: intent-based steps scaled by time_scale.
    precision: always 0 cycle steps (minutes via resolve_time_minutes).
    """
    kind = classify_moment(action)
    if temporal_mode == "classic":
        return 1, kind, False
    if temporal_mode == "precision":
        return 0, kind, kind == "rest"

    if kind == "rest":
        return 0, kind, True

    base = _NEX_BASE_STEPS.get(kind, 1)
    scaled = int(round(base * max(0.0, time_scale)))
    return scaled, kind, False


def resolve_time_minutes(
    action: str,
    *,
    temporal_mode: TemporalMode = "classic",
    time_scale: float = 1.0,
) -> tuple[int, MomentKind, bool]:
    """Return (minutes, kind, rest_until_morning) for precision mode."""
    kind = classify_moment(action)
    if temporal_mode != "precision":
        return 0, kind, False
    if kind == "rest":
        return 0, kind, True
    base = _PRECISION_MINUTES.get(kind, 1)
    scaled = int(round(base * max(0.0, time_scale)))
    if kind in ("step", "unknown") and scaled < 1:
        scaled = 1
    return scaled, kind, False


def somatic_presence_line(
    state: dict[str, Any],
    *,
    rng: random.Random | None = None,
) -> str | None:
    """One short somatic line for Nex presence (not a full turn narrative)."""
    r = rng or random.Random()
    world = state.get("world", {})
    time_key = world.get("time_of_day", "afternoon")
    if time_key not in _SOMATIC_BY_TIME:
        time_key = "afternoon"

    location = world.get("location", "")
    zone = "ashpoint"
    loc_lower = location.lower()
    if "숲" in location or "forest" in loc_lower:
        zone = "forest"
    elif "탑" in location or "tower" in loc_lower or "관측" in location:
        zone = "tower"

    pool = list(_SOMATIC_BY_TIME.get(time_key, []))
    pool.extend(_SOMATIC_BY_ZONE.get(zone, []))
    tension = int(world.get("tension", 0))
    if tension >= 55:
        pool.append("가슴이 조금 조여 오는 것 같다.")
    if tension >= 75:
        pool.append("심박이 빨라지고, 손끝이 미세하게 떨린다.")

    if not pool:
        return None
    return f"[체감] {r.choice(pool)}"


def format_clock_line(world: dict[str, Any]) -> str | None:
    """In-world clock for precision / Nex HUD."""
    minute = world.get("minute_of_day")
    if minute is None:
        return None
    from utils.world_clock import format_clock

    return f"[시각 {format_clock(int(minute))}]"


def format_moment_label(kind: MomentKind, *, temporal_mode: TemporalMode) -> str | None:
    """Optional debug/meta label for Nex / precision moments (not classic)."""
    if temporal_mode not in ("nex", "precision"):
        return None
    labels = {
        "glance": "주변을 살핀다",
        "step": "잠시 걸음을 멈춘다",
        "talk": "대화",
        "investigate": "조사",
        "explore": "탐색",
        "travel": "이동",
        "rest": "휴식",
        "combat": "전투",
        "unknown": "행동",
    }
    text = labels.get(kind)
    if not text:
        return None
    return f"[순간·{text}]"
