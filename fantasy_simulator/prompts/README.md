# Prompt files (primary)

| Prompt | Model | When | Output |
|--------|-------|------|--------|
| `narrator_claude.md` | Claude Opus 4.8 High | 서사·묘사·대사 | plain text |
| `mechanics_codex.md` | Codex 5.3 High | 전투·마법·규칙 행동 | JSON only |
| `world_arbiter.md` | Claude Opus 4.8 High | every 5 turns consistency | JSON |
| `quick_event_gpt.md` | GPT-5.5 High | lightweight branch events | JSON |

Turn orchestration: `simulation_engine.py`
