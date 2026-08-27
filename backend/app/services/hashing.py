from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Serialize data deterministically so the same record always hashes identically."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


CANONICAL_RECORD_FIELDS = (
    "source",
    "observed_at",
    "location",
    "measurements",
    "metadata",
    "raw_payload",
)


def canonical_record_payload(record: Any) -> dict[str, Any]:
    """Fields that form the content hash. Match metadata stays outside."""

    if hasattr(record, "model_dump"):
        data = record.model_dump(mode="json")
    else:
        data = dict(record)
    return {field: data[field] for field in CANONICAL_RECORD_FIELDS}


def content_hash_for_record(record: Any) -> str:
    return sha256_hex(canonical_record_payload(record))


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
