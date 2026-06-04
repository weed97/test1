"""Turn pipeline — invokes LLM roles in configured order."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from utils.llm.base import LLMMessage, LLMRequest
from utils.llm.router import LLMRouter
from utils.prompt_router import PromptRouter
from utils.structured_output import StructuredOutputClient, StructuredOutputError


@dataclass
class RoleResult:
    role: str
    model: str
    model_label: str
    provider: str
    content: str
    parsed: dict[str, Any] | None = None
    retries: int = 0


@dataclass
class TurnPipeline:
    base_dir: Path
    llm_router: LLMRouter
    prompt_router: PromptRouter
    structured: StructuredOutputClient
    state_loader: Any
    results: list[RoleResult] = field(default_factory=list)

    @classmethod
    def create(cls, base_dir: Path, state_loader: Any) -> TurnPipeline:
        root = Path(base_dir)
        llm_router = LLMRouter(root)
        prompt_router = PromptRouter.from_package_root(root)
        so_cfg = llm_router.structured_config()
        structured = StructuredOutputClient(
            schemas_dir=root / "schemas",
            max_retries=so_cfg.get("max_retries", 3),
            repair_on_failure=so_cfg.get("repair_on_failure", True),
        )
        return cls(root, llm_router, prompt_router, structured, state_loader)

    def run(
        self,
        action: str,
        *,
        state_snapshot: dict[str, Any],
        mechanical_result: dict[str, Any] | None = None,
        roles: list[str] | None = None,
        hybrid: bool = False,
    ) -> list[RoleResult]:
        self.results = []
        self.prompt_router.set_combat_context(bool(state_snapshot.get("combat")))

        if roles is not None:
            pipeline = roles
        elif hybrid:
            pipeline = self.llm_router.hybrid_pipeline(action) or self.prompt_router.pipeline_for_action(
                action
            )
        else:
            pipeline = self.prompt_router.pipeline_for_action(action)

        narrative_hint = mechanical_result.get("summary", "") if mechanical_result else ""
        event_alternatives: dict[str, Any] | None = None

        for role in pipeline:
            metadata = {
                "role": role,
                "action": action,
                "context": state_snapshot,
                "mechanical_result": mechanical_result or {},
                "mechanical_summary": (mechanical_result or {}).get("summary", ""),
                "narrative_hint": narrative_hint,
                "event_alternatives": event_alternatives,
            }
            result = self._invoke_role(role, state_snapshot, metadata)
            self.results.append(result)

            if result.parsed:
                if role == "event_alternatives":
                    event_alternatives = result.parsed
                    narrative_hint = result.parsed.get("narrative_hint", narrative_hint)
                elif role == "world_arbiter":
                    narrative_hint = result.parsed.get("narrative_hint", narrative_hint)
                self._apply_structured(role, result.parsed)

        return self.results

    def _invoke_role(
        self,
        role: str,
        state_snapshot: dict[str, Any],
        metadata: dict[str, Any],
    ) -> RoleResult:
        resolved = self.llm_router.resolve_with_fallback(role)
        provider = resolved["provider"]
        model_key = resolved["model_key"]

        system_prompt = self.prompt_router.assemble(role, model=model_key)
        user_payload = {
            "state": state_snapshot,
            "metadata": {k: v for k, v in metadata.items() if k != "context"},
        }
        if resolved["structured"] and resolved["schema"]:
            user_payload["output_schema"] = self.structured.load_schema(resolved["schema"])

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(
                role="user",
                content=json.dumps(user_payload, ensure_ascii=False, indent=2),
            ),
        ]

        schema_obj = None
        if resolved["structured"] and resolved["schema"]:
            schema_obj = self.structured.load_schema(resolved["schema"])

        request = LLMRequest(
            model=resolved["model"],
            messages=messages,
            temperature=resolved["temperature"],
            structured=resolved["structured"],
            schema_name=resolved["schema"],
            schema=schema_obj,
            max_tokens=resolved.get("max_tokens"),
            reasoning_effort=resolved.get("reasoning_effort"),
            effort=resolved.get("effort"),
            metadata=metadata,
        )

        retries = 0
        last_raw = ""
        while retries <= self.structured.max_retries:
            response = provider.complete(request)
            last_raw = response.content
            if not resolved["structured"]:
                return RoleResult(
                    role=role,
                    model=resolved["model"],
                    model_label=resolved["model_label"],
                    provider=provider.name,
                    content=response.content,
                    retries=retries,
                )
            try:
                parsed = self.structured.parse_and_validate(response.content, resolved["schema"])
                return RoleResult(
                    role=role,
                    model=resolved["model"],
                    model_label=resolved["model_label"],
                    provider=provider.name,
                    content=response.content,
                    parsed=parsed,
                    retries=retries,
                )
            except StructuredOutputError as exc:
                retries += 1
                if not self.structured.repair_on_failure or retries > self.structured.max_retries:
                    raise
                repair = self.structured.build_repair_prompt(
                    resolved["schema"], last_raw, exc.errors or [str(exc)]
                )
                request.messages.append(LLMMessage(role="assistant", content=last_raw))
                request.messages.append(LLMMessage(role="user", content=repair))

        raise StructuredOutputError("Structured output retries exhausted", raw=last_raw)

    def _apply_structured(self, role: str, parsed: dict[str, Any]) -> None:
        if role == "event_alternatives":
            state = self.state_loader.store.load()
            flags = state.setdefault("flags", {})
            flags["last_event_alternatives"] = parsed
            self.state_loader.store.save(state)

        elif role == "world_arbiter":
            patches: dict[str, Any] = {
                "event_log_append": parsed.get("event_log_append", []),
            }
            if parsed.get("world"):
                patches["world"] = parsed["world"]
            if parsed.get("factions"):
                patches["factions"] = parsed["factions"]
            if parsed.get("flags"):
                patches["flags"] = parsed["flags"]
            self.state_loader.store.apply_patches(patches)

        elif role == "combat_referee":
            wu = parsed.get("world_updates", {})
            patches: dict[str, Any] = {}
            if "combat" in wu:
                patches["combat"] = wu["combat"]
            if wu.get("event_log_append"):
                patches["event_log_append"] = wu["event_log_append"]
            if patches:
                self.state_loader.store.apply_patches(patches)
            char_updates = parsed.get("character_updates", {})
            if char_updates:
                state = self.state_loader.store.load()
                self.state_loader.apply_character_updates(state, char_updates)

    def narration_text(self) -> str:
        for r in reversed(self.results):
            if r.role == "narrator":
                return r.content
        return ""

    def structured_logs(self) -> list[str]:
        lines = []
        for r in self.results:
            if r.parsed and r.role == "combat_referee":
                lines.extend(r.parsed.get("combat_log", []))
        return lines

    def role_summary(self) -> list[str]:
        return [
            f"{r.role} [{r.model_label}/{r.provider}]"
            + (f" retries={r.retries}" if r.retries else "")
            for r in self.results
        ]
