from datetime import datetime, timezone

from app.services.dates import parse_observed_at, series_offset_to_end_year, shift_to_end_year


def test_series_offset_moves_latest_observation_into_target_year() -> None:
    first = datetime(2019, 6, 5, 17, 0, tzinfo=timezone.utc)
    last = datetime(2019, 12, 11, 17, 0, tzinfo=timezone.utc)
    offset = series_offset_to_end_year([first, last], end_year=2025)
    shifted_last = last + offset
    shifted_first = first + offset
    assert shifted_last.year == 2025
    assert shifted_last.month == 12
    assert shifted_last.day == 11
    assert shifted_first.year == 2025
    assert shifted_first.month == 6
    assert shifted_first.day == 5


def test_shift_to_end_year_preserves_spacing_when_source_is_ahead() -> None:
    first = datetime(2024, 12, 31, 12, 0)
    last = datetime(2026, 8, 18, 11, 19)
    shifted = shift_to_end_year([first, last], end_year=2025)
    assert shifted[-1].year == 2025
    assert shifted[-1].month == 8
    assert shifted[-1].day == 18
    assert (shifted[-1] - shifted[0]) == (last - first)


def test_parse_observed_at_accepts_community_date_time_timezone() -> None:
    observed = parse_observed_at(
        {"Date": "2019-06-05", "Time": "17:00", "Timezone": "-07:00"}
    )
    assert observed.isoformat() == "2019-06-05T17:00:00-07:00"


def test_parse_observed_at_accepts_ems_clock_range() -> None:
    observed = parse_observed_at({"Observed_Date_Time": "2026-05-07T10:30-10:35"})
    assert observed.year == 2026
    assert observed.month == 5
    assert observed.day == 7
    assert observed.hour == 10
    assert observed.minute == 30
