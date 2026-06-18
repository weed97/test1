"""에리어 간 외교 — 적대·중립·동맹."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from cpow_engine.areas.roles import ContributorRole


class DiplomaticStance(str, Enum):
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    ALLIANCE = "alliance"

    @classmethod
    def from_str(cls, value: str) -> DiplomaticStance:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.NEUTRAL


@dataclass
class DiplomaticLink:
    """한 방향 외교 선언."""

    from_area_id: str
    to_area_id: str
    stance: DiplomaticStance
    declared_by: str
    declared_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "from_area_id": self.from_area_id,
            "to_area_id": self.to_area_id,
            "stance": self.stance.value,
            "declared_by": self.declared_by,
            "declared_at": self.declared_at,
        }


@dataclass
class PendingHostileDeclaration:
    from_area_id: str
    to_area_id: str
    endorsers: set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "from_area_id": self.from_area_id,
            "to_area_id": self.to_area_id,
            "endorsers": sorted(self.endorsers),
            "endorsers_count": len(self.endorsers),
        }


@dataclass
class DiplomacyLedger:
    """에리어 쌍별 외교 상태 — 비대칭 선언 후 해석."""

    _links: dict[tuple[str, str], DiplomaticLink] = field(default_factory=dict)
    _pending_hostile: dict[tuple[str, str], PendingHostileDeclaration] = field(
        default_factory=dict,
    )

    def _key(self, from_area_id: str, to_area_id: str) -> tuple[str, str]:
        return (from_area_id, to_area_id)

    def declare(
        self,
        from_area_id: str,
        to_area_id: str,
        stance: DiplomaticStance,
        *,
        declared_by: str,
    ) -> DiplomaticLink:
        if from_area_id == to_area_id:
            raise ValueError("cannot declare diplomacy with self")
        link = DiplomaticLink(
            from_area_id=from_area_id,
            to_area_id=to_area_id,
            stance=stance,
            declared_by=declared_by,
        )
        self._links[self._key(from_area_id, to_area_id)] = link
        return link

    def endorse_hostile(
        self,
        from_area_id: str,
        to_area_id: str,
        actor_id: str,
        *,
        min_endorsers: int = 2,
    ) -> tuple[bool, PendingHostileDeclaration | None, str]:
        """적대 선언 — 단독 창립자 불가, 공동 확인 필요."""
        key = self._key(from_area_id, to_area_id)
        pending = self._pending_hostile.get(key)
        if pending is None:
            pending = PendingHostileDeclaration(from_area_id, to_area_id)
            self._pending_hostile[key] = pending
        pending.endorsers.add(actor_id)
        if len(pending.endorsers) < min_endorsers:
            return False, pending, "hostile_pending_endorsement"
        self._pending_hostile.pop(key, None)
        return True, pending, "hostile_confirmed"

    def pending_hostile_for(self, area_id: str) -> list[dict]:
        out: list[dict] = []
        for (src, dst), pending in self._pending_hostile.items():
            if src == area_id or dst == area_id:
                out.append(pending.to_dict())
        return out

    def direct_stance(self, from_area_id: str, to_area_id: str) -> DiplomaticStance:
        link = self._links.get(self._key(from_area_id, to_area_id))
        return link.stance if link else DiplomaticStance.NEUTRAL

    def resolved_stance(self, area_a: str, area_b: str) -> DiplomaticStance:
        """실효 관계 — 적대 우선, 상호 동맹만 협력."""
        if area_a == area_b:
            return DiplomaticStance.ALLIANCE
        ab = self.direct_stance(area_a, area_b)
        ba = self.direct_stance(area_b, area_a)
        if ab == DiplomaticStance.HOSTILE or ba == DiplomaticStance.HOSTILE:
            return DiplomaticStance.HOSTILE
        if ab == DiplomaticStance.ALLIANCE and ba == DiplomaticStance.ALLIANCE:
            return DiplomaticStance.ALLIANCE
        return DiplomaticStance.NEUTRAL


def can_cross_area_combat(stance: DiplomaticStance) -> bool:
    return stance == DiplomaticStance.HOSTILE


def can_cooperative_create(stance: DiplomaticStance, role: ContributorRole) -> bool:
    if stance != DiplomaticStance.ALLIANCE:
        return False
    return role in (ContributorRole.FOUNDER, ContributorRole.COLLABORATOR)


def observer_can_intervene_cross_area(
    stance: DiplomaticStance,
    role: ContributorRole,
) -> bool:
    """중립·적대·동맹 모두 — 관찰자는 타 에리어에 관여 불가."""
    if role != ContributorRole.OBSERVER:
        return True
    return False
