# Rules of Aldermere

These documents are the **canonical design** of the world. They are *injected into
prompts* by `utils/context_builder.py`, so the language models reason with consistent,
designer-authored systems. Editing a rule here changes how the simulation behaves —
no Python required.

| File | What it governs |
|------|-----------------|
| `world_lore.md` | Setting, history, geography, the central threat |
| `magic_system.md` | Schools of magic, mana, costs, limits |
| `combat_rules.md` | How fights are adjudicated (dice + outcomes) |
| `economy.md` | Currency, prices, the dynamic market |
| `social_system.md` | Disposition, mood, reputation, persuasion |
| `simulation_loop.md` | What happens each tick; the director's beats |

Keep each document tight. The context builder truncates long rules to protect the
model's context window, so put the most important constraints near the top.
