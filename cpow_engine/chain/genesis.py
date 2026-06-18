"""Genesis block — 프로토콜의 유전자(Genesis)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _hash_payload(data: Any) -> str:
    return hashlib.sha256(_canonical_json(data).encode()).hexdigest()


@dataclass
class PhysicsLaw:
    """불변 열역학 법칙 — Genesis에 기록되는 프로토콜 표준."""

    id: str
    name: str
    formula: str
    expression: str
    constants: dict[str, float] = field(default_factory=dict)
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "formula": self.formula,
            "expression": self.expression,
            "constants": dict(self.constants),
            "immutable": self.immutable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PhysicsLaw:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            formula=str(data["formula"]),
            expression=str(data["expression"]),
            constants={k: float(v) for k, v in data.get("constants", {}).items()},
            immutable=bool(data.get("immutable", True)),
        )


@dataclass
class GenesisValidator:
    id: str
    trust_score: float
    role: str
    pubkey: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trust_score": self.trust_score,
            "role": self.role,
            "pubkey": self.pubkey,
        }


@dataclass
class GenesisCreator:
    id: str
    trust_score: float
    role: str
    initial_energy_grant: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trust_score": self.trust_score,
            "role": self.role,
            "initial_energy_grant": self.initial_energy_grant,
        }


@dataclass
class TokenParams:
    symbol: str
    name: str
    decimals: int
    emission_model: str
    base_emission_rate: float
    min_creativity_score: float
    bot_rejection_threshold: float
    max_supply: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "decimals": self.decimals,
            "emission_model": self.emission_model,
            "base_emission_rate": self.base_emission_rate,
            "min_creativity_score": self.min_creativity_score,
            "bot_rejection_threshold": self.bot_rejection_threshold,
            "max_supply": self.max_supply,
        }


@dataclass
class GenesisBlock:
    """L1 첫 번째 블록 — 열역학 법칙 + 초기 신뢰 점수가 유전자가 됨."""

    chain_id: str
    timestamp: int
    protocol_version: str
    genesis_message: str
    physics_laws: list[PhysicsLaw]
    validators: list[GenesisValidator]
    creators: list[GenesisCreator]
    token_params: TokenParams
    rollup_params: dict[str, Any]
    consensus_params: dict[str, Any]
    hash: str = ""

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        payload = {
            "chain_id": self.chain_id,
            "timestamp": self.timestamp,
            "protocol_version": self.protocol_version,
            "genesis_message": self.genesis_message,
            "protocol_physics": {
                "laws": [law.to_dict() for law in self.physics_laws],
            },
            "genesis_validators": [v.to_dict() for v in self.validators],
            "genesis_creators": [c.to_dict() for c in self.creators],
            "token_params": self.token_params.to_dict(),
            "rollup_params": self.rollup_params,
            "consensus_params": self.consensus_params,
        }
        return _hash_payload(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "timestamp": self.timestamp,
            "protocol_version": self.protocol_version,
            "genesis_message": self.genesis_message,
            "hash": self.hash,
            "protocol_physics": {
                "description": "불변 열역학 법칙",
                "laws": [law.to_dict() for law in self.physics_laws],
            },
            "genesis_validators": [v.to_dict() for v in self.validators],
            "genesis_creators": [c.to_dict() for c in self.creators],
            "token_params": self.token_params.to_dict(),
            "rollup_params": self.rollup_params,
            "consensus_params": self.consensus_params,
        }

    def get_law_by_formula(self, formula: str) -> PhysicsLaw | None:
        for law in self.physics_laws:
            if law.formula == formula:
                return law
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenesisBlock:
        physics = data.get("protocol_physics", {})
        token = data.get("token_params", {})
        return cls(
            chain_id=str(data["chain_id"]),
            timestamp=int(data.get("timestamp", 0)),
            protocol_version=str(data.get("protocol_version", "0.1.0")),
            genesis_message=str(data.get("genesis_message", "")),
            physics_laws=[
                PhysicsLaw.from_dict(law) for law in physics.get("laws", [])
            ],
            validators=[
                GenesisValidator(**v) for v in data.get("genesis_validators", [])
            ],
            creators=[
                GenesisCreator(**c) for c in data.get("genesis_creators", [])
            ],
            token_params=TokenParams(
                symbol=str(token.get("symbol", "NRG")),
                name=str(token.get("name", "Creativity Energy")),
                decimals=int(token.get("decimals", 6)),
                emission_model=str(token.get("emission_model", "cpow_weighted")),
                base_emission_rate=float(token.get("base_emission_rate", 1.0)),
                min_creativity_score=float(token.get("min_creativity_score", 0.3)),
                bot_rejection_threshold=float(
                    token.get("bot_rejection_threshold", 0.7)
                ),
                max_supply=token.get("max_supply"),
            ),
            rollup_params=dict(data.get("rollup_params", {})),
            consensus_params=dict(data.get("consensus_params", {})),
            hash=str(data.get("hash", "")),
        )


def load_genesis(path: Path | None = None) -> GenesisBlock:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config" / "genesis.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return GenesisBlock.from_dict(data)
