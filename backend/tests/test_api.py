from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from app.main import app, ingest, issuers
from app.models.schemas import WaterQualityRecordCreate
from app.services.hashing import content_hash_for_record


client = TestClient(app)
COMMUNITY_ACCOUNT = Account.create()
GOVERNMENT_ACCOUNT = Account.create()
OUTSIDER = Account.create()


def setup_function() -> None:
    ingest.store.clear()
    issuers.reset(
        community=[COMMUNITY_ACCOUNT.address],
        government=[GOVERNMENT_ACCOUNT.address],
    )


def _record(source_kind: str, measurements: list[dict], **overrides: object) -> dict:
    payload = {
        "source": {
            "kind": source_kind,
            "provider": "test-provider",
            "dataset_id": "dataset-1",
            "source_record_id": f"{source_kind}-1",
        },
        "observed_at": "2026-08-25T12:00:00Z",
        "location": {"name": "Test inlet", "latitude": 49.271, "longitude": -123.122},
        "measurements": measurements,
        "metadata": {"test": True},
        "raw_payload": {"source_field": "preserved"},
    }
    payload.update(overrides)
    return payload


def _sign(payload: dict, account, *, anchor: bool = False) -> dict:
    digest = content_hash_for_record(WaterQualityRecordCreate.model_validate(payload))
    signed = account.sign_message(encode_defunct(primitive=bytes.fromhex(digest)))
    return {
        **payload,
        "signature": signed.signature.to_0x_hex(),
        "signerAddress": account.address,
        "signedContentHash": digest,
        "signatureMethod": "personal_sign",
        "anchor": anchor,
    }


def _ems_event() -> dict:
    return {
        "Location_ID": "E207969",
        "Location_Name": "North Arm",
        "Location_Latitude": 49.271,
        "Location_Longitude": -123.122,
        "Observed_Date_Time": "2026-08-26T09:15:00-07:00",
        "Medium": "surface water",
        "observations": [
            {"Observed_Property_Name": "PH-F", "Result": 7.2, "Unit": "pH"},
        ],
    }


def _import_ems(account=GOVERNMENT_ACCOUNT, event: dict | None = None, *, anchor: bool = False) -> dict:
    body_event = event or _ems_event()
    from app.adapters.enmods import EnmodsAdapter

    canonical = EnmodsAdapter().normalize(body_event)
    digest = content_hash_for_record(canonical)
    signed = account.sign_message(encode_defunct(primitive=bytes.fromhex(digest)))
    response = client.post(
        "/api/v1/import/ems",
        json={
            "event": body_event,
            "signature": signed.signature.to_0x_hex(),
            "signerAddress": account.address,
            "signedContentHash": digest,
            "signatureMethod": "personal_sign",
            "anchor": anchor,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_community_submit_requires_signature() -> None:
    response = client.post(
        "/api/v1/records",
        json=_record("community", [{"field": "ph", "value": 7.2, "unit": "pH"}]),
    )
    assert response.status_code == 401


def test_unregistered_community_wallet_is_forbidden() -> None:
    payload = _sign(
        _record("community", [{"field": "ph", "value": 7.2, "unit": "pH"}]),
        OUTSIDER,
    )
    response = client.post("/api/v1/records", json=payload)
    assert response.status_code == 403


def test_hash_mismatch_is_rejected() -> None:
    payload = _sign(
        _record("community", [{"field": "ph", "value": 7.2, "unit": "pH"}]),
        COMMUNITY_ACCOUNT,
    )
    payload["signedContentHash"] = "b" * 64
    response = client.post("/api/v1/records", json=payload)
    assert response.status_code == 400


def test_unmatched_community_is_stored_but_hidden() -> None:
    payload = _sign(
        _record("community", [{"field": "ph", "value": 7.2, "unit": "pH"}]),
        COMMUNITY_ACCOUNT,
    )
    created = client.post("/api/v1/records", json=payload)
    assert created.status_code == 201
    assert created.json()["displayable"] is False
    assert created.json()["match_status"] == "unmatched"

    listed = client.get("/api/v1/records")
    assert listed.json() == []
    included = client.get("/api/v1/records", params={"include_unmatched": True})
    assert len(included.json()) == 1


def test_community_matches_station_within_50_m() -> None:
    government = _import_ems()
    payload = _sign(
        _record("community", [{"field": "ph", "value": 7.5, "unit": "pH"}]),
        COMMUNITY_ACCOUNT,
        anchor=True,
    )
    created = client.post("/api/v1/records", json=payload).json()
    assert created["displayable"] is True
    assert created["matched_station_id"] == "E207969"
    assert created["blockchain"]["status"] == "simulated"
    stations_response = client.get("/api/v1/stations")
    assert stations_response.json()[0]["id"] == "E207969"
    assert government["source"]["kind"] == "government"


def test_duplicate_content_hash_returns_409() -> None:
    payload = _sign(
        _record("community", [{"field": "ph", "value": 7.2, "unit": "pH"}]),
        COMMUNITY_ACCOUNT,
    )
    assert client.post("/api/v1/records", json=payload).status_code == 201
    again = client.post("/api/v1/records", json=payload)
    assert again.status_code == 409


def test_wrong_role_cannot_import_ems() -> None:
    event = _ems_event()
    from app.adapters.enmods import EnmodsAdapter
    from app.services.hashing import content_hash_for_record

    digest = content_hash_for_record(EnmodsAdapter().normalize(event))
    signed = COMMUNITY_ACCOUNT.sign_message(encode_defunct(primitive=bytes.fromhex(digest)))
    response = client.post(
        "/api/v1/import/ems",
        json={
            "event": event,
            "signature": signed.signature.to_0x_hex(),
            "signerAddress": COMMUNITY_ACCOUNT.address,
            "signedContentHash": digest,
        },
    )
    assert response.status_code == 403


def test_create_and_verify_record() -> None:
    record = _import_ems()
    verification = client.get(f"/api/v1/records/{record['id']}/verify")
    assert verification.status_code == 200
    assert verification.json()["matches"] is True


def test_anchor_defaults_to_simulated() -> None:
    created = _import_ems()
    response = client.post(f"/api/v1/records/{created['id']}/anchor")
    assert response.status_code == 200
    assert response.json()["blockchain"]["status"] == "simulated"


def test_comparison_preserves_missing_fields() -> None:
    government = _import_ems()
    community = client.post(
        "/api/v1/records",
        json=_sign(
            _record(
                "community",
                [
                    {"field": "ph", "value": 7.5, "unit": "pH"},
                    {"field": "turbidity", "value": 2.1, "unit": "NTU"},
                ],
            ),
            COMMUNITY_ACCOUNT,
        ),
    ).json()

    response = client.post(
        "/api/v1/comparisons",
        json={
            "government_record_id": government["id"],
            "community_record_id": community["id"],
        },
    )
    fields = {field["field"]: field for field in response.json()["fields"]}
    assert fields["ph"]["status"] == "different_value_or_unit"
    assert fields["turbidity"]["status"] == "missing_from_government"
