from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000
MATCH_THRESHOLD_M = 50.0


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    latitude: float
    longitude: float
    medium: str | None = None


@dataclass(frozen=True)
class MatchResult:
    station: Station
    distance_m: float


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    chord = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(chord))


class StationRegistry:
    def __init__(self) -> None:
        self._stations: dict[str, Station] = {}

    def upsert(self, station: Station) -> Station:
        self._stations[station.id] = station
        return station

    def list(self) -> list[Station]:
        return list(self._stations.values())

    def get(self, station_id: str) -> Station | None:
        return self._stations.get(station_id)

    def clear(self) -> None:
        self._stations.clear()

    def match(self, latitude: float, longitude: float) -> MatchResult | None:
        nearest: MatchResult | None = None
        for station in self._stations.values():
            distance = haversine_m(latitude, longitude, station.latitude, station.longitude)
            if nearest is None or distance < nearest.distance_m:
                nearest = MatchResult(station=station, distance_m=distance)
        if nearest is None or nearest.distance_m > MATCH_THRESHOLD_M:
            return None
        return nearest
