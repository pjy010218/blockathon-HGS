from app.main import ingest, issuers
from app.services.demo_seed import seed_synthetic


def setup_function() -> None:
    ingest.store.clear()
    issuers.reset(community=[], government=[])


def test_seed_synthetic_matches_community_to_seeded_stations() -> None:
    counts = seed_synthetic(ingest, issuers)
    assert counts == {"government": 8, "community": 8}
    community = [item for item in ingest.store.all_records(include_unmatched=True) if item.source.kind.value == "community"]
    assert all(item.displayable for item in community)
    assert all(item.match_status == "matched" for item in community)


def test_map_endpoint_returns_match_and_review_sites() -> None:
    from fastapi.testclient import TestClient
    from app.main import app

    seed_synthetic(ingest, issuers)
    response = TestClient(app).get("/api/v1/map")
    assert response.status_code == 200
    sites = response.json()
    assert len(sites) == 8
    statuses = {site["status"] for site in sites}
    assert statuses == {"match", "review"}
    assert sum(site["status"] == "review" for site in sites) == 3
    false_creek = next(site for site in sites if site["name"] == "False Creek")
    assert false_creek["readings"]
    assert false_creek["position"] == [49.2743, -123.1057]
