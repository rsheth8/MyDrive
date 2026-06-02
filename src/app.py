from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import folium
import geopandas as gpd
import joblib
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

from src.brand import load_brand, page_title
from src.demo import ensure_demo_pipeline
from src.features import build_features
from src.geocode import geocode_address
from src.navigation import get_turn_by_turn_directions
from src.places_ui import render_place_suggestions
from src.routing.multi_route import (
    RoutePreset,
    RouteSummary,
    RouteWeights,
    build_routing_graph,
    compare_presets,
    route_with_weights,
    summarize_path,
)
from src.routing.geo_utils import haversine_km, route_looks_complete
from src.routing.tolls import fetch_live_route_tolls
from src.risk_engine import build_weather_context, risk_multiplier
from src.ui_helpers import (
    PRIORITY_HELP_KEY,
    PRIORITY_CHOICES,
    PRESET_FRIENDLY,
    ROUTE_TYPE_HELP,
    delta_vs_fastest,
    format_distance,
    format_minutes,
    format_tolls,
    help_for_summary,
    parking_label,
    render_route_info_popover,
    render_route_types_guide,
    safety_label,
    stress_label,
)

try:
    import osmnx as ox
except ImportError:  # pragma: no cover
    ox = None

ROOT = Path(__file__).resolve().parents[1]
CHICAGO_CONFIG = ROOT / "config" / "chicago_places.json"


def load_chicago_config() -> dict:
    return json.loads(CHICAGO_CONFIG.read_text())


def load_model(path: Path):
    if not path.exists():
        return None
    return joblib.load(path)


def load_fused_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def attach_risk_scores(data: pd.DataFrame, model) -> pd.DataFrame:
    if data.empty or model is None:
        return data
    X, _ = build_features(data)
    X = X.fillna(0)
    out = data.copy()
    out["risk_score"] = model.predict_proba(X)[:, 1]
    return out


def chicago_heatmap(data: pd.DataFrame, center: dict) -> folium.Map:
    fmap = folium.Map(
        location=[center["lat"], center["lon"]],
        zoom_start=center.get("zoom", 11),
        tiles="CartoDB positron",
    )
    if data.empty:
        return fmap

    heat_data = data[["latitude", "longitude", "risk_score"]].dropna().values.tolist()
    if heat_data:
        HeatMap(heat_data, radius=14, blur=18, max_zoom=13, min_opacity=0.35).add_to(fmap)
    return fmap


def route_map(
    G,
    summaries: list[RouteSummary],
    origin: tuple[float, float],
    destination: tuple[float, float],
    selected_idx: int,
    from_label: str,
    to_label: str,
) -> folium.Map:
    fmap = folium.Map(
        location=[origin[0], origin[1]],
        zoom_start=12,
        tiles="CartoDB positron",
    )

    folium.Marker(
        [origin[0], origin[1]],
        popup=from_label,
        tooltip=f"From: {from_label}",
        icon=folium.Icon(color="green", icon="home"),
    ).add_to(fmap)
    folium.Marker(
        [destination[0], destination[1]],
        popup=to_label,
        tooltip=f"To: {to_label}",
        icon=folium.Icon(color="red", icon="info-sign"),
    ).add_to(fmap)

    for idx, summary in enumerate(summaries):
        coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in summary.nodes]
        selected = idx == selected_idx
        folium.PolyLine(
            coords,
            color=summary.color,
            weight=8 if selected else 4,
            opacity=1.0 if selected else 0.45,
            tooltip=summary.label,
        ).add_to(fmap)

    bounds = [[origin[0], origin[1]], [destination[0], destination[1]]]
    for s in summaries:
        for n in s.nodes:
            bounds.append([G.nodes[n]["y"], G.nodes[n]["x"]])
    fmap.fit_bounds(bounds, padding=(30, 30))
    return fmap


@st.cache_data(show_spinner=False)
def load_risk_points(has_risk_data: bool):
    if not has_risk_data:
        return None
    fused = load_fused_data(ROOT / "data" / "processed" / "fused.csv")
    model = load_model(ROOT / "models" / "risk_model.joblib")
    data = attach_risk_scores(fused, model)
    if data.empty:
        return None
    return gpd.GeoDataFrame(
        data,
        geometry=gpd.points_from_xy(data["longitude"], data["latitude"]),
        crs="EPSG:4326",
    )


