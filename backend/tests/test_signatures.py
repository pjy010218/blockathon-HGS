import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

from app.models.schemas import Location, Measurement, SourceKind, SourceProvenance, WaterQualityRecordCreate
from app.services.hashing import canonical_record_payload, sha256_hex
from app.services.issuers import IssuerRegistry
from app.services.signatures import SignatureError, recover_signer


def _record() -> WaterQualityRecordCreate:
    return WaterQualityRecordCreate(
        source=SourceProvenance(kind=SourceKind.community, provider="test"),
        observed_at="2026-08-25T12:00:00Z",
        location=Location(name="Test inlet", latitude=49.2, longitude=-123.1),
        measurements=[Measurement(field="ph", value=7.2, unit="pH")],
        metadata={"medium": "marine"},
        raw_payload={"site": "Test inlet"},
    )


def test_canonical_payload_excludes_match_and_signature_fields() -> None:
    payload = canonical_record_payload(_record())
    assert set(payload) == {
        "source",
        "observed_at",
        "location",
        "measurements",
        "metadata",
        "raw_payload",
    }


def test_recover_signer_from_personal_sign_over_hash() -> None:
    account = Account.create()
    digest = sha256_hex(canonical_record_payload(_record()))
    signed = account.sign_message(encode_defunct(primitive=bytes.fromhex(digest)))
    assert recover_signer(digest, signed.signature.to_0x_hex()) == account.address


def test_recover_signer_rejects_bad_signature() -> None:
    with pytest.raises(SignatureError):
        recover_signer("a" * 64, "0xdead")


def test_issuer_registry_rejects_wrong_role() -> None:
    account = Account.create()
    registry = IssuerRegistry(community=[account.address], government=[])
    with pytest.raises(PermissionError, match="government"):
        registry.require(account.address, "government")


def test_issuer_registry_accepts_matching_role() -> None:
    account = Account.create()
    registry = IssuerRegistry(community=[account.address], government=[])
    registry.require(account.address, "community")
