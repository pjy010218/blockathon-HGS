from __future__ import annotations

import pytest

from app.models.schemas import AnchorStatus
from app.services.blockchain import BlockchainService
from app.services.hashing import record_hash_to_bytes32


VALID_HASH = "a" * 64


def test_record_hash_to_bytes32_rejects_wrong_width() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        record_hash_to_bytes32("aa")


def test_record_hash_to_bytes32_round_trips_sha256() -> None:
    assert record_hash_to_bytes32(VALID_HASH) == bytes.fromhex(VALID_HASH)


def test_record_hash_to_bytes32_accepts_0x_prefix() -> None:
    assert record_hash_to_bytes32("0x" + VALID_HASH) == bytes.fromhex(VALID_HASH)


def test_simulated_anchor_is_never_labeled_anchored() -> None:
    result = BlockchainService(mode="simulated", network="local").anchor(
        VALID_HASH, source="community", source_record_id="row-1"
    )
    assert result.status == AnchorStatus.simulated
    assert result.transaction_hash is not None
    assert result.transaction_hash.startswith("0x")
    assert result.contract_address is None


def test_ethereum_mode_without_config_raises() -> None:
    service = BlockchainService(
        mode="ethereum",
        network="sepolia",
        rpc_url=None,
        private_key=None,
        contract_address=None,
    )
    with pytest.raises(RuntimeError, match="not configured"):
        service.anchor(VALID_HASH, source="community", source_record_id="row-1")


def test_ethereum_mode_refuses_mainnet() -> None:
    class _Eth:
        chain_id = 1

    class _Web3:
        eth = _Eth()

        def is_connected(self) -> bool:
            return True

    service = BlockchainService(
        mode="ethereum",
        network="mainnet",
        rpc_url="https://example.invalid",
        private_key="0x" + "11" * 32,
        contract_address="0x" + "22" * 20,
        web3=_Web3(),
        account=_Account(),
        contract=_Contract([], "0x" + "22" * 20),
    )
    with pytest.raises(RuntimeError, match="mainnet"):
        service.anchor(VALID_HASH, source="community", source_record_id="row-1")


class _Call:
    def __init__(self, recorder: list, name: str) -> None:
        self._recorder = recorder
        self._name = name

    def transact(self, params: dict) -> bytes:
        self._recorder.append((self._name, params))
        return b"\xab" * 32


class _Functions:
    def __init__(self, recorder: list) -> None:
        self._recorder = recorder

    def anchorRecord(self, record_hash: bytes, source: str, source_record_id: str) -> _Call:
        self._recorder.append(("args", record_hash, source, source_record_id))
        return _Call(self._recorder, "anchorRecord")

    def anchorRecordFor(
        self,
        record_hash: bytes,
        source: str,
        source_record_id: str,
        contributor: str,
    ) -> _Call:
        self._recorder.append(("args", record_hash, source, source_record_id, contributor))
        return _Call(self._recorder, "anchorRecordFor")


class _Contract:
    def __init__(self, recorder: list, address: str) -> None:
        self.functions = _Functions(recorder)
        self.address = address


class _Account:
    address = "0x74D96FF3dc16AeE3d5342DE17E084f9DBA4B77D5"


class _Eth:
    chain_id = 11155111

    def wait_for_transaction_receipt(self, transaction_hash: bytes) -> dict:
        return {
            "transactionHash": transaction_hash,
            "blockNumber": 19_000_001,
            "status": 1,
        }


class _Web3:
    eth = _Eth()

    def is_connected(self) -> bool:
        return True

    def to_checksum_address(self, value: str) -> str:
        return value


def test_ethereum_anchor_calls_anchor_record(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder: list = []
    address = "0x0028fdb7dE6AC54FEE1658a93a5E9cE0d3B948B0"
    service = BlockchainService(
        mode="ethereum",
        network="sepolia",
        rpc_url="https://example.invalid",
        private_key="0x" + "11" * 32,
        contract_address=address,
        web3=_Web3(),
        account=_Account(),
        contract=_Contract(recorder, address),
    )

    result = service.anchor(VALID_HASH, source="enmods", source_record_id="row-42")

    assert result.status == AnchorStatus.anchored
    assert result.network == "sepolia"
    assert result.contract_address == address
    assert result.block_number == 19_000_001
    assert "anchorRecord" in {item[0] for item in recorder if isinstance(item, tuple)}
    args = next(item for item in recorder if item[0] == "args")
    assert args[1] == bytes.fromhex(VALID_HASH)
    assert args[2] == "enmods"
    assert args[3] == "row-42"


def test_ethereum_anchor_for_contributor_uses_relayer_entry() -> None:
    recorder: list = []
    address = "0x0028fdb7dE6AC54FEE1658a93a5E9cE0d3B948B0"
    contributor = "0x1111111111111111111111111111111111111111"
    service = BlockchainService(
        mode="ethereum",
        network="sepolia",
        rpc_url="https://example.invalid",
        private_key="0x" + "11" * 32,
        contract_address=address,
        web3=_Web3(),
        account=_Account(),
        contract=_Contract(recorder, address),
    )

    service.anchor(
        VALID_HASH,
        source="community",
        source_record_id="obs-1",
        attributed_to=contributor,
    )

    assert any(item[0] == "anchorRecordFor" for item in recorder if isinstance(item, tuple))
