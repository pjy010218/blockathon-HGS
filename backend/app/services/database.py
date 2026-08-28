from __future__ import annotations

from uuid import UUID

from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, Float, String, Uuid, create_engine, delete, func, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.models.schemas import WaterQualityRecord
from app.services.map_sites import station_in_lower_mainland
from app.services.stations import Station, StationRegistry


class Base(DeclarativeBase):
    pass


class RecordRow(Base):
    __tablename__ = "water_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_kind: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    matched_station_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    displayable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class StationRow(Base):
    __tablename__ = "water_stations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    medium: Mapped[str | None] = mapped_column(String, nullable=True)


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


class MemoryRecordStore:
    """In-process store for tests. Production uses SqlRecordStore."""

    def __init__(self) -> None:
        self._records: dict[UUID, WaterQualityRecord] = {}
        self._stations = StationRegistry()

    def count(self) -> int:
        return len(self._records)

    def save_record(self, record: WaterQualityRecord) -> None:
        self._records[record.id] = record

    def save_records(self, records: list[WaterQualityRecord]) -> None:
        for record in records:
            self.save_record(record)

    def save_station(self, station: Station) -> None:
        self._stations.upsert(station)

    def save_stations(self, stations: list[Station]) -> None:
        for station in stations:
            self.save_station(station)

    def get_record(self, record_id: UUID) -> WaterQualityRecord | None:
        return self._records.get(record_id)

    def all_records(self, *, include_unmatched: bool = False) -> list[WaterQualityRecord]:
        items = list(self._records.values())
        if include_unmatched:
            return items
        return [item for item in items if item.displayable]

    def find_by_hash(self, content_hash: str) -> WaterQualityRecord | None:
        for record in self._records.values():
            if record.content_hash == content_hash:
                return record
        return None

    def list_stations(self) -> list[Station]:
        return self._stations.list()

    def station_registry(self) -> StationRegistry:
        return self._stations

    def recent_records(self, limit: int = 12) -> list[WaterQualityRecord]:
        items = sorted(self._records.values(), key=lambda item: item.observed_at, reverse=True)
        return items[:limit]

    def records_for_map(self) -> list[WaterQualityRecord]:
        community = [item for item in self._records.values() if item.source.kind.value == "community"]
        paired_ids = {item.matched_station_id for item in community if item.matched_station_id}
        official_ids = {
            station.id
            for station in self.list_stations()
            if station_in_lower_mainland(station) and not station.id.startswith("DEMO-")
        }
        wanted = paired_ids | official_ids
        latest: dict[str, WaterQualityRecord] = {}
        for item in self._records.values():
            if item.source.kind.value != "government" or item.matched_station_id not in wanted:
                continue
            station_id = item.matched_station_id
            current = latest.get(station_id)
            if current is None or item.observed_at > current.observed_at:
                latest[station_id] = item
        return community + list(latest.values())

    def clear(self) -> None:
        self._records.clear()
        self._stations.clear()


