# fantasy_simulator — LLM-orchestrated world simulator (optimised architecture)

This is the **optimised** layout for Aetheria: a large-scale, text, NPC-conversational
medieval-fantasy MMORPG simulator built around language models as role-players and a
deterministic engine as the referee.

```
fantasy_simulator/
├── world_state.json        # the LIVE world — single source of truth (resumable)
├── rules/                  # design documents (magic, combat, economy, social, lore, loop)
├── characters/             # one JSON per character (sheet + memory + voice)
├── prompts/                # role-based system prompts + multi-model routing
├── simulation_engine.py    # the orchestrator main loop
└── utils/                  # llm_client, state_io, context_builder, memory, dice, logger, engine_bridge
```

## Why this shape (the optimisation)

1. **`world_state.json` is canonical.** Every subsystem reads/writes it; the world is
   always inspectable and resumable, even after thousands of ticks.
2. **`rules/` are documents, not code.** They are injected into prompts, so models reason
   with consistent, designer-authored systems — edit a rule, change the behaviour.
3. **`prompts/` separate role from engine.** Narrator, NPC actor, world-event director,
   referee, memory summariser and pacing director each have a focused system prompt.
4. **Multi-model routing** (`prompts/model_assignments.json`) sends each role to the model
   that suits it best — *"각 모델의 장점을 최대한 활용"*. A strong model voices the
   narrator and major NPCs; a fast/cheap model handles ambient crowds, events and
   summaries. With no API keys, a deterministic **Mock** provider runs everything so the
   simulation never stalls.
5. **Bounded context.** `utils/context_builder.py` injects only the *relevant* slice of
   rules + state + character + memory, and `utils/memory.py` summarises old memories — so
   prompts stay small as the world grows huge.
6. **Deterministic mechanics.** `utils/dice.py` (reusing the Aetheria RNG) adjudicates all
   chance, so a seed reproduces a run and narration never overturns the dice.

## Run it

```bash
# (Re)generate the world from the Aetheria content engine
python -m fantasy_simulator.simulation_engine --reset --seed aldermere

# Let the world run itself for N in-world hours (autonomous, offline by default)
python -m fantasy_simulator.simulation_engine --simulate 48

# Play interactively
python -m fantasy_simulator.simulation_engine --play

# Force a provider (mock / openai / anthropic)
python -m fantasy_simulator.simulation_engine --simulate 24 --provider mock
```

### Enabling real models (multi-model)

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
# edit prompts/model_assignments.json to choose models per role
python -m fantasy_simulator.simulation_engine --play
```

The client uses the official `openai` / `anthropic` SDKs if installed, otherwise plain
HTTPS. Any unavailable role transparently falls back to the Mock provider.

## The orchestration roles

| Role | Prompt | Default model tier | Job |
|------|--------|--------------------|-----|
| narrator | `narrator.md` | strong | describe scenes |
| npc_major / npc_minor | `npc_roleplay.md` | strong / fast | role-play characters |
| world_event | `world_event.md` | fast | emit events as JSON |
| referee | `referee.md` | fast, low-temp | narrate dice outcomes |
| memory_summarizer | `memory_summarizer.md` | fast, low-temp | compress memory |
| director | `director.md` | local/free | choose each tick's beat |

## The tick loop (see `rules/simulation_loop.md`)

advance time → move NPCs on schedule → drift moods → **director** picks a beat
(`advance_time` / `npc_activity` / `world_event` / `rumor_spread`) → spread rumours →
resolve skirmishes → memory upkeep → persist.

## Data flow

```
content engine ──(engine_bridge)──► world_state.json + characters/*.json
                                            │
              rules/ + prompts/  ──►  context_builder ──► llm_client (routed) ──► text
                                            │                                   │
                                          dice (referee) ◄───────────────────────┘
                                            │
                                            ▼
                                   updated world_state.json + characters/
```

## Logs

Each run writes `logs/transcript.log` (readable story) and `logs/events.jsonl`
(structured events) — handy for analysing a long simulation. The `logs/` folder is
git-ignored; `world_state.json` and `characters/` are committed as seed data.
