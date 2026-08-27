from __future__ import annotations

from typing import Any

from app.adapters.base import WaterDataSourceAdapter
from app.models.parameters import CANONICAL_UNITS, canonical_field_for_community_column, parse_measurement_value
from app.models.schemas import Location, Measurement, SourceKind, SourceProvenance, WaterQualityRecordCreate
from app.services.dates import parse_observed_at

SKIP_COLUMNS = {
    "site",
    "station",
    "station_id",
    "name",
    "location name",
    "location_name",
    "latitude",
    "lat",
    "longitude",
    "lon",
    "observed_at",
    "datetime",
    "date",
    "time",
    "timezone",
    "medium",
    "collection_method",
    "method",
    "observation id",
    "organization",
    "dataset",
    "body of water",
    "region",
    "country",
    "water body type",
    "number of readings",
    "owner name",
    "added at",
    "form",
    "notes",
    "qa status",
    "qa notes",
}


def _first(payload: dict[str, Any], *keys: str) -> Any:
    lowered = {str(key).strip().lower(): value for key, value in payload.items()}
    for key in keys:
        if key in lowered and lowered[key] not in (None, ""):
            return lowered[key]
    return None


class CommunityDataAdapter(WaterDataSourceAdapter):
    """Translate a wide community sample row into a canonical record."""

    def normalize(self, payload: dict[str, Any]) -> WaterQualityRecordCreate:
        observed_at = parse_observed_at(payload)
        site = str(
            _first(payload, "site", "station", "station_id", "name", "location name", "location_name")
            or "community site"
        ).strip()
        latitude = float(_first(payload, "latitude", "lat", "location_latitude"))
        longitude = float(_first(payload, "longitude", "lon", "location_longitude"))

        measurements: list[Measurement] = []
        seen: set[str] = set()
        for column, raw_value in payload.items():
            if str(column).strip().lower() in SKIP_COLUMNS:
                continue
            field = canonical_field_for_community_column(str(column))
            if field is None or field in seen:
                continue
            if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
                continue
            seen.add(field)
            measurements.append(
                Measurement(
                    field=field,
                    value=parse_measurement_value(raw_value),
                    unit=CANONICAL_UNITS.get(field),
                    raw_value=raw_value,
                )
            )

        return WaterQualityRecordCreate(
            source=SourceProvenance(
                kind=SourceKind.community,
                provider="community-csv",
                dataset_id="dataset_download_5399",
                source_record_id=f"{site}-{observed_at.isoformat()}",
            ),
            observed_at=observed_at,
            location=Location(name=site, latitude=latitude, longitude=longitude),
            measurements=measurements,
            metadata={
                "medium": _first(payload, "medium"),
                "collection_method": _first(payload, "collection_method", "method"),
            },
            raw_payload=dict(payload),
        )
