from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.models.schemas import ComparisonField, Measurement, WaterQualityRecord


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
                and government_measurement.unit == community_measurement.unit
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
