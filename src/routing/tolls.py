from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from src.routing.osm_tags import first_str, is_toll_edge

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "toll_rates.yaml"

DEFAULT_PER_KM = 0.35
DEFAULT_FLAT = 2.75


def load_toll_config(path: Path | None = None) -> dict[str, Any]:
    path = path or CONFIG_PATH
    if not path.exists():
        return {
            "default_per_km": DEFAULT_PER_KM,
            "flat_booth_usd": DEFAULT_FLAT,
            "by_highway": {},
        }
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def estimate_edge_toll_usd(
    data: dict[str, Any],
    length_m: float,
    config: dict[str, Any] | None = None,
) -> float:
    """
    Estimate toll cost for one graph edge using OSM tags + config rates.
    """
    if not is_toll_edge(data):
        return 0.0

    config = config or load_toll_config()
    length_km = length_m / 1000.0
    hw = first_str(data.get("highway", "unclassified")).lower()
    per_km = float(config.get("by_highway", {}).get(hw, config.get("default_per_km", DEFAULT_PER_KM)))
    flat = float(config.get("flat_booth_usd", DEFAULT_FLAT))
    return flat + per_km * length_km


def fetch_live_route_tolls(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> float | None:
    """
    Optional live toll total (USD) for an origin–destination pair.

    Set TOLLGURU_API_KEY to enable TollGuru's API; returns None if unavailable.
    See DEPLOY.md for setup.
    """
    api_key = os.getenv("TOLLGURU_API_KEY", "").strip()
    if not api_key:
        try:
            import streamlit as st

            api_key = st.secrets.get("TOLLGURU_API_KEY", "").strip()
        except Exception:
            api_key = ""
    if not api_key:
        return None

    try:
        import requests
    except ImportError:
        return None

    url = "https://apis.tollguru.com/toll/v2/origin-destination-waypoints"
    payload = {
        "from": {"lat": origin[0], "lng": origin[1]},
        "to": {"lat": destination[0], "lng": destination[1]},
        "vehicleType": "2AxlesAuto",
        "fuelPrice": 3.5,
    }
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        body = response.json()
        routes = body.get("routes") or []
        if not routes:
            return None
        tolls = routes[0].get("costs", {}).get("tagAndCash") or routes[0].get("tolls", {})
        if isinstance(tolls, dict):
            return float(tolls.get("tag", tolls.get("cash", 0)) or 0)
        return float(tolls)
    except Exception:
        return None
