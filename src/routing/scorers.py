from __future__ import annotations

from typing import Any

import geopandas as gpd

from src.routing.geo_utils import CHICAGO_UTM
from src.routing.osm_tags import first_str, parse_maxspeed_kph
from src.routing.tolls import estimate_edge_toll_usd, load_toll_config

try:
    import osmnx as ox
except ImportError:  # pragma: no cover
    ox = None

DEFAULT_SPEED_KPH = 50.0

STRESS_BY_HIGHWAY: dict[str, float] = {
    "motorway": 1.0,
    "motorway_link": 0.95,
    "trunk": 0.9,
    "trunk_link": 0.85,
    "primary": 0.7,
    "primary_link": 0.65,
    "secondary": 0.5,
    "secondary_link": 0.45,
    "tertiary": 0.35,
    "residential": 0.15,
    "living_street": 0.1,
    "unclassified": 0.3,
}

RELIABILITY_BY_HIGHWAY: dict[str, float] = {
    "motorway": 0.85,
    "motorway_link": 0.8,
    "trunk": 0.75,
    "trunk_link": 0.7,
    "primary": 0.55,
    "secondary": 0.4,
    "tertiary": 0.3,
    "residential": 0.2,
    "living_street": 0.15,
    "unclassified": 0.35,
}


def highway_stress(data: dict[str, Any]) -> float:
    hw = first_str(data.get("highway", "unclassified")).lower()
    return STRESS_BY_HIGHWAY.get(hw, 0.4)


def highway_reliability_variance(data: dict[str, Any]) -> float:
    hw = first_str(data.get("highway", "unclassified")).lower()
    return RELIABILITY_BY_HIGHWAY.get(hw, 0.4)


def edge_time_minutes(length_m: float, speed_kph: float) -> float:
    speed_kph = max(speed_kph, 5.0)
    return (length_m / 1000.0) / speed_kph * 60.0


def attach_risk_to_edges(
    G: Any,
    risk_points: gpd.GeoDataFrame,
    risk_col: str = "risk_score",
) -> gpd.GeoDataFrame:
    if ox is None:
        raise ImportError("osmnx is required for routing.")

    edges = ox.graph_to_gdfs(G, nodes=False, edges=True).reset_index()
    edges = edges.to_crs(CHICAGO_UTM)
    points = risk_points[[risk_col, "geometry"]].to_crs(CHICAGO_UTM)
    try:
        joined = gpd.sjoin_nearest(edges, points, how="left")
        edges[risk_col] = joined[risk_col].fillna(0.0)
    except Exception:
        edges[risk_col] = 0.0
    return edges


def attach_edge_scores(
    G: Any,
    risk_points: gpd.GeoDataFrame | None = None,
    risk_col: str = "risk_score",
    toll_config: dict | None = None,
    risk_multiplier: float = 1.0,
) -> Any:
    """Annotate each graph edge with decomposed costs used by multi-objective routing."""
    toll_config = toll_config or load_toll_config()
    risk_lookup: dict[tuple[int, int, int], float] = {}
    if risk_points is not None and not risk_points.empty and ox is not None:
        edges = attach_risk_to_edges(G, risk_points, risk_col=risk_col)
        for _, row in edges.iterrows():
            key = (int(row["u"]), int(row["v"]), int(row.get("key", 0)))
            risk_lookup[key] = float(row[risk_col])

    for u, v, key, data in G.edges(keys=True, data=True):
        length_m = float(data.get("length", 1.0))
        length_km = length_m / 1000.0
        speed_kph = parse_maxspeed_kph(data.get("maxspeed")) or DEFAULT_SPEED_KPH

        time_min = edge_time_minutes(length_m, speed_kph)
        toll_usd = estimate_edge_toll_usd(data, length_m, toll_config)
        stress = highway_stress(data)
        reliability_var = highway_reliability_variance(data)
        risk = risk_lookup.get((u, v, key), 0.0)
        risk = float(risk) * float(max(0.0, risk_multiplier))

        data["time_min"] = time_min
        data["toll_usd"] = toll_usd
        data["stress_unit"] = stress
        data["reliability_var"] = reliability_var
        data["risk_score"] = risk
        data["risk_multiplier"] = float(risk_multiplier)
        data["stress_cost"] = stress * length_km
        data["reliability_cost"] = reliability_var * length_km
        data["risk_cost"] = risk * length_km
        data.setdefault("parking_penalty", 0.0)
        data.setdefault("parking_cost", 0.0)

    return G
