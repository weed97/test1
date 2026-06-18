"""Block structure — L1 진실(Truth) 레이어."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _hash_payload(data: Any) -> str:
    return hashlib.sha256(_canonical_json(data).encode()).hexdigest()


class TxType(Enum):
    REGISTER_CREATION = "register_creation"
    MINT_ENERGY = "mint_energy"
    SUBMIT_ROLLUP = "submit_rollup"
    PHYSICS_AMENDMENT = "physics_amendment"
    TRANSFER = "transfer"


@dataclass
class Transaction:
    """온체인 트랜잭션 — 창조 등록·에너지 발행·롤업 제출."""

    tx_type: TxType
    sender: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tx_type": self.tx_type.value,
            "sender": self.sender,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
            "signature": self.signature,
        }

    def tx_hash(self) -> str:
        return _hash_payload(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transaction:
        return cls(
            tx_type=TxType(data["tx_type"]),
            sender=str(data["sender"]),
            payload=dict(data.get("payload", {})),
            timestamp=float(data.get("timestamp", time.time())),
            signature=str(data.get("signature", "")),
        )


@dataclass
class BlockHeader:
    version: int
    height: int
    timestamp: float
    prev_hash: str
    merkle_root: str
    validator_id: str
    cpow_weight: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "height": self.height,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "validator_id": self.validator_id,
            "cpow_weight": self.cpow_weight,
        }


@dataclass
class Block:
    header: BlockHeader
    transactions: list[Transaction] = field(default_factory=list)
    hash: str = ""

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = self.compute_hash()

    @staticmethod
    def merkle_root(transactions: list[Transaction]) -> str:
        if not transactions:
            return _hash_payload("empty")
        return Block.merkle_root_from_hashes([tx.tx_hash() for tx in transactions])

    @staticmethod
    def merkle_root_from_hashes(hashes: list[str]) -> str:
        if not hashes:
            return _hash_payload("empty")
        nodes = list(hashes)
        while len(nodes) > 1:
            if len(nodes) % 2 == 1:
                nodes.append(nodes[-1])
            nodes = [
                _hash_payload(nodes[i] + nodes[i + 1])
                for i in range(0, len(nodes), 2)
            ]
        return nodes[0]

    def compute_hash(self) -> str:
        payload = {
            "header": self.header.to_dict(),
            "merkle_root": self.merkle_root(self.transactions),
            "tx_count": len(self.transactions),
        }
        return _hash_payload(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Block:
        header_data = data["header"]
        header = BlockHeader(
            version=int(header_data["version"]),
            height=int(header_data["height"]),
            timestamp=float(header_data["timestamp"]),
            prev_hash=str(header_data["prev_hash"]),
            merkle_root=str(header_data["merkle_root"]),
            validator_id=str(header_data["validator_id"]),
            cpow_weight=float(header_data.get("cpow_weight", 0.0)),
        )
        txs = [Transaction.from_dict(tx) for tx in data.get("transactions", [])]
        return cls(
            header=header,
            transactions=txs,
            hash=str(data.get("hash", "")),
        )

    @classmethod
    def create(
        cls,
        height: int,
        prev_hash: str,
        transactions: list[Transaction],
        validator_id: str,
        *,
        cpow_weight: float = 0.0,
    ) -> Block:
        merkle = cls.merkle_root(transactions)
        header = BlockHeader(
            version=1,
            height=height,
            timestamp=time.time(),
            prev_hash=prev_hash,
            merkle_root=merkle,
            validator_id=validator_id,
            cpow_weight=cpow_weight,
        )
        return cls(header=header, transactions=transactions)
