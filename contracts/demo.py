"""Prove the audit trail end to end, using nothing but the contracts.

Runs on an in-process EVM by default, so it needs no RPC endpoint, key, or
faucet — the contract side can be demonstrated even if the backend and frontend
are not ready. Set ETH_RPC_URL, ETH_PRIVATE_KEY and ETH_CONTRACT_ADDRESS to run
the same script against a deployed testnet contract instead.

    PYTHONPATH=. .venv/bin/python demo.py

The sample records use a placeholder shape. Whatever shape the team freezes must
be used consistently, because a digest computed under different rules will not
match.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from web3 import EthereumTesterProvider, Web3

from build import compile_registry, content_hash, record_hash_to_bytes32

COMMUNITY_SAMPLE = {
    "station_id": "OlympicVillage",
    "source": "community",
    "source_record_id": "swimdrinkfish-2019-06-05-1700",
    "medium": "marine",
    "observed_at": "2019-06-05T17:00:00-07:00",
    "readings": [
        {"parameter": "pH", "value": 8.01, "unit": "pH"},
        {"parameter": "dissolved_oxygen", "value": 9.37, "unit": "mg/L"},
        {"parameter": "e_coli", "value": 13.66, "unit": "CFU/100mL"},
    ],
}

AUTHORITY_SAMPLE = {
    "station_id": "E207969",
    "source": "authority",
    "source_record_id": "EMS-E207969-2026-08-26-001",
    "medium": "waste",
    "observed_at": "2026-08-26T09:15:00-07:00",
    "readings": [
        {"parameter": "pH", "value": 6.4, "unit": "pH"},
        {"parameter": "e_coli", "value": 240.0, "unit": "CFU/100mL"},
    ],
}

NEVER_SUBMITTED_SAMPLE = {
    "station_id": "E207969",
    "source": "authority",
    "source_record_id": "EMS-E207969-2026-08-27-001",
    "medium": "waste",
    "observed_at": "2026-08-27T09:15:00-07:00",
    "readings": [{"parameter": "e_coli", "value": 900.0, "unit": "CFU/100mL"}],
}


def heading(text: str) -> None:
    print(f"\n{text}\n{'-' * len(text)}")


def reading_of(record: dict, parameter: str) -> float:
    return next(r["value"] for r in record["readings"] if r["parameter"] == parameter)


def connect() -> tuple[Web3, object, str, object | None]:
    """Return a web3 client, the registry contract, the sender, and its key.

    Falls back to an in-process EVM when no RPC endpoint is configured.
    """

    rpc_url = os.getenv("ETH_RPC_URL")
    if not rpc_url:
        web3 = Web3(EthereumTesterProvider())
        abi, bytecode = compile_registry()
        factory = web3.eth.contract(abi=abi, bytecode=bytecode)
        owner, sender = web3.eth.accounts[0], web3.eth.accounts[1]
        receipt = web3.eth.wait_for_transaction_receipt(
            factory.constructor().transact({"from": owner})
        )
        registry = web3.eth.contract(address=receipt["contractAddress"], abi=abi)
        web3.eth.wait_for_transaction_receipt(
            registry.functions.registerIssuer(sender, "community").transact({"from": owner})
        )
        print("network  : in-process EVM (no testnet configured)")
        print(f"registry : {registry.address}")
        return web3, registry, sender, None

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    account = web3.eth.account.from_key(os.environ["ETH_PRIVATE_KEY"])
    abi, _bytecode = compile_registry()
    registry = web3.eth.contract(
        address=Web3.to_checksum_address(os.environ["ETH_CONTRACT_ADDRESS"]), abi=abi
    )
    print(f"network  : chain id {web3.eth.chain_id}")
    print(f"registry : {registry.address}")
    return web3, registry, account.address, account


def anchor(web3, registry, sender, key, record: dict) -> str:
    digest = content_hash(record)
    call = registry.functions.anchorRecord(
        record_hash_to_bytes32(digest), record["source"], record["source_record_id"]
    )
    if key is None:
        transaction_hash = call.transact({"from": sender})
    else:
        transaction = call.build_transaction(
            {
                "from": sender,
                "nonce": web3.eth.get_transaction_count(sender),
                "chainId": web3.eth.chain_id,
            }
        )
        transaction_hash = web3.eth.send_raw_transaction(
            key.sign_transaction(transaction).raw_transaction
        )
    web3.eth.wait_for_transaction_receipt(transaction_hash)
    return digest


def main() -> None:
    heading("Setup")
    web3, registry, sender, key = connect()
    role = registry.functions.issuerRole(sender).call().rstrip(b"\x00").decode() or "none"
    print(f"submitter: {sender}")
    print(f"role     : {role}")
    if role == "none":
        print("This account is not a registered issuer, so anchoring will be refused.")

    heading("1. Submit — two readings are anchored")
    community_digest = anchor(web3, registry, sender, key, COMMUNITY_SAMPLE)
    authority_digest = anchor(web3, registry, sender, key, AUTHORITY_SAMPLE)
    print(f"community reading -> {community_digest[:32]}...")
    print(f"authority reading -> {authority_digest[:32]}...")
    print("The readings themselves stay off-chain. Only the digest is published.")

    heading("2. Verify — the record still matches what was anchored")
    recomputed = content_hash(COMMUNITY_SAMPLE)
    anchored_at, submitter, _attributed_to, issuer_role, source, source_record_id = (
        registry.functions.getAnchor(record_hash_to_bytes32(recomputed)).call()
    )
    when = datetime.fromtimestamp(anchored_at, tz=timezone.utc).isoformat()
    print(f"recomputed digest matches : {recomputed == community_digest}")
    print(f"anchored at               : {when}")
    print(f"anchored by               : {submitter}")
    print(f"issuer role               : {issuer_role.rstrip(b"\x00").decode()}")
    print(f"declared source           : {source} / {source_record_id}")

    heading("3. Tamper — an authority reading is quietly lowered")
    tampered = {
        **AUTHORITY_SAMPLE,
        "readings": [
            {**r, "value": 24.0} if r["parameter"] == "e_coli" else r
            for r in AUTHORITY_SAMPLE["readings"]
        ],
    }
    original_value = reading_of(AUTHORITY_SAMPLE, "e_coli")
    tampered_value = reading_of(tampered, "e_coli")
    tampered_digest = content_hash(tampered)

    print(f"E. coli reported as {original_value}, later shown as {tampered_value} CFU/100mL")
    print(f"digest of the altered record  : {tampered_digest[:32]}...")
    print(f"matches what was anchored     : {tampered_digest == authority_digest}")
    print(
        "is the altered version on-chain: "
        f"{registry.functions.isAnchored(record_hash_to_bytes32(tampered_digest)).call()}"
    )
    print("The original digest is still anchored, so the change is provable.")

    heading("4. Not reported — a sample that was never submitted")
    missing_digest = content_hash(NEVER_SUBMITTED_SAMPLE)
    print(f"station {NEVER_SUBMITTED_SAMPLE['station_id']} on 2026-08-27")
    print(
        "anchored: "
        f"{registry.functions.isAnchored(record_hash_to_bytes32(missing_digest)).call()}"
    )
    print("Absence is visible: nothing was ever committed for this sample.")

    heading("What this does not prove")
    print("That a measurement is accurate, or that a sensor was calibrated.")
    print("Only that a record has not changed since it was anchored, and who anchored it.")


if __name__ == "__main__":
    main()
