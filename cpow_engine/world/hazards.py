"""바이옴 위험 주기 — 소리 예고 단계."""

from __future__ import annotations

from dataclasses import dataclass

from cpow_engine.world.biomes import BIOME_CATALOG, BiomeDef, HazardPhase


@dataclass
class HazardState:
    phase_index: int = 0
    tick_in_phase: int = 0

    def to_dict(self) -> dict:
        return {
            "phase_index": self.phase_index,
            "tick_in_phase": self.tick_in_phase,
        }


_PHASE_TICKS = 120


def advance_hazard(state: HazardState, biome: BiomeDef) -> HazardState:
    state.tick_in_phase += 1
    if state.tick_in_phase >= _PHASE_TICKS:
        state.tick_in_phase = 0
        state.phase_index = (state.phase_index + 1) % max(1, len(biome.phases))
    return state


def hazard_phase_for(biome: BiomeDef, state: HazardState) -> HazardPhase:
    phases = biome.phases or ("calm",)
    phase_id = phases[state.phase_index % len(phases)]
    danger = 0
    if "warning" in phase_id:
        danger = 2
    elif phase_id not in ("calm", "harvest", "growth", "tide_low"):
        danger = 3 if "eruption" in phase_id or "tsunami" in phase_id else 2
    audio = biome.hazard_audio.get(phase_id, "")
    stage = "distant"
    if "warning" in phase_id:
        stage = "warning"
        seconds = max(0.0, (_PHASE_TICKS - state.tick_in_phase) * 1.0)
    elif danger >= 3:
        stage = "imminent"
        seconds = 0.0
    else:
        seconds = 0.0
    return HazardPhase(
        phase_id=phase_id,
        label=phase_id,
        danger_level=danger,
        audio_cue=audio,
        audio_stage=stage,
        seconds_to_event=seconds,
    )


def hazard_snapshot(biome: BiomeDef, state: HazardState) -> dict:
    phase = hazard_phase_for(biome, state)
    return {
        "phase": {
            "phase_id": phase.phase_id,
            "label": phase.label,
            "danger_level": phase.danger_level,
            "audio_cue": phase.audio_cue,
            "audio_stage": phase.audio_stage,
            "seconds_to_event": phase.seconds_to_event,
        },
        "state": state.to_dict(),
    }
