"""에리어 활동·체류 — 실제 인간 공동창작 vs 봇 창작 구분."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cpow_engine.areas.area import CreatedArea


def is_human_member(area: CreatedArea, user_id: str) -> bool:
    return user_id in area.members and user_id not in area.npcs


def is_npc_creation(obj) -> bool:
    return obj.get_property("is_npc_creation") is not None


@dataclass
class MemberAreaRecord:
    user_id: str
    joined_at: float
    last_active_at: float
    human_confirmed_creations: int = 0
    creation_power_invested: float = 0.0
    co_creation_events: int = 0
    consensus_votes_cast: int = 0
    collaborative_pulses: int = 0

    def collab_signals(self) -> int:
        return (
            self.co_creation_events
            + self.consensus_votes_cast
            + self.collaborative_pulses
        )

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "user_id": self.user_id,
            "joined_at": self.joined_at,
            "last_active_at": self.last_active_at,
            "human_confirmed_creations": self.human_confirmed_creations,
            "creation_power_invested": round(self.creation_power_invested, 2),
            "co_creation_events": self.co_creation_events,
            "consensus_votes_cast": self.consensus_votes_cast,
            "collaborative_pulses": self.collaborative_pulses,
            "collab_signals": self.collab_signals(),
        }


@dataclass
class AreaVitalitySnapshot:
    human_members: int = 0
    npc_members: int = 0
    human_confirmed_creations: int = 0
    npc_creations: int = 0
    collaborative_events: int = 0
    distinct_human_creators: int = 0

    @property
    def npc_creation_share(self) -> float:
        total = self.human_confirmed_creations + self.npc_creations
        if total <= 0:
            return 0.0
        return self.npc_creations / total

    def to_dict(self) -> dict[str, float | int]:
        return {
            "human_members": self.human_members,
            "npc_members": self.npc_members,
            "human_confirmed_creations": self.human_confirmed_creations,
            "npc_creations": self.npc_creations,
            "collaborative_events": self.collaborative_events,
            "distinct_human_creators": self.distinct_human_creators,
            "npc_creation_share": round(self.npc_creation_share, 3),
        }


@dataclass
class AreaActivityTracker:
    """에리어별 인간 창작·공동창작 활동 기록."""

    area_id: str
    members: dict[str, MemberAreaRecord] = field(default_factory=dict)
    _human_creators: set[str] = field(default_factory=set)
    human_confirmed_creations: int = 0
    npc_creations: int = 0
    collaborative_events: int = 0

    def record_join(self, user_id: str, *, now: float | None = None) -> None:
        ts = now if now is not None else time.time()
        if user_id not in self.members:
            self.members[user_id] = MemberAreaRecord(user_id, ts, ts)
        else:
            self.members[user_id].last_active_at = ts

    def record_human_creation(
        self,
        user_id: str,
        *,
        invested: float,
        now: float | None = None,
    ) -> None:
        ts = now if now is not None else time.time()
        rec = self.members.setdefault(
            user_id,
            MemberAreaRecord(user_id, ts, ts),
        )
        rec.human_confirmed_creations += 1
        rec.creation_power_invested += invested
        rec.last_active_at = ts
        self.human_confirmed_creations += 1
        self._human_creators.add(user_id)

    def record_npc_creation(self) -> None:
        self.npc_creations += 1

    def record_co_creation(
        self,
        user_id: str,
        *,
        now: float | None = None,
    ) -> None:
        ts = now if now is not None else time.time()
        rec = self.members.setdefault(
            user_id,
            MemberAreaRecord(user_id, ts, ts),
        )
        rec.co_creation_events += 1
        rec.last_active_at = ts
        self.collaborative_events += 1

    def record_consensus_vote(
        self,
        user_id: str,
        *,
        now: float | None = None,
    ) -> None:
        ts = now if now is not None else time.time()
        rec = self.members.setdefault(
            user_id,
            MemberAreaRecord(user_id, ts, ts),
        )
        rec.consensus_votes_cast += 1
        rec.last_active_at = ts
        self.collaborative_events += 1

    def record_pulse_collab(
        self,
        human_creators: set[str],
        *,
        now: float | None = None,
    ) -> None:
        if len(human_creators) < 2:
            return
        ts = now if now is not None else time.time()
        self.collaborative_events += 1
        for uid in human_creators:
            rec = self.members.setdefault(
                uid,
                MemberAreaRecord(uid, ts, ts),
            )
            rec.collaborative_pulses += 1
            rec.last_active_at = ts

    def member_record(self, user_id: str) -> MemberAreaRecord | None:
        return self.members.get(user_id)

    def vitality(self, area: CreatedArea) -> AreaVitalitySnapshot:
        human_members = sum(
            1 for uid in area.members if is_human_member(area, uid)
        )
        npc_members = len(area.npcs)
        return AreaVitalitySnapshot(
            human_members=human_members,
            npc_members=npc_members,
            human_confirmed_creations=self.human_confirmed_creations,
            npc_creations=self.npc_creations,
            collaborative_events=self.collaborative_events,
            distinct_human_creators=len(self._human_creators),
        )

    def to_public_dict(self, area: CreatedArea) -> dict:
        return {
            "area_id": self.area_id,
            "vitality": self.vitality(area).to_dict(),
            "members": {
                uid: rec.to_dict()
                for uid, rec in self.members.items()
                if is_human_member(area, uid)
            },
        }
