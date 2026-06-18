"""시뮬레이션 모드 — 창조 / 모험 / 창조모험."""

from __future__ import annotations

from enum import Enum


class SimulationMode(str, Enum):
    """에리어별 플레이 모드."""

    CREATION = "creation"
    """초기 창조자가 법칙·틀을 세우는 모드."""

    ADVENTURE = "adventure"
    """창조된 틀 안에서 탐험·상호작용하는 모드."""

    CREATION_ADVENTURE = "creation_adventure"
    """창조자와 협력자가 함께 영역을 키우는 하이브리드 모드."""

    @classmethod
    def from_str(cls, value: str) -> SimulationMode:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.CREATION_ADVENTURE
