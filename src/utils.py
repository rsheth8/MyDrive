from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def ensure_dir(path: str | Path) -> Path:
    """Ensure a directory exists and return its Path."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    return pd.read_csv(path)


def save_csv(df: pd.DataFrame, path: str | Path) -> None:
    """Save a DataFrame to CSV."""
    path = Path(path)
    ensure_dir(path.parent)
    df.to_csv(path, index=False)


def coerce_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Ensure specified columns exist; fill with NA if missing."""
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA
    return df
