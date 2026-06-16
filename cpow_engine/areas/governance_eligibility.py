"""거버넌스 발의 자격 — 단순 창작 차단, 긴 흐름만 허용."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _kind_value(kind: Any) -> str:
    if hasattr(kind, "value"):
        return str(kind.value).lower()
    return str(kind).lower()


@dataclass
class LongFlowPolicy:
    """봇·단순 발의 차단 — 거버넌스는 긴 흐름 창작만."""

    min_flow_steps: int = 3
    min_rationale_chars: int = 120
    min_step_description_chars: int = 40
    min_title_chars: int = 12
    min_drafting_sec: float = 300.0
    min_composer_spread_sec: float = 60.0
    min_complexity_score: float = 3.0
    max_trivial_spec_keys: int = 2

    def to_dict(self) -> dict[str, float | int]:
        return {
            "min_flow_steps": self.min_flow_steps,
            "min_rationale_chars": self.min_rationale_chars,
            "min_step_description_chars": self.min_step_description_chars,
            "min_title_chars": self.min_title_chars,
            "min_drafting_sec": self.min_drafting_sec,
            "min_composer_spread_sec": self.min_composer_spread_sec,
            "min_complexity_score": self.min_complexity_score,
            "max_trivial_spec_keys": self.max_trivial_spec_keys,
        }


@dataclass
class LongFlowValidation:
    ok: bool
    reason: str = ""
    codes: list[str] = field(default_factory=list)
    complexity_score: float = 0.0
    flow_step_count: int = 0


def extract_flow_steps(spec: dict) -> list[dict]:
    """spec에서 단계 목록 추출 — long_flow.steps 또는 flow_steps."""
    if not spec:
        return []
    long_flow = spec.get("long_flow")
    if isinstance(long_flow, dict):
        steps = long_flow.get("steps")
        if isinstance(steps, list):
            return [s for s in steps if isinstance(s, dict)]
    flow_steps = spec.get("flow_steps")
    if isinstance(flow_steps, list):
        return [s for s in flow_steps if isinstance(s, dict)]
    return []


def compute_flow_complexity(steps: list[dict]) -> float:
    if not steps:
        return 0.0
    score = float(len(steps))
    for step in steps:
        label = str(step.get("label", ""))
        desc = str(step.get("description", step.get("detail", "")))
        score += min(2.0, len(label) / 20.0)
        score += min(3.0, len(desc) / 50.0)
        if step.get("requires_consensus"):
            score += 0.5
        if step.get("requires_creation_power"):
            score += 0.5
    return score


def is_trivial_spec(spec: dict, *, max_keys: int) -> bool:
    """단일 수치·짧은 키만 있는 봇형 spec."""
    if not spec:
        return True
    flow_steps = extract_flow_steps(spec)
    if flow_steps:
        return False
    shallow_keys = {
        k for k in spec
        if k not in ("rationale", "long_flow", "flow_steps", "title")
    }
    if len(shallow_keys) <= max_keys and "rationale" not in spec:
        return True
    if len(spec) <= max_keys and not flow_steps:
        return True
    return False


def validate_long_flow_proposal(
    *,
    kind: Any,
    title: str,
    spec: dict | None,
    policy: LongFlowPolicy | None = None,
) -> LongFlowValidation:
    """거버넌스 진입 — 긴 흐름 창작만 통과."""
    rules = policy or LongFlowPolicy()
    spec = dict(spec or {})
    codes: list[str] = []

    if len(title.strip()) < rules.min_title_chars:
        codes.append("title_too_short")

    rationale = str(spec.get("rationale", "")).strip()
    if len(rationale) < rules.min_rationale_chars:
        codes.append("rationale_too_short")

    if is_trivial_spec(spec, max_keys=rules.max_trivial_spec_keys):
        codes.append("trivial_spec_blocked")

    steps = extract_flow_steps(spec)
    if len(steps) < rules.min_flow_steps:
        codes.append("insufficient_flow_steps")

    for idx, step in enumerate(steps):
        desc = str(step.get("description", step.get("detail", ""))).strip()
        label = str(step.get("label", "")).strip()
        if not label:
            codes.append(f"step_{idx}_missing_label")
        if len(desc) < rules.min_step_description_chars:
            codes.append(f"step_{idx}_description_too_short")

    complexity = compute_flow_complexity(steps)
    if complexity < rules.min_complexity_score:
        codes.append("complexity_too_low")

    # kind별 최소 단계 (전쟁·매크로 방지는 더 긴 흐름)
    kind_min = rules.min_flow_steps
    kind_name = _kind_value(kind)
    if kind_name in ("macro_bot_defense", "election_war"):
        kind_min = max(kind_min, 4)
    if len(steps) < kind_min:
        if "insufficient_flow_steps" not in codes:
            codes.append("kind_requires_deeper_flow")

    if codes:
        return LongFlowValidation(
            False,
            reason="simple_creation_blocked",
            codes=codes,
            complexity_score=complexity,
            flow_step_count=len(steps),
        )

    return LongFlowValidation(
        True,
        reason="long_flow_accepted",
        complexity_score=complexity,
        flow_step_count=len(steps),
    )


def drafting_duration_ok(
    created_at: float,
    now: float,
    *,
    policy: LongFlowPolicy | None = None,
) -> bool:
    rules = policy or LongFlowPolicy()
    return (now - created_at) >= rules.min_drafting_sec


def composer_spread_ok(
    composer_times: dict[str, float],
    *,
    policy: LongFlowPolicy | None = None,
) -> bool:
    """구성 서명이 한순간에 몰리면 봇 의심."""
    rules = policy or LongFlowPolicy()
    if len(composer_times) < 2:
        return True
    times = sorted(composer_times.values())
    return (times[-1] - times[0]) >= rules.min_composer_spread_sec


def make_long_flow_spec(
    rationale: str,
    steps: list[dict],
    *,
    extra: dict | None = None,
) -> dict:
    """테스트·클라이언트용 긴 흐름 spec 빌더."""
    spec: dict = {
        "rationale": rationale,
        "long_flow": {
            "steps": steps,
            "estimated_duration_sec": len(steps) * 600,
        },
    }
    if extra:
        spec.update(extra)
    return spec
