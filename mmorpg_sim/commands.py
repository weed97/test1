from __future__ import annotations

from .engine import SimulatorEngine


HELP_TEXT = """
Commands:
  help
  status
  map
  look
  where
  travel <region_key>
  talk <npc_key_or_name> | <message>
  hunt
  rest
  inventory
  quests
  quest accept <quest_key>
  quest complete <quest_key>
  buy <item_key> [amount]
  sell <item_key> [amount]
  consume <item_key>
  logs [count]
  simulate <days>
  exit / quit
""".strip()


class CommandProcessor:
    def __init__(self, engine: SimulatorEngine) -> None:
        self.engine = engine

    def handle(self, raw: str) -> str:
        line = raw.strip()
        if not line:
            return "Type 'help' to see available commands."
        lower = line.lower()

        if lower in {"help", "h"}:
            return HELP_TEXT
        if lower in {"status", "stat"}:
            return self.engine.status()
        if lower == "map":
            return self.engine.world_map()
        if lower in {"look", "inspect"}:
            return self.engine.look()
        if lower == "where":
            return f"You are in {self.engine.current_region.name} ({self.engine.current_region.key})."
        if lower == "hunt":
            return self.engine.hunt()
        if lower == "rest":
            return self.engine.rest()
        if lower in {"inventory", "inv"}:
            return self.engine.inventory()
        if lower in {"quests", "quest list"}:
            return self.engine.list_quests()

        parts = line.split()
        cmd = parts[0].lower()

        if cmd == "travel":
            if len(parts) < 2:
                return "Usage: travel <region_key>"
            return self.engine.travel(parts[1])

        if cmd == "talk":
            if "|" not in line:
                return "Usage: talk <npc_key_or_name> | <message>"
            left, right = line.split("|", 1)
            left_parts = left.strip().split(maxsplit=1)
            if len(left_parts) < 2:
                return "Usage: talk <npc_key_or_name> | <message>"
            npc_ref = left_parts[1].strip()
            message = right.strip()
            if not message:
                return "Your message cannot be empty."
            return self.engine.talk(npc_ref, message)

        if cmd == "quest":
            if len(parts) < 3:
                return "Usage: quest <accept|complete> <quest_key>"
            action = parts[1].lower()
            quest_key = parts[2].lower()
            if action == "accept":
                return self.engine.accept_quest(quest_key)
            if action == "complete":
                return self.engine.complete_quest(quest_key)
            return "Unknown quest action. Use accept or complete."

        if cmd == "buy":
            if len(parts) < 2:
                return "Usage: buy <item_key> [amount]"
            amount = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            return self.engine.buy(parts[1], amount)

        if cmd == "sell":
            if len(parts) < 2:
                return "Usage: sell <item_key> [amount]"
            amount = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            return self.engine.sell(parts[1], amount)

        if cmd == "consume":
            if len(parts) < 2:
                return "Usage: consume <item_key>"
            return self.engine.consume(parts[1])

        if cmd == "logs":
            amount = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 8
            return self.engine.logs(amount)

        if cmd == "simulate":
            if len(parts) < 2 or not parts[1].isdigit():
                return "Usage: simulate <days>"
            return self.engine.mega_simulate(int(parts[1]))

        if lower in {"quit", "exit"}:
            return "__EXIT__"
        return "Unknown command. Type 'help' to inspect available actions."
