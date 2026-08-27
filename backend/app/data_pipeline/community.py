"""Conversion of community long-table rows into canonical records."""

from __future__ import annotations

from typing import Any

from app.data_pipeline.errors import DataNormalizationError
from app.data_pipeline.mapping import CANONICAL_UNITS, canonical_parameter_for_community_field
from app.data_pipeline.normalization import first_value, parse_coordinate, parse_datetime, parse_number
from app.models.schemas import Measurement, SourceKind, WaterQualityRecordCreate


def _source_value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for key, value in row.items():
        if key.strip().casefold() in {name.casefold() for name in names}:
            if value is not None and str(value).strip():
                return value
    return default


def _normalize_long_row(row: dict[str, Any], *, row_number: int | None = None) -> Measurement | None:
    canonical = canonical_parameter_for_community_field(_source_value(row, "CharacteristicName", "characteristic_name", default=""))
    if canonical is None:
        return None
    raw_value = _source_value(row, "ResultValue", "result_value", default=None)
    value = parse_number(raw_value, field="ResultValue")
    if value is None:
        return None
    return Measurement(
        field=canonical,
        value=value,
        unit=CANONICAL_UNITS[canonical],
        raw_value=raw_value,
        method=_source_value(row, "MethodName", "method_name", default=None),
    )


def normalize_community_event(rows: list[dict[str, Any]], *, row_number: int | None = None) -> WaterQualityRecordCreate:
    """Combine the parameter rows belonging to one community sample."""

    if not rows:
        raise DataNormalizationError("community event is empty")
    first = rows[0]
    measurements = [
        measurement
        for row in rows
        if (measurement := _normalize_long_row(row, row_number=row_number)) is not None
    ]
    if not measurements:
        raise DataNormalizationError("community event contains no supported measurements")
    observed_date = _source_value(first, "ActivityStartDate", "activity_start_date", "observed_at", default=None)
    observed_time = _source_value(first, "ActivityStartTime", "activity_start_time", default="00:00:00")
    observed_at = f"{observed_date}T{observed_time}" if observed_date and "T" not in str(observed_date) else observed_date
    return WaterQualityRecordCreate(
        source={
            "kind": SourceKind.community,
            "provider": str(_source_value(first, "DatasetName", "provider", "source", default="community")),
            "dataset_id": _source_value(first, "DatasetName", "dataset_id", "dataset", default=None),
            "source_record_id": _source_value(first, "ReadingID", "reading_id", "sample_id", default=None),
        },
        observed_at=parse_datetime(observed_at),
        location={
            "name": _source_value(first, "MonitoringLocationName", "location_name", "site_name", default=None),
            "latitude": parse_coordinate(_source_value(first, "MonitoringLocationLatitude", "latitude", "lat"), field="latitude", minimum=-90, maximum=90),
            "longitude": parse_coordinate(_source_value(first, "MonitoringLocationLongitude", "longitude", "lon"), field="longitude", minimum=-180, maximum=180),
        },
        measurements=measurements,
        metadata={
            "monitoring_location_id": _source_value(first, "MonitoringLocationID", default=None),
            "activity_media_name": _source_value(first, "ActivityMediaName", default=None),
            "result_value_type": _source_value(first, "ResultValueType", default=None),
        },
        raw_payload={"rows": [dict(row) for row in rows]},
    )


def normalize_community_row(row: dict[str, Any], *, row_number: int | None = None) -> WaterQualityRecordCreate:
    """Normalize one row, supporting the real long format and legacy wide rows."""

    if not row:
        raise DataNormalizationError("community row is empty")
    if _source_value(row, "CharacteristicName", "ResultValue", default=None) is not None:
        return normalize_community_event([row], row_number=row_number)
    latitude = _source_value(row, "latitude", "lat", "site_latitude")
    longitude = _source_value(row, "longitude", "lon", "lng", "site_longitude")
    measurements: list[Measurement] = []
    for field, raw_value in row.items():
        canonical = canonical_parameter_for_community_field(field)
        if canonical is None or raw_value is None or str(raw_value).strip() == "":
            continue
        value = parse_number(raw_value, field=field)
        if value is None:
            continue
        measurements.append(
            Measurement(
                field=canonical,
                value=value,
                unit=CANONICAL_UNITS[canonical],
                raw_value=raw_value,
            )
        )
    if not measurements:
        raise DataNormalizationError("community row contains no supported measurements")
    return WaterQualityRecordCreate(
        source={
            "kind": SourceKind.community,
            "provider": str(first_value(row, "provider", "source", default="community")),
            "dataset_id": _source_value(row, "dataset_id", "dataset", default=None),
            "source_record_id": _source_value(row, "source_record_id", "record_id", "sample_id", default=str(row_number) if row_number is not None else None),
        },
        observed_at=parse_datetime(_source_value(row, "observed_at", "observed_at_utc", "date", "datetime", "sampled_at")),
        location={
            "name": _source_value(row, "location_name", "site_name", "station_name", "name", default=None),
            "latitude": parse_coordinate(latitude, field="latitude", minimum=-90, maximum=90),
            "longitude": parse_coordinate(longitude, field="longitude", minimum=-180, maximum=180),
        },
        measurements=measurements,
        metadata={"row_number": row_number} if row_number is not None else {},
        raw_payload=dict(row),
    )
