"""유저 창조력·파괴력 게이지."""

from __future__ import annotations

from dataclasses import dataclass, field


PENALTY_REDEEM_RATE = 0.55
REDEMPTION_MIN_SPEND = 8.0


@dataclass
class UserPowers:
    """모든 유저는 창조력·파괴력을 동시에 보유."""

    user_id: str
    creation_gauge: float = 100.0
    creation_gauge_max: float = 100.0
    destruction_gauge: float = 100.0
    destruction_gauge_max: float = 100.0
    creation_data_score: float = 0.0
    destruction_penalty: float = 0.0

    def effective_creation_cap(self) -> float:
        """파괴 패널티가 쌓이면 창조 상한이 줄어듦."""
        penalty_factor = min(0.85, self.destruction_penalty * 0.12)
        return self.creation_gauge_max * (1.0 - penalty_factor)

    def spend_creation(self, amount: float) -> bool:
        if amount > self.creation_gauge:
            return False
        self.creation_gauge -= amount
        self.creation_data_score += amount
        return True

    def spend_destruction(self, amount: float) -> bool:
        if amount > self.destruction_gauge:
            return False
        self.destruction_gauge -= amount
        return True

    def apply_destruction_penalty(self, amount: float) -> float:
        """파괴 시 창조 데이터 마이너스 + 창조력 패널티."""
        self.destruction_penalty += amount
        self.creation_data_score = max(-500.0, self.creation_data_score - amount * 1.5)
        cap = self.effective_creation_cap()
        if self.creation_gauge > cap:
            self.creation_gauge = cap
        return amount

    def resolve_creation_spend(self, full_cost: float) -> float:
        """확정 창조에 쓸 창조력 — 패널티 중에는 부분 소비로 회복 경로를 연다."""
        if full_cost <= 0.0:
            return 0.0
        if self.creation_gauge + 1e-9 < full_cost:
            if self.destruction_penalty <= 0.0:
                return 0.0
            if self.creation_gauge + 1e-9 < REDEMPTION_MIN_SPEND:
                return 0.0
            return self.creation_gauge
        return full_cost

    def redeem_penalty_with_creation(self, creation_spent: float) -> float:
        """패널티 해소는 오직 창조로만 — 창조력 소비량만큼 패널티 감소."""
        if self.destruction_penalty <= 0.0 or creation_spent <= 0.0:
            return 0.0
        redemption = creation_spent * PENALTY_REDEEM_RATE
        applied = min(self.destruction_penalty, redemption)
        self.destruction_penalty -= applied
        self.creation_data_score += applied * 0.85
        new_cap = self.effective_creation_cap()
        self.creation_gauge = min(
            self.creation_gauge + applied * 0.25,
            new_cap,
            self.creation_gauge_max,
        )
        return applied

    def to_dict(self) -> dict[str, float | str]:
        return {
            "user_id": self.user_id,
            "creation_gauge": round(self.creation_gauge, 2),
            "creation_gauge_max": round(self.creation_gauge_max, 2),
            "destruction_gauge": round(self.destruction_gauge, 2),
            "destruction_gauge_max": round(self.destruction_gauge_max, 2),
            "creation_data_score": round(self.creation_data_score, 2),
            "destruction_penalty": round(self.destruction_penalty, 2),
            "effective_creation_cap": round(self.effective_creation_cap(), 2),
        }


@dataclass
class PowerLedger:
    """에리어 구성원 파워 상태."""

    members: dict[str, UserPowers] = field(default_factory=dict)

    def get_or_create(self, user_id: str) -> UserPowers:
        if user_id not in self.members:
            self.members[user_id] = UserPowers(user_id=user_id)
        return self.members[user_id]

    def to_dict(self) -> dict[str, dict]:
        return {uid: p.to_dict() for uid, p in self.members.items()}


def creation_cost_for_object(heat_intensity: float = 0.0, *, is_material: bool = False) -> float:
    cost = 12.0 + heat_intensity * 0.18
    if is_material:
        cost += 18.0
    return cost
