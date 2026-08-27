"""Behaviour of the on-chain record registry.

These tests describe what an anchor does and does not prove. The contract records
that a digest existed at a point in time, who submitted it, and which issuer role
they held. It says nothing about whether the underlying measurement is accurate.
"""

from __future__ import annotations

import pytest
from web3.exceptions import ContractLogicError

from build import record_hash_to_bytes32
from conftest import ROLE_COMMUNITY, ROLE_GOVERNMENT

GOVERNMENT_HASH = record_hash_to_bytes32("a" * 64)
COMMUNITY_HASH = record_hash_to_bytes32("b" * 64)
EMPTY_HASH = b"\x00" * 32
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# A revert surfaces as ContractLogicError against a real node, and as
# TransactionFailed through the in-process EVM used here. Accept either so the
# same assertions hold whichever backend the tests run against.
try:
    from eth_tester.exceptions import TransactionFailed

    REVERT = (ContractLogicError, TransactionFailed)
except ImportError:  # pragma: no cover - only when running against a real node
    REVERT = (ContractLogicError,)


def anchor(registry, web3, record_hash: bytes, source: str, source_record_id: str, sender: str):
    transaction_hash = registry.functions.anchorRecord(
        record_hash, source, source_record_id
    ).transact({"from": sender})
    return web3.eth.wait_for_transaction_receipt(transaction_hash)


def read_anchor(registry, record_hash: bytes) -> dict:
    """``getAnchor`` as a mapping, so field additions do not ripple through tests."""

    anchored_at, submitter, attributed_to, issuer_role, source, source_record_id = (
        registry.functions.getAnchor(record_hash).call()
    )
    return {
        "anchored_at": anchored_at,
        "submitter": submitter,
        "attributed_to": attributed_to,
        "issuer_role": issuer_role,
        "source": source,
        "source_record_id": source_record_id,
    }


# --- Anchoring --------------------------------------------------------------


def test_anchor_stores_provenance_and_block_timestamp(registry, web3, submitter) -> None:
    receipt = anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", submitter)
    stored = read_anchor(registry, GOVERNMENT_HASH)

    assert stored["submitter"] == submitter
    assert stored["attributed_to"] == submitter
    assert stored["issuer_role"] == ROLE_COMMUNITY
    assert stored["source"] == "enmods"
    assert stored["source_record_id"] == "row-42"
    assert stored["anchored_at"] == web3.eth.get_block(receipt["blockNumber"])["timestamp"]


def test_anchor_emits_record_anchored_event(registry, web3, submitter) -> None:
    receipt = anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", submitter)

    events = registry.events.RecordAnchored().process_receipt(receipt)
    assert len(events) == 1

    args = events[0]["args"]
    assert args["recordHash"] == GOVERNMENT_HASH
    assert args["submitter"] == submitter
    assert args["attributedTo"] == submitter
    assert args["issuerRole"] == ROLE_COMMUNITY
    assert args["source"] == "enmods"
    assert args["sourceRecordId"] == "row-42"


def test_unanchored_hash_reads_as_empty(registry) -> None:
    """A hash that was never anchored must be distinguishable from an anchored one.

    ``getAnchor`` returns a zeroed struct rather than reverting, so callers detect
    "not anchored" by ``anchoredAt == 0`` and must not read the other fields as
    meaningful.
    """

    stored = read_anchor(registry, COMMUNITY_HASH)

    assert stored["anchored_at"] == 0
    assert stored["submitter"] == ZERO_ADDRESS
    assert stored["attributed_to"] == ZERO_ADDRESS
    assert stored["source"] == ""


def test_existing_anchor_cannot_be_replaced(registry, web3, submitter, other_submitter) -> None:
    """A correction must create a new anchor; it must never overwrite an old one."""

    anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", submitter)

    with pytest.raises(REVERT, match="record already anchored"):
        anchor(registry, web3, GOVERNMENT_HASH, "spoofed", "row-99", other_submitter)

    stored = read_anchor(registry, GOVERNMENT_HASH)
    assert stored["submitter"] == submitter
    assert stored["source"] == "enmods"


def test_empty_record_hash_is_rejected(registry, web3, submitter) -> None:
    """The zero hash is the sentinel for "not anchored" and must stay unusable."""

    with pytest.raises(REVERT, match="empty record hash"):
        anchor(registry, web3, EMPTY_HASH, "enmods", "row-42", submitter)


def test_provenance_strings_round_trip_unchanged(registry, web3, submitter) -> None:
    """Source identifiers are stored verbatim, including non-ASCII and empty values."""

    source = "BC Data Catalogue / EnMoDS — Nechako"
    anchor(registry, web3, GOVERNMENT_HASH, source, "", submitter)

    stored = read_anchor(registry, GOVERNMENT_HASH)
    assert stored["source"] == source
    assert stored["source_record_id"] == ""


