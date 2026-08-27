from __future__ import annotations

from app.data_pipeline.community import normalize_community_event, normalize_community_row
from app.data_pipeline.ems import normalize_ems_event, normalize_ems_row
from app.data_pipeline.grouping import group_community_rows, group_ems_rows
from app.data_pipeline.errors import DataNormalizationError


def test_community_wide_row_preserves_raw_data_and_maps_parameters() -> None:
    record = normalize_community_row({
        "site_name": "Creek",
        "latitude": "49.2",
        "longitude": "-123.1",
        "sampled_at": "2026-08-25T12:00:00Z",
        "ph (std_units, field)": "7.2",
        "oxygen (mg_l, field)": "NOT_DETECTED",
        "unmapped_note": "kept",
    }, row_number=4)
    assert {item.field for item in record.measurements} == {"ph", "dissolved_oxygen"}
    assert record.measurements[1].value == "NOT_DETECTED"
    assert record.raw_payload["unmapped_note"] == "kept"


def test_real_community_long_rows_are_combined_into_one_sample() -> None:
    rows = [
        {"DatasetName": "Community", "MonitoringLocationID": "site-1", "MonitoringLocationName": "Vanier Park", "MonitoringLocationLatitude": "49.278553", "MonitoringLocationLongitude": "-123.147244", "ReadingID": "reading-1", "ActivityMediaName": "Surface Water", "ActivityStartDate": "2019-12-12", "ActivityStartTime": "00:00:00", "CharacteristicName": "ph", "ResultValue": "7.57", "ResultUnit": "std_units", "MethodName": "test_strips_ph"},
        {"DatasetName": "Community", "MonitoringLocationID": "site-1", "MonitoringLocationName": "Vanier Park", "MonitoringLocationLatitude": "49.278553", "MonitoringLocationLongitude": "-123.147244", "ReadingID": "reading-2", "ActivityMediaName": "Surface Water", "ActivityStartDate": "2019-12-12", "ActivityStartTime": "00:00:00", "CharacteristicName": "oxygen", "ResultValue": "7.05", "ResultUnit": "mg_l", "MethodName": "multimeter_do"},
    ]
    record = normalize_community_event(rows)
    assert {item.field for item in record.measurements} == {"ph", "dissolved_oxygen"}
    assert record.source.dataset_id == "Community"
    assert len(record.raw_payload["rows"]) == 2


def test_community_grouping_uses_sampling_context() -> None:
    rows = [
        {"MonitoringLocationID": "A", "ActivityStartDate": "2020-01-01", "ActivityStartTime": "10:00:00", "ActivityMediaName": "Water"},
        {"MonitoringLocationID": "A", "ActivityStartDate": "2020-01-01", "ActivityStartTime": "10:00:00", "ActivityMediaName": "Water"},
        {"MonitoringLocationID": "A", "ActivityStartDate": "2020-01-02", "ActivityStartTime": "10:00:00", "ActivityMediaName": "Water"},
    ]
    assert [len(group) for group in group_community_rows(rows)] == [2, 1]


def test_ems_rows_are_grouped_and_normalized() -> None:
    rows = [
        {"Location_ID": "A", "Observed_Date_Time": "2026-08-25T12:00:00Z", "Medium": "Water", "Location_Latitude": 49.2, "Location_Longitude": -123.1, "Observed_Property_Name": "0004", "Observed_Value": "7.1"},
        {"Location_ID": "A", "Observed_Date_Time": "2026-08-25T12:00:00Z", "Medium": "Water", "Location_Latitude": 49.2, "Location_Longitude": -123.1, "Observed_Property_Name": "DO-F", "Observed_Value": "9.0"},
    ]
    event = normalize_ems_event(next(group_ems_rows(rows)))
    assert {item.field for item in event.measurements} == {"ph", "dissolved_oxygen"}


def test_ems_event_retains_unmapped_rows() -> None:
    rows = [
        {"Location_ID": "A", "Observed_Date_Time": "2026-08-25T12:00:00Z", "Medium": "Water", "Location_Latitude": 49.2, "Location_Longitude": -123.1, "Observed_Property_Name": "0004", "Observed_Value": "7.1"},
        {"Location_ID": "A", "Observed_Date_Time": "2026-08-25T12:00:00Z", "Medium": "Water", "Location_Latitude": 49.2, "Location_Longitude": -123.1, "Observed_Property_Name": "SR-D", "Observed_Value": "0.1"},
    ]
    event = normalize_ems_event(rows)
    assert len(event.measurements) == 1
    assert len(event.raw_payload["rows"]) == 2


def test_unknown_ems_parameter_is_skipped() -> None:
    assert normalize_ems_row({"Observed_Property_Name": "UNKNOWN", "Observed_Value": "1"}) is None


def test_ems_code_can_be_read_from_property_description() -> None:
    normalized = normalize_ems_row({
        "Observed_Property_Name": "unknown label",
        "Observed_Property_Description": "pH; EMS code: PH-F",
        "Result_Value": "7.2",
    })
    assert normalized is not None
    assert normalized["canonical"] == "ph"


def test_ems_temperature_uses_project_canonical_name() -> None:
    normalized = normalize_ems_row({
        "Observed_Property_Name": "TEMF",
        "Result_Value": "12.5",
    })
    assert normalized is not None
    assert normalized["canonical"] == "temperature"


def test_ems_not_detected_is_not_fabricated_as_zero() -> None:
    normalized = normalize_ems_row({
        "Observed_Property_Name": "PH-F",
        "Result_Value": "NOT_DETECTED",
    })
    assert normalized is not None
    assert normalized["value"] is None


def test_invalid_coordinate_is_rejected() -> None:
    try:
        normalize_community_row({"latitude": 95, "longitude": 0, "observed_at": "2026-08-25T12:00:00Z", "ph": 7})
    except DataNormalizationError as error:
        assert "latitude" in str(error)
    else:
        raise AssertionError("expected invalid coordinate error")
