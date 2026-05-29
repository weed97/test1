"""헌터 상태창 / 이벤트 로그 출력 포매터.

콘솔에 보기 좋게 자동 출력되는 텍스트를 생성한다. 색상 코드를 쓰지 않아
어떤 터미널/파일로 리다이렉트해도 안전하다.
"""

from __future__ import annotations

from typing import Dict, List

from .models import EventRecord, GameState

_WIDTH = 60


def _bar(value: int, maximum: int, length: int = 20) -> str:
    maximum = max(1, maximum)
    ratio = max(0.0, min(1.0, value / maximum))
    filled = int(round(ratio * length))
    return "█" * filled + "░" * (length - filled)


def _box_line(text: str = "") -> str:
    return "│ " + text.ljust(_WIDTH - 3) + "│"


def _rule(char: str = "─") -> str:
    return "├" + char * (_WIDTH - 1) + "┤"


def render_status(state: GameState) -> str:
    h = state.hunter
    c = state.constellation
    lines: List[str] = []
    lines.append("┌" + "─" * (_WIDTH - 1) + "┐")
    lines.append(_box_line(f"[ 헌터 상태창 ]   턴 {state.turn}"))
    lines.append(_rule())
    lines.append(_box_line(f"{h.name}  «{h.title}»   Lv.{h.level}  (EXP {h.exp}/{h.level*100})"))
    lines.append(_box_line(f"HP   {_bar(h.hp, h.max_hp)} {h.hp}/{h.max_hp}"))
    lines.append(_box_line(f"기력  {_bar(h.stamina, h.max_stamina)} {h.stamina}/{h.max_stamina}"))
    lines.append(_box_line(f"정신  {_bar(h.sanity, h.max_sanity)} {h.sanity}/{h.max_sanity}"))
    lines.append(_box_line(f"공격 {h.attack:<5} 방어 {h.defense:<5} 행운 {h.luck:<5} 코인 {h.coins}"))
    lines.append(_rule())
    lines.append(_box_line(f"성좌 [{c.name}]"))
    lines.append(_box_line(f"후원 '{c.patronage}'   호감도 {c.favor}"))
    lines.append("└" + "─" * (_WIDTH - 1) + "┘")
    return "\n".join(lines)


def render_uvars(uvars: Dict[str, float]) -> str:
    parts = [f"{k}={v:g}" for k, v in uvars.items()]
    head = "예측 불가 변수 8종 ▷ "
    return head + "  ".join(parts)


def _format_effects(effects: Dict[str, int]) -> str:
    label = {
        "hp": "HP", "stamina": "기력", "sanity": "정신", "coins": "코인",
        "attack": "공격", "defense": "방어", "luck": "행운", "favor": "호감도", "exp": "경험치",
    }
    parts = []
    for k, v in effects.items():
        if not v:
            continue
        sign = "+" if v > 0 else ""
        parts.append(f"{label.get(k, k)} {sign}{v}")
    return ", ".join(parts) if parts else "변화 없음"


def render_event(event: EventRecord) -> str:
    arrow = "  ↳ " if event.chained else "▶ "
    tag = f"[{event.kind}]"
    head = f"{arrow}{tag} {event.title}"
    body = f"      {event.description}"
    foot = f"      효과: {_format_effects(event.effects)}"
    return "\n".join([head, body, foot])


def render_turn_log(events: List[EventRecord]) -> str:
    return "\n".join(render_event(e) for e in events)


def render_summary(state: GameState) -> str:
    h = state.hunter
    lines: List[str] = []
    lines.append("=" * _WIDTH)
    lines.append(" 시뮬레이션 종료 요약")
    lines.append("=" * _WIDTH)
    lines.append(f" 결과       : {state.outcome}")
    lines.append(f" 진행 턴    : {state.turn}")
    lines.append(f" 최종 레벨  : Lv.{h.level}")
    lines.append(f" 생존 여부  : {'생존' if h.alive else '사망/광기'}")
    lines.append(f" 코인       : {h.coins}")
    lines.append(f" 성좌 호감도: {state.constellation.favor}")
    mutated = sum(1 for e in state.log if e.mutated)
    chained = sum(1 for e in state.log if e.chained)
    lines.append(f" 총 이벤트  : {len(state.log)} (변이 {mutated} / 연쇄 {chained})")
    lines.append("=" * _WIDTH)
    return "\n".join(lines)
