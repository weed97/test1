"""Creation Registry — 창조물 등록 온체인 장부."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cpow_engine.chain.block import Transaction, TxType
from cpow_engine.models import CreativeObject


@dataclass
class RegistryEntry:
    """온체인 창조물 기록 — 소유권·탄생 증명."""

    object_id: str
    creator_id: str
    content_hash: str
    creativity_fingerprint: str
    complexity_score: float
    block_height: int
    energy_minted: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "creator_id": self.creator_id,
            "content_hash": self.content_hash,
            "creativity_fingerprint": self.creativity_fingerprint,
            "complexity_score": self.complexity_score,
            "block_height": self.block_height,
            "energy_minted": self.energy_minted,
            "metadata": dict(self.metadata),
        }


class CreationRegistry:
    """창조물 등록·조회·중복 검증."""

    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._fingerprints: dict[str, str] = {}

    @property
    def entries(self) -> dict[str, RegistryEntry]:
        return dict(self._entries)

    def register(
        self,
        obj: CreativeObject,
        block_height: int,
        *,
        complexity_score: float | None = None,
        content_hash: str | None = None,
    ) -> RegistryEntry:
        if obj.creativity_fingerprint in self._fingerprints:
            existing_id = self._fingerprints[obj.creativity_fingerprint]
            raise ValueError(
                f"Duplicate fingerprint {obj.creativity_fingerprint} "
                f"already registered as {existing_id}"
            )

        complexity = complexity_score if complexity_score is not None else (
            len(obj.properties) * 0.2 + len(obj.connections) * 0.1 + 1.0
        )

        entry = RegistryEntry(
            object_id=obj.id,
            creator_id=obj.creator_id,
            content_hash=content_hash or obj.creativity_fingerprint,
            creativity_fingerprint=obj.creativity_fingerprint,
            complexity_score=complexity,
            block_height=block_height,
        )
        self._entries[obj.id] = entry
        self._fingerprints[obj.creativity_fingerprint] = obj.id
        return entry

    def get(self, object_id: str) -> RegistryEntry | None:
        return self._entries.get(object_id)

    def is_fingerprint_known(self, fingerprint: str) -> bool:
        return fingerprint in self._fingerprints

    def build_register_tx(
        self, obj: CreativeObject, sender: str
    ) -> Transaction:
        return Transaction(
            tx_type=TxType.REGISTER_CREATION,
            sender=sender,
            payload={
                "object_id": obj.id,
                "creator_id": obj.creator_id,
                "content_hash": obj.creativity_fingerprint,
                "creativity_fingerprint": obj.creativity_fingerprint,
                "label": obj.label,
                "property_count": len(obj.properties),
            },
        )

    def apply_register_tx(
        self, tx: Transaction, block_height: int
    ) -> RegistryEntry:
        if tx.tx_type != TxType.REGISTER_CREATION:
            raise ValueError(f"Expected REGISTER_CREATION, got {tx.tx_type}")

        fp = str(tx.payload["creativity_fingerprint"])
        if self.is_fingerprint_known(fp):
            raise ValueError(f"Fingerprint {fp} already on-chain")

        entry = RegistryEntry(
            object_id=str(tx.payload["object_id"]),
            creator_id=str(tx.payload["creator_id"]),
            content_hash=str(tx.payload.get("content_hash", fp)),
            creativity_fingerprint=fp,
            complexity_score=float(tx.payload.get("property_count", 1)) * 0.2 + 1.0,
            block_height=block_height,
        )
        self._entries[entry.object_id] = entry
        self._fingerprints[fp] = entry.object_id
        return entry
