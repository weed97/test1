"""Off-chain ↔ On-chain bridge — 엔진 결과를 L1에 제출."""

from __future__ import annotations

from dataclasses import dataclass, field

from cpow_engine.chain.block import Block, Transaction, TxType
from cpow_engine.chain.consensus import CPoWConsensus
from cpow_engine.chain.genesis import GenesisBlock, load_genesis
from cpow_engine.chain.registry import CreationRegistry
from cpow_engine.chain.rollup import RollupBatch, RollupSubmitter
from cpow_engine.chain.validator import ValidatorNode
from cpow_engine.cpow import CPoWScore
from cpow_engine.engine import SimulationEngine
from cpow_engine.models import ActionRecord, CreativeObject, WorldDelta


@dataclass
class SubmissionResult:
    success: bool
    block_height: int
    tx_hashes: list[str] = field(default_factory=list)
    energy_minted: float = 0.0
    reason: str = ""


class OffChainBridge:
    """오프체인 시뮬레이션 엔진 → L1 제출 브릿지."""

    def __init__(
        self,
        engine: SimulationEngine,
        genesis: GenesisBlock | None = None,
    ) -> None:
        self.engine = engine
        self.genesis = genesis or load_genesis()
        self.registry = CreationRegistry()
        self.consensus = CPoWConsensus(self.genesis)
        self.consensus.initialize()
        self.validator = ValidatorNode(
            "validator_genesis_0",
            self.genesis,
            self.registry,
        )
        batch_size = int(self.genesis.rollup_params.get("batch_size_ticks", 10))
        self.rollup = RollupSubmitter(batch_size=batch_size)
        self._energy_ledger: dict[str, float] = {}

    def submit_creation(self, obj: CreativeObject) -> SubmissionResult:
        tx = self.registry.build_register_tx(obj, obj.creator_id)
        validation = self.validator.validate_register_tx(tx)
        if not validation.valid:
            return SubmissionResult(False, self.consensus.height, reason=validation.reason)

        block_height = self.consensus.height + 1
        try:
            self.registry.apply_register_tx(tx, block_height)
        except ValueError as exc:
            return SubmissionResult(False, self.consensus.height, reason=str(exc))

        block = Block.create(
            height=block_height,
            prev_hash=self.consensus.tip_hash,
            transactions=[tx],
            validator_id=self.validator.validator_id,
        )
        result = self.consensus.propose_block(block)
        if not result.accepted:
            return SubmissionResult(
                False, self.consensus.height, reason=result.reason
            )

        return SubmissionResult(
            True,
            block_height,
            tx_hashes=[tx.tx_hash()],
            reason="creation registered on-chain",
        )

    def submit_energy_mint(
        self,
        action: ActionRecord,
        delta: WorldDelta,
        score: CPoWScore,
    ) -> SubmissionResult:
        mint_tx = Transaction(
            tx_type=TxType.MINT_ENERGY,
            sender=action.actor_id,
            payload={
                "energy": score.energy,
                "creativity_score": score.creativity_score,
                "bot_risk": score.bot_risk,
                "tick": delta.tick,
            },
        )

        validation = self.validator.validate_mint_tx(
            mint_tx, score, self.engine.state, delta, action
        )
        if not validation.valid:
            return SubmissionResult(False, self.consensus.height, reason=validation.reason)

        block_height = self.consensus.height + 1
        block = Block.create(
            height=block_height,
            prev_hash=self.consensus.tip_hash,
            transactions=[mint_tx],
            validator_id=self.validator.validator_id,
            cpow_weight=score.creativity_score,
        )
        result = self.consensus.propose_block(block)
        if not result.accepted:
            return SubmissionResult(False, self.consensus.height, reason=result.reason)

        self._energy_ledger[action.actor_id] = (
            self._energy_ledger.get(action.actor_id, 0.0) + score.energy
        )

        return SubmissionResult(
            True,
            block_height,
            tx_hashes=[mint_tx.tx_hash()],
            energy_minted=score.energy,
            reason="energy minted on-chain",
        )

    def tick_and_maybe_submit(self) -> tuple[WorldDelta, CPoWScore | None, SubmissionResult | None]:
        """오프체인 틱 실행 + 롤업 배치 준비."""
        delta, score = self.engine.tick()

        submission: SubmissionResult | None = None
        if score and self.engine.state.action_log:
            action = self.engine.state.action_log[-1]
            submission = self.submit_energy_mint(action, delta, score)

        batch = self.rollup.add_tick(delta, score)
        if batch:
            submission = self.submit_rollup(batch)

        return delta, score, submission

    def submit_rollup(self, batch: RollupBatch) -> SubmissionResult:
        leaf_hashes = [p.leaf_hash for p in batch.proofs]
        validation = self.validator.validate_rollup_batch(
            batch.merkle_root, leaf_hashes, batch.total_energy
        )
        if not validation.valid:
            return SubmissionResult(False, self.consensus.height, reason=validation.reason)

        tx = batch.build_submit_tx()
        block_height = self.consensus.height + 1
        block = Block.create(
            height=block_height,
            prev_hash=self.consensus.tip_hash,
            transactions=[tx],
            validator_id=self.validator.validator_id,
            cpow_weight=batch.total_energy * 0.01,
        )
        result = self.consensus.propose_block(block)
        if not result.accepted:
            return SubmissionResult(False, self.consensus.height, reason=result.reason)

        return SubmissionResult(
            True,
            block_height,
            tx_hashes=[tx.tx_hash()],
            energy_minted=batch.total_energy,
            reason=f"rollup batch {batch.batch_id} submitted",
        )

    def get_energy_balance(self, creator_id: str) -> float:
        return self._energy_ledger.get(creator_id, 0.0)

    @property
    def chain_height(self) -> int:
        return self.consensus.height
