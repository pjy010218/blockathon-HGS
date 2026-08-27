"""Behaviour of the volunteer contribution credential.

The credential recognises that an address anchored records. It is deliberately
not a tradeable asset and has no issuer: a contributor credits themselves, and
only for a record they anchored, so nobody can grant or withhold recognition.
"""

from __future__ import annotations

import pytest
from web3.exceptions import ContractLogicError

from build import record_hash_to_bytes32

FIRST_HASH = record_hash_to_bytes32("a" * 64)
SECOND_HASH = record_hash_to_bytes32("b" * 64)
UNANCHORED_HASH = record_hash_to_bytes32("c" * 64)

try:
    from eth_tester.exceptions import TransactionFailed

    REVERT = (ContractLogicError, TransactionFailed)
except ImportError:  # pragma: no cover - only when running against a real node
    REVERT = (ContractLogicError,)


def anchor(registry, web3, record_hash: bytes, sender: str):
    transaction_hash = registry.functions.anchorRecord(
        record_hash, "community", "obs-1"
    ).transact({"from": sender})
    return web3.eth.wait_for_transaction_receipt(transaction_hash)


def claim(credential, web3, record_hash: bytes, sender: str):
    transaction_hash = credential.functions.claimContribution(record_hash).transact(
        {"from": sender}
    )
    return web3.eth.wait_for_transaction_receipt(transaction_hash)


def test_contributor_can_claim_a_record_they_anchored(
    credential, registry, web3, other_submitter
) -> None:
    anchor(registry, web3, FIRST_HASH, other_submitter)
    claim(credential, web3, FIRST_HASH, other_submitter)

    assert credential.functions.contributionCount(other_submitter).call() == 1
    assert credential.functions.isCredited(FIRST_HASH).call() is True


def test_count_accumulates_across_records(credential, registry, web3, other_submitter) -> None:
    for record_hash in (FIRST_HASH, SECOND_HASH):
        anchor(registry, web3, record_hash, other_submitter)
        claim(credential, web3, record_hash, other_submitter)

    assert credential.functions.contributionCount(other_submitter).call() == 2


def test_claiming_someone_elses_record_is_rejected(
    credential, registry, web3, submitter, other_submitter
) -> None:
    """Recognition follows the address that actually anchored the record."""

    anchor(registry, web3, FIRST_HASH, submitter)

    with pytest.raises(REVERT, match="another address"):
        claim(credential, web3, FIRST_HASH, other_submitter)

    assert credential.functions.contributionCount(other_submitter).call() == 0


def test_claiming_an_unanchored_record_is_rejected(credential, web3, other_submitter) -> None:
    """A credential cannot be created out of nothing; the record must exist on-chain."""

    with pytest.raises(REVERT, match="not anchored"):
        claim(credential, web3, UNANCHORED_HASH, other_submitter)


def test_a_record_counts_only_once(credential, registry, web3, other_submitter) -> None:
    anchor(registry, web3, FIRST_HASH, other_submitter)
    claim(credential, web3, FIRST_HASH, other_submitter)

    with pytest.raises(REVERT, match="already credited"):
        claim(credential, web3, FIRST_HASH, other_submitter)

    assert credential.functions.contributionCount(other_submitter).call() == 1


def test_unknown_address_has_no_contributions(credential, other_submitter) -> None:
    assert credential.functions.contributionCount(other_submitter).call() == 0


def test_claim_emits_running_count(credential, registry, web3, other_submitter) -> None:
    anchor(registry, web3, FIRST_HASH, other_submitter)
    receipt = claim(credential, web3, FIRST_HASH, other_submitter)

    events = credential.events.ContributionCredited().process_receipt(receipt)
    assert len(events) == 1

    args = events[0]["args"]
    assert args["volunteer"] == other_submitter
    assert args["recordHash"] == FIRST_HASH
    assert args["contributionCount"] == 1


def test_credential_cannot_be_transferred(compiled_credential) -> None:
    """No market can form around something with no way to move it.

    The credential exposes no transfer, approval, mint, or burn path, so it is not
    a tradeable unit and there is nothing to sell.
    """

    abi, _bytecode = compiled_credential
    function_names = {entry["name"] for entry in abi if entry["type"] == "function"}

    forbidden = {
        name
        for name in function_names
        if any(
            word in name.lower()
            for word in ("transfer", "approve", "mint", "burn", "allowance", "permit")
        )
    }
    assert forbidden == set()


def test_credential_has_no_administrative_surface(compiled_credential) -> None:
    """No owner, no issuer, no pause: nobody can grant or withhold recognition."""

    abi, _bytecode = compiled_credential
    function_names = {entry["name"] for entry in abi if entry["type"] == "function"}

    administrative = {
        name
        for name in function_names
        if any(
            word in name.lower()
            for word in ("owner", "issuer", "admin", "pause", "upgrade", "withdraw")
        )
    }
    assert administrative == set()
    assert function_names == {"registry", "claimContribution", "contributionCount", "isCredited"}


def test_relayed_contribution_credits_the_signer_not_the_relayer(
    credential, registry, web3, submitter, unregistered
) -> None:
    """A contributor whose record was relayed for them can still claim it.

    The registry attributes the record to the signer while the issuer pays the
    gas, so credit does not follow whoever sent the transaction.
    """

    web3.eth.wait_for_transaction_receipt(
        registry.functions.anchorRecordFor(
            FIRST_HASH, "community", "obs-1", unregistered
        ).transact({"from": submitter})
    )

    claim(credential, web3, FIRST_HASH, unregistered)

    assert credential.functions.contributionCount(unregistered).call() == 1
    assert credential.functions.contributionCount(submitter).call() == 0
