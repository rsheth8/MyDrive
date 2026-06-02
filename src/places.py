from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from src.geocode import geocode_address

ROOT = Path(__file__).resolve().parents[1]
CHICAGO_CONFIG = ROOT / "config" / "chicago_places.json"

# Chicagoland metro (includes suburbs e.g. Vernon Hills, Naperville)
CHICAGO_CENTER = (41.8781, -87.6298)
# min_lon, min_lat, max_lon, max_lat
CHICAGO_BBOX = (-88.5, 41.3, -86.5, 42.6)

PHOTON_URL = "https://photon.komoot.io/api/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "MyDrive/1.0 (Chicagoland route app; local dev)"


@dataclass(frozen=True)
class PlaceSuggestion:
    id: str
    label: str
    subtitle: str
    lat: float
    lon: float
    source: str  # local | photon | nominatim | mapbox

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_presets() -> list[dict[str, Any]]:
    if not CHICAGO_CONFIG.exists():
        return []
    return json.loads(CHICAGO_CONFIG.read_text()).get("presets", [])


def _format_photon_feature(props: dict[str, Any], lon: float, lat: float) -> PlaceSuggestion | None:
    name = props.get("name") or props.get("street") or props.get("city")
    if not name:
        return None
    parts = [
        props.get("housenumber"),
        props.get("street"),
        props.get("city"),
        props.get("state"),
    ]
    subtitle = ", ".join(p for p in parts if p and p != name)
    if props.get("postcode") and props.get("postcode") not in (subtitle or ""):
        subtitle = f"{subtitle}, {props['postcode']}" if subtitle else props["postcode"]
    osm_id = props.get("osm_id") or props.get("osm_type", "")
    return PlaceSuggestion(
        id=f"photon-{osm_id}-{lat:.4f}-{lon:.4f}",
        label=str(name),
        subtitle=subtitle or "Chicagoland",
        lat=lat,
        lon=lon,
        source="photon",
    )


def _local_suggestions(query: str, limit: int) -> list[PlaceSuggestion]:
    q = query.strip().lower()
    if len(q) < 1:
        return []

    seen: set[str] = set()
    out: list[PlaceSuggestion] = []

    def add(
        place_id: str,
        label: str,
        subtitle: str,
        lat: float,
        lon: float,
    ) -> None:
        key = f"{label.lower()}|{lat:.3f}|{lon:.3f}"
        if key in seen:
            return
        if q not in label.lower() and q not in subtitle.lower():
            return
        seen.add(key)
        out.append(
            PlaceSuggestion(
                id=place_id,
                label=label,
                subtitle=subtitle,
                lat=lat,
                lon=lon,
                source="local",
            )
        )

    for preset in _load_presets():
        trip = preset.get("label", "")
        for suffix, label_key, addr_key, lat_key, lon_key in (
            ("from", "from_label", "from_address", "from_lat", "from_lon"),
            ("to", "to_label", "to_address", "to_lat", "to_lon"),
        ):
            label = preset.get(label_key, "")
            addr = preset.get(addr_key, "")
            lat = preset.get(lat_key)
            lon = preset.get(lon_key)
            if lat is None or lon is None:
                continue
            subtitle = f"{addr} · {trip}" if trip else addr
            add(f"local-{preset['id']}-{suffix}", label or addr, subtitle, float(lat), float(lon))

    return out[:limit]


@lru_cache(maxsize=256)
def _photon_search(query: str, limit: int) -> tuple[PlaceSuggestion, ...]:
    min_lon, min_lat, max_lon, max_lat = CHICAGO_BBOX
    params = {
        "q": query,
        "limit": limit,
        "lat": CHICAGO_CENTER[0],
        "lon": CHICAGO_CENTER[1],
        "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "lang": "en",
    }
    try:
        r = requests.get(PHOTON_URL, params=params, timeout=4, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        data = r.json()
    except Exception:
        return ()

    out: list[PlaceSuggestion] = []
    for feat in data.get("features", []):
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        props = feat.get("properties") or {}
        sug = _format_photon_feature(props, lon, lat)
        if sug:
            out.append(sug)
    return tuple(out)


@lru_cache(maxsize=128)
def _nominatim_search(query: str, limit: int) -> tuple[PlaceSuggestion, ...]:
    min_lon, min_lat, max_lon, max_lat = CHICAGO_BBOX
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "viewbox": f"{min_lon},{max_lat},{max_lon},{min_lat}",
        "bounded": 1,
        "countrycodes": "us",
        "addressdetails": 1,
    }
    try:
        r = requests.get(
            NOMINATIM_URL,
            params=params,
            timeout=5,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return ()

    out: list[PlaceSuggestion] = []
    for item in data:
        lat = float(item["lat"])
        lon = float(item["lon"])
        label = item.get("display_name", "").split(",")[0]
        subtitle = item.get("display_name", "")
        out.append(
            PlaceSuggestion(
                id=f"osm-{item.get('osm_id', '')}",
                label=label,
                subtitle=subtitle,
                lat=lat,
                lon=lon,
                source="nominatim",
            )
        )
    return tuple(out)


def _mapbox_search(query: str, limit: int) -> list[PlaceSuggestion]:
    token = os.environ.get("MAPBOX_ACCESS_TOKEN", "").strip()
    if not token:
        return []

    min_lon, min_lat, max_lon, max_lat = CHICAGO_BBOX
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(query)}.json"
    params = {
        "access_token": token,
        "autocomplete": "true",
        "limit": limit,
        "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "proximity": f"{CHICAGO_CENTER[1]},{CHICAGO_CENTER[0]}",
        "country": "US",
    }
    try:
        r = requests.get(url, params=params, timeout=4)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    out: list[PlaceSuggestion] = []
    for feat in data.get("features", []):
        center = feat.get("center") or []
        if len(center) < 2:
            continue
        lon, lat = float(center[0]), float(center[1])
        out.append(
            PlaceSuggestion(
                id=f"mapbox-{feat.get('id', '')}",
                label=feat.get("text") or feat.get("place_name", query),
                subtitle=feat.get("place_name", ""),
                lat=lat,
                lon=lon,
                source="mapbox",
            )
        )
    return out


def search_places(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Autocomplete suggestions biased to Chicagoland."""
    q = query.strip()
    if len(q) < 1:
        return []

    merged: list[PlaceSuggestion] = []
    seen: set[str] = set()

    def extend(items: list[PlaceSuggestion] | tuple[PlaceSuggestion, ...]) -> None:
        for item in items:
            key = f"{item.label.lower()}|{item.lat:.3f}|{item.lon:.3f}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= limit:
                break

    extend(_local_suggestions(q, limit))
    if len(merged) < limit and len(q) >= 2:
        extend(_mapbox_search(q, limit))
    if len(merged) < limit and len(q) >= 2:
        extend(_photon_search(q, limit))
    if len(merged) < limit and len(q) >= 3:
        extend(_nominatim_search(q, limit))

    return [s.to_dict() for s in merged[:limit]]


def resolve_coordinates(
    query: str,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, float] | None:
    """Resolve to lat/lon; use provided coords when user picked a suggestion."""
    if lat is not None and lon is not None:
        return {"lat": float(lat), "lon": float(lon)}
    if os.environ.get("MAPBOX_ACCESS_TOKEN", "").strip():
        hits = _mapbox_search(query, 1)
        if hits:
            return {"lat": hits[0].lat, "lon": hits[0].lon}
    coords = geocode_address(query)
    if coords is None:
        return None
    return {"lat": coords[0], "lon": coords[1]}
