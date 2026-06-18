"""1인 1계정 — 거버넌스 참여 신원 검증."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field


def person_id_from_key(person_key: str) -> str:
    """실명·외부 ID 등 person_key → 불가역 person_id."""
    normalized = person_key.strip().encode("utf-8")
    digest = hashlib.sha256(normalized).hexdigest()
    return f"person_{digest[:24]}"


@dataclass
class IdentityPolicy:
    """1인 1계정 — 시스템 거버넌스 참여 전 신원 등록 필수."""

    require_verified: bool = True
    min_person_key_chars: int = 8
    one_person_one_account: bool = True
    one_account_one_person: bool = True
    block_duplicate_person_in_proposal: bool = True

    def to_dict(self) -> dict[str, bool | int]:
        return {
            "require_verified": self.require_verified,
            "min_person_key_chars": self.min_person_key_chars,
            "one_person_one_account": self.one_person_one_account,
            "one_account_one_person": self.one_account_one_person,
            "block_duplicate_person_in_proposal": self.block_duplicate_person_in_proposal,
        }


@dataclass
class IdentityBinding:
    person_id: str
    user_id: str
    bound_at: float = field(default_factory=time.time)
    verification_method: str = "person_key"

    def to_public_dict(self) -> dict[str, str | float]:
        return {
            "person_id": self.person_id,
            "user_id": self.user_id,
            "bound_at": self.bound_at,
            "verification_method": self.verification_method,
        }


@dataclass
class IdentityResult:
    ok: bool
    reason: str = ""
    codes: list[str] = field(default_factory=list)
    binding: IdentityBinding | None = None


class MemberIdentityRegistry:
    """전역 1인 1계정 — person_id ↔ user_id 양방향 유일."""

    def __init__(self, policy: IdentityPolicy | None = None) -> None:
        self.policy = policy or IdentityPolicy()
        self._person_to_user: dict[str, str] = {}
        self._user_to_person: dict[str, str] = {}
        self._bindings: dict[str, IdentityBinding] = {}

    def register(self, user_id: str, person_key: str) -> IdentityResult:
        if not user_id:
            return IdentityResult(False, reason="user_id_required", codes=["user_id_required"])
        if len(person_key.strip()) < self.policy.min_person_key_chars:
            return IdentityResult(
                False,
                reason="person_key_too_short",
                codes=["person_key_too_short"],
            )

        person_id = person_id_from_key(person_key)

        if self.policy.one_person_one_account:
            existing_user = self._person_to_user.get(person_id)
            if existing_user is not None and existing_user != user_id:
                return IdentityResult(
                    False,
                    reason="duplicate_person_account",
                    codes=["one_person_one_account"],
                )

        if self.policy.one_account_one_person:
            existing_person = self._user_to_person.get(user_id)
            if existing_person is not None and existing_person != person_id:
                return IdentityResult(
                    False,
                    reason="account_identity_locked",
                    codes=["one_account_one_person"],
                )

        binding = IdentityBinding(person_id=person_id, user_id=user_id)
        self._person_to_user[person_id] = user_id
        self._user_to_person[user_id] = person_id
        self._bindings[user_id] = binding
        return IdentityResult(True, reason="identity_registered", binding=binding)

    def is_verified(self, user_id: str) -> bool:
        return user_id in self._user_to_person

    def person_id_for(self, user_id: str) -> str | None:
        return self._user_to_person.get(user_id)

    def user_id_for_person(self, person_id: str) -> str | None:
        return self._person_to_user.get(person_id)

    def binding_for(self, user_id: str) -> IdentityBinding | None:
        return self._bindings.get(user_id)

    def validate_for_governance(self, user_id: str) -> IdentityResult:
        if not self.policy.require_verified:
            return IdentityResult(True, reason="identity_check_skipped")
        if not self.is_verified(user_id):
            return IdentityResult(
                False,
                reason="identity_not_verified",
                codes=["identity_registration_required"],
            )
        binding = self._bindings.get(user_id)
        return IdentityResult(True, reason="identity_verified", binding=binding)

    def proposal_person_conflict(
        self,
        user_id: str,
        participant_user_ids: set[str],
    ) -> IdentityResult:
        """동일 인물이 여러 계정으로 같은 발의에 참여하는지."""
        if not self.policy.block_duplicate_person_in_proposal:
            return IdentityResult(True, reason="duplicate_check_skipped")
        person_id = self.person_id_for(user_id)
        if person_id is None:
            return IdentityResult(
                False,
                reason="identity_not_verified",
                codes=["identity_registration_required"],
            )
        for other in participant_user_ids:
            if other == user_id:
                continue
            if self.person_id_for(other) == person_id:
                return IdentityResult(
                    False,
                    reason="duplicate_person_in_proposal",
                    codes=["one_person_one_account"],
                )
        return IdentityResult(True, reason="no_person_conflict")

    def verified_count(self) -> int:
        return len(self._user_to_person)

    def bindings_public(self) -> list[dict[str, str | float]]:
        return [b.to_public_dict() for b in self._bindings.values()]
