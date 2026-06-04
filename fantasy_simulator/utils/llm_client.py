"""Multi-model LLM client with role-based routing and an offline Mock provider.

This is where *"각 모델의 장점을 최대한 활용"* lives: every orchestration **role**
(narrator, npc, world_event, referee, memory_summarizer, director) is routed to the
model best suited to it via ``prompts/model_assignments.json``.  A strong model can voice
the narrator and major NPCs while a cheap, fast model handles ambient crowds and
summaries.

Providers implemented:
* ``mock``      — deterministic, context-aware, **always available** (needs no network).
* ``openai``    — OpenAI Chat Completions (uses the ``openai`` SDK if installed, else HTTP).
* ``anthropic`` — Anthropic Messages   (uses the ``anthropic`` SDK if installed, else HTTP).

If a routed provider is unavailable (missing key/SDK/network), the client transparently
falls back to ``mock`` so a large simulation never stalls.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .dice import Dice


@dataclass
class LLMResponse:
    text: str
    role: str
    provider: str
    model: str
    approx_tokens: int = 0
    fell_back: bool = False
    raw: Any = None


# --------------------------------------------------------------------------- #
#  Providers                                                                   #
# --------------------------------------------------------------------------- #
class BaseProvider:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def complete(self, system: str, user: str, *, model: str, temperature: float,
                 max_tokens: int, context: dict | None = None) -> str:
        raise NotImplementedError


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system, user, *, model, temperature, max_tokens, context=None) -> str:
        try:  # prefer the official SDK if present
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            resp = client.chat.completions.create(
                model=model, temperature=temperature, max_tokens=max_tokens,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}])
            return resp.choices[0].message.content or ""
        except ImportError:
            pass
        payload = json.dumps({
            "model": model, "temperature": temperature, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=payload,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self) -> None:
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system, user, *, model, temperature, max_tokens, context=None) -> str:
        try:
            from anthropic import Anthropic  # type: ignore
            client = Anthropic(api_key=self.api_key, base_url=self.base_url)
            resp = client.messages.create(
                model=model, temperature=temperature, max_tokens=max_tokens,
                system=system, messages=[{"role": "user", "content": user}])
            return "".join(block.text for block in resp.content if hasattr(block, "text"))
        except ImportError:
            pass
        payload = json.dumps({
            "model": model, "temperature": temperature, "max_tokens": max_tokens,
            "system": system, "messages": [{"role": "user", "content": user}],
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/messages", data=payload,
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        return "".join(b.get("text", "") for b in data.get("content", []))


class MockProvider(BaseProvider):
    """Deterministic, context-aware stand-in so the world runs with no network.

    It produces role-appropriate text by reading the structured ``context`` the
    orchestrator passes, so offline runs are coherent and genuinely useful for
    developing the simulation before wiring real models.
    """

    name = "mock"

    def available(self) -> bool:
        return True

    def complete(self, system, user, *, model, temperature, max_tokens, context=None) -> str:
        ctx = context or {}
        role = ctx.get("role", "narrator")
        rng = Dice(f"{role}:{ctx.get('seed_key', user[:32])}")
        handler = getattr(self, f"_gen_{role}", self._gen_narrator)
        return handler(ctx, rng)

    # -- per-role generators -------------------------------------------------
    def _gen_npc(self, ctx: dict, rng: Dice) -> str:
        name = ctx.get("name", "The stranger")
        mood = ctx.get("mood", "content")
        disp = ctx.get("disposition", "neutral")
        topic = ctx.get("topic", "greeting")
        voice = ctx.get("voice", "")
        traits = ctx.get("traits", [])
        openings = {
            "hostile": ["Speak quickly, before I lose patience.",
                        "You dare address me?"],
            "wary": ["What do you want?", "State your business."],
            "neutral": ["Well met.", "Hm? Yes?"],
            "friendly": ["Ah, good to see you!", "Always a pleasure."],
            "devoted": ["My friend! Anything you need.", "You honour me."],
        }
        body = {
            "greeting": "",
            "rumors": rng.choice([
                "Folk say the Wyrm of Frostpeak stirs in its sleep.",
                "The Redhand grow bolder on the roads each week.",
                "Strange lights drift over the Mirewater Fen at night.",
            ]),
            "quest": "There is a task, if you've the stomach for it.",
            "trade": "Coin talks. Take a look at my wares.",
            "about": ctx.get("self_line", "I get by, same as anyone."),
            "area": f"This is {ctx.get('location', 'a quiet place')}.",
            "farewell": rng.choice(["Safe travels.", "Mind how you go."]),
        }
        line = openings.get(disp, openings["neutral"])[rng.randint(0, 1)]
        extra = body.get(topic, "")
        flavour = ""
        if mood in ("angry", "grumpy"):
            flavour = " (said with a scowl)"
        elif mood in ("happy", "cheerful"):
            flavour = " (said warmly)"
        text = f'{name}: "{line}'
        if extra:
            text += f" {extra}"
        text += f'"{flavour}'
        if voice and rng.chance(0.3):
            text += f"  [{voice}]"
        return text

    def _gen_narrator(self, ctx: dict, rng: Dice) -> str:
        loc = ctx.get("location", "the road")
        tod = ctx.get("time_of_day", "Day")
        season = ctx.get("season", "Spring")
        present = ctx.get("present", [])
        dark = tod in ("Dusk", "Night", "Midnight")
        if dark:
            weather = rng.choice(["Lanterns flicker against the dark.",
                                  "The air is cold and still.",
                                  "Moonlight silvers the rooftops.",
                                  "Shadows pool in the corners."])
        else:
            weather = rng.choice(["A cool wind stirs.", "The air is busy with the day.",
                                  "Clouds drift overhead.", "Pale sunlight filters down."])
        who = ""
        if present:
            who = " " + rng.choice([
                f"{present[0]} goes about their business nearby.",
                f"You notice {', '.join(present[:3])} here.",
            ])
        return (f"[{tod}, {season}] You stand in {loc}. {weather}{who}")

    def _gen_world_event(self, ctx: dict, rng: Dice) -> str:
        events = [
            {"headline": "A merchant caravan is ambushed on the King's Road.",
             "mood_shift": -3, "market": {"weapon": 1.1}},
            {"headline": "Word spreads of a bountiful catch on the coast.",
             "mood_shift": 3, "market": {"food": 0.9}},
            {"headline": "The Conclave issues a warning about the Frostpeaks.",
             "mood_shift": -4, "market": {}},
            {"headline": "A wandering bard lifts the town's spirits.",
             "mood_shift": 5, "market": {"luxury": 1.1}},
        ]
        return json.dumps(rng.choice(events), ensure_ascii=False)

    def _gen_referee(self, ctx: dict, rng: Dice) -> str:
        success = ctx.get("success", True)
        action = ctx.get("action", "the attempt")
        if success:
            return f"Success: {action} works as intended."
        return f"Failure: {action} does not go as hoped."

    def _gen_memory_summarizer(self, ctx: dict, rng: Dice) -> str:
        events = ctx.get("events", [])
        if not events:
            return "Nothing of note has happened recently."
        keep = events[-3:]
        return "Recently: " + "; ".join(keep) + "."

    def _gen_director(self, ctx: dict, rng: Dice) -> str:
        beats = ["advance_time", "npc_activity", "world_event", "rumor_spread"]
        weights = [3, 4, 1, 2]
        return rng.choices(beats, weights=weights)[0]


# --------------------------------------------------------------------------- #
#  Client                                                                      #
# --------------------------------------------------------------------------- #
class LLMClient:
    def __init__(self, assignments_path: str, force_provider: str | None = None) -> None:
        with open(assignments_path, "r", encoding="utf-8") as fh:
            self.config = json.load(fh)
        self.force_provider = force_provider
        self._providers: dict[str, BaseProvider] = {
            "mock": MockProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
        }
        self.stats: dict[str, dict] = {}

    def _route(self, role: str) -> dict:
        roles = self.config.get("roles", {})
        default = self.config.get("default", {"provider": "mock", "model": "mock-1",
                                              "temperature": 0.8, "max_tokens": 400})
        return {**default, **roles.get(role, {})}

    def _resolve_provider(self, want: str) -> tuple[str, BaseProvider]:
        if self.force_provider:
            want = self.force_provider
        provider = self._providers.get(want)
        if provider and provider.available():
            return want, provider
        return "mock", self._providers["mock"]

    @staticmethod
    def _approx_tokens(*texts: str) -> int:
        return sum(max(1, len(t) // 4) for t in texts)

    def complete(self, role: str, system: str, user: str,
                 context: dict | None = None) -> LLMResponse:
        route = self._route(role)
        want = route.get("provider", "mock")
        provider_name, provider = self._resolve_provider(want)
        fell_back = provider_name != (self.force_provider or want)
        ctx = dict(context or {})
        ctx.setdefault("role", role)
        model = route.get("model", "mock-1")
        try:
            text = provider.complete(
                system, user, model=model,
                temperature=float(route.get("temperature", 0.8)),
                max_tokens=int(route.get("max_tokens", 400)),
                context=ctx)
        except (urllib.error.URLError, Exception):  # noqa: BLE001 - robust fallback
            provider_name, provider = "mock", self._providers["mock"]
            fell_back = True
            text = provider.complete(system, user, model="mock-1",
                                     temperature=0.8, max_tokens=400, context=ctx)
            model = "mock-1"
        tokens = self._approx_tokens(system, user, text)
        self._record(role, provider_name, model, tokens)
        return LLMResponse(text=text.strip(), role=role, provider=provider_name,
                           model=model, approx_tokens=tokens, fell_back=fell_back)

    def _record(self, role: str, provider: str, model: str, tokens: int) -> None:
        key = f"{provider}:{model}"
        bucket = self.stats.setdefault(key, {"calls": 0, "approx_tokens": 0, "roles": {}})
        bucket["calls"] += 1
        bucket["approx_tokens"] += tokens
        bucket["roles"][role] = bucket["roles"].get(role, 0) + 1

    def summary(self) -> str:
        if not self.stats:
            return "No model calls yet."
        lines = ["Model usage:"]
        for key, b in sorted(self.stats.items()):
            roles = ", ".join(f"{r}×{n}" for r, n in b["roles"].items())
            lines.append(f"  {key}: {b['calls']} calls, ~{b['approx_tokens']} tokens ({roles})")
        return "\n".join(lines)
