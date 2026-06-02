from __future__ import annotations

from typing import Tuple

try:
    import osmnx as ox
except ImportError:  # pragma: no cover
    ox = None

Coord = Tuple[float, float]


def geocode_address(query: str, region_hint: str = "Chicagoland, IL") -> Coord | None:
    """Resolve a place name or address to (lat, lon)."""
    if ox is None or not query.strip():
        return None

    q = query.strip()
    if "chicago" not in q.lower() and "il" not in q.lower():
        q = f"{q}, {region_hint}"

    try:
        lat, lon = ox.geocode(q)
        return float(lat), float(lon)
    except Exception:
        return None
