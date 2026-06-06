from __future__ import annotations

import random
from typing import Dict, List

from .models import NPC, Player, Quest, WorldState


POSITIVE_TOKENS = {"thanks", "thank", "help", "honor", "trade", "peace", "heal", "quest"}
NEGATIVE_TOKENS = {"threat", "steal", "lie", "betray", "kill", "hate", "raid"}
QUEST_TOKENS = {"quest", "job", "task", "mission", "work"}
RUMOR_TOKENS = {"rumor", "news", "war", "market", "frontier", "secret"}


def _tone_from_personality(npc: NPC) -> str:
    honor = npc.personality.get("honor", 5)
    warmth = npc.personality.get("warmth", 5)
    greed = npc.personality.get("greed", 5)
    mystic = npc.personality.get("mystic", 5)
    if mystic >= 8:
        return "enigmatic"
    if honor >= 8 and warmth <= 5:
        return "stern"
    if warmth >= 8:
        return "welcoming"
    if greed >= 8:
        return "calculating"
    return "pragmatic"


def _relation_band(score: int) -> str:
    if score >= 35:
        return "trusted ally"
    if score >= 10:
        return "favored traveler"
    if score > -10:
        return "known wanderer"
    if score > -35:
        return "unwelcome outsider"
    return "sworn nuisance"


def _keyword_shift(message: str) -> int:
    lowered = message.lower()
    words = set(lowered.replace(",", " ").replace(".", " ").split())
    shift = 0
    if words & POSITIVE_TOKENS:
        shift += 4
    if words & NEGATIVE_TOKENS:
        shift -= 6
    return shift


def _quest_hint(available: List[Quest], world: WorldState) -> str:
    if not available:
        return "No contracts are open for you right now."
    first = available[0]
    region_name = world.regions[first.region_key].name
    return f"You should seek '{first.title}' in {region_name}."


def _rumor(world: WorldState, rng: random.Random) -> str:
    focus = rng.choice(list(world.regions.values()))
    faction = rng.choice(list(world.factions.values()))
    tension = sum(abs(value) for value in faction.relations.values()) // max(1, len(faction.relations))
    if tension > 40:
        return f"Rumor says {faction.name} is preparing hard moves near {focus.name}."
    return f"Merchants whisper that prices in {focus.name} will shift by next market bell."


def generate_reply(
    world: WorldState,
    player: Player,
    npc: NPC,
    message: str,
    available_quests: List[Quest],
    rng: random.Random,
) -> str:
    mood_shift = _keyword_shift(message)
    faction_rep = player.reputation.get(npc.faction_key, 0)
    npc.disposition = max(-60, min(60, npc.disposition + mood_shift + faction_rep // 8))
    tone = _tone_from_personality(npc)
    band = _relation_band(npc.disposition + faction_rep)

    lowered = message.lower()
    response_parts: List[str] = [
        f"{npc.name} ({npc.role}, {tone}):",
        f"To me, you are a {band}.",
    ]

    if any(token in lowered for token in QUEST_TOKENS):
        response_parts.append(_quest_hint(available_quests, world))
    elif any(token in lowered for token in RUMOR_TOKENS):
        response_parts.append(_rumor(world, rng))
    elif "faction" in lowered or "alliance" in lowered:
        allies = sorted(npc.dialogue_tags)[:2]
        response_parts.append(
            f"The {world.factions[npc.faction_key].name} values {', '.join(allies) if allies else 'results'}."
        )
    elif "heal" in lowered and player.health < player.max_health:
        restored = min(14, player.max_health - player.health)
        player.health += restored
        response_parts.append(f"I can patch your wounds. You recover {restored} health.")
    else:
        if npc.memory:
            response_parts.append(f"I remember: {npc.memory[-1]}")
        else:
            response_parts.append("Speak plainly and I may open more doors for you.")

    npc.remember(f"Day {world.day}: {player.name} said '{message[:64]}'")
    return " ".join(response_parts)
