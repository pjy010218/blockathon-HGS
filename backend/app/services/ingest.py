from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import SourceKind, WaterQualityRecord, WaterQualityRecordCreate
from app.services.blockchain import BlockchainService
from app.services.hashing import content_hash_for_record
from app.services.stations import Station


class DuplicateRecord(Exception):
    def __init__(self, record: WaterQualityRecord) -> None:
        self.record = record
        super().__init__("This exact record has already been submitted.")


class IngestService:
    def __init__(self, store, blockchain: BlockchainService) -> None:
        self.store = store
        self.blockchain = blockchain

    def find_by_hash(self, content_hash: str) -> WaterQualityRecord | None:
        return self.store.find_by_hash(content_hash)

    def ingest(
        self,
        payload: WaterQualityRecordCreate,
        *,
        signer: str,
        anchor: bool = False,
    ) -> WaterQualityRecord:
        digest = content_hash_for_record(payload)
        existing = self.find_by_hash(digest)
        if existing is not None:
            raise DuplicateRecord(existing)

        record = WaterQualityRecord(
            **payload.model_dump(),
            ingested_at=datetime.now(timezone.utc),
            content_hash=digest,
            signer_address=signer,
        )
        self._apply_station(record, payload)

        if anchor:
            record.blockchain = self.blockchain.anchor(
                digest,
                source=payload.source.kind.value,
                source_record_id=payload.source.source_record_id or str(record.id),
                attributed_to=signer,
            )

        self.store.save_record(record)
        return record

    def ingest_many(
        self,
        payloads: list[WaterQualityRecordCreate],
        *,
        signer: str,
        anchor: bool = False,
        chunk_size: int = 200,
    ) -> int:
        """Persist many records without a per-row round trip.

        Duplicate content hashes inside the batch are skipped. Existing database
        rows are not queried first; use this on an empty store or accept unique
        constraint errors from the database.
        """

        seen: set[str] = set()
        batch: list[WaterQualityRecord] = []
        stored = 0
        for payload in payloads:
            digest = content_hash_for_record(payload)
            if digest in seen:
                continue
            seen.add(digest)
            record = WaterQualityRecord(
                **payload.model_dump(),
                ingested_at=datetime.now(timezone.utc),
                content_hash=digest,
                signer_address=signer,
            )
            self._apply_station(record, payload)
            if anchor:
                record.blockchain = self.blockchain.anchor(
                    digest,
                    source=payload.source.kind.value,
                    source_record_id=payload.source.source_record_id or str(record.id),
                    attributed_to=signer,
                )
            batch.append(record)
            if len(batch) >= chunk_size:
                self.store.save_records(batch)
                stored += len(batch)
                batch = []
        if batch:
            self.store.save_records(batch)
            stored += len(batch)
        return stored

    def upsert_government_station(
        self,
        *,
        location_id: str,
        name: str | None,
        latitude: float,
        longitude: float,
        medium: str | None,
    ) -> Station:
        station = Station(
            id=location_id,
            name=name or location_id,
            latitude=latitude,
            longitude=longitude,
            medium=medium,
        )
        self.store.save_station(station)
        return station

    def _apply_station(self, record: WaterQualityRecord, payload: WaterQualityRecordCreate) -> None:
        if payload.source.kind == SourceKind.community:
            match = self.store.station_registry().match(payload.location.latitude, payload.location.longitude)
            if match is None:
                record.displayable = False
                record.match_status = "unmatched"
                return
            record.displayable = True
            record.match_status = "matched"
            record.matched_station_id = match.station.id
            record.matched_station_name = match.station.name
            record.match_distance_m = round(match.distance_m, 2)
            return

        location_id = payload.metadata.get("location_id")
        record.displayable = True
        if isinstance(location_id, str):
            record.matched_station_id = location_id
            record.matched_station_name = payload.location.name
            record.match_status = "matched"
