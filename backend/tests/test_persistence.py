from pathlib import Path

from app.services.blockchain import BlockchainService
from app.services.csv_import import seed_from_files
from app.services.database import SqlRecordStore
from app.services.hashing import content_hash_for_record
from app.services.ingest import IngestService
from app.services.issuers import IssuerRegistry


FIXTURES = Path(__file__).parent / "fixtures"


def _ingest(tmp_path):
    url = f"sqlite:///{tmp_path / 'audit.db'}"
    store = SqlRecordStore(url)
    ingest = IngestService(store, BlockchainService(mode="simulated", network="local"))
    return url, store, ingest


def test_initial_import_persists_hash_and_survives_reload(tmp_path) -> None:
    url, store, ingest = _ingest(tmp_path)
    seed_from_files(
        ingest,
        IssuerRegistry(),
        community_csv=FIXTURES / "community_sample.csv",
        ems_events=FIXTURES / "ems_events.json",
        end_year=2025,
        shift_dates=True,
        anchor=True,
    )
    saved = store.all_records(include_unmatched=True)
    assert saved
    assert store.count() == len(saved)
    for record in saved:
        assert content_hash_for_record(record) == record.content_hash
        assert record.blockchain.status.value == "simulated"
        assert record.blockchain.transaction_hash

    hashes = {record.id: record.content_hash for record in saved}
    observed = {record.id: record.observed_at.isoformat() for record in saved}

    reloaded = SqlRecordStore(url)
    loaded = reloaded.all_records(include_unmatched=True)
    assert len(loaded) == len(hashes)
    assert reloaded.list_stations()
    mapped = reloaded.records_for_map()
    assert mapped
    assert all(
        item.source.kind.value == "community"
        or item.matched_station_id in {record.matched_station_id for record in mapped if record.source.kind.value == "community"}
        for item in mapped
    )
    by_id = {record.id: record for record in loaded}
    for record_id, digest in hashes.items():
        record = by_id[record_id]
        assert record.content_hash == digest
        assert record.observed_at.isoformat() == observed[record_id]
        assert content_hash_for_record(record) == digest
        assert record.blockchain.status.value == "simulated"


def test_second_boot_skips_import_when_database_has_rows(tmp_path) -> None:
    url, store, ingest = _ingest(tmp_path)
    seed_from_files(
        ingest,
        IssuerRegistry(),
        community_csv=FIXTURES / "community_sample.csv",
        ems_events=FIXTURES / "ems_events.json",
        end_year=2025,
        shift_dates=True,
        anchor=True,
    )
    first_hashes = sorted(item.content_hash for item in store.all_records(include_unmatched=True))
    assert SqlRecordStore(url).count() > 0
    assert SqlRecordStore(url).count() == len(first_hashes)
