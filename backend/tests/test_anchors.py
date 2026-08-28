from app.models.schemas import AnchorStatus, BlockchainAnchor
from app.services.anchors import transaction_url


def test_simulated_anchor_has_no_explorer_url() -> None:
    anchor = BlockchainAnchor(status=AnchorStatus.simulated, network="local", transaction_hash="0xabc")
    assert transaction_url(anchor) is None


def test_sepolia_anchor_uses_etherscan() -> None:
    anchor = BlockchainAnchor(
        status=AnchorStatus.anchored,
        network="sepolia",
        transaction_hash="0xdeadbeef",
    )
    assert transaction_url(anchor) == "https://sepolia.etherscan.io/tx/0xdeadbeef"
