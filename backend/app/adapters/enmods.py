from __future__ import annotations

from datetime import datetime
from typing import Any

from app.adapters.base import WaterDataSourceAdapter
from app.models.parameters import CANONICAL_UNITS, UNDETECTED_TOKENS, canonical_field_for_ems_code
from app.models.schemas import Location, Measurement, SourceKind, SourceProvenance, WaterQualityRecordCreate


def _parse_result(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, str) and raw.strip().upper() in UNDETECTED_TOKENS:
        return None
    if isinstance(raw, (int, float, bool)):
        return raw
    text = str(raw).strip()
    if text.upper() in UNDETECTED_TOKENS:
        return None
    try:
        return float(text)
    except ValueError:
        return None


class EnmodsAdapter(WaterDataSourceAdapter):
    """Translate a grouped EMS event into a canonical government record.

    Unknown parameters are omitted from measurements. The full event stays in
    ``raw_payload`` so unmapped fields are not discarded.
    """

    def normalize(self, payload: dict[str, Any]) -> WaterQualityRecordCreate:
        location_id = str(payload["Location_ID"])
        observed_at = payload["Observed_Date_Time"]
        if isinstance(observed_at, str):
            observed_at_dt = datetime.fromisoformat(observed_at)
        else:
            observed_at_dt = observed_at

        measurements: list[Measurement] = []
        for observation in payload.get("observations") or []:
            code = str(observation.get("Observed_Property_Name") or "")
            field = canonical_field_for_ems_code(code)
            if field is None:
                continue
            raw_value = observation.get("Result")
            unit = observation.get("Unit") or CANONICAL_UNITS.get(field)
            measurements.append(
                Measurement(
                    field=field,
                    value=_parse_result(raw_value),
                    unit=unit,
                    raw_value=raw_value,
                )
            )

        if not measurements:
            raise ValueError("EMS event contains no supported water-quality measurements.")

        return WaterQualityRecordCreate(
            source=SourceProvenance(
                kind=SourceKind.government,
                provider="enmods",
                dataset_id="ems",
                source_record_id=(
                    f"{location_id}-{payload['Observed_Date_Time']}"
                    f"-{payload.get('Medium') or ''}"
                ),
            ),
            observed_at=observed_at_dt,
            location=Location(
                name=payload.get("Location_Name"),
                latitude=float(payload["Location_Latitude"]),
                longitude=float(payload["Location_Longitude"]),
            ),
            measurements=measurements,
            metadata={
                "medium": payload.get("Medium"),
                "location_id": location_id,
            },
            raw_payload=dict(payload),
        )
