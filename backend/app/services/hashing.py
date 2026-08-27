from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Serialize data deterministically so the same record always hashes identically."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


RECORD_HASH_BYTES = 32


def record_hash_to_bytes32(content_hash: str) -> bytes:
    """Convert a hex SHA-256 digest into the bytes32 the registry expects.

    Rejects padding or truncation so the on-chain slot is always the same
    digest the API stored, matching ``contracts/build.py``.
    """

    digest = bytes.fromhex(content_hash.removeprefix("0x"))
    if len(digest) != RECORD_HASH_BYTES:
        raise ValueError(
            f"A record hash must be {RECORD_HASH_BYTES} bytes; got {len(digest)}"
        )
    return digest
