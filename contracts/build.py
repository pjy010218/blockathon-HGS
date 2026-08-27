"""Compile this project's Solidity contracts.

The single place that knows how to turn a ``.sol`` file into an ABI and
deployment bytecode. The deploy script and the tests both use it, so a contract
change is picked up everywhere without a checked-in build artifact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import solcx

SOLC_VERSION = "0.8.24"
CONTRACTS_DIR = Path(__file__).resolve().parent

REGISTRY_NAME = "WaterAuditRegistry"
CREDENTIAL_NAME = "VolunteerCredential"

# A record hash is a SHA-256 digest, which is exactly the width of a bytes32 slot.
RECORD_HASH_BYTES = 32


def ensure_solc() -> None:
    """Install the pinned solc release if it is not already present."""

    installed = {str(version) for version in solcx.get_installed_solc_versions()}
    if SOLC_VERSION not in installed:
        solcx.install_solc(SOLC_VERSION)


def compile_contract(contract_name: str) -> tuple[list[dict[str, Any]], str]:
    """Return a contract's ABI and its deployment bytecode."""

    ensure_solc()
    source_path = CONTRACTS_DIR / f"{contract_name}.sol"
    compiled = solcx.compile_source(
        source_path.read_text(),
        output_values=["abi", "bin"],
        solc_version=SOLC_VERSION,
    )
    key = next(name for name in compiled if name.endswith(f":{contract_name}"))
    return compiled[key]["abi"], compiled[key]["bin"]


def compile_registry() -> tuple[list[dict[str, Any]], str]:
    return compile_contract(REGISTRY_NAME)


def compile_credential() -> tuple[list[dict[str, Any]], str]:
    return compile_contract(CREDENTIAL_NAME)


def content_hash(record: Any) -> str:
    """Hash a record the way the backend does.

    Canonical form: JSON with sorted keys, no whitespace, UTF-8 kept as-is, then
    SHA-256. It must stay identical to the backend's rule, because a digest
    computed under different rules simply will not match.
    """

    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_hash_to_bytes32(content_hash: str) -> bytes:
    """Convert a hex SHA-256 content hash into the bytes32 the contract expects.

    The hash is rejected rather than padded or truncated, so a caller can never
    silently anchor a digest that is not the one it computed.
    """

    digest = bytes.fromhex(content_hash.removeprefix("0x"))
    if len(digest) != RECORD_HASH_BYTES:
        raise ValueError(
            f"A record hash must be {RECORD_HASH_BYTES} bytes; got {len(digest)}"
        )
    return digest


if __name__ == "__main__":
    import json
    import sys

    name = sys.argv[1] if len(sys.argv) > 1 else REGISTRY_NAME
    abi, _bytecode = compile_contract(name)
    print(json.dumps(abi, indent=2))
