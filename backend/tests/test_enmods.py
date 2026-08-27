from app.adapters.enmods import EnmodsAdapter


EVENT = {
    "Location_ID": "E207969",
    "Location_Name": "North Arm",
    "Location_Latitude": 49.271,
    "Location_Longitude": -123.122,
    "Observed_Date_Time": "2026-08-26T09:15:00-07:00",
    "Medium": "surface water",
    "observations": [
        {"Observed_Property_Name": "PH-F", "Result": 6.4, "Unit": "pH"},
        {"Observed_Property_Name": "0147", "Result": 240.0, "Unit": "CFU/100mL"},
        {"Observed_Property_Name": "UNMAPPED", "Result": 1, "Unit": "unknown"},
        {"Observed_Property_Name": "DO-F", "Result": "NOT_DETECTED", "Unit": "mg/L"},
    ],
}


def test_normalize_maps_shared_parameters_and_keeps_raw_event() -> None:
    record = EnmodsAdapter().normalize(EVENT)
    assert record.source.kind.value == "government"
    assert record.source.provider == "enmods"
    assert record.source.source_record_id == "E207969-2026-08-26T09:15:00-07:00-surface water"
    assert record.location.latitude == 49.271
    assert record.location.name == "North Arm"
    fields = {item.field: item for item in record.measurements}
    assert set(fields) == {"ph", "e_coli", "dissolved_oxygen"}
    assert fields["ph"].value == 6.4
    assert fields["e_coli"].value == 240.0
    assert fields["dissolved_oxygen"].value is None
    assert fields["dissolved_oxygen"].raw_value == "NOT_DETECTED"
    assert record.raw_payload["Location_ID"] == "E207969"
    assert record.metadata["medium"] == "surface water"


def test_unknown_parameters_are_not_invented_as_measurements() -> None:
    record = EnmodsAdapter().normalize(EVENT)
    assert all(item.field != "UNMAPPED" for item in record.measurements)


def test_medium_participates_in_ems_source_record_identity() -> None:
    freshwater = EnmodsAdapter().normalize(EVENT)
    marine_event = {**EVENT, "Medium": "marine"}
    marine = EnmodsAdapter().normalize(marine_event)

    assert freshwater.source.source_record_id != marine.source.source_record_id