def compute_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    buffer_km: float,
    priority_key: str,
    use_live_tolls: bool,
    has_risk_data: bool,
    depart_at_iso: str | None,
    precipitation: float | None,
    visibility: float | None,
    wind_speed: float | None,
    traffic_volume: float | None,
):
    origin = (origin_lat, origin_lon)
    destination = (dest_lat, dest_lon)
    risk_points = load_risk_points(has_risk_data)

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

    live_toll = fetch_live_route_tolls(origin, destination) if use_live_tolls else None
    presets = compare_presets(G, origin, destination, live_toll_usd=live_toll)

    custom_weights = PRIORITY_CHOICES[priority_key]
    custom_path = route_with_weights(G, origin, destination, custom_weights)
    custom = summarize_path(G, custom_path, RoutePreset.BALANCED)
    custom = RouteSummary(
        preset=custom.preset,
        label=f"Your pick · {priority_key.split(' ', 1)[-1]}",
        nodes=custom.nodes,
        time_min=custom.time_min,
        toll_usd=custom.toll_usd,
        distance_km=custom.distance_km,
        stress_index=custom.stress_index,
        risk_exposure=custom.risk_exposure,
        reliability_index=custom.reliability_index,
        parking_index=custom.parking_index,
        live_toll_usd=live_toll,
        explanation="Based on what you chose in the sidebar.",
        color="#111827",
    )

    return G, presets + [custom], live_toll, {"multiplier": mult, "summary": summary, "factors": factors, "ctx": ctx}


def run_route_search(
    origin: tuple[float, float],
    destination: tuple[float, float],
    from_label: str,
    to_label: str,
    buffer_km: float,
    priority: str,
    use_live_tolls: bool,
    has_risk_data: bool,
    depart_at_iso: str | None,
    precipitation: float | None,
    visibility: float | None,
    wind_speed: float | None,
    traffic_volume: float | None,
) -> None:
    with st.spinner("Finding routes on Chicagoland roads…"):
        G, summaries, live_toll, risk = compute_routes(
            origin[0],
            origin[1],
            destination[0],
            destination[1],
            buffer_km,
            priority,
            use_live_tolls,
            has_risk_data=has_risk_data,
            depart_at_iso=depart_at_iso,
            precipitation=precipitation,
            visibility=visibility,
            wind_speed=wind_speed,
            traffic_volume=traffic_volume,
        )
    st.session_state["from_lat"], st.session_state["from_lon"] = origin
    st.session_state["to_lat"], st.session_state["to_lon"] = destination
    st.session_state["from_label"] = from_label
    st.session_state["to_label"] = to_label
    st.session_state["routes"] = {
        "G": G,
        "summaries": summaries,
        "live_toll": live_toll,
        "origin": origin,
        "destination": destination,
        "risk": risk,
    }
    st.session_state["selected_route"] = 0


def init_session(chicago: dict) -> None:
    default = chicago["presets"][0]
    st.session_state.setdefault("from_address", default["from_address"])
    st.session_state.setdefault("to_address", default["to_address"])
    st.session_state.setdefault("from_lat", default["from_lat"])
    st.session_state.setdefault("from_lon", default["from_lon"])
    st.session_state.setdefault("to_lat", default["to_lat"])
    st.session_state.setdefault("to_lon", default["to_lon"])
    st.session_state.setdefault("from_label", default["from_label"])
    st.session_state.setdefault("to_label", default["to_label"])
    st.session_state.setdefault("selected_route", 0)
    st.session_state.setdefault("routes", None)
    st.session_state.setdefault("from_coords", None)
    st.session_state.setdefault("to_coords", None)
    st.session_state.setdefault("from_resolved_label", "")
    st.session_state.setdefault("to_resolved_label", "")


def _resolve_trip_point(
    address: str,
    *,
    coords_key: str,
    resolved_label_key: str,
) -> tuple[float, float] | None:
    if (
        st.session_state.get(resolved_label_key) == address
        and st.session_state.get(coords_key)
    ):
        lat, lon = st.session_state[coords_key]
        return float(lat), float(lon)
    coords = geocode_address(address)
    if coords:
        st.session_state[coords_key] = coords
        st.session_state[resolved_label_key] = address
    return coords


