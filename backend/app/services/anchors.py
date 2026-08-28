from __future__ import annotations

from app.models.schemas import AnchorStatus, BlockchainAnchor

SEPOLIA_TX = "https://sepolia.etherscan.io/tx/{hash}"


def transaction_url(anchor: BlockchainAnchor | None) -> str | None:
    """Public explorer URL for a real testnet transaction. Simulated hashes have none."""

    if anchor is None or not anchor.transaction_hash:
        return None
    if anchor.status != AnchorStatus.anchored:
        return None
    network = (anchor.network or "").lower()
    if "sepolia" in network:
        return SEPOLIA_TX.format(hash=anchor.transaction_hash)
    return None
