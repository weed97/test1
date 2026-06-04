"""Assemble role prompts with model-specific overlays."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.io_helpers import load_json, load_text


class PromptRouter:
    """Resolve base + model overlay prompts for a role."""

    def __init__(self, base_dir: Path, routing_config: dict[str, Any]) -> None:
        self.base_dir = base_dir
        self.routing = routing_config
        self._cache: dict[tuple[str, str], str] = {}
        self._in_combat = False

    @classmethod
    def from_package_root(cls, root: Path | str) -> PromptRouter:
        root = Path(root)
        routing = load_json(root / "config" / "llm_routing.json")
        return cls(root, routing)

    def set_combat_context(self, in_combat: bool) -> None:
        self._in_combat = in_combat

    def model_for_role(self, role: str) -> str:
        return self.routing["roles"][role]["model"]

    def role_config(self, role: str) -> dict[str, Any]:
        return self.routing["roles"][role]

    def pipeline_for_action(self, action: str) -> list[str]:
        pipelines = self.routing.get("pipelines", {})
        if action == "combat" or (action == "combat_round") or self._in_combat:
            return pipelines.get("combat_round", ["combat_referee", "narrator"])
        return pipelines.get(action, ["narrator"])

    def assemble(self, role: str, *, model: str | None = None) -> str:
        model = model or self.model_for_role(role)
        cache_key = (role, model)
        if cache_key in self._cache:
            return self._cache[cache_key]

        base_path = self.base_dir / "prompts" / "base" / f"{role}.txt"
        if not base_path.exists():
            raise FileNotFoundError(f"Base prompt missing: {base_path}")

        parts = [load_text(base_path)]

        overlay_path = self.base_dir / "prompts" / "models" / model / f"{role}_overlay.txt"
        if overlay_path.exists():
            parts.append(load_text(overlay_path))

        traits = self.routing.get("models", {}).get(model, {}).get("traits", {})
        if traits:
            trait_lines = "\n".join(f"- {k}: {v}" for k, v in traits.items())
            parts.append(f"## 모델 특성\n{trait_lines}")

        text = "\n\n".join(parts)
        self._cache[cache_key] = text
        return text

    def schema_name_for_role(self, role: str) -> str | None:
        cfg = self.role_config(role)
        if cfg.get("structured"):
            return cfg.get("schema")
        return None
