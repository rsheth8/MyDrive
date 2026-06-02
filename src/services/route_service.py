from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import joblib
import pandas as pd

from src.features import build_features
from src.geocode import geocode_address
from src.places import resolve_coordinates
from src.routing.geo_utils import route_looks_complete
from src.routing.multi_route import (
    RoutePreset,
    RouteSummary,
    RouteWeights,
    build_routing_graph,
    compare_presets,
    route_with_weights,
    summarize_path,
)
from src.risk_engine import build_weather_context, risk_multiplier
from src.ui_helpers import (
    PRESET_FRIENDLY,
    delta_vs_fastest,
    format_distance,
    format_minutes,
    format_tolls,
    help_for_summary,
    parking_label,
    safety_label,
    stress_label,
)

ROOT = Path(__file__).resolve().parents[2]
CHICAGO_CONFIG = ROOT / "config" / "chicago_places.json"
BRAND_CONFIG = ROOT / "config" / "brand.json"

PRIORITY_MAP: dict[str, RouteWeights] = {
    "fastest": RouteWeights(time=1.0),
    "cheapest": RouteWeights(time=0.35, money=0.65),
    "safest": RouteWeights(time=0.3, risk=0.7),
    "calm": RouteWeights(time=0.3, stress=0.7),
    "parking": RouteWeights(time=0.25, parking=0.75),
    "balanced": RouteWeights(
        time=0.3, money=0.15, stress=0.15, risk=0.15, reliability=0.15, parking=0.1
    ),
}


def load_chicago_config() -> dict:
    data = json.loads(CHICAGO_CONFIG.read_text())
    if BRAND_CONFIG.exists():
        data["brand"] = json.loads(BRAND_CONFIG.read_text())
    return data


def _load_risk_points() -> gpd.GeoDataFrame | None:
    fused_path = ROOT / "data" / "processed" / "fused.csv"
    model_path = ROOT / "models" / "risk_model.joblib"
    if not fused_path.exists() or not model_path.exists():
        return None
    data = pd.read_csv(fused_path)
    model = joblib.load(model_path)
    X, _ = build_features(data)
    X = X.fillna(0)
    data = data.copy()
    data["risk_score"] = model.predict_proba(X)[:, 1]
    return gpd.GeoDataFrame(
        data,
        geometry=gpd.points_from_xy(data["longitude"], data["latitude"]),
        crs="EPSG:4326",
    )


def _maps_urls(origin: tuple[float, float], destination: tuple[float, float]) -> dict[str, str]:
    o = f"{origin[0]},{origin[1]}"
    d = f"{destination[0]},{destination[1]}"
    return {
        "google": (
            f"https://www.google.com/maps/dir/?api=1&origin={o}&destination={d}&travelmode=driving"
        ),
        "apple": f"http://maps.apple.com/?saddr={o}&daddr={d}&dirflg=d",
    }


def _polyline_from_path(G: Any, nodes: list[int]) -> list[list[float]]:
    return [[float(G.nodes[n]["y"]), float(G.nodes[n]["x"])] for n in nodes]


def _summary_to_dict(
    G: Any,
    summary: RouteSummary,
    fastest: RouteSummary,
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> dict[str, Any]:
    info = help_for_summary(summary)
    preset_id = summary.preset.value if "Your pick" not in summary.label else "your_pick"
    return {
        "id": preset_id,
        "label": PRESET_FRIENDLY.get(summary.preset, summary.label)
        if "Your pick" not in summary.label
        else summary.label,
        "tagline": info["tagline"],
        "detail": info["detail"],
        "pick_when": info["pick_when"],
        "time_min": round(summary.time_min, 1),
        "time_display": format_minutes(summary.time_min),
        "tolls_display": format_tolls(summary.toll_usd),
        "distance_display": format_distance(summary.distance_km),
        "safety": safety_label(summary.risk_exposure),
        "feel": stress_label(summary.stress_index),
        "parking": parking_label(summary.parking_index),
        "vs_fastest": delta_vs_fastest(summary, fastest),
        "risk_exposure": round(float(summary.risk_exposure), 4),
        "polyline": _polyline_from_path(G, summary.nodes),
        "maps": _maps_urls(origin, destination),
    }


def compare_routes_for_trip(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    *,
    buffer_km: float = 2.0,
    priority: str = "balanced",
    include_your_pick: bool = True,
    depart_at_iso: str | None = None,
    precipitation: float | None = None,
    visibility: float | None = None,
    wind_speed: float | None = None,
    traffic_volume: float | None = None,
) -> dict[str, Any]:
    origin = (origin_lat, origin_lon)
    destination = (dest_lat, dest_lon)
    risk_points = _load_risk_points()

    depart_at = pd.to_datetime(depart_at_iso, errors="coerce") if depart_at_iso else pd.Timestamp.now()
    if pd.isna(depart_at):
        depart_at = pd.Timestamp.now()
    ctx = build_weather_context(
        depart_at=depart_at.to_pydatetime(),
        precipitation=precipitation,
        visibility=visibility,
        wind_speed=wind_speed,
        traffic_volume=traffic_volume,
    )
    mult, factors, summary = risk_multiplier(ctx)

    G = build_routing_graph(
        origin,
        destination,
        buffer_km=buffer_km,
        risk_points=risk_points,
        parking_aware=True,
        risk_multiplier=mult,
    )

    summaries = compare_presets(G, origin, destination)
    if include_your_pick:
        weights = PRIORITY_MAP.get(priority, PRIORITY_MAP["balanced"])
        path = route_with_weights(G, origin, destination, weights)
        custom = summarize_path(G, path, RoutePreset.BALANCED)
        custom = RouteSummary(
            preset=custom.preset,
            label="Your pick",
            nodes=custom.nodes,
            time_min=custom.time_min,
            toll_usd=custom.toll_usd,
            distance_km=custom.distance_km,
            stress_index=custom.stress_index,
            risk_exposure=custom.risk_exposure,
            reliability_index=custom.reliability_index,
            parking_index=custom.parking_index,
            live_toll_usd=None,
            explanation="",
            color="#111827",
        )
        summaries = summaries + [custom]

    fastest = next(s for s in summaries if s.preset == RoutePreset.FASTEST)
    routes = [_summary_to_dict(G, s, fastest, origin, destination) for s in summaries]

    return {
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": dest_lat, "lon": dest_lon},
        "maps": _maps_urls(origin, destination),
        "complete": route_looks_complete(fastest.distance_km, origin, destination),
        "routes": routes,
        "risk": {
            "depart_at": ctx.depart_at.isoformat(),
            "source": ctx.source,
            "precipitation": ctx.precipitation,
            "visibility": ctx.visibility,
            "wind_speed": ctx.wind_speed,
            "traffic_volume": ctx.traffic_volume,
            "multiplier": round(mult, 3),
            "summary": summary,
            "factors": factors,
        },
    }


def resolve_place(
    query: str,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, float] | None:
    return resolve_coordinates(query, lat=lat, lon=lon)
