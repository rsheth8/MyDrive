#!/usr/bin/env python3
"""
Compare preset routes for one or more origin–destination pairs.

Prints a table vs fastest baseline and aggregate insights (toll saved, risk reduced).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import geopandas as gpd
import pandas as pd

from src.routing.compare import aggregate_insights, comparisons_vs_baseline
from src.routing.multi_route import RoutePreset, build_routing_graph, compare_presets
from src.routing.tolls import fetch_live_route_tolls


def load_risk_points() -> gpd.GeoDataFrame | None:
    fused = ROOT / "data" / "processed" / "fused.csv"
    model_path = ROOT / "models" / "risk_model.joblib"
    if not fused.exists() or not model_path.exists():
        return None

    import joblib

    from src.features import build_features

    data = pd.read_csv(fused)
    model = joblib.load(model_path)
    X, _ = build_features(data)
    X = X.fillna(0)
    data["risk_score"] = model.predict_proba(X)[:, 1]
    return gpd.GeoDataFrame(
        data,
        geometry=gpd.points_from_xy(data["longitude"], data["latitude"]),
        crs="EPSG:4326",
    )


def run_pair(
    name: str,
    origin: tuple[float, float],
    destination: tuple[float, float],
    buffer_km: float,
    live_tolls: bool,
) -> tuple[pd.DataFrame, dict[str, float]]:
    risk_points = load_risk_points()
    G = build_routing_graph(
        origin,
        destination,
        buffer_km=buffer_km,
        risk_points=risk_points,
        parking_aware=True,
    )

    live_toll = fetch_live_route_tolls(origin, destination) if live_tolls else None
    summaries = compare_presets(G, origin, destination, live_toll_usd=live_toll)
    df = comparisons_vs_baseline(summaries)
    df.insert(0, "od_pair", name)
    if live_toll is not None:
        df["live_toll_usd"] = live_toll
    insights = aggregate_insights(df)
    insights["od_pair"] = name
    if live_toll is not None:
        insights["live_toll_usd"] = live_toll
    return df, insights


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare smart routes vs fastest baseline")
    parser.add_argument("--origin-lat", type=float)
    parser.add_argument("--origin-lon", type=float)
    parser.add_argument("--dest-lat", type=float)
    parser.add_argument("--dest-lon", type=float)
    parser.add_argument(
        "--routes-file",
        type=Path,
        default=ROOT / "config" / "demo_routes.json",
        help="JSON list of named OD pairs",
    )
    parser.add_argument("--buffer-km", type=float, default=2.0)
    parser.add_argument("--live-tolls", action="store_true", help="Query TollGuru if API key set")
    parser.add_argument("--output", type=Path, help="Write CSV results")
    args = parser.parse_args()

    pairs: list[dict] = []
    if args.origin_lat is not None:
        pairs.append(
            {
                "name": "custom",
                "origin_lat": args.origin_lat,
                "origin_lon": args.origin_lon,
                "dest_lat": args.dest_lat,
                "dest_lon": args.dest_lon,
            }
        )
    else:
        pairs = json.loads(args.routes_file.read_text())

    all_frames: list[pd.DataFrame] = []
    all_insights: list[dict] = []

    for p in pairs:
        name = p["name"]
        origin = (p["origin_lat"], p["origin_lon"])
        dest = (p["dest_lat"], p["dest_lon"])
        print(f"\n=== {name} ===")
        df, insights = run_pair(name, origin, dest, args.buffer_km, args.live_tolls)
        print(df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
        if insights:
            print("\nInsights vs fastest:")
            for k, v in insights.items():
                if k == "od_pair":
                    continue
                if isinstance(v, float):
                    print(f"  {k}: {v:.2f}")
                else:
                    print(f"  {k}: {v}")
        all_frames.append(df)
        all_insights.append(insights)

    combined = pd.concat(all_frames, ignore_index=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(args.output, index=False)
        print(f"\nWrote {args.output}")

    if len(all_insights) > 1:
        print("\n=== Aggregate across OD pairs ===")
        toll_saved = [i.get("max_toll_saved_usd", 0) for i in all_insights]
        extra_time = [i.get("avg_extra_time_min", 0) for i in all_insights]
        print(f"  Mean max toll saved: ${sum(toll_saved)/len(toll_saved):.2f}")
        print(f"  Mean extra time (non-fastest avg): {sum(extra_time)/len(extra_time):.1f} min")


if __name__ == "__main__":
    main()