# --- Issuer registry --------------------------------------------------------


def test_deployer_becomes_the_owner(registry, owner) -> None:
    assert registry.functions.owner().call() == owner


def test_only_the_owner_can_register_an_issuer(registry, submitter, unregistered) -> None:
    with pytest.raises(REVERT, match="caller is not the owner"):
        registry.functions.registerIssuer(unregistered, "community").transact(
            {"from": submitter}
        )

    assert registry.functions.issuerRole(unregistered).call() == b"\x00" * 32


def test_unregistered_account_cannot_anchor(registry, web3, unregistered) -> None:
    """Anchoring is restricted so a stranger cannot publish records as a source."""

    with pytest.raises(REVERT, match="caller is not a registered issuer"):
        anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", unregistered)


def test_registering_grants_the_ability_to_anchor(registry, web3, owner, unregistered) -> None:
    web3.eth.wait_for_transaction_receipt(
        registry.functions.registerIssuer(unregistered, "government").transact(
            {"from": owner}
        )
    )
    anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", unregistered)

    assert registry.functions.isIssuer(unregistered, "government").call() is True
    assert registry.functions.isIssuer(unregistered, "community").call() is False
    assert read_anchor(registry, GOVERNMENT_HASH)["issuer_role"] == ROLE_GOVERNMENT


def test_unknown_role_is_rejected(registry, owner, unregistered) -> None:
    with pytest.raises(REVERT, match="unknown issuer role"):
        registry.functions.registerIssuer(unregistered, "auditor").transact({"from": owner})


def test_revoking_removes_the_ability_to_anchor(registry, web3, owner, submitter) -> None:
    web3.eth.wait_for_transaction_receipt(
        registry.functions.revokeIssuer(submitter).transact({"from": owner})
    )

    with pytest.raises(REVERT, match="caller is not a registered issuer"):
        anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", submitter)


def test_revocation_does_not_rewrite_earlier_anchors(registry, web3, owner, submitter) -> None:
    """The role in force at anchoring time stays on the record.

    Losing an issuer role later must not retroactively change what a past record
    says about who submitted it and under what authority.
    """

    anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", submitter)
    web3.eth.wait_for_transaction_receipt(
        registry.functions.revokeIssuer(submitter).transact({"from": owner})
    )

    stored = read_anchor(registry, GOVERNMENT_HASH)
    assert stored["submitter"] == submitter
    assert stored["issuer_role"] == ROLE_COMMUNITY
    assert registry.functions.issuerRole(submitter).call() == b"\x00" * 32


def test_revoking_an_unregistered_account_is_rejected(registry, owner, unregistered) -> None:
    with pytest.raises(REVERT, match="issuer is not registered"):
        registry.functions.revokeIssuer(unregistered).transact({"from": owner})


# --- Relayed submission -----------------------------------------------------


def test_relayer_can_anchor_on_behalf_of_a_contributor(
    registry, web3, submitter, unregistered
) -> None:
    """Gas is paid by the issuer; credit follows the contributor who signed."""

    web3.eth.wait_for_transaction_receipt(
        registry.functions.anchorRecordFor(
            GOVERNMENT_HASH, "community", "obs-1", unregistered
        ).transact({"from": submitter})
    )

    stored = read_anchor(registry, GOVERNMENT_HASH)
    assert stored["submitter"] == submitter
    assert stored["attributed_to"] == unregistered


def test_relaying_still_requires_a_registered_issuer(registry, unregistered, submitter) -> None:
    with pytest.raises(REVERT, match="caller is not a registered issuer"):
        registry.functions.anchorRecordFor(
            GOVERNMENT_HASH, "community", "obs-1", submitter
        ).transact({"from": unregistered})


def test_relaying_to_the_zero_address_is_rejected(registry, submitter) -> None:
    with pytest.raises(REVERT, match="contributor address required"):
        registry.functions.anchorRecordFor(
            GOVERNMENT_HASH, "community", "obs-1", ZERO_ADDRESS
        ).transact({"from": submitter})


# --- Public read path -------------------------------------------------------


def test_lookup_functions_are_all_view(compiled_registry) -> None:
    """Nothing a reader needs to call changes state, so nothing costs gas."""

    abi, _bytecode = compiled_registry
    lookups = {"getAnchor", "isAnchored", "getAnchors", "isIssuer", "issuerRole"}
    for entry in abi:
        if entry.get("name") in lookups:
            assert entry["stateMutability"] == "view", entry["name"]


def test_is_anchored_answers_existence_directly(registry, web3, submitter) -> None:
    """The map UI asks one question per pin: is this record on-chain?"""

    assert registry.functions.isAnchored(GOVERNMENT_HASH).call() is False
    anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", submitter)
    assert registry.functions.isAnchored(GOVERNMENT_HASH).call() is True


