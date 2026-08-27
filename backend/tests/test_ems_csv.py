from pathlib import Path

from app.services.ems_csv import grouped_ems_events


FIXTURES = Path(__file__).parent / "fixtures"


def test_grouped_ems_events_merges_shared_parameters_and_skips_unmapped() -> None:
    events = grouped_ems_events(FIXTURES / "ems_observations.csv")
    assert len(events) == 2
    first = next(event for event in events if event["Observed_Date_Time"].startswith("2026-07-20"))
    assert first["Location_ID"] == "E1"
    codes = {item["Observed_Property_Name"] for item in first["observations"]}
    assert codes == {"PH-F", "DO-F"}
    assert all(item["Result"] for item in first["observations"])
