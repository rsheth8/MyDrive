from __future__ import annotations

import math

# UTM zone 16N — appropriate for Chicagoland distance/geometry ops
CHICAGO_UTM = "EPSG:32616"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def trip_bbox(
    origin: tuple[float, float],
    destination: tuple[float, float],
    buffer_km: float = 2.0,
) -> tuple[float, float, float, float]:
    """Return (west, south, east, north) with padding for OSMnx."""
    pad_deg = max(buffer_km / 111.0, 0.015)
    north = max(origin[0], destination[0]) + pad_deg
    south = min(origin[0], destination[0]) - pad_deg
    east = max(origin[1], destination[1]) + pad_deg
    west = min(origin[1], destination[1]) - pad_deg
    return west, south, east, north


def route_looks_complete(path_km: float, origin: tuple[float, float], destination: tuple[float, float]) -> bool:
    """Heuristic: path should be at least ~85% of straight-line distance."""
    straight_km = haversine_km(origin[0], origin[1], destination[0], destination[1])
    if straight_km < 1.0:
        return path_km >= straight_km * 0.5
    return path_km >= straight_km * 0.85
