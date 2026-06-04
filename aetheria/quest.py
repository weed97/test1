"""Quests, objectives and the journal that tracks them.

Quests are data: a list of typed :class:`Objective` s plus a :class:`QuestReward`.
The :class:`QuestManager` reacts to gameplay events (a monster slain, an item
gathered, an NPC spoken to, a location reached) and advances any matching objective.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ObjectiveType(str, Enum):
    KILL = "kill"            # target = npc/monster template id
    COLLECT = "collect"      # target = item id
    TALK = "talk"            # target = npc id
    REACH = "reach"          # target = location id
    DELIVER = "deliver"      # target = item id (consumed on turn-in)


@dataclass
class Objective:
    type: ObjectiveType
    target: str
    count: int = 1
    description: str = ""

    def render(self, current: int) -> str:
        text = self.description or f"{self.type.value} {self.target}"
        return f"{text} ({min(current, self.count)}/{self.count})"


@dataclass
class QuestReward:
    xp: int = 0
    gold: int = 0
    items: tuple[tuple[str, int], ...] = ()        # (item_id, qty)
    reputation: tuple[tuple[str, int], ...] = ()   # (faction_id, delta)
    title: str = ""
    ability: str = ""


@dataclass
class Quest:
    id: str
    name: str
    giver_id: str
    summary: str
    objectives: tuple[Objective, ...]
    reward: QuestReward
    faction: str = ""
    prerequisites: tuple[str, ...] = ()
    turn_in_id: str = ""           # NPC to report back to (defaults to giver)
    on_offer: str = ""
    on_complete: str = ""
    repeatable: bool = False

    @property
    def report_to(self) -> str:
        return self.turn_in_id or self.giver_id


class QuestRegistry:
    def __init__(self) -> None:
        self._quests: dict[str, Quest] = {}

    def register(self, quest: Quest) -> Quest:
        self._quests[quest.id] = quest
        return quest

    def get(self, quest_id: str) -> Quest:
        return self._quests[quest_id]

    def exists(self, quest_id: str) -> bool:
        return quest_id in self._quests

    def all(self) -> list[Quest]:
        return list(self._quests.values())


class QuestManager:
    """Bridges quest definitions with the player's mutable progress."""

    def __init__(self, registry: QuestRegistry) -> None:
        self.registry = registry

    def can_start(self, player, quest_id: str) -> bool:
        if not self.registry.exists(quest_id):
            return False
        quest = self.registry.get(quest_id)
        if quest_id in player.active_quests:
            return False
        if quest_id in player.completed_quests and not quest.repeatable:
            return False
        return all(pre in player.completed_quests for pre in quest.prerequisites)

    def start(self, player, quest_id: str) -> list[str]:
        if not self.can_start(player, quest_id):
            return []
        quest = self.registry.get(quest_id)
        player.active_quests.append(quest_id)
        player.quest_progress[quest_id] = {str(i): 0 for i in range(len(quest.objectives))}
        msgs = [f"Quest accepted: {quest.name}"]
        if quest.on_offer:
            msgs.append(quest.on_offer)
        for obj in quest.objectives:
            msgs.append(f"  - {obj.render(0)}")
        player.journal.append(f"Began '{quest.name}'.")
        return msgs

    INVENTORY_OBJECTIVES = (ObjectiveType.COLLECT, ObjectiveType.DELIVER)

    def _progress(self, player, quest_id: str) -> dict:
        return player.quest_progress.setdefault(quest_id, {})

    def objective_current(self, player, quest, idx: int) -> int:
        """How far along an objective is, reading inventory for collect/deliver."""
        obj = quest.objectives[idx]
        if obj.type in self.INVENTORY_OBJECTIVES and player.inventory:
            return player.inventory.count(obj.target)
        return self._progress(player, quest.id).get(str(idx), 0)

    def record_event(self, player, event_type: ObjectiveType, target: str,
                     amount: int = 1) -> list[str]:
        messages: list[str] = []
        for quest_id in list(player.active_quests):
            quest = self.registry.get(quest_id)
            progress = self._progress(player, quest_id)
            for idx, obj in enumerate(quest.objectives):
                if obj.type is not event_type or obj.target != target:
                    continue
                if obj.type in self.INVENTORY_OBJECTIVES:
                    continue  # tracked via inventory, not events
                key = str(idx)
                current = progress.get(key, 0)
                if current >= obj.count:
                    continue
                progress[key] = min(obj.count, current + amount)
                messages.append(f"[{quest.name}] {obj.render(progress[key])}")
            if self.is_complete(player, quest_id):
                messages.append(f"Quest ready to turn in: {quest.name} "
                                f"(report to its giver).")
        return messages

    def is_complete(self, player, quest_id: str) -> bool:
        if quest_id not in player.active_quests:
            return False
        quest = self.registry.get(quest_id)
        return all(self.objective_current(player, quest, i) >= obj.count
                   for i, obj in enumerate(quest.objectives))

    def completable_for(self, player, npc_id: str) -> list[str]:
        ready = []
        for quest_id in player.active_quests:
            quest = self.registry.get(quest_id)
            if quest.report_to == npc_id and self.is_complete(player, quest_id):
                ready.append(quest_id)
        return ready

    def turn_in(self, player, quest_id: str, world=None) -> list[str]:
        if not self.is_complete(player, quest_id):
            return ["That quest is not yet complete."]
        quest = self.registry.get(quest_id)
        messages = [f"Quest complete: {quest.name}!"]
        if quest.on_complete:
            messages.append(quest.on_complete)
        # consume DELIVER items
        for obj in quest.objectives:
            if obj.type is ObjectiveType.DELIVER and player.inventory:
                player.inventory.remove(obj.target, obj.count)
        reward = quest.reward
        if reward.gold:
            player.gold += reward.gold
            messages.append(f"  Received {reward.gold} copper.")
        for item_id, qty in reward.items:
            if player.inventory:
                player.inventory.add(item_id, qty)
            messages.append(f"  Received {qty}x {item_id}.")
        if reward.xp:
            messages.extend(player.add_xp(reward.xp))
            messages.append(f"  Gained {reward.xp} XP.")
        if reward.ability:
            player.learn(reward.ability)
            messages.append(f"  Learned a new ability: {reward.ability}.")
        if reward.title:
            player.play_title = reward.title
            messages.append(f"  You are now known as the {reward.title}.")
        if world is not None:
            for faction_id, delta in reward.reputation:
                messages.extend(world.factions.apply_reputation(player, faction_id, delta))
        elif reward.reputation:
            for faction_id, delta in reward.reputation:
                player.adjust_reputation(faction_id, delta)

        player.active_quests.remove(quest_id)
        if quest_id not in player.completed_quests:
            player.completed_quests.append(quest_id)
        player.quest_progress.pop(quest_id, None)
        player.journal.append(f"Completed '{quest.name}'.")
        return messages

    def journal_lines(self, player) -> list[str]:
        lines = []
        for quest_id in player.active_quests:
            quest = self.registry.get(quest_id)
            status = "READY TO TURN IN" if self.is_complete(player, quest_id) else "in progress"
            lines.append(f"* {quest.name} [{status}]")
            lines.append(f"    {quest.summary}")
            for i, obj in enumerate(quest.objectives):
                lines.append(f"    - {obj.render(self.objective_current(player, quest, i))}")
        return lines or ["Your journal is empty."]
