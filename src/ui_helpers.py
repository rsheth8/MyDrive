from __future__ import annotations

import streamlit as st

from src.routing.multi_route import RoutePreset, RouteSummary, RouteWeights


def format_minutes(minutes: float) -> str:
    m = max(0, int(round(minutes)))
    if m == 0:
        return "< 1 min"
    return f"{m} min"


def format_tolls(usd: float) -> str:
    if usd < 0.01:
        return "No tolls"
    return f"${usd:.2f} tolls"


def format_distance(km: float) -> str:
    miles = km * 0.621371
    return f"{miles:.1f} mi"


def safety_label(risk_exposure: float) -> str:
    if risk_exposure < 0.15:
        return "Low risk"
    if risk_exposure < 0.35:
        return "Moderate risk"
    return "Higher risk"


def stress_label(stress_index: float) -> str:
    if stress_index < 0.5:
        return "Easy drive"
    if stress_index < 1.2:
        return "Mixed roads"
    return "Highway-heavy"


def parking_label(parking_index: float) -> str:
    if parking_index < 0.4:
        return "Good parking access"
    if parking_index < 0.9:
        return "OK parking access"
    return "Limited parking nearby"


def delta_vs_fastest(summary: RouteSummary, fastest: RouteSummary) -> str:
    if summary.preset == RoutePreset.FASTEST:
        return "Fastest option"

    parts: list[str] = []
    delta_min = summary.time_min - fastest.time_min
    delta_toll = summary.toll_usd - fastest.toll_usd

    if abs(delta_min) >= 0.5:
        sign = "+" if delta_min > 0 else ""
        parts.append(f"{sign}{int(round(delta_min))} min vs fastest")
    else:
        parts.append("Same time as fastest")

    if delta_toll <= -0.01:
        parts.append(f"save ${abs(delta_toll):.2f} in tolls")
    elif delta_toll >= 0.01:
        parts.append(f"+${delta_toll:.2f} tolls")

    if summary.risk_exposure < fastest.risk_exposure - 0.02:
        parts.append("safer route")
    if summary.stress_index < fastest.stress_index - 0.15:
        parts.append("calmer drive")

    return " · ".join(parts)


PRIORITY_CHOICES: dict[str, RouteWeights] = {
    "⚡ Fastest": RouteWeights(time=1.0),
    "💰 Save on tolls": RouteWeights(time=0.35, money=0.65),
    "🛡️ Safest": RouteWeights(time=0.3, risk=0.7),
    "😌 Calmest drive": RouteWeights(time=0.3, stress=0.7),
    "🅿️ Easy parking": RouteWeights(time=0.25, parking=0.75),
    "⚖️ Balanced": RouteWeights(
        time=0.3, money=0.15, stress=0.15, risk=0.15, reliability=0.15, parking=0.1
    ),
}

PRESET_FRIENDLY: dict[RoutePreset, str] = {
    RoutePreset.FASTEST: "⚡ Fastest",
    RoutePreset.CHEAPEST: "💰 Cheapest",
    RoutePreset.CALM: "😌 Calmest",
    RoutePreset.SAFEST: "🛡️ Safest",
    RoutePreset.RELIABLE: "🕐 Steady ETA",
    RoutePreset.BALANCED: "⚖️ Balanced",
    RoutePreset.PARKING: "🅿️ Parking-friendly",
}

