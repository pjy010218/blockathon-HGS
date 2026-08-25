from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import AnchorStatus, BlockchainAnchor
from app.services.hashing import sha256_hex


class BlockchainService:
    """Blockchain adapter boundary.

    The default mode is explicitly simulated so local development never presents a
    fake transaction as an Ethereum transaction. Replace this adapter with a Web3
    provider when deploying the contract.
    """

    def __init__(self, mode: str = "simulated", network: str = "local") -> None:
        self.mode = mode
        self.network = network

    def anchor(self, content_hash: str) -> BlockchainAnchor:
        now = datetime.now(timezone.utc)
        if self.mode != "ethereum":
            return BlockchainAnchor(
                status=AnchorStatus.simulated,
                network=self.network,
                transaction_hash=f"0x{sha256_hex({'simulated': content_hash, 'at': now.isoformat()})}",
                anchored_at=now,
            )

        raise RuntimeError(
            "Ethereum anchoring is not configured. Set up a Web3 provider and contract adapter first."
        )
