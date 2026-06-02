from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.routing.multi_route import RoutePreset, RouteSummary


@dataclass
class RouteComparisonRow:
    route_name: str
    time_min: float
    toll_usd: float
    delta_time_min: float
    delta_toll_usd: float
    delta_risk: float
    delta_stress: float
    parking_index: float
    distance_km: float


def comparisons_vs_baseline(
    summaries: list[RouteSummary],
    baseline_preset: RoutePreset = RoutePreset.FASTEST,
) -> pd.DataFrame:
    baseline = next(s for s in summaries if s.preset == baseline_preset)
    rows: list[RouteComparisonRow] = []

    for s in summaries:
        rows.append(
            RouteComparisonRow(
                route_name=s.label,
                time_min=s.time_min,
                toll_usd=s.toll_usd,
                delta_time_min=s.time_min - baseline.time_min,
                delta_toll_usd=s.toll_usd - baseline.toll_usd,
                delta_risk=s.risk_exposure - baseline.risk_exposure,
                delta_stress=s.stress_index - baseline.stress_index,
                parking_index=s.parking_index,
                distance_km=s.distance_km,
            )
        )

    return pd.DataFrame([r.__dict__ for r in rows])


def aggregate_insights(df: pd.DataFrame) -> dict[str, float]:
    if df.empty or len(df) < 2:
        return {}

    non_baseline = df.iloc[1:]
    cheapest = non_baseline.loc[non_baseline["delta_toll_usd"].idxmin()]
    safest = non_baseline.loc[non_baseline["delta_risk"].idxmin()]

    return {
        "avg_extra_time_min": float(non_baseline["delta_time_min"].mean()),
        "max_toll_saved_usd": float(-cheapest["delta_toll_usd"]),
        "best_toll_saver": str(cheapest["route_name"]),
        "best_risk_reduction": float(-safest["delta_risk"]),
        "best_risk_route": str(safest["route_name"]),
    }
