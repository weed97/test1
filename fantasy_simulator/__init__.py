"""fantasy_simulator — an LLM-orchestrated, large-scale medieval-fantasy world simulator.

This package is the *optimised* architecture for Aetheria.  Instead of hard-coding
every line of NPC dialogue, it treats large language models as role-players and uses a
deterministic engine as the referee.  The design follows a clean separation:

    world_state.json        the single source of truth for the live world
    rules/                  detailed design documents (magic, combat, economy, ...)
    characters/             per-character data (sheet + memory + voice)
    prompts/                role-based system prompts + multi-model routing
    simulation_engine.py    the orchestrator main loop
    utils/                  llm client, state IO, context building, memory, dice

Why this shape?

* **world_state.json is canonical.**  Every subsystem reads/writes it, so the world is
  always inspectable and resumable.
* **rules/ are documents, not code.**  They are injected into prompts so models reason
  with consistent, designer-authored systems — and they can be edited without touching
  Python.
* **prompts/ separate *role* from *engine*.**  A narrator, an NPC actor, a world-event
  director, a rules referee and a memory summariser each have a focused system prompt.
* **multi-model routing** lets each role use the model that suits it best (a strong model
  for the narrator and major NPCs, a cheap/fast model for ambient crowds) — see
  ``prompts/model_assignments.json``.
* **offline by default.**  With no API keys the deterministic Mock provider drives the
  whole simulation so it always runs; real providers plug in via environment variables.
"""

from __future__ import annotations

import os

__version__ = "1.0.0"

ROOT = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.join(ROOT, "rules")
CHARACTERS_DIR = os.path.join(ROOT, "characters")
PROMPTS_DIR = os.path.join(ROOT, "prompts")
LOGS_DIR = os.path.join(ROOT, "logs")
WORLD_STATE_PATH = os.path.join(ROOT, "world_state.json")

__all__ = ["__version__", "ROOT", "RULES_DIR", "CHARACTERS_DIR", "PROMPTS_DIR",
           "LOGS_DIR", "WORLD_STATE_PATH"]
