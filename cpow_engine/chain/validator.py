"""Validator node — 가짜 창조물·봇 탈취 방지."""

from __future__ import annotations

from dataclasses import dataclass, field

from cpow_engine.chain.block import Transaction, TxType
from cpow_engine.chain.genesis import GenesisBlock
from cpow_engine.chain.registry import CreationRegistry
from cpow_engine.cpow import CPoWEngine, CPoWScore
from cpow_engine.models import ActionRecord, SimulationState, WorldDelta


@dataclass
class ValidationResult:
    valid: bool
    reason: str
    energy_approved: float = 0.0
    warnings: list[str] = field(default_factory=list)


class ValidatorNode:
    """검증자 노드 — 유니크함·CPoW 점수·Genesis 법칙 준수 검증."""

    def __init__(
        self,
        validator_id: str,
        genesis: GenesisBlock,
        registry: CreationRegistry,
    ) -> None:
        self.validator_id = validator_id
        self.genesis = genesis
        self.registry = registry
        self.cpow = CPoWEngine(
            bot_threshold=genesis.token_params.bot_rejection_threshold,
        )
        self._trust_scores: dict[str, float] = {
            c.id: c.trust_score for c in genesis.creators
        }

    def validate_register_tx(self, tx: Transaction) -> ValidationResult:
        if tx.tx_type != TxType.REGISTER_CREATION:
            return ValidationResult(False, "wrong tx type")

        fp = str(tx.payload.get("creativity_fingerprint", ""))
        if not fp:
            return ValidationResult(False, "missing fingerprint")

        if self.registry.is_fingerprint_known(fp):
            return ValidationResult(False, f"duplicate fingerprint: {fp}")

        prop_count = int(tx.payload.get("property_count", 0))
        if prop_count < 1:
            return ValidationResult(False, "creation must have at least 1 property")

        return ValidationResult(True, "valid creation")

    def validate_mint_tx(
        self,
        tx: Transaction,
        claimed_score: CPoWScore,
        state: SimulationState,
        delta: WorldDelta,
        action: ActionRecord,
    ) -> ValidationResult:
        if tx.tx_type != TxType.MINT_ENERGY:
            return ValidationResult(False, "wrong tx type")

        if claimed_score.bot_risk >= self.genesis.token_params.bot_rejection_threshold:
            return ValidationResult(
                False,
                f"bot risk {claimed_score.bot_risk:.2f} exceeds threshold",
            )

        if claimed_score.creativity_score < self.genesis.token_params.min_creativity_score:
            return ValidationResult(
                False,
                f"creativity {claimed_score.creativity_score:.2f} below minimum",
            )

        recomputed = self.cpow.score_action(action, delta, state)
        tolerance = 0.15
        energy_diff = abs(recomputed.energy - claimed_score.energy)
        if energy_diff > claimed_score.energy * tolerance + 1.0:
            return ValidationResult(
                False,
                f"energy mismatch: claimed={claimed_score.energy:.2f} "
                f"recomputed={recomputed.energy:.2f}",
            )

        return ValidationResult(
            True,
            "valid mint",
            energy_approved=claimed_score.energy,
        )

    def validate_physics_formula(self, formula: str) -> ValidationResult:
        """오프체인 연산이 Genesis 법칙에 등록된 formula인지 확인."""
        law = self.genesis.get_law_by_formula(formula)
        if law is None:
            return ValidationResult(False, f"formula '{formula}' not in genesis laws")
        return ValidationResult(True, f"formula '{formula}' verified against genesis")

    def validate_rollup_batch(
        self,
        merkle_root: str,
        leaf_hashes: list[str],
        total_energy: float,
    ) -> ValidationResult:
        from cpow_engine.chain.block import Block

        computed_root = Block.merkle_root_from_hashes(leaf_hashes)
        if computed_root != merkle_root:
            return ValidationResult(False, "merkle root mismatch")

        if total_energy < 0:
            return ValidationResult(False, "negative energy in batch")

        return ValidationResult(
            True,
            "valid rollup batch",
            energy_approved=total_energy,
        )

    def get_creator_trust(self, creator_id: str) -> float:
        return self._trust_scores.get(creator_id, 0.5)
