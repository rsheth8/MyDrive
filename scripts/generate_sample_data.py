#!/usr/bin/env python3
"""Generate synthetic Chicagoland crash + weather CSVs for demo."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# Chicagoland anchor (The Loop)
CENTER_LAT = 41.8781
CENTER_LON = -87.6298


def generate_crash(n_rows: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    hours = pd.date_range("2023-01-01", periods=n_rows, freq="h")
    lat = CENTER_LAT + rng.normal(0, 0.06, n_rows)
    lon = CENTER_LON + rng.normal(0, 0.09, n_rows)
    hour_of_day = hours.hour
    # Higher accident probability at night + rush hour + bad weather proxy later
    base_p = 0.12 + 0.08 * ((hour_of_day >= 22) | (hour_of_day <= 5))
    rush = ((hour_of_day >= 7) & (hour_of_day <= 9)) | ((hour_of_day >= 16) & (hour_of_day <= 18))
    base_p += 0.06 * rush
    accident = (rng.random(n_rows) < np.clip(base_p, 0, 0.45)).astype(int)
    traffic_volume = rng.integers(200, 5000, n_rows)

    return pd.DataFrame(
        {
            "timestamp": hours.strftime("%Y-%m-%dT%H:%M:%S"),
            "latitude": lat,
            "longitude": lon,
            "accident": accident,
            "traffic_volume": traffic_volume,
        }
    )


def generate_weather(n_rows: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    hours = pd.date_range("2023-01-01", periods=n_rows, freq="h")
    month = hours.month
    precip = np.clip(rng.exponential(0.4, n_rows) + 0.1 * (month % 6), 0, 5)
    visibility = np.clip(rng.normal(8, 2, n_rows) - precip * 0.5, 0.5, 15)
    wind = np.clip(rng.normal(12, 5, n_rows), 0, 40)

    return pd.DataFrame(
        {
            "timestamp": hours.strftime("%Y-%m-%dT%H:%M:%S"),
            "precipitation": precip.round(2),
            "visibility": visibility.round(2),
            "wind_speed": wind.round(2),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate demo crash/weather CSVs")
    parser.add_argument("--rows", type=int, default=720, help="Hours of synthetic data")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/sample"),
        help="Output directory (committed sample files)",
    )
    parser.add_argument("--copy-to-data", action="store_true", help="Also write data/crash.csv")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    crash = generate_crash(args.rows)
    weather = generate_weather(args.rows)

    crash_path = args.out_dir / "crash.csv"
    weather_path = args.out_dir / "weather.csv"
    crash.to_csv(crash_path, index=False)
    weather.to_csv(weather_path, index=False)
    print(f"Wrote {crash_path} ({len(crash)} rows)")
    print(f"Wrote {weather_path} ({len(weather)} rows)")

    if args.copy_to_data:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        crash.to_csv(data_dir / "crash.csv", index=False)
        weather.to_csv(data_dir / "weather.csv", index=False)
        print("Copied to data/crash.csv and data/weather.csv")


if __name__ == "__main__":
    main()
