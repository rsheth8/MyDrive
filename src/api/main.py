from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.brand import load_brand
from src.navigation import get_geo_providers_status, get_turn_by_turn_directions
from src.places import search_places
from src.services.route_service import compare_routes_for_trip, load_chicago_config, resolve_place

ROOT = Path(__file__).resolve().parents[2]
MOBILE_DIR = ROOT / "mobile"

_brand = load_brand()
app = FastAPI(title=f"{_brand['name']} Mobile API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CompareRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    buffer_km: float = Field(2.0, ge=1.0, le=8.0)
    priority: str = Field("balanced", pattern="^(fastest|cheapest|safest|calm|parking|balanced)$")
    depart_at_iso: str | None = None
    precipitation: float | None = None
    visibility: float | None = None
    wind_speed: float | None = None
    traffic_volume: float | None = None


class GeocodeRequest(BaseModel):
    query: str = Field(..., min_length=1)
    lat: float | None = None
    lon: float | None = None


class DirectionsRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    provider: str = Field("auto", pattern="^(auto|osrm|mapbox)$")
    route_label: str | None = None
    polyline: list[list[float]] | None = None


@app.get("/api/health")
def health():
    return {"status": "ok", "product": f"{_brand['name']} Mobile"}


@app.get("/api/config")
def config():
    return load_chicago_config()


@app.get("/api/places/autocomplete")
def places_autocomplete(
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(8, ge=1, le=12),
):
    return {"suggestions": search_places(q, limit=limit)}


@app.post("/api/geocode")
def geocode(body: GeocodeRequest):
    loc = resolve_place(body.query, lat=body.lat, lon=body.lon)
    if loc is None:
        raise HTTPException(404, detail="Place not found. Try a Chicagoland address or pick a suggestion.")
    return loc


@app.post("/api/routes/compare")
def compare_routes(body: CompareRequest):
    try:
        return compare_routes_for_trip(
            body.origin_lat,
            body.origin_lon,
            body.dest_lat,
            body.dest_lon,
            buffer_km=body.buffer_km,
            priority=body.priority,
            depart_at_iso=body.depart_at_iso,
            precipitation=body.precipitation,
            visibility=body.visibility,
            wind_speed=body.wind_speed,
            traffic_volume=body.traffic_volume,
        )
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@app.get("/api/geo/providers")
def geo_providers():
    return get_geo_providers_status()


@app.post("/api/navigation/directions")
def navigation_directions(body: DirectionsRequest):
    try:
        return get_turn_by_turn_directions(
            body.origin_lat,
            body.origin_lon,
            body.dest_lat,
            body.dest_lon,
            provider=body.provider,
            polyline=body.polyline,
            route_label=body.route_label,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@app.get("/mobile/nav.html")
def mobile_nav():
    nav = MOBILE_DIR / "nav.html"
    if not nav.exists():
        raise HTTPException(404, detail="Navigation UI not found")
    return FileResponse(nav)


@app.get("/api/traffic/status")
def traffic_status():
    """Placeholder until a live traffic provider API key is configured."""
    return {
        "available": False,
        "message": "Live traffic: not connected (future: Google/TomTom). Routes use road types + model risk only.",
    }


@app.get("/")
def mobile_home():
    index = MOBILE_DIR / "index.html"
    if not index.exists():
        raise HTTPException(404, detail="Mobile UI not found")
    return FileResponse(index)


if MOBILE_DIR.exists():
    app.mount("/mobile", StaticFiles(directory=str(MOBILE_DIR)), name="mobile_static")
