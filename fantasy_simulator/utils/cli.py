"""CLI helpers — input parsing, interactive REPL, friendly errors."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from utils.game_session import GameSession

INTERACTIVE_HELP = """\
명령어:
  explore              마을/주변 탐험 (씨앗 이벤트 발생 가능)
  investigate well     우물 조사
  investigate forest   북쪽 숲 조사 (퀘스트 2단계)
  talk torren          NPC 대화 (토렌/릴리안/회색 망토/장로/리사)
  rest                 휴식 (HP/MP 회복)
  combat silver_stalker  보스 전투 (3단계 이후)
  quest                퀘스트 진행 상황
  status               현재 상태
  help / quit

팁: 밤/저녁에 explore하면 다른 이벤트가 뜹니다.
  Tab 키로 명령어 자동완성 (터미널 지원 시)
"""

BASE_COMMANDS = ("explore", "rest", "quest", "status", "help", "quit", "talk", "investigate", "combat")
TALK_NPCS = ("torren", "lilian", "grey", "maren", "lysa", "finn", "회색", "장로", "릴리안", "토렌")
INVESTIGATE_TARGETS = ("well", "forest", "우물", "숲")
META_COMMANDS = ("status", "help", "quit", "exit", "q", "stat", "s", "h", "?")


def _root_path(base_dir: Path | str | Any) -> Path:
    if hasattr(base_dir, "base_dir"):
        return Path(base_dir.base_dir)
    return Path(base_dir)


def enemy_short_names(base_dir: Path | str | Any) -> list[str]:
    """Short names for combat tab completion."""
    names: set[str] = set()
    for path in sorted(_root_path(base_dir).joinpath("characters").glob("*.json")):
        stem = path.stem
        names.add(stem.split("_")[0])
        names.add(stem)
    return sorted(names)


def completion_candidates(line: str, base_dir: Path | str | Any | None = None) -> list[str]:
    """Return tab-completion options for the partial input line (testable without readline)."""
    buffer = line
    parts = buffer.split()
    if not parts:
        return list(BASE_COMMANDS)

    cmd = parts[0].lower()
    completing_word = parts[-1] if parts else ""
    ends_with_space = buffer.endswith(" ") or (len(parts) > 1 and not completing_word)

    if len(parts) == 1 and not buffer.endswith(" "):
        return [c for c in BASE_COMMANDS if c.startswith(cmd)]

    if cmd == "talk":
        prefix = "" if len(parts) == 1 or buffer.endswith(" ") else completing_word.lower()
        return [n for n in TALK_NPCS if n.lower().startswith(prefix)]

    if cmd == "investigate":
        prefix = "" if len(parts) == 1 or buffer.endswith(" ") else completing_word.lower()
        return [t for t in INVESTIGATE_TARGETS if t.lower().startswith(prefix)]

    if cmd == "combat" and base_dir is not None:
        prefix = "" if len(parts) == 1 or buffer.endswith(" ") else completing_word.lower()
        return [e for e in enemy_short_names(base_dir) if e.lower().startswith(prefix)]

    if cmd in META_COMMANDS and len(parts) == 1:
        return [c for c in META_COMMANDS if c.startswith(cmd)]

    return []


def setup_readline_completer(base_dir: Path | str | Any) -> bool:
    """Enable Tab completion when readline is available. Returns True if enabled."""
    try:
        import readline
    except ImportError:
        return False

    def _completer(text: str, state: int) -> str | None:
        line = readline.get_line_buffer()
        options = completion_candidates(line, base_dir)
        # readline passes `text` = word fragment; filter to suffix matches
        if text:
            options = [o for o in options if o.lower().startswith(text.lower())]
        return options[state] if state < len(options) else None

    readline.set_completer(_completer)
    readline.parse_and_bind("tab: complete")
    if hasattr(readline, "set_completer_delims"):
        readline.set_completer_delims(" \t\n")
    return True


def prompt_player_input() -> str:
    """Read one line from the player."""
    return input("\n행동을 입력하세요: ")


def resolve_enemy_id(query: str, base_dir: Path | str | Any) -> str:
    """Match partial enemy name to characters/*.json id."""
    if hasattr(base_dir, "base_dir"):
        base_dir = base_dir.base_dir
    root = Path(base_dir)
    q = query.strip().lower().replace("-", "_").replace(" ", "_")
    char_dir = root / "characters"
    available = sorted(p.stem for p in char_dir.glob("*.json"))
    if q in available:
        return q
    for cid in available:
        if q in cid or cid.startswith(q):
            return cid
    return q


def parse_player_input(raw: str, base_dir: Path | str | None = None) -> dict[str, Any]:
    """Parse REPL input into a structured command."""
    text = raw.strip()
    if not text:
        return {"kind": "empty"}
    lower = text.lower()
    if lower in ("quit", "exit", "q"):
        return {"kind": "quit"}
    if lower in ("status", "stat", "s"):
        return {"kind": "status"}
    if lower in ("help", "h", "?"):
        return {"kind": "help"}
    if lower.startswith("combat"):
        parts = text.split(maxsplit=1)
        enemy_query = parts[1] if len(parts) > 1 else "malachar"
        enemy_id = resolve_enemy_id(enemy_query, base_dir) if base_dir else enemy_query
        return {"kind": "turn", "action": "combat", "enemy_id": enemy_id}
    return {"kind": "turn", "action": text}


def format_user_error(exc: Exception) -> str:
    """Turn exceptions into player-friendly Korean messages."""
    if isinstance(exc, FileNotFoundError):
        return (
            f"파일/캐릭터를 찾을 수 없습니다.\n"
            f"  원인: {exc}\n"
            f"  힌트: 'help'로 명령어 확인 · NPC 이름은 torren, lilian, grey cloak"
        )
    if isinstance(exc, KeyError):
        return f"게임 상태 오류 (키 누락: {exc}). 'status'로 확인하거나 저장 파일을 점검하세요."
    if isinstance(exc, ValueError):
        return f"입력/설정 오류: {exc}\n  'help'로 사용 가능한 명령을 확인하세요."
    return f"오류: {type(exc).__name__}: {exc}"


def print_turn_result(result: dict[str, Any]) -> None:
    print(f"\n[Turn {result['turn']}] Day {result['day']} — {result['time']} ({result['mode']})")
    for line in result["lines"]:
        print(f"  {line}")


def run_interactive_loop(session: GameSession) -> int:
    """Interactive while-True REPL."""
    print("=== Eldoria 시뮬레이터 시작 ===")
    print(f"모드: {session.mode}")
    print("명령어: explore · talk <npc> · investigate · quest · help · quit")
    if setup_readline_completer(session.manager.base_dir):
        print("Tab: 명령어 자동완성")

    while True:
        try:
            raw = prompt_player_input()
        except (EOFError, KeyboardInterrupt):
            print("\n\n게임 종료. 상태 저장 중...")
            session.save()
            return 0

        parsed = parse_player_input(raw, session.manager.base_dir)
        kind = parsed["kind"]

        if kind == "empty":
            continue
        if kind == "quit":
            session.save()
            print("게임 종료. 상태 저장 완료.")
            return 0
        if kind == "status":
            print(session.status_report())
            continue
        if kind == "help":
            print(INTERACTIVE_HELP)
            continue

        try:
            result = session.run_turn(
                action=parsed["action"],
                enemy_id=parsed.get("enemy_id"),
            )
        except Exception as exc:
            print(format_user_error(exc))
            continue

        print_turn_result(result)

    return 0
