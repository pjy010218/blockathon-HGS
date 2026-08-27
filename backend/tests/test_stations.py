from app.services.stations import Station, StationRegistry


NEAR = Station(
    id="E207969",
    name="False Creek inner",
    latitude=49.2710,
    longitude=-123.1220,
)


def test_match_within_50_metres() -> None:
    registry = StationRegistry()
    registry.upsert(NEAR)
    match = registry.match(49.2711, -123.1221)
    assert match is not None
    assert match.station.id == "E207969"
    assert match.distance_m <= 50


def test_unmatched_beyond_50_metres() -> None:
    registry = StationRegistry()
    registry.upsert(NEAR)
    # ~120 m north
    assert registry.match(49.2721, -123.1220) is None


def test_nearest_station_wins() -> None:
    registry = StationRegistry()
    registry.upsert(NEAR)
    registry.upsert(
        Station(id="E999999", name="Farther", latitude=49.2712, longitude=-123.1222)
    )
    match = registry.match(49.2710, -123.1220)
    assert match is not None
    assert match.station.id == "E207969"


def test_upsert_replaces_coordinates() -> None:
    registry = StationRegistry()
    registry.upsert(NEAR)
    registry.upsert(
        Station(id="E207969", name="Moved", latitude=49.2800, longitude=-123.1220)
    )
    stations = registry.list()
    assert len(stations) == 1
    assert stations[0].name == "Moved"
    assert stations[0].latitude == 49.2800
