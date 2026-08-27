from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from app.models.schemas import AnchorStatus, BlockchainAnchor
from app.services.hashing import record_hash_to_bytes32, sha256_hex

_UNSET = object()
MAINNET_CHAIN_ID = 1

# Must match WaterAuditRegistry.sol: one tuple output, not flattened fields.
# See contracts/test_water_audit_registry.py::test_get_anchor_returns_a_single_struct
REGISTRY_ABI: list[dict[str, Any]] = [
    {
        "inputs": [
            {"name": "recordHash", "type": "bytes32"},
            {"name": "source", "type": "string"},
            {"name": "sourceRecordId", "type": "string"},
        ],
        "name": "anchorRecord",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "recordHash", "type": "bytes32"},
            {"name": "source", "type": "string"},
            {"name": "sourceRecordId", "type": "string"},
            {"name": "contributor", "type": "address"},
        ],
        "name": "anchorRecordFor",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class BlockchainService:
    """Blockchain adapter boundary.

    Default mode is simulated so local development never presents a fake
    transaction as an Ethereum transaction. Set BLOCKCHAIN_MODE=ethereum with
    ETH_RPC_URL, ETH_PRIVATE_KEY, and ETH_CONTRACT_ADDRESS to call the live
    WaterAuditRegistry. Mainnet is refused.
    """

    def __init__(
        self,
        mode: str = "simulated",
        network: str = "local",
        *,
        rpc_url: Any = _UNSET,
        private_key: Any = _UNSET,
        contract_address: Any = _UNSET,
        web3: Any = None,
        account: Any = None,
        contract: Any = None,
    ) -> None:
        self.mode = mode
        self.network = network
        self.rpc_url = os.getenv("ETH_RPC_URL") if rpc_url is _UNSET else rpc_url
        self.private_key = os.getenv("ETH_PRIVATE_KEY") if private_key is _UNSET else private_key
        self.contract_address = (
            os.getenv("ETH_CONTRACT_ADDRESS") if contract_address is _UNSET else contract_address
        )
        self._web3 = web3
        self._account = account
        self._contract = contract

    def anchor(
        self,
        content_hash: str,
        *,
        source: str,
        source_record_id: str,
        attributed_to: str | None = None,
    ) -> BlockchainAnchor:
        now = datetime.now(timezone.utc)
        if self.mode != "ethereum":
            return BlockchainAnchor(
                status=AnchorStatus.simulated,
                network=self.network,
                transaction_hash=f"0x{sha256_hex({'simulated': content_hash, 'at': now.isoformat()})}",
                anchored_at=now,
            )

        web3, account, contract = self._ethereum_client()
        if web3.eth.chain_id == MAINNET_CHAIN_ID:
            raise RuntimeError("Refusing to anchor on Ethereum mainnet. This project is testnet only.")

        digest = record_hash_to_bytes32(content_hash)
        if attributed_to:
            contributor = web3.to_checksum_address(attributed_to)
            call = contract.functions.anchorRecordFor(
                digest, source, source_record_id, contributor
            )
        else:
            call = contract.functions.anchorRecord(digest, source, source_record_id)

        receipt = self._send(web3, account, call)
        if receipt.get("status") == 0:
            raise RuntimeError("The anchor transaction reverted.")

        transaction_hash = receipt["transactionHash"]
        if isinstance(transaction_hash, bytes):
            transaction_hex = "0x" + transaction_hash.hex()
        else:
            transaction_hex = str(transaction_hash)

        return BlockchainAnchor(
            status=AnchorStatus.anchored,
            network=self.network,
            contract_address=contract.address,
            transaction_hash=transaction_hex,
            block_number=receipt.get("blockNumber"),
            anchored_at=now,
        )

    def _ethereum_client(self) -> tuple[Any, Any, Any]:
        if self._web3 is not None and self._account is not None and self._contract is not None:
            return self._web3, self._account, self._contract

        if not self.rpc_url or not self.private_key or not self.contract_address:
            raise RuntimeError(
                "Ethereum anchoring is not configured. Set ETH_RPC_URL, ETH_PRIVATE_KEY, "
                "and ETH_CONTRACT_ADDRESS, or keep BLOCKCHAIN_MODE=simulated."
            )

        try:
            from web3 import Web3
        except ImportError as error:
            raise RuntimeError("web3 is required for BLOCKCHAIN_MODE=ethereum.") from error

        web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not web3.is_connected():
            raise RuntimeError("Could not reach the RPC endpoint. Check ETH_RPC_URL.")

        account = web3.eth.account.from_key(self.private_key)
        contract = web3.eth.contract(
            address=web3.to_checksum_address(self.contract_address),
            abi=REGISTRY_ABI,
        )
        return web3, account, contract

    def _send(self, web3: Any, account: Any, call: Any) -> dict[str, Any]:
        if hasattr(call, "build_transaction") and self._contract is None:
            transaction = call.build_transaction(
                {
                    "from": account.address,
                    "nonce": web3.eth.get_transaction_count(account.address),
                    "chainId": web3.eth.chain_id,
                }
            )
            signed = account.sign_transaction(transaction)
            raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
            transaction_hash = web3.eth.send_raw_transaction(raw)
            return web3.eth.wait_for_transaction_receipt(transaction_hash)

        transaction_hash = call.transact({"from": account.address})
        return web3.eth.wait_for_transaction_receipt(transaction_hash)
