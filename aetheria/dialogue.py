"""The conversational NPC engine — the beating heart of the MMORPG.

Conversations are *generated* from each NPC's living state rather than being a fixed
script.  An NPC's reply is shaped by:

* their **disposition** toward the player (hostile … devoted),
* their current **mood** (angry, content, cheerful, drunk …),
* their five-axis **personality** (warmth, bravery, honesty, greed, curiosity),
* their **memories** of past interactions,
* the **time of day** and the **place** they are standing in,
* the player's **reputation** with the NPC's faction.

The engine exposes the *topics* a player may raise and resolves each one into spoken
lines plus side effects (relationship/mood shifts, rumours learned, quests offered,
charisma-based persuasion checks, gifts, and so on).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .character import NPC, Player, Disposition, Mood
from .gametime import GameClock
from .rng import GameRandom
from .stats import Attribute


# --------------------------------------------------------------------------- #
#  Flavour banks                                                              #
# --------------------------------------------------------------------------- #

GREETINGS: dict[Disposition, list[str]] = {
    Disposition.HOSTILE: [
        "Get out of my sight before I make you.",
        "You've a lot of nerve showing your face here.",
        "I've nothing to say to the likes of you.",
    ],
    Disposition.WARY: [
        "What do you want? Be quick about it.",
        "I'm watching you, stranger.",
        "State your business and move along.",
    ],
    Disposition.NEUTRAL: [
        "Well met, traveller.",
        "Hm? Oh, hello there.",
        "Greetings. New around here, aren't you?",
    ],
    Disposition.FRIENDLY: [
        "Ah, good to see a friendly face!",
        "Well met again, friend.",
        "Come, come — you're always welcome here.",
    ],
    Disposition.DEVOTED: [
        "My friend! The day brightens at your arrival.",
        "You honour me with your visit, truly.",
        "Whatever you need, you need only ask.",
    ],
}

MOOD_COLOUR: dict[Mood, str] = {
    Mood.ANGRY: "snaps, knuckles white",
    Mood.GRUMPY: "grumbles, barely looking up",
    Mood.CONTENT: "says evenly",
    Mood.HAPPY: "says with a smile",
    Mood.CHEERFUL: "beams brightly",
    Mood.FEARFUL: "says, eyes darting",
    Mood.SORROWFUL: "says, voice heavy",
    Mood.DRUNK: "slurs, swaying a little",
    Mood.TIRED: "says with a weary sigh",
}

TIME_FLAVOUR = {
    "Dawn": "The first grey light creeps in.",
    "Morning": "The day's work has begun in earnest.",
    "Noon": "The sun stands high overhead.",
    "Afternoon": "The afternoon wears on.",
    "Dusk": "Long shadows stretch across the ground.",
    "Night": "Lanterns flicker against the dark.",
    "Midnight": "The world is hushed and sleeping.",
}


@dataclass
class Topic:
    key: str
    label: str


@dataclass
class DialogueResult:
    lines: list[str] = field(default_factory=list)
    relationship_delta: int = 0
    mood_delta: int = 0
    learned_rumor: str | None = None
    offered_quest: str | None = None
    opened_trade: bool = False
    started_combat: bool = False
    ended: bool = False


class DialogueEngine:
    def __init__(self, rng: GameRandom) -> None:
        self.rng = rng

    # -- presentation helpers ------------------------------------------------
    def _voice(self, npc: NPC, text: str) -> str:
        colour = MOOD_COLOUR.get(npc.mood, "says")
        return f'{npc.name} {colour}: "{text}"'

    def greeting(self, npc: NPC, player: Player, clock: GameClock) -> str:
        if npc.greeting and npc.disposition not in (Disposition.HOSTILE,):
            base = npc.greeting
        else:
            base = self.rng.choice(GREETINGS[npc.disposition])
        return self._voice(npc, base)

    # -- topic listing -------------------------------------------------------
    def available_topics(self, npc: NPC, player: Player) -> list[Topic]:
        topics = [
            Topic("about", f"Ask {npc.name} about themselves"),
            Topic("rumors", "Ask if they've heard any news"),
            Topic("area", "Ask about this place"),
        ]
        undelivered = [q for q in npc.quests_offered if q not in player.completed_quests]
        if undelivered:
            topics.append(Topic("quest", "Ask about work or tasks"))
        if npc.is_merchant and npc.disposition is not Disposition.HOSTILE:
            topics.append(Topic("trade", "Browse their wares"))
        topics.append(Topic("compliment", "Offer a kind word"))
        topics.append(Topic("persuade", "Try to win them over"))
        topics.append(Topic("intimidate", "Threaten them"))
        topics.append(Topic("gift", "Give them a gift"))
        if npc.disposition is Disposition.HOSTILE or npc.hostile_by_default:
            topics.append(Topic("provoke", "Draw your weapon"))
        topics.append(Topic("farewell", "Take your leave"))
        return topics

    # -- topic resolution ----------------------------------------------------
    def handle(self, npc: NPC, player: Player, clock: GameClock, topic_key: str,
               *, world=None, gift_item: str | None = None) -> DialogueResult:
        handler = getattr(self, f"_topic_{topic_key}", None)
        if handler is None:
            return DialogueResult(lines=[self._voice(npc, "I don't follow you.")])
        result = handler(npc, player, clock, world=world, gift_item=gift_item)
        # apply side effects on the NPC
        if result.relationship_delta:
            npc.adjust_relationship(result.relationship_delta)
        if result.mood_delta:
            npc.adjust_mood(result.mood_delta)
        return result

    # ---- individual topics -------------------------------------------------
    def _topic_about(self, npc: NPC, player: Player, clock: GameClock, **_) -> DialogueResult:
        p = npc.personality
        bits: list[str] = []
        role_line = {
            "blacksmith": "I work the forge here. Steel doesn't shape itself.",
            "innkeeper": "I keep the hearth warm and the ale flowing.",
            "guard": "I keep the peace, such as it is.",
            "merchant": "I trade in whatever folk will pay for.",
            "healer": "I tend the sick and the wounded as best I can.",
            "farmer": "I work the land from dawn to dusk.",
            "scholar": "I study the old lore — there's always more to learn.",
            "priest": "I tend to souls, and to the temple.",
            "hunter": "I track game in the wilds beyond the walls.",
            "noble": "My family has held these lands for generations.",
            "bandit": "I take what I need. That's all you need know.",
            "mage": "I bend the arcane to my will — carefully.",
        }.get(npc.role, "I get by, same as anyone.")
        bits.append(role_line)
        if p.warmth > 70:
            bits.append("Always glad of company, I am.")
        elif p.warmth < 30:
            bits.append("I keep to myself, mostly.")
        if p.curiosity > 70:
            bits.append("And what of you? You've the look of someone with stories.")
        delta = 1 if npc.disposition is not Disposition.HOSTILE else 0
        return DialogueResult(lines=[self._voice(npc, " ".join(bits))],
                              relationship_delta=delta)

    def _topic_rumors(self, npc: NPC, player: Player, clock: GameClock, *, world=None, **_) -> DialogueResult:
        if npc.disposition is Disposition.HOSTILE:
            return DialogueResult(lines=[self._voice(npc, "I'd not tell you if the sky were falling.")])
        pool = list(npc.known_rumors)
        if world is not None:
            pool += world.rumor_pool
        if not pool:
            return DialogueResult(lines=[self._voice(npc, "Can't say I've heard anything worth repeating.")])
        rumor = self.rng.choice(pool)
        intro = self.rng.choice([
            "Well, now that you mention it...",
            "Keep this between us, but...",
            "Folk are saying...",
            "If you must know...",
        ])
        return DialogueResult(
            lines=[self._voice(npc, f"{intro} {rumor}")],
            learned_rumor=rumor,
            relationship_delta=1,
        )

    def _topic_area(self, npc: NPC, player: Player, clock: GameClock, *, world=None, **_) -> DialogueResult:
        lines = []
        if world is not None and npc.current_location in world.map.locations:
            loc = world.map.get_location(npc.current_location)
            region = world.map.get_region(loc.region_id)
            lines.append(self._voice(npc, f"This is {loc.name}, in {region.name}."))
            if region.controlling_faction:
                fac = world.factions.get(region.controlling_faction)
                fname = fac.name if fac else region.controlling_faction
                lines.append(self._voice(npc, f"These lands answer to {fname}."))
            if region.lore:
                lines.append(self._voice(npc, region.lore))
        else:
            lines.append(self._voice(npc, "Just a quiet corner of the realm."))
        lines.append(f"({TIME_FLAVOUR.get(clock.time_of_day.value, '')})")
        return DialogueResult(lines=lines)

    def _topic_quest(self, npc: NPC, player: Player, clock: GameClock, *, world=None, **_) -> DialogueResult:
        undelivered = [q for q in npc.quests_offered
                       if q not in player.completed_quests and q not in player.active_quests]
        if not undelivered:
            if any(q in player.active_quests for q in npc.quests_offered):
                return DialogueResult(lines=[self._voice(npc, "You've already taken up my task. Off you go.")])
            return DialogueResult(lines=[self._voice(npc, "I've nothing for you at the moment.")])
        quest_id = undelivered[0]
        intro = "I do have something, if you're capable."
        if npc.disposition is Disposition.FRIENDLY or npc.disposition is Disposition.DEVOTED:
            intro = "As it happens, I could use someone I trust."
        return DialogueResult(
            lines=[self._voice(npc, intro)],
            offered_quest=quest_id,
        )

    def _topic_trade(self, npc: NPC, player: Player, clock: GameClock, **_) -> DialogueResult:
        if not npc.is_merchant:
            return DialogueResult(lines=[self._voice(npc, "I'm no merchant.")])
        return DialogueResult(
            lines=[self._voice(npc, "Take a look. Coin talks, browsing walks.")],
            opened_trade=True,
        )

    def _topic_compliment(self, npc: NPC, player: Player, clock: GameClock, **_) -> DialogueResult:
        cha = player.attrs.modifier(Attribute.CHARISMA)
        warmth_bonus = (npc.personality.warmth - 50) // 25
        if npc.mood in (Mood.ANGRY, Mood.GRUMPY) and cha + warmth_bonus < 1:
            return DialogueResult(
                lines=[self._voice(npc, "Flattery won't work on me.")],
                relationship_delta=-1,
            )
        return DialogueResult(
            lines=[self._voice(npc, self.rng.choice([
                "Heh. Kind of you to say.",
                "Well, aren't you pleasant.",
                "You've a silver tongue, traveller.",
            ]))],
            relationship_delta=2 + max(0, cha),
            mood_delta=3,
        )

    def _topic_persuade(self, npc: NPC, player: Player, clock: GameClock, **_) -> DialogueResult:
        cha = player.attrs.modifier(Attribute.CHARISMA)
        dc = 10 + max(0, -npc.relationship // 10) - (npc.personality.warmth - 50) // 20
        roll = self.rng.dice(1, 20) + cha
        if roll >= dc:
            return DialogueResult(
                lines=[f"(Persuasion check: {roll} vs {dc} — success)",
                       self._voice(npc, "...Aye, alright. You make a fair point.")],
                relationship_delta=8,
                mood_delta=2,
            )
        return DialogueResult(
            lines=[f"(Persuasion check: {roll} vs {dc} — failure)",
                   self._voice(npc, "Save your breath. I'm not convinced.")],
            relationship_delta=-3,
        )

    def _topic_intimidate(self, npc: NPC, player: Player, clock: GameClock, **_) -> DialogueResult:
        strn = player.attrs.modifier(Attribute.STRENGTH)
        cha = player.attrs.modifier(Attribute.CHARISMA)
        dc = 10 + (npc.personality.bravery - 50) // 10
        roll = self.rng.dice(1, 20) + max(strn, cha)
        if roll >= dc:
            return DialogueResult(
                lines=[f"(Intimidation check: {roll} vs {dc} — success)",
                       self._voice(npc, "A-alright! No need for that. I'll cooperate.")],
                relationship_delta=-4,
                mood_delta=-10,
            )
        return DialogueResult(
            lines=[f"(Intimidation check: {roll} vs {dc} — failure)",
                   self._voice(npc, "Threaten me? You'll regret that.")],
            relationship_delta=-15,
            mood_delta=-15,
        )

    def _topic_gift(self, npc: NPC, player: Player, clock: GameClock, *, gift_item=None, **_) -> DialogueResult:
        if not gift_item or not player.inventory or not player.inventory.has(gift_item):
            return DialogueResult(lines=[self._voice(npc, "You offer me... nothing?")])
        template = player.inventory.registry.get(gift_item)
        player.inventory.remove(gift_item, 1)
        value = template.value
        greed_factor = npc.personality.greed / 50.0
        delta = max(1, int((value / 8) * greed_factor) + 2)
        delta = min(delta, 25)
        return DialogueResult(
            lines=[self._voice(npc, self.rng.choice([
                f"For me? {template.name}... you have my thanks!",
                f"A fine {template.name}. You're too generous.",
                f"Well now, {template.name}! I'll not forget this.",
            ]))],
            relationship_delta=delta,
            mood_delta=5,
        )

    def _topic_provoke(self, npc: NPC, player: Player, clock: GameClock, **_) -> DialogueResult:
        return DialogueResult(
            lines=[self._voice(npc, "So that's how it is. Have at you!")],
            started_combat=True,
            ended=True,
        )

    def _topic_farewell(self, npc: NPC, player: Player, clock: GameClock, **_) -> DialogueResult:
        farewells = {
            Disposition.HOSTILE: "Good riddance.",
            Disposition.WARY: "Mind how you go.",
            Disposition.NEUTRAL: "Safe travels, then.",
            Disposition.FRIENDLY: "Come back any time, friend.",
            Disposition.DEVOTED: "Until we meet again, my friend. Walk in the light.",
        }
        return DialogueResult(
            lines=[self._voice(npc, farewells[npc.disposition])],
            ended=True,
        )
