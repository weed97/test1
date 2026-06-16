"""CPoW-weighted consensus — 창조 가치 기반 합의."""

from __future__ import annotations

from dataclasses import dataclass, field

from cpow_engine.chain.block import Block
from cpow_engine.chain.genesis import GenesisBlock


@dataclass
class ValidatorVote:
    validator_id: str
    block_hash: str
    trust_score: float
    cpow_weight: float
    approved: bool


@dataclass
class ConsensusResult:
    accepted: bool
    block: Block
    votes: list[ValidatorVote]
    total_weight: float
    approval_ratio: float
    reason: str = ""


class CPoWConsensus:
    """Tendermint-style 합의 + CPoW 가중치 하이브리드 (레퍼런스 구현)."""

    def __init__(self, genesis: GenesisBlock) -> None:
        self.genesis = genesis
        self._validators: dict[str, float] = {
            v.id: v.trust_score for v in genesis.validators
        }
        self._chain: list[Block] = []
        self._pending_votes: dict[str, list[ValidatorVote]] = {}

    @property
    def chain(self) -> list[Block]:
        return list(self._chain)

    @property
    def height(self) -> int:
        return len(self._chain)

    @property
    def tip_hash(self) -> str:
        if not self._chain:
            return self.genesis.hash
        return self._chain[-1].hash

    def initialize(self) -> None:
        genesis_block = Block.create(
            height=0,
            prev_hash="0" * 64,
            transactions=[],
            validator_id="genesis",
            cpow_weight=0.0,
        )
        genesis_block.hash = self.genesis.hash
        self._chain = [genesis_block]

    def add_validator(self, validator_id: str, trust_score: float) -> None:
        self._validators[validator_id] = trust_score

    def propose_block(self, block: Block) -> ConsensusResult:
        if block.header.prev_hash != self.tip_hash:
            return ConsensusResult(
                accepted=False,
                block=block,
                votes=[],
                total_weight=0.0,
                approval_ratio=0.0,
                reason="prev_hash mismatch",
            )

        votes = self._collect_votes(block)
        total_weight = sum(
            v.trust_score * (1.0 + v.cpow_weight * 0.5)
            for v in votes
            if v.approved
        )
        max_weight = sum(
            self._validators.get(vid, 0.0) for vid in self._validators
        )
        ratio = total_weight / max_weight if max_weight > 0 else 0.0

        threshold = float(
            self.genesis.consensus_params.get("validator_threshold", 0.67)
        )
        accepted = ratio >= threshold

        if accepted:
            self._chain.append(block)

        return ConsensusResult(
            accepted=accepted,
            block=block,
            votes=votes,
            total_weight=total_weight,
            approval_ratio=ratio,
            reason="accepted" if accepted else f"approval {ratio:.2f} < {threshold}",
        )

    def _collect_votes(self, block: Block) -> list[ValidatorVote]:
        votes: list[ValidatorVote] = []
        for vid, trust in self._validators.items():
            cpow_w = block.header.cpow_weight if vid == block.header.validator_id else 0.0
            votes.append(
                ValidatorVote(
                    validator_id=vid,
                    block_hash=block.hash,
                    trust_score=trust,
                    cpow_weight=cpow_w,
                    approved=True,
                )
            )
        return votes

    def verify_chain_integrity(self) -> bool:
        if not self._chain:
            return False
        for i in range(1, len(self._chain)):
            if self._chain[i].header.prev_hash != self._chain[i - 1].hash:
                return False
        return True
