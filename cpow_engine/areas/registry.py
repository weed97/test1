"""에리어 레지스트리 — 창조·모험 월드 목록."""

from __future__ import annotations

from cpow_engine.areas.area import CreatedArea, found_area
from cpow_engine.areas.laws import AreaLawSet
from cpow_engine.areas.modes import SimulationMode
from cpow_engine.areas.roles import ContributorRole


class AreaRegistry:
    def __init__(self) -> None:
        self._areas: dict[str, CreatedArea] = {}

    def found(
        self,
        founder_id: str,
        label: str,
        *,
        mode: SimulationMode = SimulationMode.CREATION_ADVENTURE,
        template: str | None = None,
        laws: AreaLawSet | None = None,
    ) -> CreatedArea:
        area = found_area(
            founder_id,
            label,
            mode=mode,
            template=template,
            laws=laws,
        )
        self._areas[area.area_id] = area
        return area

    def get(self, area_id: str) -> CreatedArea | None:
        return self._areas.get(area_id)

    def get_or_raise(self, area_id: str) -> CreatedArea:
        area = self.get(area_id)
        if area is None:
            raise KeyError(f"unknown area: {area_id}")
        return area

    def list_areas(self) -> list[CreatedArea]:
        return list(self._areas.values())

    def join(
        self,
        area_id: str,
        creator_id: str,
        *,
        role: ContributorRole | None = None,
    ) -> CreatedArea:
        area = self.get_or_raise(area_id)
        area.join(creator_id, requested_role=role)
        area.maybe_advance_pulse()
        return area
