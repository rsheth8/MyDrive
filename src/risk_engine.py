from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class WeatherContext:
    depart_at: datetime
    precipitation: float | None = None  # mm/hr (or unitless demo proxy)
    visibility: float | None = None  # km (or unitless demo proxy)
    wind_speed: float | None = None  # kph (or unitless demo proxy)
    traffic_volume: float | None = None  # vehicles/hr proxy
    source: str = "typical"

    @property
    def hour(self) -> int:
        return int(self.depart_at.hour)

    @property
    def day_of_week(self) -> int:
        return int(self.depart_at.weekday())

    @property
    def month(self) -> int:
        return int(self.depart_at.month)


def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        x = float(v)
        if pd.isna(x):
            return None
        return x
    except Exception:
        return None


def _load_typical_weather_table() -> pd.DataFrame | None:
    """
    Load a (month, hour) → typical weather table.

    Uses processed fused data if present; falls back to committed sample weather.
    """
    processed = ROOT / "data" / "processed" / "fused.csv"
    sample = ROOT / "data" / "sample" / "weather.csv"
    if processed.exists():
        df = pd.read_csv(processed)
    elif sample.exists():
        df = pd.read_csv(sample)
    else:
        return None

    if "timestamp" not in df.columns:
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["month"] = df["timestamp"].dt.month
    df["hour"] = df["timestamp"].dt.hour

    cols = [c for c in ("precipitation", "visibility", "wind_speed", "traffic_volume") if c in df.columns]
    if not cols:
        return None

    typical = df.groupby(["month", "hour"], as_index=False)[cols].mean(numeric_only=True)
    return typical


_TYPICAL_WEATHER: pd.DataFrame | None = None


def typical_weather_for(dt: datetime) -> dict[str, float | None]:
    global _TYPICAL_WEATHER
    if _TYPICAL_WEATHER is None:
        _TYPICAL_WEATHER = _load_typical_weather_table()
    if _TYPICAL_WEATHER is None or _TYPICAL_WEATHER.empty:
        return {"precipitation": None, "visibility": None, "wind_speed": None, "traffic_volume": None}

    month = int(dt.month)
    hour = int(dt.hour)
    row = _TYPICAL_WEATHER[(_TYPICAL_WEATHER["month"] == month) & (_TYPICAL_WEATHER["hour"] == hour)]
    if row.empty:
        # fallback to hour-only average
        row = _TYPICAL_WEATHER[_TYPICAL_WEATHER["hour"] == hour]
    if row.empty:
        return {"precipitation": None, "visibility": None, "wind_speed": None, "traffic_volume": None}

    r = row.iloc[0].to_dict()
    return {
        "precipitation": _safe_float(r.get("precipitation")),
        "visibility": _safe_float(r.get("visibility")),
        "wind_speed": _safe_float(r.get("wind_speed")),
        "traffic_volume": _safe_float(r.get("traffic_volume")),
    }


def build_weather_context(
    *,
    depart_at: datetime,
    precipitation: float | None = None,
    visibility: float | None = None,
    wind_speed: float | None = None,
    traffic_volume: float | None = None,
) -> WeatherContext:
    if any(v is not None for v in (precipitation, visibility, wind_speed, traffic_volume)):
        return WeatherContext(
            depart_at=depart_at,
            precipitation=_safe_float(precipitation),
            visibility=_safe_float(visibility),
            wind_speed=_safe_float(wind_speed),
            traffic_volume=_safe_float(traffic_volume),
            source="manual",
        )

    typical = typical_weather_for(depart_at)
    return WeatherContext(
        depart_at=depart_at,
        precipitation=typical.get("precipitation"),
        visibility=typical.get("visibility"),
        wind_speed=typical.get("wind_speed"),
        traffic_volume=typical.get("traffic_volume"),
        source="typical",
    )


def risk_multiplier(ctx: WeatherContext) -> tuple[float, list[str], str]:
    """
    Return (multiplier, factors, summary).

    This is a deliberately simple, explainable model:
    - Applies global weather/time multipliers to spatial risk exposure along the route.
    - Intended to make the app feel “alive” even with demo data (no live forecasts).
    """
    factors: list[str] = []
    mult = 1.0

    # Time-of-day trends
    h = ctx.hour
    night = (h >= 22) or (h <= 5)
    rush = (7 <= h <= 9) or (16 <= h <= 18)
    if night:
        mult *= 1.18
        factors.append("Night driving trend (+18%)")
    if rush:
        mult *= 1.12
        factors.append("Rush-hour trend (+12%)")

    # Weather impacts (thresholds tuned for demo units)
    p = ctx.precipitation
    if p is not None:
        if p >= 3.0:
            mult *= 1.45
            factors.append("Heavy precipitation (+45%)")
        elif p >= 1.0:
            mult *= 1.22
            factors.append("Rain / snow conditions (+22%)")

    vis = ctx.visibility
    if vis is not None:
        if vis <= 1.0:
            mult *= 1.55
            factors.append("Very low visibility (+55%)")
        elif vis <= 3.0:
            mult *= 1.28
            factors.append("Low visibility (+28%)")

    w = ctx.wind_speed
    if w is not None:
        if w >= 35.0:
            mult *= 1.22
            factors.append("High winds (+22%)")
        elif w >= 25.0:
            mult *= 1.12
            factors.append("Windy (+12%)")

    # Traffic volume is a proxy; mild effect to avoid dominating.
    tv = ctx.traffic_volume
    if tv is not None:
        if tv >= 4000:
            mult *= 1.10
            factors.append("High traffic volume proxy (+10%)")
        elif tv <= 600:
            mult *= 0.95
            factors.append("Light traffic proxy (-5%)")

    # Keep the UX stable.
    mult = max(0.6, min(2.5, mult))

    summary_bits: list[str] = []
    if ctx.source == "manual":
        summary_bits.append("manual weather")
    else:
        summary_bits.append("typical weather")
    summary_bits.append(ctx.depart_at.strftime("%a %I:%M %p"))

    summary = f"Risk adjusted for {', '.join(summary_bits)} · x{mult:.2f}"
    return mult, factors, summary

