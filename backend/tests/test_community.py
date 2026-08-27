from app.adapters.community import CommunityDataAdapter


WIDE_ROW = {
    "site": "Olympic Village",
    "latitude": "49.27237",
    "longitude": "-123.10345",
    "observed_at": "2019-06-05T17:00:00-07:00",
    "medium": "marine",
    "ph (std_units, field)": "8.01",
    "oxygen (mg_l, field)": "9.37",
    "e_coli (cfu_per_100ml, field)": "13.66",
    "Field_Visit_Participants": "kept in raw",
    "unmapped_extra": "yes",
}


def test_normalize_maps_wide_community_columns() -> None:
    record = CommunityDataAdapter().normalize(WIDE_ROW)
    assert record.source.kind.value == "community"
    assert record.location.name == "Olympic Village"
    assert record.location.latitude == 49.27237
    fields = {item.field: item for item in record.measurements}
    assert set(fields) == {"ph", "dissolved_oxygen", "e_coli"}
    assert fields["ph"].value == 8.01
    assert record.raw_payload["Field_Visit_Participants"] == "kept in raw"
    assert record.raw_payload["unmapped_extra"] == "yes"


def test_blank_community_values_are_omitted_not_zero() -> None:
    row = {**WIDE_ROW, "nitrites (mg_l, field)": "", "nitrates (mg_l, field)": "NOT_DETECTED"}
    record = CommunityDataAdapter().normalize(row)
    fields = {item.field: item for item in record.measurements}
    assert "nitrite" not in fields
    assert fields["nitrate"].value is None
    assert fields["nitrate"].raw_value == "NOT_DETECTED"


def test_normalize_reads_swim_drink_fish_date_columns() -> None:
    row = {
        "Location name": "Olympic Village ",
        "Latitude": "49.27237",
        "Longitude": "-123.10345",
        "Date": "2019-06-05",
        "Time": "17:00",
        "Timezone": "-07:00",
        "ph (std_units, api_saltwater_ph)": "8.01",
        "oxygen (mg_l, ysi_multimeter_do_mgl)": "9.37",
    }
    record = CommunityDataAdapter().normalize(row)
    assert record.location.name == "Olympic Village"
    assert record.observed_at.isoformat() == "2019-06-05T17:00:00-07:00"
    fields = {item.field: item for item in record.measurements}
    assert fields["ph"].value == 8.01
    assert record.raw_payload["Date"] == "2019-06-05"