def test_get_anchors_reads_a_batch_in_order(registry, web3, submitter) -> None:
    """One call for a screenful of pins, with unanchored records kept in place."""

    third_hash = record_hash_to_bytes32("c" * 64)
    anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", submitter)
    anchor(registry, web3, third_hash, "datastream", "obs-7", submitter)

    batch = registry.functions.getAnchors([GOVERNMENT_HASH, COMMUNITY_HASH, third_hash]).call()

    assert [entry[5] for entry in batch] == ["row-42", "", "obs-7"]
    assert batch[1][0] == 0  # COMMUNITY_HASH was never anchored


def test_get_anchors_accepts_an_empty_batch(registry) -> None:
    assert registry.functions.getAnchors([]).call() == []


def test_get_anchor_returns_a_single_struct(compiled_registry) -> None:
    """``getAnchor`` returns one tuple, not several separate values.

    A hand-written ABI that flattens the struct decodes the return data
    incorrectly, so any client ABI must keep the tuple wrapper.
    """

    abi, _bytecode = compiled_registry
    get_anchor = next(entry for entry in abi if entry.get("name") == "getAnchor")

    assert len(get_anchor["outputs"]) == 1
    output = get_anchor["outputs"][0]
    assert output["type"] == "tuple"
    assert [component["name"] for component in output["components"]] == [
        "anchoredAt",
        "submitter",
        "attributedTo",
        "issuerRole",
        "source",
        "sourceRecordId",
    ]


def test_contributions_are_enumerable_per_contributor(
    registry, web3, submitter, other_submitter
) -> None:
    """``RecordAnchored`` indexes the contributor, so one address's records can be listed.

    This is the evidence a volunteer contribution record is built from, and it
    follows ``attributedTo`` so relayed submissions still reach the right person.
    """

    anchor(registry, web3, GOVERNMENT_HASH, "community", "obs-1", submitter)
    anchor(registry, web3, COMMUNITY_HASH, "community", "obs-2", other_submitter)

    mine = registry.events.RecordAnchored.get_logs(
        from_block=0, argument_filters={"attributedTo": submitter}
    )
    assert [event["args"]["sourceRecordId"] for event in mine] == ["obs-1"]


def test_indexed_fields_support_the_read_paths(compiled_registry) -> None:
    """Filtering by source is a client-side scan, not an RPC topic filter.

    Only indexed event arguments become log topics. A map view that needs to find
    anchors by location or source therefore needs an off-chain index.
    """

    abi, _bytecode = compiled_registry
    event = next(entry for entry in abi if entry.get("name") == "RecordAnchored")
    indexed = {argument["name"] for argument in event["inputs"] if argument["indexed"]}

    assert indexed == {"recordHash", "submitter", "attributedTo"}


# --- Batch anchoring --------------------------------------------------------


def test_batch_anchors_every_submission(registry, web3, submitter) -> None:
    submissions = [
        (record_hash_to_bytes32(f"{index:064x}"), "enmods", f"row-{index}")
        for index in range(1, 4)
    ]
    web3.eth.wait_for_transaction_receipt(
        registry.functions.anchorRecords(submissions).transact({"from": submitter})
    )

    for record_hash, _source, source_record_id in submissions:
        stored = read_anchor(registry, record_hash)
        assert stored["anchored_at"] != 0
        assert stored["attributed_to"] == submitter
        assert stored["source_record_id"] == source_record_id


def test_batch_is_all_or_nothing(registry, web3, submitter) -> None:
    """A batch containing an already-anchored record leaves no partial run behind."""

    anchor(registry, web3, GOVERNMENT_HASH, "enmods", "row-42", submitter)
    fresh_hash = record_hash_to_bytes32("d" * 64)

    with pytest.raises(REVERT, match="record already anchored"):
        registry.functions.anchorRecords(
            [(fresh_hash, "enmods", "row-43"), (GOVERNMENT_HASH, "enmods", "row-42")]
        ).transact({"from": submitter})

    assert registry.functions.isAnchored(fresh_hash).call() is False


def test_batch_requires_a_registered_issuer(registry, unregistered) -> None:
    with pytest.raises(REVERT, match="caller is not a registered issuer"):
        registry.functions.anchorRecords(
            [(GOVERNMENT_HASH, "enmods", "row-42")]
        ).transact({"from": unregistered})


def test_empty_batch_changes_nothing(registry, web3, submitter) -> None:
    receipt = web3.eth.wait_for_transaction_receipt(
        registry.functions.anchorRecords([]).transact({"from": submitter})
    )
    assert receipt["status"] == 1


def test_published_constants_show_the_stored_encoding(registry) -> None:
    """The interface names roles; these constants document how they are stored."""

    assert registry.functions.ROLE_COMMUNITY().call() == ROLE_COMMUNITY
    assert registry.functions.ROLE_GOVERNMENT().call() == ROLE_GOVERNMENT
