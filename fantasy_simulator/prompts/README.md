# Prompts

Each **role** in the orchestration has a focused system prompt here. The context builder
(`utils/context_builder.py`) appends the relevant rules, world state and character data
to these prompts at runtime, and `utils/llm_client.py` routes each role to a model via
`model_assignments.json`.

| Prompt | Role | Routed (default) |
|--------|------|------------------|
| `narrator.md` | scene description & world voice | strong model |
| `npc_roleplay.md` | role-play any character | strong (major) / fast (minor) |
| `world_event.md` | generate world events as JSON | fast model |
| `referee.md` | narrate dice-adjudicated outcomes | fast, low-temp model |
| `memory_summarizer.md` | compress character memory | fast, low-temp model |
| `director.md` | choose the next simulation beat | local/free |

**Editing prompts changes behaviour without touching code.** Keep them tight and
imperative; the models also receive the rule documents, so don't duplicate the rules
here — point to the constraints and define the *voice and format* of each role.
