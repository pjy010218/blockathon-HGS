from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from app.models.parameters import CANONICAL_UNITS
from app.models.schemas import MapReading, MapSite, SourceKind, WaterQualityRecord
from app.services.comparison import compare_records


def _format(measurement) -> str:
    if measurement is None or measurement.value is None:
        return "—"
    value = measurement.value
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def build_map_sites(records: Iterable[WaterQualityRecord]) -> list[MapSite]:
    grouped: dict[str, dict[str, WaterQualityRecord]] = defaultdict(dict)
    for record in records:
        if not record.displayable or not record.matched_station_id:
            continue
        kind = record.source.kind.value
        existing = grouped[record.matched_station_id].get(kind)
        if existing is None or record.observed_at > existing.observed_at:
            grouped[record.matched_station_id][kind] = record

    sites: list[MapSite] = []
    for station_id, pair in grouped.items():
        government = pair.get(SourceKind.government.value)
        community = pair.get(SourceKind.community.value)
        if government is None or community is None:
            continue
        fields = compare_records(government, community)
        status = (
            "review"
            if any(field.status == "different_value_or_unit" for field in fields)
            else "match"
        )
        gov_by_field = {item.field: item for item in government.measurements}
        community_by_field = {item.field: item for item in community.measurements}
        readings = [
            MapReading(
                parameter=field,
                official=_format(gov_by_field.get(field)),
                community=_format(community_by_field.get(field)),
            )
            for field in CANONICAL_UNITS
            if field in gov_by_field or field in community_by_field
        ]
        sites.append(
            MapSite(
                id=station_id,
                name=government.location.name or station_id,
                area=str(government.metadata.get("medium") or community.metadata.get("medium") or ""),
                position=[government.location.latitude, government.location.longitude],
                status=status,
                matched_station_id=station_id,
                compared=community.observed_at.isoformat(),
                readings=readings,
                community_record_id=community.id,
                government_record_id=government.id,
                community_hash=community.content_hash,
                government_hash=government.content_hash,
            )
        )
    return sites
