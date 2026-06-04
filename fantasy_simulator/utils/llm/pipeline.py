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
        quick_event: dict[str, Any] | None = None
        mechanics_result: dict[str, Any] | None = None

        for role in pipeline:
            metadata = {
                "role": role,
                "action": action,
                "context": state_snapshot,
                "mechanical_result": mechanical_result or {},
                "mechanical_summary": (mechanical_result or {}).get("summary", ""),
                "narrative_hint": narrative_hint,
                "quick_event": quick_event,
                "mechanics_result": mechanics_result,
            }
            result = self._invoke_role(role, state_snapshot, metadata)
            self.results.append(result)

            if result.parsed:
                if role == "quick_event":
                    quick_event = result.parsed
                    narrative_hint = result.parsed.get("description", narrative_hint)
                elif role == "mechanics":
                    mechanics_result = result.parsed
                    narrative_hint = result.parsed.get("description", narrative_hint)
                self._apply_structured(role, result.parsed, turn=state_snapshot.get("next_turn"))

        return self.results

    def run_consistency_check(self, state_snapshot: dict[str, Any]) -> RoleResult:
        """World arbiter — long-term consistency (every N turns)."""
        metadata = {
            "role": "world_arbiter",
            "action": "consistency_check",
            "context": state_snapshot,
            "mechanical_result": {},
            "mechanical_summary": "",
            "narrative_hint": "",
        }
        result = self._invoke_role("world_arbiter", state_snapshot, metadata)
        self.results = [result]
        if result.parsed:
            self._apply_structured("world_arbiter", result.parsed, turn=state_snapshot.get("next_turn"))
        return result

    def _invoke_role(
        self,
        role: str,
        state_snapshot: dict[str, Any],
        metadata: dict[str, Any],
    ) -> RoleResult:
        resolved = self.llm_router.resolve_with_fallback(role)
        provider = resolved["provider"]

        system_prompt = self.prompt_router.assemble(role)
        user_payload: dict[str, Any] = {
            "state": state_snapshot,
            "metadata": {k: v for k, v in metadata.items() if k != "context"},
        }

        if role == "mechanics":
            user_payload["rules"] = {
                "combat": self.state_loader.load_rule("combat"),
                "magic_system": self.state_loader.load_rule("magic_system"),
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

    def _apply_structured(self, role: str, parsed: dict[str, Any], *, turn: int | None) -> None:
        if role == "quick_event":
            state = self.state_loader.store.load()
            flags = state.setdefault("flags", {})
            flags["last_quick_event"] = parsed
            changes = parsed.get("suggested_state_changes") or {}
            if changes:
                self.state_loader.store.apply_state_changes(changes, turn=turn)
            self.state_loader.store.save(state)

        elif role == "mechanics":
            changes = parsed.get("state_changes") or {}
            if not changes.get("event_log_append") and parsed.get("description") and turn:
                changes = dict(changes)
                changes.setdefault(
                    "event_log_append",
                    [{"turn": turn, "type": parsed.get("result_type", "event"), "summary": parsed["description"]}],
                )
            self.state_loader.store.apply_state_changes(changes, turn=turn)
            char_updates = changes.get("character_updates", {})
            if char_updates:
                state = self.state_loader.store.load()
                self.state_loader.apply_character_updates(state, char_updates)

        elif role == "world_arbiter":
            state = self.state_loader.store.load()
            flags = state.setdefault("flags", {})
            flags["last_consistency_check"] = parsed
            flags["consistency_score"] = parsed.get("consistency_score")
            self.state_loader.store.save(state)

    def narration_text(self) -> str:
        for r in reversed(self.results):
            if r.role == "narrator":
                return r.content
        return ""

    def structured_logs(self) -> list[str]:
        lines: list[str] = []
        for r in self.results:
            if not r.parsed:
                continue
            if r.role == "mechanics":
                lines.append(r.parsed.get("description", ""))
                lines.extend(r.parsed.get("consequences", []))
            elif r.role == "quick_event":
                lines.append(f"[{r.parsed.get('event_title', 'event')}] {r.parsed.get('description', '')}")
        return [ln for ln in lines if ln]

    def consistency_report(self) -> str:
        for r in self.results:
            if r.role == "world_arbiter" and r.parsed:
                p = r.parsed
                return (
                    f"Consistency {p.get('consistency_score')}/10 — "
                    f"{p.get('narrative_direction_suggestion', '')}"
                )
        return ""

    def role_summary(self) -> list[str]:
        return [
            f"{r.role} [{r.model_label}/{r.provider}]"
            + (f" retries={r.retries}" if r.retries else "")
            for r in self.results
        ]
