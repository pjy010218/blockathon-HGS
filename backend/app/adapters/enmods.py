from __future__ import annotations

from typing import Any

from app.adapters.base import WaterDataSourceAdapter
from app.models.parameters import CANONICAL_UNITS, canonical_field_for_ems_code, parse_measurement_value
from app.models.schemas import Location, Measurement, SourceKind, SourceProvenance, WaterQualityRecordCreate
from app.services.dates import parse_observed_at


class EnmodsAdapter(WaterDataSourceAdapter):
    """Translate a grouped EMS event into a canonical government record.

    Unknown parameters are omitted from measurements. The full event stays in
    ``raw_payload`` so unmapped fields are not discarded.
    """

    def normalize(self, payload: dict[str, Any]) -> WaterQualityRecordCreate:
        location_id = str(payload["Location_ID"])
        observed_at_dt = parse_observed_at(payload)

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
                    value=parse_measurement_value(raw_value),
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
