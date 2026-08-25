from fastapi.testclient import TestClient

from app.main import app, records


client = TestClient(app)


def setup_function() -> None:
    records.clear()


def _record(source_kind: str, measurements: list[dict]) -> dict:
    return {
        "source": {
            "kind": source_kind,
            "provider": "test-provider",
            "dataset_id": "dataset-1",
            "source_record_id": f"{source_kind}-1",
        },
        "observed_at": "2026-08-25T12:00:00Z",
        "location": {"name": "Test inlet", "latitude": 49.2, "longitude": -123.1},
        "measurements": measurements,
        "metadata": {"test": True},
        "raw_payload": {"source_field": "preserved"},
    }


def test_create_and_verify_record() -> None:
    response = client.post(
        "/api/v1/records",
        json=_record("government", [{"field": "ph", "value": 7.2, "unit": "pH"}]),
    )
    assert response.status_code == 201
    record = response.json()

    verification = client.get(f"/api/v1/records/{record['id']}/verify")
    assert verification.status_code == 200
    assert verification.json()["matches"] is True


def test_comparison_preserves_missing_fields() -> None:
    government = client.post(
        "/api/v1/records",
        json=_record("government", [{"field": "ph", "value": 7.2, "unit": "pH"}]),
    ).json()
    community = client.post(
        "/api/v1/records",
        json=_record(
            "community",
            [
                {"field": "ph", "value": 7.5, "unit": "pH"},
                {"field": "turbidity", "value": 2.1, "unit": "NTU"},
            ],
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