def main() -> None:
    brand = load_brand()
    st.set_page_config(
        page_title=page_title(),
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    chicago = load_chicago_config()
    init_session(chicago)

    try:
        with st.spinner("Loading Chicagoland demo data…"):
            ensure_demo_pipeline()
    except Exception as exc:
        st.warning(f"Demo setup skipped: {exc}")

    model = load_model(ROOT / "models" / "risk_model.joblib")
    risk_data = attach_risk_scores(load_fused_data(ROOT / "data" / "processed" / "fused.csv"), model)

    # --- Header ---
    st.markdown(f"## {brand['name']}")
    st.caption(f"{brand['tagline']} — {brand['subtitle']}")
    render_route_types_guide(expanded=False)

    if ox is None:
        st.error("Install osmnx and networkx to use route planning.")
        return

    # --- Preferences ---
    priority = list(PRIORITY_CHOICES.keys())[5]
    buffer_km = 2.0
    use_live_tolls = False
    show_risk_map = False
    depart_at = pd.Timestamp.now()
    use_manual_weather = False
    precipitation = None
    visibility = None
    wind_speed = None
    traffic_volume = None
    with st.expander("Route preferences", expanded=False):
        pref_cols = st.columns([3, 1])
        with pref_cols[0]:
            priority = st.radio(
                "What matters most for *Your pick*?",
                list(PRIORITY_CHOICES.keys()),
                index=5,
                horizontal=True,
                help="Your pick is the custom route on the results map. Preset routes are always shown too.",
            )
        with pref_cols[1]:
            st.write("")
            with st.popover("ℹ️ Priorities"):
                st.markdown("### Your pick vs preset routes")
                st.markdown(
                    "The buttons after you search (Fastest, Calmest, etc.) are **presets**. "
                    "**Your pick** is the extra route shaped by the choice below."
                )
                if priority in PRIORITY_HELP_KEY:
                    info = ROUTE_TYPE_HELP[PRIORITY_HELP_KEY[priority]]
                    st.markdown(f"**Currently: {info['title']}**")
                    st.caption(info["detail"])
        if priority in PRIORITY_HELP_KEY:
            hint = ROUTE_TYPE_HELP[PRIORITY_HELP_KEY[priority]]
            st.caption(f"**Your pick** will favor: {hint['tagline']}")
        buffer_km = st.slider(
            "Road network buffer (km)",
            1.0,
            5.0,
            2.0,
            0.5,
            help="Extra padding around your trip when downloading streets. "
            "The map always covers the full route from origin to destination.",
        )
        use_live_tolls = st.checkbox("Include live toll estimate (TollGuru API key)", value=False)
        show_risk_map = st.checkbox("Show safety heatmap layer", value=False)
        st.markdown("### Accident risk (weather + trends)")
        dt_cols = st.columns([2, 1])
        with dt_cols[0]:
            d = st.date_input("Departure date", value=depart_at.date())
        with dt_cols[1]:
            t = st.time_input("Departure time", value=depart_at.to_pydatetime().time())
        depart_at = pd.Timestamp(datetime.combine(d, t))
        use_manual_weather = st.checkbox("Manually enter weather", value=False)
        if use_manual_weather:
            w1, w2, w3, w4 = st.columns(4)
            with w1:
                precipitation = st.number_input("Precip (mm/hr)", min_value=0.0, max_value=10.0, value=0.0, step=0.1)
            with w2:
                visibility = st.number_input("Visibility (km)", min_value=0.2, max_value=20.0, value=8.0, step=0.2)
            with w3:
                wind_speed = st.number_input("Wind (kph)", min_value=0.0, max_value=60.0, value=10.0, step=1.0)
            with w4:
                traffic_volume = st.number_input(
                    "Traffic proxy", min_value=0.0, max_value=6000.0, value=1800.0, step=50.0
                )

    # --- Quick trips ---
    st.markdown("**Popular trips**")
    trip_cols = st.columns(len(chicago["presets"]))
    for col, preset in zip(trip_cols, chicago["presets"]):
        if col.button(preset["label"], width="stretch"):
            st.session_state["from_address"] = preset["from_address"]
            st.session_state["to_address"] = preset["to_address"]
            run_route_search(
                (preset["from_lat"], preset["from_lon"]),
                (preset["to_lat"], preset["to_lon"]),
                preset["from_label"],
                preset["to_label"],
                buffer_km,
                priority,
                use_live_tolls,
                has_risk_data=not risk_data.empty and model is not None,
                depart_at_iso=depart_at.isoformat(),
                precipitation=precipitation,
                visibility=visibility,
                wind_speed=wind_speed,
                traffic_volume=traffic_volume,
            )
            st.rerun()

    # --- Search bar ---
    s1, s2, s3 = st.columns([5, 5, 1])
    with s1:
        from_address = st.text_input(
            "From",
            key="from_address",
            placeholder="Start typing an address or place…",
        )
        render_place_suggestions(
            "from",
            from_address,
            coords_key="from_coords",
            label_key="from_address",
        )
    with s2:
        to_address = st.text_input(
            "To",
            key="to_address",
            placeholder="Start typing an address or place…",
        )
        render_place_suggestions(
            "to",
            to_address,
            coords_key="to_coords",
            label_key="to_address",
        )
    with s3:
        st.write("")
        st.write("")
        get_routes = st.button("Go", type="primary", width="stretch")

    # Resolve addresses on Go
    if get_routes:
        origin = _resolve_trip_point(
            from_address,
            coords_key="from_coords",
            resolved_label_key="from_resolved_label",
        )
        destination = _resolve_trip_point(
            to_address,
            coords_key="to_coords",
            resolved_label_key="to_resolved_label",
        )
        if origin is None or destination is None:
            st.error(
                "Couldn't find one or both places. Try a Chicagoland address "
                "(e.g. 'Navy Pier, Chicago' or 'Naperville, IL') or pick a popular trip above."
            )
        else:
            run_route_search(
                origin,
                destination,
                from_address,
                to_address,
                buffer_km,
                priority,
                use_live_tolls,
                has_risk_data=not risk_data.empty and model is not None,
                depart_at_iso=depart_at.isoformat(),
                precipitation=precipitation,
                visibility=visibility,
                wind_speed=wind_speed,
                traffic_volume=traffic_volume,
            )
            st.rerun()

    routes_state = st.session_state.get("routes")

    # --- Results ---
    if routes_state:
        G = routes_state["G"]
        summaries: list[RouteSummary] = routes_state["summaries"]
        origin = routes_state["origin"]
        destination = routes_state["destination"]
        fastest = next(s for s in summaries if s.preset == RoutePreset.FASTEST)
        selected_idx = st.session_state.get("selected_route", 0)
        selected = summaries[selected_idx]
        risk = routes_state.get("risk") or {}

        straight_km = haversine_km(origin[0], origin[1], destination[0], destination[1])
        if not route_looks_complete(fastest.distance_km, origin, destination):
            st.warning(
                f"This route looks incomplete ({format_distance(fastest.distance_km)} driven vs "
                f"{format_distance(straight_km)} direct). Try increasing the road network buffer "
                "in Route preferences, or check that both addresses geocoded correctly."
            )

        st.markdown("---")
        st.markdown(
            f"**{st.session_state['from_label']}** → **{st.session_state['to_label']}** · "
            f"{format_distance(selected.distance_km)} · {format_minutes(selected.time_min)}"
        )

        # Route option pills + ℹ️ info per type
        st.caption("Tap a route to highlight it on the map · ℹ️ for what each type means")
        pill_cols = st.columns(len(summaries))
        for idx, (col, summary) in enumerate(zip(pill_cols, summaries)):
            friendly = PRESET_FRIENDLY.get(summary.preset, summary.label)
            title = friendly if summary.preset != RoutePreset.BALANCED or "Your pick" in summary.label else summary.label
            is_selected = idx == selected_idx

            with col:
                btn_col, info_col = st.columns([6, 1], gap="small")
                with btn_col:
                    label = (
                        f"{title}\n"
                        f"{format_minutes(summary.time_min)} · {format_tolls(summary.toll_usd)}"
                    )
                    if st.button(
                        label,
                        key=f"route_{idx}",
                        width="stretch",
                        type="primary" if is_selected else "secondary",
                    ):
                        st.session_state["selected_route"] = idx
                        st.rerun()
                with info_col:
                    st.write("")
                    render_route_info_popover(summary, key=f"route_info_{idx}")

        selected_idx = st.session_state.get("selected_route", 0)
        selected = summaries[selected_idx]

        # Hero summary for selected route
        route_help = help_for_summary(selected)
        st.markdown(f"#### {route_help['title']}")
        st.markdown(f"_{route_help['tagline']}_")
        st.caption(route_help["detail"])

        hero1, hero2, hero3, hero4 = st.columns(4)
        hero1.metric("Drive time", format_minutes(selected.time_min), help="Estimated minutes driving this path.")
        hero2.metric("Tolls", format_tolls(selected.toll_usd), help="Estimated tolls from OpenStreetMap + our toll table.")
        hero3.metric(
            "Safety",
            safety_label(selected.risk_exposure),
            help="Based on crash + weather model risk along the route (lower is better).",
        )
        hero4.metric(
            "Feel",
            stress_label(selected.stress_index),
            help="Calmest = more local streets; Highway-heavy = more expressways and merges.",
        )
        if risk:
            st.caption(f"**Accident risk context:** {risk.get('summary', '')}")
            factors = risk.get("factors") or []
            if factors:
                with st.expander("Why risk changed", expanded=False):
                    for f in factors[:6]:
                        st.markdown(f"- {f}")

        st.info(delta_vs_fastest(selected, fastest))
        st.caption(
            f"{parking_label(selected.parking_index)} · "
            f"{format_distance(selected.distance_km)} total"
        )
        if selected.live_toll_usd is not None:
            st.caption(f"Live toll API estimate for this trip: **${selected.live_toll_usd:.2f}**")

        # Map
        fmap = route_map(
            G,
            summaries,
            origin,
            destination,
            selected_idx,
            st.session_state["from_label"],
            st.session_state["to_label"],
        )
        st_folium(fmap, width=None, height=520, returned_objects=[], key="route_map")

        # Turn-by-turn navigation (OSRM / Mapbox)
        with st.expander("🧭 In-app navigation (beta)", expanded=False):
            st.caption(
                "Google Maps–style turn-by-turn. Park before you start. "
                "On your phone, use the PWA **Navigate** button after comparing routes."
            )
            if st.button("Load driving directions", key="load_nav_directions"):
                try:
                    with st.spinner("Fetching turn-by-turn from OSRM/Mapbox…"):
                        nav = get_turn_by_turn_directions(
                            origin[0],
                            origin[1],
                            destination[0],
                            destination[1],
                        )
                    st.session_state["nav_directions"] = nav
                except ValueError as exc:
                    st.error(str(exc))
            nav = st.session_state.get("nav_directions")
            if nav:
                st.success(
                    f"{nav['duration_display']} · {nav['distance_display']} · via **{nav['provider']}**"
                )
                for i, step in enumerate(nav.get("steps") or [], start=1):
                    st.markdown(f"{i}. **{step['instruction']}** — _{step['distance_display']}_")
                st.link_button(
                    "Open full-screen navigation (mobile)",
                    f"http://localhost:8000/mobile/nav.html",
                    help="Run ./scripts/dev.sh mobile first",
                )

        # Comparison table (plain English)
        with st.expander("Compare all routes", expanded=False):
            rows = []
            for s in summaries:
                name = PRESET_FRIENDLY.get(s.preset, s.label)
                if "Your pick" in s.label:
                    name = s.label
                info = help_for_summary(s)
                rows.append(
                    {
                        "Route": name,
                        "What it means": info["tagline"],
                        "Time": format_minutes(s.time_min),
                        "Tolls": format_tolls(s.toll_usd),
                        "Distance": format_distance(s.distance_km),
                        "Safety": safety_label(s.risk_exposure),
                        "Drive feel": stress_label(s.stress_index),
                        "Parking": parking_label(s.parking_index),
                        "Vs fastest": delta_vs_fastest(s, fastest),
                    }
                )
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    else:
        # Landing state — Chicagoland map + hint
        st.markdown("---")
        st.markdown("Pick a **popular trip** or enter **From / To** and click **Go**.")
        center = chicago["center"]
        landing = chicago_heatmap(risk_data, center)
        st_folium(landing, width=None, height=420, returned_objects=[], key="landing_map")

    if show_risk_map and not risk_data.empty and not routes_state:
        st.markdown("---")
        st.subheader("Safety heatmap · Chicagoland")
        st.caption("Where our model sees higher accident risk (from regional crash + weather data).")
        st_folium(
            chicago_heatmap(risk_data, chicago["center"]),
            width=None,
            height=400,
            returned_objects=[],
            key="safety_heatmap",
        )


if __name__ == "__main__":
    main()
