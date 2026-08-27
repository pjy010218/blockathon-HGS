"""Conversion of EMS observations/events into canonical records."""

from __future__ import annotations

import re
from typing import Any, Iterable

from app.data_pipeline.errors import DataNormalizationError
from app.data_pipeline.mapping import CANONICAL_UNITS, canonical_parameter_for_ems_code
from app.data_pipeline.normalization import first_value, parse_coordinate, parse_datetime, parse_number
from app.models.schemas import Measurement, SourceKind, WaterQualityRecordCreate


def _measurement_value(row: dict[str, Any]) -> Any:
    return first_value(row, "Observed_Value", "Observation_Value", "Result_Value", "Result", "Value", "value")


def normalize_ems_row(row: dict[str, Any], *, row_number: int | None = None) -> dict[str, Any] | None:
    code = first_value(row, "Observed_Property_Name", "Observed_Property_Code", "Parameter_Code", "Parameter", "Code")
    canonical = canonical_parameter_for_ems_code(code)
    if canonical is None:
        description = first_value(row, "Observed_Property_Description", "Property_Description", default="")
        match = re.search(r"EMS code:\s*([A-Za-z0-9-]+)", str(description), flags=re.IGNORECASE)
        if match:
            canonical = canonical_parameter_for_ems_code(match.group(1))
    if canonical is None:
        return None
    parsed_value = parse_number(_measurement_value(row), field="observed value")
    if isinstance(parsed_value, str) and parsed_value.casefold() in {"not_detected", "not detected", "nd", "na", "n/a", "null"}:
        value: float | int | str | None = None
    else:
        value = parsed_value
    return {
        "canonical": canonical,
        "value": value,
        "unit": CANONICAL_UNITS[canonical],
        "raw": dict(row),
        "row_number": row_number,
    }


def normalize_ems_event(rows: Iterable[dict[str, Any]], *, row_number: int | None = None) -> WaterQualityRecordCreate:
    source_rows = list(rows)
    if not source_rows:
        raise DataNormalizationError("EMS event is empty")
    first = source_rows[0]
    normalized = [item for row in source_rows if (item := normalize_ems_row(row, row_number=row_number)) is not None]
    if not normalized:
        raise DataNormalizationError("EMS event contains no supported parameters")
    measurements = [
        Measurement(field=item["canonical"], value=item["value"], unit=item["unit"], raw_value=item["raw"])
        for item in normalized
    ]
    return WaterQualityRecordCreate(
        source={
            "kind": SourceKind.government,
            "provider": str(first_value(first, "provider", "Source", default="EnMoDS")),
            "dataset_id": first_value(first, "Dataset_ID", "Dataset_Id", "dataset_id", default=None),
            "source_record_id": first_value(first, "Event_ID", "Record_ID", "Observation_ID", default=None),
        },
        observed_at=parse_datetime(first_value(first, "Observed_Date_Time", "ObservedDateTime", "observed_at", "Date_Time")),
        location={
            "name": first_value(first, "Location_Name", "Station_Name", "location_name", default=None),
            "latitude": parse_coordinate(first_value(first, "Location_Latitude", "Latitude", "latitude"), field="latitude", minimum=-90, maximum=90),
            "longitude": parse_coordinate(first_value(first, "Location_Longitude", "Longitude", "longitude"), field="longitude", minimum=-180, maximum=180),
        },
        measurements=measurements,
        metadata={
            "location_id": first_value(first, "Location_ID", "Station_ID", "location_id", default=None),
            "medium": first_value(first, "Medium", "medium", default=None),
        },
        raw_payload={"rows": [dict(row) for row in source_rows]},
    )
