from __future__ import annotations

from pathlib import Path

import folium
import geopandas as gpd
import joblib
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

from src.features import build_features

try:
    import networkx as nx
    import osmnx as ox
except ImportError:  # pragma: no cover - optional dependency
    nx = None
    ox = None


def load_model(path: Path):
    if not path.exists():
        return None
    return joblib.load(path)


def load_fused_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def render_heatmap(df: pd.DataFrame, risk_col: str = "risk_score") -> folium.Map:
    if df.empty:
        return folium.Map(location=[0, 0], zoom_start=2)

    center = [df["latitude"].mean(), df["longitude"].mean()]
    fmap = folium.Map(location=center, zoom_start=12, tiles="cartodbpositron")

    heat_data = df[["latitude", "longitude", risk_col]].dropna().values.tolist()
    HeatMap(heat_data, radius=12, max_zoom=15).add_to(fmap)
    return fmap


def attach_risk_to_edges(G, risk_points: gpd.GeoDataFrame, risk_col: str = "risk_score"):
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True).reset_index()
    edges = edges.to_crs("EPSG:4326")
    try:
        joined = gpd.sjoin_nearest(
            edges,
            risk_points[[risk_col, "geometry"]],
            how="left",
        )
        edges[risk_col] = joined[risk_col].fillna(0)
    except Exception:
        edges[risk_col] = 0
    return edges


def safe_route(G, origin, destination, risk_points: gpd.GeoDataFrame):
    if nx is None or ox is None:
        return None

    origin_node = ox.distance.nearest_nodes(G, origin[1], origin[0])
    dest_node = ox.distance.nearest_nodes(G, destination[1], destination[0])

    edges = attach_risk_to_edges(G, risk_points)
    for _, row in edges.iterrows():
        G[row["u"]][row["v"]][0]["risk_score"] = float(row["risk_score"])
        G[row["u"]][row["v"]][0]["risk_weight"] = float(row["length"]) * (1 + float(row["risk_score"]))

    try:
        return nx.shortest_path(G, origin_node, dest_node, weight="risk_weight")
    except Exception:
        return nx.shortest_path(G, origin_node, dest_node, weight="length")


def main() -> None:
    st.set_page_config(page_title="SafePath", layout="wide")
    st.title("SafePath - Risk Heatmap and Safe Route")

    model_path = Path("models") / "risk_model.joblib"
    fused_path = Path("data") / "processed" / "fused.csv"

    model = load_model(model_path)
    data = load_fused_data(fused_path)

    if data.empty:
        st.warning("No fused data found. Run `python src/ingest.py` first.")
        return

    if model is None:
        st.warning("No trained model found. Run `python src/model.py` to train.")
        return

    X, _ = build_features(data)
    X = X.fillna(0)
    data["risk_score"] = model.predict_proba(X)[:, 1]

    st.subheader("Accident Risk Heatmap")
    fmap = render_heatmap(data)
    st_folium(fmap, width=900, height=600)

    st.subheader("Safe Route Planner (MVP)")
    if ox is None:
        st.info("Install osmnx to enable route planning.")
        return

    col1, col2 = st.columns(2)
    with col1:
        origin_lat = st.number_input("Origin latitude", value=float(data["latitude"].mean()))
        origin_lon = st.number_input("Origin longitude", value=float(data["longitude"].mean()))
    with col2:
        dest_lat = st.number_input("Destination latitude", value=float(data["latitude"].mean()))
        dest_lon = st.number_input("Destination longitude", value=float(data["longitude"].mean()))

    if st.button("Compute Safe Route"):
        center = (origin_lat, origin_lon)
        G = ox.graph_from_point(center, dist=3000, network_type="drive")
        risk_points = gpd.GeoDataFrame(
            data,
            geometry=gpd.points_from_xy(data["longitude"], data["latitude"]),
            crs="EPSG:4326",
        )
        path = safe_route(G, (origin_lat, origin_lon), (dest_lat, dest_lon), risk_points)
        if path is None:
            st.error("Route planning is unavailable. Install networkx/osmnx.")
            return

        route_fmap = folium.Map(location=[origin_lat, origin_lon], zoom_start=13, tiles="cartodbpositron")
        route = ox.plot_route_folium(G, path, route_map=route_fmap, color="#2f6fed", weight=5)
        st_folium(route, width=900, height=600)


if __name__ == "__main__":
    main()
