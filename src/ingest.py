from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils import coerce_columns, load_csv, save_csv

DEFAULT_TIME_COL = "timestamp"
DEFAULT_LAT_COL = "latitude"
DEFAULT_LON_COL = "longitude"


def load_crash_data(path: str | Path) -> pd.DataFrame:
    df = load_csv(path)
    df = coerce_columns(df, [DEFAULT_TIME_COL, DEFAULT_LAT_COL, DEFAULT_LON_COL])
    df[DEFAULT_TIME_COL] = pd.to_datetime(df[DEFAULT_TIME_COL], errors="coerce")
    return df


def load_weather_data(path: str | Path) -> pd.DataFrame:
    df = load_csv(path)
    df = coerce_columns(df, [DEFAULT_TIME_COL, "precipitation", "visibility", "wind_speed"])
    df[DEFAULT_TIME_COL] = pd.to_datetime(df[DEFAULT_TIME_COL], errors="coerce")
    return df


def fuse_data(
    crash_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    time_col: str = DEFAULT_TIME_COL,
) -> pd.DataFrame:
    """
    Fuse crash and weather data by hour.

    For MVP, this uses a simple temporal join on the hour bucket.
    Spatial joins to road segments can be added in `features.py`.
    """
    crash_df = crash_df.copy()
    weather_df = weather_df.copy()

    crash_df["hour_bucket"] = crash_df[time_col].dt.floor("H")
    weather_df["hour_bucket"] = weather_df[time_col].dt.floor("H")

    weather_hourly = (
        weather_df.dropna(subset=["hour_bucket"])
        .groupby("hour_bucket", as_index=False)
        .mean(numeric_only=True)
    )

    fused = crash_df.merge(weather_hourly, on="hour_bucket", how="left", suffixes=("", "_weather"))
    return fused


def main() -> None:
    data_dir = Path("data")
    crash_path = data_dir / "crash.csv"
    weather_path = data_dir / "weather.csv"
    output_path = data_dir / "processed" / "fused.csv"

    if not crash_path.exists() or not weather_path.exists():
        raise FileNotFoundError(
            "Expected data/crash.csv and data/weather.csv. "
            "Provide sample data before running ingestion."
        )

    crash_df = load_crash_data(crash_path)
    weather_df = load_weather_data(weather_path)
    fused_df = fuse_data(crash_df, weather_df)

    save_csv(fused_df, output_path)
    print(f"Saved fused dataset to {output_path}")


if __name__ == "__main__":
    main()
