"""게이트 몬스터 유닛 / 성좌 헌터 로스터 로더.

config JSON 의 'gate_monsters' 와 'hunter_roster' 섹션을 데이터 모델로 변환한다.
해당 섹션이 없어도 기존 단일 hunter/constellation 설정으로 동작하도록 호환된다.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from .models import Constellation, Hunter, HunterPreset, MonsterUnit
from .variables import VariableManager


def _filter_fields(cls: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    fields = getattr(cls, "__dataclass_fields__", {})
    return {k: v for k, v in (data or {}).items() if k in fields}


def load_monsters(variables: VariableManager) -> List[MonsterUnit]:
    """게이트 몬스터 유닛 목록을 로드한다."""
    raw = variables.data.get("gate_monsters", []) or []
    monsters: List[MonsterUnit] = []
    for entry in raw:
        kwargs = _filter_fields(MonsterUnit, entry)
        if "id" not in kwargs or "name" not in kwargs:
            continue
        ev = entry.get("exception_variables", {}) or {}
        kwargs["exception_variables"] = {str(k): float(v) for k, v in ev.items()}
        monsters.append(MonsterUnit(**kwargs))
    return monsters


def load_hunter_roster(variables: VariableManager) -> "OrderedDict[str, HunterPreset]":
    """성좌 헌터 로스터를 {id: HunterPreset} 형태로 로드한다."""
    raw = variables.data.get("hunter_roster", []) or []
    roster: "OrderedDict[str, HunterPreset]" = OrderedDict()
    for entry in raw:
        hid = entry.get("id")
        if not hid:
            continue
        hunter = Hunter(**_filter_fields(Hunter, entry.get("hunter", {})))
        _sync_maxes(hunter)
        const = Constellation(**_filter_fields(Constellation, entry.get("constellation", {})))
        roster[hid] = HunterPreset(id=hid, hunter=hunter, constellation=const)
    return roster


def _sync_maxes(hunter: Hunter) -> None:
    """max_* 가 누락된 경우 현재값으로 채워 일관성을 유지한다."""
    if hunter.max_hp < hunter.hp:
        hunter.max_hp = hunter.hp
    if hunter.max_stamina < hunter.stamina:
        hunter.max_stamina = hunter.stamina
    if hunter.max_sanity < hunter.sanity:
        hunter.max_sanity = hunter.sanity


def select_hunter(
    variables: VariableManager, hunter_id: Optional[str]
) -> Tuple[Hunter, Constellation, Optional[str]]:
    """헌터를 선택한다.

    우선순위: 명시된 hunter_id → simulation.selected_hunter → 기본 hunter 설정.
    반환: (Hunter, Constellation, 사용된 로스터 id 또는 None)
    """
    roster = load_hunter_roster(variables)

    chosen = hunter_id or variables.simulation_config().get("selected_hunter")
    if chosen and chosen in roster:
        preset = roster[chosen]
        # 원본 보존을 위해 복사본 반환
        return _clone_hunter(preset.hunter), _clone_const(preset.constellation), chosen

    # 폴백: 기존 단일 설정
    hunter = Hunter(**_filter_fields(Hunter, variables.hunter_config()))
    _sync_maxes(hunter)
    const = Constellation(**_filter_fields(Constellation, variables.constellation_config()))
    return hunter, const, None


def _clone_hunter(h: Hunter) -> Hunter:
    return Hunter(**h.to_dict())


def _clone_const(c: Constellation) -> Constellation:
    return Constellation(**c.to_dict())


def roster_summary(variables: VariableManager) -> List[str]:
    lines: List[str] = []
    for hid, preset in load_hunter_roster(variables).items():
        h = preset.hunter
        c = preset.constellation
        lines.append(
            f"  - {hid:<14} {h.name} «{h.title}» Lv.{h.level} "
            f"(HP {h.max_hp}/ATK {h.attack}/LUK {h.luck}) · 성좌 [{c.name}]"
        )
    return lines


def monster_summary(variables: VariableManager) -> List[str]:
    lines: List[str] = []
    for m in load_monsters(variables):
        ev = ", ".join(f"{k}={v:g}" for k, v in m.exception_variables.items()) or "없음"
        lines.append(
            f"  - [{m.grade}] {m.name:<10} HP {m.hp}/ATK {m.attack}/DEF {m.defense} "
            f"· 특성 '{m.trait}' · 예외변수: {ev}"
        )
    return lines
