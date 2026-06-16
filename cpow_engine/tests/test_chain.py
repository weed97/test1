"""L1 chain protocol tests."""

import unittest

from cpow_engine.chain.block import Block, Transaction, TxType
from cpow_engine.chain.bridge import OffChainBridge
from cpow_engine.chain.consensus import CPoWConsensus
from cpow_engine.chain.genesis import GenesisBlock, load_genesis
from cpow_engine.chain.registry import CreationRegistry
from cpow_engine.chain.rollup import RollupProof, RollupSubmitter
from cpow_engine.chain.validator import ValidatorNode
from cpow_engine.cpow import CPoWScore
from cpow_engine.engine import SimulationEngine
from cpow_engine.models import ActionRecord, WorldDelta
from cpow_engine.physics import create_heat_object, create_material_object


class TestGenesis(unittest.TestCase):
    def test_load_genesis_has_physics_laws(self) -> None:
        genesis = load_genesis()
        self.assertEqual(genesis.chain_id, "cpow-mainnet-1")
        self.assertGreaterEqual(len(genesis.physics_laws), 3)
        self.assertTrue(genesis.hash)

    def test_genesis_hash_is_deterministic(self) -> None:
        g1 = load_genesis()
        g2 = load_genesis()
        self.assertEqual(g1.hash, g2.hash)

    def test_genesis_contains_validators_and_creators(self) -> None:
        genesis = load_genesis()
        self.assertGreater(len(genesis.validators), 0)
        self.assertGreater(len(genesis.creators), 0)
        self.assertEqual(genesis.token_params.symbol, "NRG")

    def test_physics_law_lookup(self) -> None:
        genesis = load_genesis()
        law = genesis.get_law_by_formula("heat_transfer")
        self.assertIsNotNone(law)
        assert law is not None
        self.assertTrue(law.immutable)


class TestBlock(unittest.TestCase):
    def test_merkle_root_deterministic(self) -> None:
        txs = [
            Transaction(TxType.REGISTER_CREATION, "u1", {"id": "a"}),
            Transaction(TxType.MINT_ENERGY, "u1", {"energy": 10}),
        ]
        r1 = Block.merkle_root(txs)
        r2 = Block.merkle_root(txs)
        self.assertEqual(r1, r2)

    def test_block_chain_linking(self) -> None:
        tx = Transaction(TxType.REGISTER_CREATION, "u1", {"id": "obj1"})
        b1 = Block.create(1, "0" * 64, [tx], "val1")
        b2 = Block.create(2, b1.hash, [], "val1")
        self.assertEqual(b2.header.prev_hash, b1.hash)


class TestRegistry(unittest.TestCase):
    def test_register_and_reject_duplicate(self) -> None:
        registry = CreationRegistry()
        obj = create_heat_object("u1", "열원", 50.0)
        registry.register(obj, block_height=1)

        dup = create_heat_object("u2", "복제", 50.0)
        dup.creativity_fingerprint = obj.creativity_fingerprint
        with self.assertRaises(ValueError):
            registry.register(dup, block_height=2)

    def test_apply_register_tx(self) -> None:
        registry = CreationRegistry()
        obj = create_heat_object("u1", "열원", 50.0)
        tx = registry.build_register_tx(obj, "u1")
        entry = registry.apply_register_tx(tx, block_height=1)
        self.assertEqual(entry.creator_id, "u1")


class TestConsensus(unittest.TestCase):
    def test_initialize_and_propose(self) -> None:
        genesis = load_genesis()
        consensus = CPoWConsensus(genesis)
        consensus.initialize()
        self.assertEqual(consensus.height, 1)

        tx = Transaction(TxType.REGISTER_CREATION, "u1", {"id": "x"})
        block = Block.create(1, consensus.tip_hash, [tx], "validator_genesis_0")
        result = consensus.propose_block(block)
        self.assertTrue(result.accepted)
        self.assertEqual(consensus.height, 2)

    def test_reject_invalid_prev_hash(self) -> None:
        genesis = load_genesis()
        consensus = CPoWConsensus(genesis)
        consensus.initialize()
        block = Block.create(1, "bad_hash", [], "validator_genesis_0")
        result = consensus.propose_block(block)
        self.assertFalse(result.accepted)


class TestValidator(unittest.TestCase):
    def test_reject_bot_mint(self) -> None:
        genesis = load_genesis()
        validator = ValidatorNode("v1", genesis, CreationRegistry())
        score = CPoWScore(
            energy=100, economic_value=200, creativity_score=0.5,
            entropy_bonus=0, repetition_penalty=1, bot_risk=0.9,
        )
        tx = Transaction(TxType.MINT_ENERGY, "bot", {"energy": 100})
        result = validator.validate_mint_tx(
            tx, score, SimulationEngine().state,
            WorldDelta(tick=1), ActionRecord("bot", "farm"),
        )
        self.assertFalse(result.valid)

    def test_validate_genesis_formula(self) -> None:
        genesis = load_genesis()
        validator = ValidatorNode("v1", genesis, CreationRegistry())
        result = validator.validate_physics_formula("energy_emission")
        self.assertTrue(result.valid)

        bad = validator.validate_physics_formula("magic_missile")
        self.assertFalse(bad.valid)


class TestRollup(unittest.TestCase):
    def test_batch_flush(self) -> None:
        submitter = RollupSubmitter(batch_size=3)
        batch = None
        for i in range(3):
            batch = submitter.add_tick(WorldDelta(tick=i), None)
        assert batch is not None
        self.assertEqual(len(batch.proofs), 3)
        self.assertTrue(batch.merkle_root)

    def test_merkle_proof_verification(self) -> None:
        genesis = load_genesis()
        validator = ValidatorNode("v1", genesis, CreationRegistry())
        proofs = [
            RollupProof(tick=1, energy_delta=10, interaction_count=2, score=None),
            RollupProof(tick=2, energy_delta=20, interaction_count=1, score=None),
        ]
        root = Block.merkle_root_from_hashes([p.leaf_hash for p in proofs])
        result = validator.validate_rollup_batch(root, [p.leaf_hash for p in proofs], 30)
        self.assertTrue(result.valid)


class TestBridge(unittest.TestCase):
    def test_full_onchain_flow(self) -> None:
        engine = SimulationEngine()
        bridge = OffChainBridge(engine)

        heat = create_heat_object("creator_1", "열원", 100.0)
        metal = create_material_object("creator_1", "철", "iron")

        reg = bridge.submit_creation(heat)
        self.assertTrue(reg.success, reg.reason)

        reg2 = bridge.submit_creation(metal)
        self.assertTrue(reg2.success, reg2.reason)

        engine.create_object(heat)
        engine.create_object(metal)
        engine.connect_objects(heat.id, metal.id)

        delta, score, submission = bridge.tick_and_maybe_submit()
        self.assertIsNotNone(score)
        if submission:
            self.assertTrue(submission.success, submission.reason)

        self.assertGreater(bridge.chain_height, 1)

    def test_genesis_block_is_chain_root(self) -> None:
        bridge = OffChainBridge(SimulationEngine())
        self.assertEqual(bridge.consensus.chain[0].hash, bridge.genesis.hash)


if __name__ == "__main__":
    unittest.main()
