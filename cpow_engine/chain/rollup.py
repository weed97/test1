"""Rollup — 오프체인 연산 배치 제출로 가스비 최적화."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from cpow_engine.chain.block import Block, Transaction, TxType
from cpow_engine.cpow import CPoWScore
from cpow_engine.models import WorldDelta


def _hash_leaf(data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class RollupProof:
    """단일 틱의 오프체인 증명."""

    tick: int
    energy_delta: float
    interaction_count: int
    score: CPoWScore | None
    leaf_hash: str = ""

    def __post_init__(self) -> None:
        if not self.leaf_hash:
            self.leaf_hash = _hash_leaf({
                "tick": self.tick,
                "energy_delta": self.energy_delta,
                "interaction_count": self.interaction_count,
                "score_energy": self.score.energy if self.score else 0.0,
            })

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "energy_delta": self.energy_delta,
            "interaction_count": self.interaction_count,
            "score": self.score.to_dict() if self.score else None,
            "leaf_hash": self.leaf_hash,
        }


@dataclass
class RollupBatch:
    """오프체인 틱들을 배치로 묶어 L1에 제출."""

    batch_id: str
    submitter: str
    proofs: list[RollupProof] = field(default_factory=list)
    merkle_root: str = ""
    total_energy: float = 0.0
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.proofs and not self.merkle_root:
            self.merkle_root = self._compute_merkle()
            self.total_energy = sum(p.energy_delta for p in self.proofs)

    def _compute_merkle(self) -> str:
        return Block.merkle_root_from_hashes([p.leaf_hash for p in self.proofs])

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "submitter": self.submitter,
            "proofs": [p.to_dict() for p in self.proofs],
            "merkle_root": self.merkle_root,
            "total_energy": self.total_energy,
            "created_at": self.created_at,
        }

    def build_submit_tx(self) -> Transaction:
        return Transaction(
            tx_type=TxType.SUBMIT_ROLLUP,
            sender=self.submitter,
            payload={
                "batch_id": self.batch_id,
                "merkle_root": self.merkle_root,
                "total_energy": self.total_energy,
                "proof_count": len(self.proofs),
                "leaf_hashes": [p.leaf_hash for p in self.proofs],
            },
        )


class RollupSubmitter:
    """오프체인 엔진 틱 → 롤업 배치 변환."""

    def __init__(self, batch_size: int = 10) -> None:
        self.batch_size = batch_size
        self._buffer: list[RollupProof] = []
        self._batch_counter = 0

    def add_tick(
        self,
        delta: WorldDelta,
        score: CPoWScore | None,
    ) -> RollupBatch | None:
        energy = sum(abs(i.energy_delta) for i in delta.interactions)
        proof = RollupProof(
            tick=delta.tick,
            energy_delta=energy,
            interaction_count=len(delta.interactions),
            score=score,
        )
        self._buffer.append(proof)

        if len(self._buffer) >= self.batch_size:
            return self.flush()
        return None

    def flush(self, submitter: str = "engine") -> RollupBatch | None:
        if not self._buffer:
            return None
        self._batch_counter += 1
        batch = RollupBatch(
            batch_id=f"batch_{self._batch_counter}",
            submitter=submitter,
            proofs=list(self._buffer),
        )
        self._buffer.clear()
        return batch
