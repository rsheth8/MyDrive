from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import networkx as nx

from src.routing.geo_utils import CHICAGO_UTM, haversine_km, route_looks_complete, trip_bbox
from src.routing.parking import attach_parking_penalties
from src.routing.scorers import attach_edge_scores

try:
    import osmnx as ox
except ImportError:  # pragma: no cover
    ox = None

_ROUTING_CACHE = Path(__file__).resolve().parents[2] / "cache"


@dataclass(frozen=True)
class RouteWeights:
    time: float = 1.0
    money: float = 0.0
    stress: float = 0.0
    risk: float = 0.0
    reliability: float = 0.0
    parking: float = 0.0

    def normalized(self) -> RouteWeights:
        total = (
            self.time + self.money + self.stress + self.risk + self.reliability + self.parking
        )
        if total <= 0:
            return RouteWeights(time=1.0)
        return RouteWeights(
            time=self.time / total,
            money=self.money / total,
            stress=self.stress / total,
            risk=self.risk / total,
            reliability=self.reliability / total,
            parking=self.parking / total,
        )


class RoutePreset(str, Enum):
    FASTEST = "fastest"
    CHEAPEST = "cheapest"
    CALM = "calm"
    SAFEST = "safest"
    RELIABLE = "reliable"
    BALANCED = "balanced"
    PARKING = "parking"


PRESET_LABELS: dict[RoutePreset, str] = {
    RoutePreset.FASTEST: "Fastest",
    RoutePreset.CHEAPEST: "Cheapest",
    RoutePreset.CALM: "Calm",
    RoutePreset.SAFEST: "Safest",
    RoutePreset.RELIABLE: "Most reliable",
    RoutePreset.BALANCED: "Smart balance",
    RoutePreset.PARKING: "Parking-friendly",
}

PRESET_WEIGHTS: dict[RoutePreset, RouteWeights] = {
    RoutePreset.FASTEST: RouteWeights(time=1.0),
    RoutePreset.CHEAPEST: RouteWeights(time=0.35, money=0.65),
    RoutePreset.CALM: RouteWeights(time=0.3, stress=0.7),
    RoutePreset.SAFEST: RouteWeights(time=0.3, risk=0.7),
    RoutePreset.RELIABLE: RouteWeights(time=0.35, reliability=0.65),
    RoutePreset.BALANCED: RouteWeights(
        time=0.3, money=0.15, stress=0.15, risk=0.15, reliability=0.15, parking=0.1
    ),
    RoutePreset.PARKING: RouteWeights(time=0.25, parking=0.75),
}

PRESET_COLORS: dict[RoutePreset, str] = {
    RoutePreset.FASTEST: "#2f6fed",
    RoutePreset.CHEAPEST: "#16a34a",
    RoutePreset.CALM: "#7c3aed",
    RoutePreset.SAFEST: "#ea580c",
    RoutePreset.RELIABLE: "#0891b2",
    RoutePreset.BALANCED: "#0f766e",
    RoutePreset.PARKING: "#db2777",
}


@dataclass
class RouteSummary:
    preset: RoutePreset
    label: str
    nodes: list[int]
    time_min: float
    toll_usd: float
    distance_km: float
    stress_index: float
    risk_exposure: float
    reliability_index: float
    parking_index: float
    live_toll_usd: float | None
    explanation: str
    color: str


def prepare_graph_weights(G: Any, weights: RouteWeights) -> None:
    w = weights.normalized()
    for _, _, _, data in G.edges(keys=True, data=True):
        data["composite_weight"] = (
            w.time * float(data.get("time_min", 0.0))
            + w.money * float(data.get("toll_usd", 0.0)) * 10.0
            + w.stress * float(data.get("stress_cost", 0.0)) * 5.0
            + w.risk * float(data.get("risk_cost", 0.0)) * 8.0
            + w.reliability * float(data.get("reliability_cost", 0.0)) * 5.0
            + w.parking * float(data.get("parking_cost", 0.0)) * 6.0
        )


def _path_edges(G: Any, path: list[int]) -> list[tuple[int, int, int, dict]]:
    edges: list[tuple[int, int, int, dict]] = []
    for u, v in zip(path[:-1], path[1:]):
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            continue
        key = min(
            edge_data,
            key=lambda k: edge_data[k].get("composite_weight", edge_data[k].get("length", 1.0)),
        )
        edges.append((u, v, key, edge_data[key]))
    return edges


