from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from app.models.parameters import CANONICAL_UNITS
from app.models.schemas import MapReading, MapSite, SourceKind, WaterQualityRecord
from app.services.anchors import transaction_url
from app.services.comparison import compare_records
from app.services.stations import Station

# Vancouver / Lower Mainland window used for official-only EMS markers.
LOWER_MAINLAND = (49.0, 49.45, -123.35, -122.70)


def station_in_lower_mainland(station: Station) -> bool:
    lat0, lat1, lon0, lon1 = LOWER_MAINLAND
    return lat0 <= station.latitude <= lat1 and lon0 <= station.longitude <= lon1


def _format(measurement) -> str:
    if measurement is None or measurement.value is None:
        return "—"
    value = measurement.value
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _proof(record: WaterQualityRecord | None, prefix: str) -> dict[str, object]:
    if record is None:
        return {
            f"{prefix}_record_id": None,
            f"{prefix}_hash": None,
            f"{prefix}_transaction_hash": None,
            f"{prefix}_transaction_url": None,
            f"{prefix}_anchor_status": None,
        }
    return {
        f"{prefix}_record_id": record.id,
        f"{prefix}_hash": record.content_hash,
        f"{prefix}_transaction_hash": record.blockchain.transaction_hash,
        f"{prefix}_transaction_url": transaction_url(record.blockchain),
        f"{prefix}_anchor_status": record.blockchain.status.value,
    }


def build_map_sites(
    records: Iterable[WaterQualityRecord],
    stations: Iterable[Station] | None = None,
) -> list[MapSite]:
    grouped: dict[str, dict[str, WaterQualityRecord]] = defaultdict(dict)
    latest_government: dict[str, WaterQualityRecord] = {}
    for record in records:
        if not record.displayable or not record.matched_station_id:
            continue
        kind = record.source.kind.value
        existing = grouped[record.matched_station_id].get(kind)
        if existing is None or record.observed_at > existing.observed_at:
            grouped[record.matched_station_id][kind] = record
        if kind == SourceKind.government.value:
            current = latest_government.get(record.matched_station_id)
            if current is None or record.observed_at > current.observed_at:
                latest_government[record.matched_station_id] = record

    sites: list[MapSite] = []
    paired_ids: set[str] = set()
    for station_id, pair in grouped.items():
        government = pair.get(SourceKind.government.value)
        community = pair.get(SourceKind.community.value)
        if government is None or community is None:
            continue
        paired_ids.add(station_id)
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
                kind="pair",
                matched_station_id=station_id,
                compared=community.observed_at.isoformat(),
                readings=readings,
                **_proof(community, "community"),
                **_proof(government, "government"),
            )
        )

    for station in stations or []:
        if station.id.startswith("DEMO-") or station.id in paired_ids:
            continue
        if not station_in_lower_mainland(station):
            continue
        government = latest_government.get(station.id)
        gov_by_field = {item.field: item for item in government.measurements} if government else {}
        readings = [
            MapReading(parameter=field, official=_format(gov_by_field.get(field)), community="—")
            for field in CANONICAL_UNITS
            if field in gov_by_field
        ]
        observed = government.observed_at.isoformat() if government else ""
        sites.append(
            MapSite(
                id=station.id,
                name=station.name or station.id,
                area=station.medium or "EMS",
                position=[station.latitude, station.longitude],
                status="official",
                kind="official",
                matched_station_id=station.id,
                compared=observed,
                readings=readings,
                **_proof(None, "community"),
                **_proof(government, "government"),
            )
        )
    return sites