# Plain-English explanations shown in the app
ROUTE_TYPE_HELP: dict[str, dict[str, str]] = {
    "fastest": {
        "title": "⚡ Fastest",
        "tagline": "Get there as quickly as possible.",
        "detail": (
            "Prioritizes drive time above everything else — similar to the default route "
            "in Google Maps. May use highways, tolled roads, or busier corridors if they save time."
        ),
        "pick_when": "You're in a rush or running late.",
    },
    "cheapest": {
        "title": "💰 Cheapest",
        "tagline": "Avoid tolls when a longer detour is worth the savings.",
        "detail": (
            "Skips roads tagged as tolled in OpenStreetMap and favors routes with lower "
            "estimated toll cost. You might drive a few extra minutes to save money at toll plazas "
            "or on the Jane Addams / I-PASS system."
        ),
        "pick_when": "You'd rather add a little time than pay tolls.",
    },
    "calm": {
        "title": "😌 Calmest",
        "tagline": "A less intense drive — fewer highways and stressful merges.",
        "detail": (
            "Prefers residential streets, arterials, and calmer road types over expressways "
            "and highways. \"Stress\" here means things like highway speed, lane changes, and "
            "road type — not your personal mood. Expect a more neighborhood-style drive."
        ),
        "pick_when": "You dislike highway driving or want a more relaxed trip.",
    },
    "safest": {
        "title": "🛡️ Safest",
        "tagline": "Routes away from areas with higher predicted accident risk.",
        "detail": (
            "Uses our crash + weather model to score road segments and avoids corridors with "
            "higher historical risk. This is a *prediction*, not a guarantee — always drive alert."
        ),
        "pick_when": "Safety matters more than saving a few minutes (night driving, bad weather, etc.).",
    },
    "reliable": {
        "title": "🕐 Steady ETA",
        "tagline": "Favors roads that tend to have more predictable travel times.",
        "detail": (
            "Avoids leaning too hard on major highways that often have bigger rush-hour swings. "
            "Useful when you need to arrive close to a set time and can't risk a huge traffic surprise."
        ),
        "pick_when": "You care about consistency (airport drop-off, shift start, reservations).",
    },
    "balanced": {
        "title": "⚖️ Balanced",
        "tagline": "A little bit of everything — time, cost, calm, safety, and reliability.",
        "detail": (
            "No single factor dominates. Good default when you don't want an extreme "
            "fastest-only or toll-avoiding route."
        ),
        "pick_when": "You want a sensible everyday drive without optimizing one thing too hard.",
    },
    "parking": {
        "title": "🅿️ Parking-friendly",
        "tagline": "Ends your trip closer to actual parking near the destination.",
        "detail": (
            "Looks for parking lots/garages from OpenStreetMap near where you're going and "
            "penalizes routes that leave you far from a place to park. Helpful for events, "
            "dense neighborhoods, or stadiums."
        ),
        "pick_when": "You need to park at the destination and don't want a long walk from your car.",
    },
    "your_pick": {
        "title": "Your pick",
        "tagline": "Built from what you chose under Route preferences.",
        "detail": (
            "Weights time, tolls, calm, safety, reliability, and parking the way you set "
            "in the sidebar. Change the priority and run Go again to update this route."
        ),
        "pick_when": "You want a custom mix instead of one of the presets above.",
    },
}

PRESET_HELP_KEY: dict[RoutePreset, str] = {
    RoutePreset.FASTEST: "fastest",
    RoutePreset.CHEAPEST: "cheapest",
    RoutePreset.CALM: "calm",
    RoutePreset.SAFEST: "safest",
    RoutePreset.RELIABLE: "reliable",
    RoutePreset.BALANCED: "balanced",
    RoutePreset.PARKING: "parking",
}

PRIORITY_HELP_KEY: dict[str, str] = {
    "⚡ Fastest": "fastest",
    "💰 Save on tolls": "cheapest",
    "🛡️ Safest": "safest",
    "😌 Calmest drive": "calm",
    "🅿️ Easy parking": "parking",
    "⚖️ Balanced": "balanced",
}


def help_for_summary(summary: RouteSummary) -> dict[str, str]:
    if "Your pick" in summary.label:
        return ROUTE_TYPE_HELP["your_pick"]
    key = PRESET_HELP_KEY.get(summary.preset, "balanced")
    return ROUTE_TYPE_HELP[key]


def render_route_info_popover(summary: RouteSummary, *, key: str) -> None:
    """Small ℹ️ button that expands with details for one route type."""
    info = help_for_summary(summary)
    with st.popover("ℹ️", help=f"Learn about {info['title']}", key=key):
        st.markdown(f"### {info['title']}")
        st.markdown(f"**{info['tagline']}**")
        st.markdown(info["detail"])
        st.markdown(f"**Best when:** {info['pick_when']}")


def render_route_types_guide(*, expanded: bool = False) -> None:
    """Collapsible reference for all route types."""
    with st.expander("📖 What do these route types mean?", expanded=expanded):
        for key in (
            "fastest",
            "cheapest",
            "calm",
            "safest",
            "reliable",
            "balanced",
            "parking",
            "your_pick",
        ):
            info = ROUTE_TYPE_HELP[key]
            st.markdown(f"**{info['title']}** — {info['tagline']}")
            st.caption(info["detail"])
            st.markdown(f"*Best when:* {info['pick_when']}")
            st.markdown("")