def summarize_path(
    G: Any,
    path: list[int],
    preset: RoutePreset,
    live_toll_usd: float | None = None,
) -> RouteSummary:
    edges = _path_edges(G, path)
    time_min = sum(float(e[3].get("time_min", 0.0)) for e in edges)
    toll_usd = sum(float(e[3].get("toll_usd", 0.0)) for e in edges)
    distance_km = sum(float(e[3].get("length", 0.0)) for e in edges) / 1000.0
    stress_index = sum(float(e[3].get("stress_cost", 0.0)) for e in edges)
    risk_exposure = sum(float(e[3].get("risk_cost", 0.0)) for e in edges)
    reliability_index = sum(float(e[3].get("reliability_cost", 0.0)) for e in edges)
    parking_index = sum(float(e[3].get("parking_cost", 0.0)) for e in edges)

    explanation = _build_explanation(
        preset=preset,
        time_min=time_min,
        toll_usd=toll_usd,
        stress_index=stress_index,
        risk_exposure=risk_exposure,
        reliability_index=reliability_index,
        parking_index=parking_index,
    )

    return RouteSummary(
        preset=preset,
        label=PRESET_LABELS[preset],
        nodes=path,
        time_min=time_min,
        toll_usd=toll_usd,
        distance_km=distance_km,
        stress_index=stress_index,
        risk_exposure=risk_exposure,
        reliability_index=reliability_index,
        parking_index=parking_index,
        live_toll_usd=live_toll_usd,
        explanation=explanation,
        color=PRESET_COLORS[preset],
    )


def _build_explanation(
    preset: RoutePreset,
    time_min: float,
    toll_usd: float,
    stress_index: float,
    risk_exposure: float,
    reliability_index: float,
    parking_index: float = 0.0,
) -> str:
    if preset == RoutePreset.FASTEST:
        return "Optimizes drive time above all other factors."
    if preset == RoutePreset.CHEAPEST:
        if toll_usd > 0:
            return f"Avoids tolled segments where possible (~${toll_usd:.2f} estimated tolls on this path)."
        return "Minimizes estimated toll exposure; this path has no tagged toll segments."
    if preset == RoutePreset.CALM:
        return f"Prefers lower-stress roads (stress index {stress_index:.2f} km·weight)."
    if preset == RoutePreset.SAFEST:
        return f"Routes around higher predicted risk exposure ({risk_exposure:.2f} km·risk)."
    if preset == RoutePreset.RELIABLE:
        return f"Favors roads with lower ETA variance proxy ({reliability_index:.2f} km·weight)."
    if preset == RoutePreset.PARKING:
        return (
            f"Prioritizes destination access near parking "
            f"(parking index {parking_index:.2f} km·weight)."
        )
    return (
        f"Balances time ({time_min:.0f} min), tolls (${toll_usd:.2f}), "
        f"stress, risk, and reliability for everyday driving."
    )


def route_with_weights(
    G: Any,
    origin: tuple[float, float],
    destination: tuple[float, float],
    weights: RouteWeights,
) -> list[int]:
    if ox is None:
        raise ImportError("osmnx is required for routing.")

    origin_node = ox.distance.nearest_nodes(G, origin[1], origin[0])
    dest_node = ox.distance.nearest_nodes(G, destination[1], destination[0])
    prepare_graph_weights(G, weights)

    try:
        return nx.shortest_path(G, origin_node, dest_node, weight="composite_weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound, ValueError):
        return nx.shortest_path(G, origin_node, dest_node, weight="length")


def compare_presets(
    G: Any,
    origin: tuple[float, float],
    destination: tuple[float, float],
    presets: list[RoutePreset] | None = None,
    live_toll_usd: float | None = None,
) -> list[RouteSummary]:
    if presets is None:
        presets = list(RoutePreset)

    results: list[RouteSummary] = []
    for preset in presets:
        path = route_with_weights(G, origin, destination, PRESET_WEIGHTS[preset])
        results.append(summarize_path(G, path, preset, live_toll_usd=live_toll_usd))
    return results


def build_routing_graph(
    origin: tuple[float, float],
    destination: tuple[float, float],
    buffer_km: float = 2.0,
    risk_points: Any | None = None,
    parking_aware: bool = True,
    risk_multiplier: float = 1.0,
) -> Any:
    """
    Build a drive network that covers the full origin→destination trip.

    Uses a bounding box around both points (not a small circle at the origin).
    """
    if ox is None:
        raise ImportError("osmnx is required for routing.")

    _ROUTING_CACHE.mkdir(parents=True, exist_ok=True)
    ox.settings.cache_folder = str(_ROUTING_CACHE)
    ox.settings.use_cache = True

    west, south, east, north = trip_bbox(origin, destination, buffer_km=buffer_km)
    G = ox.graph_from_bbox(
        bbox=(west, south, east, north),
        network_type="drive",
        simplify=True,
    )
    G = attach_edge_scores(G, risk_points=risk_points, risk_multiplier=risk_multiplier)
    if parking_aware:
        attach_parking_penalties(G, destination)
    return G
