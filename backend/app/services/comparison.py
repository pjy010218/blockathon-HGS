from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.models.parameters import CANONICAL_UNITS
from app.models.schemas import ComparisonField, Measurement, WaterQualityRecord

# EMS reports pH as "pH units"; the community form uses the canonical "pH".
_UNIT_ALIASES = {
    "ph": "pH",
    "ph units": "pH",
    "std_units": "pH",
}


def _normalized_unit(field: str, unit: str | None) -> str | None:
    if unit is None or not str(unit).strip():
        return CANONICAL_UNITS.get(field)
    key = " ".join(str(unit).strip().lower().split())
    if key in _UNIT_ALIASES:
        return _UNIT_ALIASES[key]
    canonical = CANONICAL_UNITS.get(field)
    if canonical and key == canonical.strip().lower():
        return canonical
    return unit.strip()


def _units_match(field: str, left: str | None, right: str | None) -> bool:
    return _normalized_unit(field, left) == _normalized_unit(field, right)


def _by_field(measurements: Iterable[Measurement]) -> dict[str, list[Measurement]]:
    grouped: dict[str, list[Measurement]] = defaultdict(list)
    for measurement in measurements:
        grouped[measurement.field].append(measurement)
    return dict(grouped)


def compare_records(
    government: WaterQualityRecord, community: WaterQualityRecord
) -> list[ComparisonField]:
    government_fields = _by_field(government.measurements)
    community_fields = _by_field(community.measurements)

    result: list[ComparisonField] = []
    for field in sorted(set(government_fields) | set(community_fields)):
        government_measurements = government_fields.get(field, [])
        community_measurements = community_fields.get(field, [])
        occurrence_count = max(len(government_measurements), len(community_measurements))

        for index in range(occurrence_count):
            government_measurement = (
                government_measurements[index] if index < len(government_measurements) else None
            )
            community_measurement = (
                community_measurements[index] if index < len(community_measurements) else None
            )

            if government_measurement is None:
                status = "missing_from_government"
            elif community_measurement is None:
                status = "missing_from_community"
            elif (
                government_measurement.value == community_measurement.value
                and _units_match(field, government_measurement.unit, community_measurement.unit)
            ):
                status = "same_value_and_unit"
            else:
                status = "different_value_or_unit"

            display_field = field if occurrence_count == 1 else f"{field} [{index + 1}]"
            result.append(
                ComparisonField(
                    field=display_field,
                    government=government_measurement,
                    community=community_measurement,
                    status=status,
                )
            )
    return result
