"""성좌 헌터 시뮬레이터의 핵심 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class Hunter:
    """헌터(플레이어) 상태."""

    name: str = "무명"
    title: str = "각성하지 못한 자"
    level: int = 1
    hp: int = 100
    max_hp: int = 100
    stamina: int = 50
    max_stamina: int = 50
    attack: int = 12
    defense: int = 8
    luck: int = 10
    sanity: int = 80
    max_sanity: int = 80
    coins: int = 0
    exp: int = 0

    @property
    def alive(self) -> bool:
        return self.hp > 0 and self.sanity > 0

    def clamp(self) -> None:
        """모든 스탯을 유효 범위로 보정한다."""
        self.hp = max(0, min(self.hp, self.max_hp))
        self.stamina = max(0, min(self.stamina, self.max_stamina))
        self.sanity = max(0, min(self.sanity, self.max_sanity))
        self.coins = max(0, self.coins)
        self.exp = max(0, self.exp)
        self.level = max(1, self.level)

    def gain_exp(self, amount: int) -> int:
        """경험치를 얻고 레벨업한 횟수를 반환한다."""
        self.exp += max(0, amount)
        levels = 0
        while self.exp >= self.level * 100:
            self.exp -= self.level * 100
            self.level += 1
            self.max_hp += 15
            self.max_stamina += 8
            self.attack += 3
            self.defense += 2
            self.luck += 1
            self.max_sanity += 5
            self.hp = self.max_hp
            self.sanity = self.max_sanity
            levels += 1
        return levels

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Constellation:
    """헌터를 후원하는 성좌."""

    name: str = "이름 없는 성좌"
    favor: int = 30
    patronage: str = "방관자"

    def clamp(self) -> None:
        self.favor = max(0, min(self.favor, 1000))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MonsterUnit:
    """게이트 몬스터 유닛. exception_variables 는 전투 중에만 적용되는 예외 변수다."""

    id: str
    name: str
    grade: str = "F"
    hp: int = 40
    attack: int = 10
    defense: int = 5
    reward_coins: int = 30
    reward_exp: int = 25
    trait: str = ""
    exception_variables: Dict[str, float] = field(default_factory=dict)

    def power(self) -> float:
        return self.attack + self.defense * 0.5 + self.hp * 0.05

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HunterPreset:
    """성좌 헌터 로스터 항목 (헌터 + 후원 성좌 프리셋)."""

    id: str
    hunter: Hunter
    constellation: Constellation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "hunter": self.hunter.to_dict(),
            "constellation": self.constellation.to_dict(),
        }


@dataclass
class EventRecord:
    """단일 이벤트 로그 항목."""

    turn: int
    kind: str
    title: str
    description: str
    effects: Dict[str, int] = field(default_factory=dict)
    mutated: bool = False
    chained: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GameState:
    """시뮬레이션 전체 상태."""

    hunter: Hunter = field(default_factory=Hunter)
    constellation: Constellation = field(default_factory=Constellation)
    turn: int = 0
    log: List[EventRecord] = field(default_factory=list)
    finished: bool = False
    outcome: str = ""
    defeated_monsters: List[str] = field(default_factory=list)

    def record(self, event: EventRecord) -> None:
        self.log.append(event)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hunter": self.hunter.to_dict(),
            "constellation": self.constellation.to_dict(),
            "turn": self.turn,
            "finished": self.finished,
            "outcome": self.outcome,
            "defeated_monsters": list(self.defeated_monsters),
            "log": [e.to_dict() for e in self.log],
        }