class SqlRecordStore:
    """Postgres/SQLite record store. Nothing is kept in process memory between requests."""

    def __init__(self, url: str) -> None:
        normalized = normalize_database_url(url)
        connect_args = {"check_same_thread": False} if normalized.startswith("sqlite") else {}
        self.engine = create_engine(normalized, connect_args=connect_args)
        Base.metadata.create_all(self.engine)
        self._session = sessionmaker(bind=self.engine)
        self._ensure_columns()

    def _ensure_columns(self) -> None:
        inspector = inspect(self.engine)
        if "water_records" not in inspector.get_table_names():
            return
        cols = {column["name"] for column in inspector.get_columns("water_records")}
        dialect = self.engine.dialect.name
        alters: list[str] = []
        if "source_kind" not in cols:
            alters.append("ALTER TABLE water_records ADD COLUMN source_kind VARCHAR")
        if "matched_station_id" not in cols:
            alters.append("ALTER TABLE water_records ADD COLUMN matched_station_id VARCHAR")
        if "observed_at" not in cols:
            if dialect == "postgresql":
                alters.append("ALTER TABLE water_records ADD COLUMN observed_at TIMESTAMP WITH TIME ZONE")
            else:
                alters.append("ALTER TABLE water_records ADD COLUMN observed_at TIMESTAMP")
        if "displayable" not in cols:
            if dialect == "postgresql":
                alters.append("ALTER TABLE water_records ADD COLUMN displayable BOOLEAN NOT NULL DEFAULT TRUE")
            else:
                alters.append("ALTER TABLE water_records ADD COLUMN displayable BOOLEAN DEFAULT 1 NOT NULL")
        if not alters:
            return
        with self.engine.begin() as connection:
            for statement in alters:
                connection.execute(text(statement))

    def reset_schema(self) -> None:
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def _row_from_record(self, record: WaterQualityRecord) -> RecordRow:
        return RecordRow(
            id=record.id,
            content_hash=record.content_hash,
            source_kind=record.source.kind.value,
            matched_station_id=record.matched_station_id,
            observed_at=record.observed_at,
            displayable=record.displayable,
            body=record.model_dump(mode="json"),
        )

    def count(self) -> int:
        with self._session() as session:
            return int(session.scalar(select(func.count()).select_from(RecordRow)) or 0)

    def save_record(self, record: WaterQualityRecord) -> None:
        with self._session() as session:
            session.merge(self._row_from_record(record))
            session.commit()

    def save_records(self, records: list[WaterQualityRecord]) -> None:
        with self._session() as session:
            for record in records:
                session.merge(self._row_from_record(record))
            session.commit()

    def save_station(self, station: Station) -> None:
        with self._session() as session:
            session.merge(
                StationRow(
                    id=station.id,
                    name=station.name,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    medium=station.medium,
                )
            )
            session.commit()

    def save_stations(self, stations: list[Station]) -> None:
        with self._session() as session:
            for station in stations:
                session.merge(
                    StationRow(
                        id=station.id,
                        name=station.name,
                        latitude=station.latitude,
                        longitude=station.longitude,
                        medium=station.medium,
                    )
                )
            session.commit()

    def get_record(self, record_id: UUID) -> WaterQualityRecord | None:
        with self._session() as session:
            row = session.get(RecordRow, record_id)
            if row is None:
                return None
            return WaterQualityRecord.model_validate(row.body)

    def all_records(self, *, include_unmatched: bool = False) -> list[WaterQualityRecord]:
        with self._session() as session:
            records = [WaterQualityRecord.model_validate(row.body) for row in session.scalars(select(RecordRow))]
        if include_unmatched:
            return records
        return [item for item in records if item.displayable]

    def find_by_hash(self, content_hash: str) -> WaterQualityRecord | None:
        with self._session() as session:
            row = session.scalar(select(RecordRow).where(RecordRow.content_hash == content_hash))
            if row is None:
                return None
            return WaterQualityRecord.model_validate(row.body)

    def list_stations(self) -> list[Station]:
        with self._session() as session:
            return [
                Station(
                    id=row.id,
                    name=row.name,
                    latitude=row.latitude,
                    longitude=row.longitude,
                    medium=row.medium,
                )
                for row in session.scalars(select(StationRow))
            ]

    def station_registry(self) -> StationRegistry:
        registry = StationRegistry()
        for station in self.list_stations():
            registry.upsert(station)
        return registry

    def recent_records(self, limit: int = 12) -> list[WaterQualityRecord]:
        with self._session() as session:
            rows = session.scalars(
                select(RecordRow).order_by(RecordRow.observed_at.desc()).limit(limit)
            )
            return [WaterQualityRecord.model_validate(row.body) for row in rows]

    def _latest_government_for_stations(self, station_ids: set[str]) -> list[WaterQualityRecord]:
        if not station_ids:
            return []
        with self._session() as session:
            query = select(RecordRow).where(
                RecordRow.source_kind == "government",
                RecordRow.matched_station_id.in_(station_ids),
            )
            if self.engine.dialect.name == "postgresql":
                rows = session.scalars(
                    query.distinct(RecordRow.matched_station_id).order_by(
                        RecordRow.matched_station_id,
                        RecordRow.observed_at.desc(),
                    )
                )
                return [WaterQualityRecord.model_validate(row.body) for row in rows]
            records = [WaterQualityRecord.model_validate(row.body) for row in session.scalars(query)]
        latest: dict[str, WaterQualityRecord] = {}
        for record in records:
            station_id = record.matched_station_id
            if not station_id:
                continue
            current = latest.get(station_id)
            if current is None or record.observed_at > current.observed_at:
                latest[station_id] = record
        return list(latest.values())

    def records_for_map(self) -> list[WaterQualityRecord]:
        with self._session() as session:
            community = [
                WaterQualityRecord.model_validate(row.body)
                for row in session.scalars(select(RecordRow).where(RecordRow.source_kind == "community"))
            ]
        paired_ids = {item.matched_station_id for item in community if item.matched_station_id}
        official_ids = {
            station.id
            for station in self.list_stations()
            if station_in_lower_mainland(station) and not station.id.startswith("DEMO-")
        }
        return community + self._latest_government_for_stations(paired_ids | official_ids)

    def clear(self) -> None:
        with self._session() as session:
            session.execute(delete(RecordRow))
            session.execute(delete(StationRow))
            session.commit()


def open_store(url: str | None) -> SqlRecordStore | None:
    if not url or not url.strip():
        return None
    return SqlRecordStore(url.strip())
