from __future__ import annotations

from typing import Any

import geopandas as gpd

from src.routing.geo_utils import CHICAGO_UTM, haversine_km

try:
    import osmnx as ox
except ImportError:  # pragma: no cover
    ox = None

PARKING_TAGS = {"amenity": "parking"}


def fetch_parking_near(
    point: tuple[float, float],
    dist_m: int = 800,
) -> gpd.GeoDataFrame:
    """Load OSM parking amenities near a lat/lon point."""
    if ox is None:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    try:
        gdf = ox.features_from_point(point, dist=dist_m, tags=PARKING_TAGS)
    except Exception:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    if gdf.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    gdf = gdf.reset_index(drop=True)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    else:
        gdf = gdf.to_crs("EPSG:4326")
    projected = gdf.to_crs(CHICAGO_UTM)
    gdf["geometry"] = projected.geometry.centroid.to_crs("EPSG:4326")
    return gdf


def edge_parking_penalty(
    edge_lat: float,
    edge_lon: float,
    dest: tuple[float, float],
    parking_gdf: gpd.GeoDataFrame,
    dest_radius_km: float = 1.5,
) -> float:
    """Penalty grows when an edge is near the destination but far from parking."""
    dist_dest_km = haversine_km(edge_lat, edge_lon, dest[0], dest[1])
    if dist_dest_km > dest_radius_km:
        return 0.0

    if parking_gdf.empty:
        return 1.0 * (1.0 - dist_dest_km / dest_radius_km)

    parking_lats = parking_gdf.geometry.y.values
    parking_lons = parking_gdf.geometry.x.values
    dists_km = [
        haversine_km(edge_lat, edge_lon, float(la), float(lo))
        for la, lo in zip(parking_lats, parking_lons)
    ]
    nearest_km = min(dists_km)
    return float(min(1.0, max(0.0, (nearest_km - 0.05) / 0.4)))


def attach_parking_penalties(
    G: Any,
    destination: tuple[float, float],
    parking_gdf: gpd.GeoDataFrame | None = None,
    search_radius_m: int = 800,
) -> gpd.GeoDataFrame:
    if ox is None:
        raise ImportError("osmnx is required for parking scoring.")

    if parking_gdf is None:
        parking_gdf = fetch_parking_near(destination, dist_m=search_radius_m)

    edges = ox.graph_to_gdfs(G, nodes=False, edges=True).reset_index()
    projected = edges.to_crs(CHICAGO_UTM)
    centroids = projected.geometry.centroid.to_crs("EPSG:4326")

    for idx, row in edges.iterrows():
        u, v, key = int(row["u"]), int(row["v"]), int(row.get("key", 0))
        c = centroids.iloc[idx]
        penalty = edge_parking_penalty(float(c.y), float(c.x), destination, parking_gdf)
        if G.has_edge(u, v, key):
            G[u][v][key]["parking_penalty"] = penalty
            length_km = float(G[u][v][key].get("length", 1.0)) / 1000.0
            G[u][v][key]["parking_cost"] = penalty * length_km
    return parking_gdf
