from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import requests

USER_AGENT = "MyDrive/1.0 (Chicagoland navigation)"
OSRM_BASE = os.environ.get("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
MAPBOX_DIRECTIONS = "https://api.mapbox.com/directions/v5/mapbox/driving"


def _fmt_distance(meters: float) -> str:
    mi = meters / 1609.34
    if mi < 0.1:
        return f"{int(meters)} m"
    return f"{mi:.1f} mi"


def _fmt_duration(seconds: float) -> str:
    s = int(max(0, seconds))
    if s < 60:
        return f"{s} sec"
    mins = s // 60
    if mins < 60:
        return f"{mins} min"
    h, m = divmod(mins, 60)
    return f"{h} hr {m} min"


def _clean_instruction(raw: str, maneuver: str) -> str:
    text = (raw or "").strip()
    if text:
        return text
    defaults = {
        "depart": "Head out",
        "arrive": "You have arrived",
        "turn": "Turn",
        "new name": "Continue",
        "merge": "Merge",
        "on ramp": "Take the ramp",
        "off ramp": "Take the exit",
        "fork": "Keep left or right at the fork",
        "end of road": "Turn at the end of the road",
        "continue": "Continue straight",
        "roundabout": "Enter the roundabout",
        "rotary": "Enter the rotary",
        "roundabout turn": "Exit the roundabout",
    }
    for key, msg in defaults.items():
        if key in (maneuver or "").lower():
            return msg
    return "Continue on route"


def _geojson_to_latlon(coords: list[list[float]]) -> list[list[float]]:
    """GeoJSON positions are [lon, lat] → [lat, lon] for Leaflet."""
    return [[float(c[1]), float(c[0])] for c in coords if len(c) >= 2]


def _parse_osrm(data: dict[str, Any]) -> dict[str, Any] | None:
    routes = data.get("routes") or []
    if not routes:
        return None
    route = routes[0]
    legs = route.get("legs") or []
    steps_out: list[dict[str, Any]] = []
    geometry: list[list[float]] = []

    geom = route.get("geometry") or {}
    if geom.get("type") == "LineString":
        geometry = _geojson_to_latlon(geom.get("coordinates") or [])

    for leg in legs:
        for step in leg.get("steps") or []:
            maneuver = step.get("maneuver") or {}
            loc = maneuver.get("location") or []
            lat = float(loc[1]) if len(loc) >= 2 else 0.0
            lon = float(loc[0]) if len(loc) >= 2 else 0.0
            mtype = maneuver.get("type") or ""
            modifier = maneuver.get("modifier") or ""
            name = step.get("name") or ""
            instr = _clean_instruction(
                maneuver.get("instruction") or f"{mtype} {modifier} {name}".strip(),
                f"{mtype} {modifier}",
            )
            steps_out.append(
                {
                    "instruction": instr,
                    "name": name,
                    "distance_m": round(float(step.get("distance") or 0)),
                    "duration_s": round(float(step.get("duration") or 0)),
                    "distance_display": _fmt_distance(float(step.get("distance") or 0)),
                    "duration_display": _fmt_duration(float(step.get("duration") or 0)),
                    "maneuver": f"{mtype}-{modifier}".strip("-"),
                    "location": [lat, lon],
                }
            )

    dist = float(route.get("distance") or 0)
    dur = float(route.get("duration") or 0)
    return {
        "provider": "osrm",
        "distance_m": round(dist),
        "duration_s": round(dur),
        "distance_display": _fmt_distance(dist),
        "duration_display": _fmt_duration(dur),
        "geometry": geometry,
        "steps": steps_out,
    }


def _parse_mapbox(data: dict[str, Any]) -> dict[str, Any] | None:
    routes = data.get("routes") or []
    if not routes:
        return None
    route = routes[0]
    legs = route.get("legs") or []
    steps_out: list[dict[str, Any]] = []
    geometry = _geojson_to_latlon((route.get("geometry") or {}).get("coordinates") or [])

    for leg in legs:
        for step in leg.get("steps") or []:
            maneuver = step.get("maneuver") or {}
            loc = maneuver.get("location") or []
            lat = float(loc[1]) if len(loc) >= 2 else 0.0
            lon = float(loc[0]) if len(loc) >= 2 else 0.0
            mtype = maneuver.get("type") or ""
            modifier = maneuver.get("modifier") or ""
            raw_instr = maneuver.get("instruction") or ""
            steps_out.append(
                {
                    "instruction": _clean_instruction(raw_instr, f"{mtype} {modifier}"),
                    "name": step.get("name") or "",
                    "distance_m": round(float(step.get("distance") or 0)),
                    "duration_s": round(float(step.get("duration") or 0)),
                    "distance_display": _fmt_distance(float(step.get("distance") or 0)),
                    "duration_display": _fmt_duration(float(step.get("duration") or 0)),
                    "maneuver": f"{mtype}-{modifier}".strip("-"),
                    "location": [lat, lon],
                }
            )

    dist = float(route.get("distance") or 0)
    dur = float(route.get("duration") or 0)
    return {
        "provider": "mapbox",
        "distance_m": round(dist),
        "duration_s": round(dur),
        "distance_display": _fmt_distance(dist),
        "duration_display": _fmt_duration(dur),
        "geometry": geometry,
        "steps": steps_out,
    }


def _sample_polyline(points: list[list[float]], max_points: int = 25) -> list[list[float]]:
    """Down-sample [lat, lon] points for OSRM waypoint routing."""
    if len(points) <= max_points:
        return points
    if len(points) < 2:
        return points
    stride = (len(points) - 1) / (max_points - 1)
    return [points[int(round(i * stride))] for i in range(max_points)]


def _fetch_osrm_waypoints(waypoints: list[list[float]]) -> dict[str, Any] | None:
    """Route through [lat, lon] waypoints (max ~25)."""
    if len(waypoints) < 2:
        return None
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in waypoints)
    url = f"{OSRM_BASE}/route/v1/driving/{coord_str}"
    params = {"steps": "true", "geometries": "geojson", "overview": "full"}
    try:
        r = requests.get(
            url,
            params=params,
            timeout=15,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != "Ok":
            return None
        return _parse_osrm(data)
    except Exception:
        return None


def _fetch_osrm(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> dict[str, Any] | None:
    return _fetch_osrm_waypoints(
        [[origin_lat, origin_lon], [dest_lat, dest_lon]],
    )


def _fetch_mapbox_waypoints(
    waypoints: list[list[float]],
    token: str,
) -> dict[str, Any] | None:
    if len(waypoints) < 2:
        return None
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in waypoints)
    url = f"{MAPBOX_DIRECTIONS}/{quote(coord_str, safe=';,')}"
    params = {
        "access_token": token,
        "steps": "true",
        "geometries": "geojson",
        "overview": "full",
        "language": "en",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return _parse_mapbox(r.json())
    except Exception:
        return None


def _fetch_mapbox(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    token: str,
) -> dict[str, Any] | None:
    return _fetch_mapbox_waypoints(
        [[origin_lat, origin_lon], [dest_lat, dest_lon]],
        token,
    )


def get_geo_providers_status() -> dict[str, Any]:
    token = os.environ.get("MAPBOX_ACCESS_TOKEN", "").strip()
    return {
        "autocomplete": {
            "photon": True,
            "nominatim": True,
            "mapbox": bool(token),
        },
        "navigation": {
            "osrm": True,
            "mapbox": bool(token),
        },
        "mapbox_configured": bool(token),
    }


def get_turn_by_turn_directions(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    *,
    provider: str = "auto",
    polyline: list[list[float]] | None = None,
    route_label: str | None = None,
) -> dict[str, Any]:
    """
    Turn-by-turn driving directions (Google Maps–style steps).
    auto: Mapbox if token set, else OSRM.
    If polyline is provided (MyDrive compare route), steps follow that path via waypoints.
    """
    token = os.environ.get("MAPBOX_ACCESS_TOKEN", "").strip()
    result: dict[str, Any] | None = None

    waypoints: list[list[float]] | None = None
    mydrive_line: list[list[float]] | None = None
    if polyline and len(polyline) >= 2:
        mydrive_line = [[float(p[0]), float(p[1])] for p in polyline if len(p) >= 2]
        if len(mydrive_line) >= 2:
            sampled = _sample_polyline(mydrive_line, max_points=25)
            sampled[0] = [origin_lat, origin_lon]
            sampled[-1] = [dest_lat, dest_lon]
            waypoints = sampled

    if waypoints and len(waypoints) >= 2:
        if provider in ("auto", "mapbox") and token:
            result = _fetch_mapbox_waypoints(waypoints, token)
        if result is None and provider in ("auto", "osrm"):
            result = _fetch_osrm_waypoints(waypoints)
    else:
        if provider in ("auto", "mapbox") and token:
            result = _fetch_mapbox(origin_lat, origin_lon, dest_lat, dest_lon, token)
        if result is None and provider in ("auto", "osrm"):
            result = _fetch_osrm(origin_lat, origin_lon, dest_lat, dest_lon)

    if result is None:
        raise ValueError(
            "Could not load driving directions. Try again or use Google/Apple Maps handoff."
        )

    if mydrive_line:
        result["geometry"] = mydrive_line
        result["geometry_source"] = "mydrive"
    if route_label:
        result["route_label"] = route_label

    result["origin"] = {"lat": origin_lat, "lon": origin_lon}
    result["destination"] = {"lat": dest_lat, "lon": dest_lon}
    return result
