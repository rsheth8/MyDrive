from __future__ import annotations

from pathlib import Path
from typing import Tuple

import geopandas as gpd
import numpy as np
import pandas as pd

from src.utils import load_csv, save_csv


def add_temporal_features(df: pd.DataFrame, time_col: str = "timestamp") -> pd.DataFrame:
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    df["hour"] = df[time_col].dt.hour
    df["day_of_week"] = df[time_col].dt.dayofweek
    df["month"] = df[time_col].dt.month
    return df


def add_spatial_features(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
) -> gpd.GeoDataFrame:
    geo_df = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs="EPSG:4326",
    )
    return geo_df


def build_features(df: pd.DataFrame, target_col: str = "accident") -> Tuple[pd.DataFrame, pd.Series]:
    df = add_temporal_features(df)

    feature_cols = [
        "hour",
        "day_of_week",
        "month",
        "precipitation",
        "visibility",
        "wind_speed",
        "traffic_volume",
    ]

    for col in feature_cols:
        if col not in df.columns:
            df[col] = np.nan

    X = df[feature_cols].copy()
    y = df[target_col].copy() if target_col in df.columns else pd.Series(dtype=int)
    return X, y


def main() -> None:
    data_path = Path("data") / "processed" / "fused.csv"
    output_path = Path("data") / "processed" / "features.csv"

    if not data_path.exists():
        raise FileNotFoundError("Run src/ingest.py to generate data/processed/fused.csv.")

    df = load_csv(data_path)
    X, y = build_features(df)
    features_df = X.copy()
    if not y.empty:
        features_df["accident"] = y

    save_csv(features_df, output_path)
    print(f"Saved feature dataset to {output_path}")


if __name__ == "__main__":
    main()
