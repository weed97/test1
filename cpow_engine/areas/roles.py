"""에리어 기여자 역할 — 창시자·협력자·모험가."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cpow_engine.areas.modes import SimulationMode


class ContributorRole(str, Enum):
    FOUNDER = "founder"
    COLLABORATOR = "collaborator"
    ADVENTURER = "adventurer"
    OBSERVER = "observer"

    @classmethod
    def from_str(cls, value: str) -> ContributorRole:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.ADVENTURER


@dataclass(frozen=True)
class RolePermissions:
    can_edit_laws: bool
    can_create_objects: bool
    can_collaborate: bool
    can_adventure: bool
    max_heat_intensity: float
    creations_per_pulse: int


ROLE_PERMISSIONS: dict[ContributorRole, RolePermissions] = {
    ContributorRole.FOUNDER: RolePermissions(
        can_edit_laws=True,
        can_create_objects=True,
        can_collaborate=True,
        can_adventure=True,
        max_heat_intensity=500.0,
        creations_per_pulse=2,
    ),
    ContributorRole.COLLABORATOR: RolePermissions(
        can_edit_laws=False,
        can_create_objects=True,
        can_collaborate=True,
        can_adventure=True,
        max_heat_intensity=200.0,
        creations_per_pulse=1,
    ),
    ContributorRole.ADVENTURER: RolePermissions(
        can_edit_laws=False,
        can_create_objects=False,
        can_collaborate=False,
        can_adventure=True,
        max_heat_intensity=80.0,
        creations_per_pulse=1,
    ),
    ContributorRole.OBSERVER: RolePermissions(
        can_edit_laws=False,
        can_create_objects=False,
        can_collaborate=False,
        can_adventure=False,
        max_heat_intensity=0.0,
        creations_per_pulse=0,
    ),
}


def default_role_for_mode(
    mode: SimulationMode,
    *,
    is_founder: bool = False,
) -> ContributorRole:
    if is_founder:
        return ContributorRole.FOUNDER
    if mode == SimulationMode.CREATION:
        return ContributorRole.COLLABORATOR
    if mode == SimulationMode.ADVENTURE:
        return ContributorRole.ADVENTURER
    return ContributorRole.COLLABORATOR


def permissions_for(role: ContributorRole) -> RolePermissions:
    return ROLE_PERMISSIONS[role]
