from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.models.schemas import SourceKind, WaterQualityRecord, WaterQualityRecordCreate
from app.services.blockchain import BlockchainService
from app.services.hashing import content_hash_for_record
from app.services.stations import Station, StationRegistry


class DuplicateRecord(Exception):
    def __init__(self, record: WaterQualityRecord) -> None:
        self.record = record
        super().__init__("This exact record has already been submitted.")


class IngestService:
    def __init__(
        self,
        records: dict[UUID, WaterQualityRecord],
        stations: StationRegistry,
        blockchain: BlockchainService,
    ) -> None:
        self.records = records
        self.stations = stations
        self.blockchain = blockchain

    def find_by_hash(self, content_hash: str) -> WaterQualityRecord | None:
        for record in self.records.values():
            if record.content_hash == content_hash:
                return record
        return None

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

        self.records[record.id] = record
        return record

    def upsert_government_station(
        self,
        *,
        location_id: str,
        name: str | None,
        latitude: float,
        longitude: float,
        medium: str | None,
    ) -> Station:
        return self.stations.upsert(
            Station(
                id=location_id,
                name=name or location_id,
                latitude=latitude,
                longitude=longitude,
                medium=medium,
            )
        )

    def _apply_station(self, record: WaterQualityRecord, payload: WaterQualityRecordCreate) -> None:
        if payload.source.kind == SourceKind.community:
            match = self.stations.match(payload.location.latitude, payload.location.longitude)
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
