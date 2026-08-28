from pathlib import Path

from app.main import ingest, issuers
from app.services.csv_import import seed_from_files
from app.services.map_sites import build_map_sites


FIXTURES = Path(__file__).parent / "fixtures"


def setup_function() -> None:
    ingest.store.clear()
    issuers.reset(community=[], government=[])


def test_seed_from_files_shifts_dates_to_end_in_2025_and_pairs_sites() -> None:
    counts = seed_from_files(
        ingest,
        issuers,
        community_csv=FIXTURES / "community_sample.csv",
        ems_events=FIXTURES / "ems_events.json",
        end_year=2025,
    )
    assert counts["community"] == 2
    assert counts["government"] >= 1

    community = [item for item in ingest.store.all_records(include_unmatched=True) if item.source.kind.value == "community"]
    government = [item for item in ingest.store.all_records(include_unmatched=True) if item.source.kind.value == "government"]
    assert max(item.observed_at.year for item in community) == 2025
    assert max(item.observed_at.month for item in community) == 12
    assert max(item.observed_at.day for item in community) == 11
    assert min(item.observed_at.month for item in community) == 6
    assert all(item.raw_payload.get("Date") == "2019-06-05" or item.raw_payload.get("Date") == "2019-12-11" for item in community)
    assert max(item.observed_at.year for item in government) == 2025
    assert all(item.displayable for item in community)

    sites = build_map_sites(ingest.store.all_records(include_unmatched=True), ingest.store.list_stations())
    pairs = [site for site in sites if site.kind == "pair"]
    assert len(pairs) == 1
    assert pairs[0].name == "Olympic Village"
    assert pairs[0].compared.startswith("2025-12-11")
    assert pairs[0].community_hash
    assert pairs[0].government_hash


def test_seed_from_ems_csv_groups_rows_and_shifts_dates() -> None:
    counts = seed_from_files(
        ingest,
        issuers,
        community_csv=FIXTURES / "community_sample.csv",
        ems_csv=FIXTURES / "ems_observations.csv",
        end_year=2025,
    )
    assert counts["community"] == 2
    assert counts["government"] >= 3
    government = [
        item
        for item in ingest.store.all_records(include_unmatched=True)
        if item.source.kind.value == "government"
    ]
    assert max(item.observed_at.year for item in government) == 2025
    assert any(item.metadata.get("location_id") == "E1" for item in government)


def test_map_uses_latest_observation_per_source() -> None:
    seed_from_files(
        ingest,
        issuers,
        community_csv=FIXTURES / "community_sample.csv",
        ems_events=FIXTURES / "ems_events.json",
        end_year=2025,
    )
    sites = build_map_sites(ingest.store.all_records(include_unmatched=True), ingest.store.list_stations())
    pair = next(site for site in sites if site.kind == "pair")
    community_reading = next(
        reading for reading in pair.readings if reading.parameter == "ph"
    )
    assert community_reading.community == "7.9"
