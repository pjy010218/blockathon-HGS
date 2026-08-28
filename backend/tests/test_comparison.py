from datetime import datetime, timezone

from app.models.schemas import Location, Measurement, SourceKind, SourceProvenance, WaterQualityRecord
from app.services.comparison import compare_records


def _record(kind: SourceKind, unit: str, value: float = 7.1) -> WaterQualityRecord:
    now = datetime(2026, 8, 28, tzinfo=timezone.utc)
    return WaterQualityRecord(
        source=SourceProvenance(kind=kind, provider="test"),
        observed_at=now,
        location=Location(name="PE233", latitude=49.1103, longitude=-123.148),
        measurements=[Measurement(field="ph", value=value, unit=unit)],
        ingested_at=now,
        content_hash="0" * 64,
    )


def test_ph_unit_aliases_with_same_value_are_a_match() -> None:
    fields = compare_records(
        _record(SourceKind.government, "pH units"),
        _record(SourceKind.community, "pH"),
    )
    assert fields[0].status == "same_value_and_unit"


def test_different_ph_values_still_need_review() -> None:
    fields = compare_records(
        _record(SourceKind.government, "pH units", 7.1),
        _record(SourceKind.community, "pH", 6.4),
    )
    assert fields[0].status == "different_value_or_unit"
