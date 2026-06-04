"""Character & world memory with LLM-assisted summarisation.

Long simulations would otherwise accumulate unbounded memory.  Each character keeps a
short rolling list of recent events; when it grows past a threshold the manager asks the
*memory_summarizer* role to compress it into a durable summary, keeping prompts small
even after thousands of ticks.
"""

from __future__ import annotations


class MemoryManager:
    def __init__(self, store, llm, context_builder, logger=None,
                 recent_threshold: int = 8, keep_recent: int = 3,
                 world_event_cap: int = 30) -> None:
        self.store = store
        self.llm = llm
        self.ctx = context_builder
        self.logger = logger
        self.recent_threshold = recent_threshold
        self.keep_recent = keep_recent
        self.world_event_cap = world_event_cap

    def remember(self, char: dict, text: str, *, summarize: bool = True) -> None:
        mem = char.setdefault("memory", {"summary": "", "recent": []})
        mem.setdefault("recent", []).append(text)
        if summarize and len(mem["recent"]) > self.recent_threshold:
            self.summarize(char)

    def summarize(self, char: dict) -> None:
        system, user, ctx = self.ctx.build_memory_summary(char)
        resp = self.llm.complete("memory_summarizer", system, user, ctx)
        mem = char["memory"]
        mem["summary"] = resp.text
        mem["recent"] = mem["recent"][-self.keep_recent:]
        if self.logger:
            self.logger.event("memory_summary", character=char["id"], summary=resp.text)

    def record_world_event(self, world: dict, headline: str) -> None:
        events = world.setdefault("recent_events", [])
        events.append(headline)
        if len(events) > self.world_event_cap:
            del events[: len(events) - self.world_event_cap]

    def add_rumor(self, world: dict, rumor: str, cap: int = 24) -> None:
        pool = world.setdefault("rumor_pool", [])
        if rumor and rumor not in pool:
            pool.append(rumor)
            if len(pool) > cap:
                pool.pop(0)
