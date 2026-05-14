from __future__ import annotations

from pathlib import Path
from typing import Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from src.utils import load_csv

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover - fallback for environments without xgboost
    XGBClassifier = None


def train_model(X: pd.DataFrame, y: pd.Series) -> object:
    if XGBClassifier is None:
        raise ImportError("xgboost is required. Install with `pip install xgboost`.")

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="auc",
        n_jobs=4,
    )
    model.fit(X, y)
    return model


def evaluate_model(model: object, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
    preds = model.predict_proba(X)[:, 1]
    roc_auc = roc_auc_score(y, preds)
    return {"roc_auc": float(roc_auc)}


def main() -> None:
    features_path = Path("data") / "processed" / "features.csv"
    model_path = Path("models") / "risk_model.joblib"

    if not features_path.exists():
        raise FileNotFoundError("Run src/features.py to generate data/processed/features.csv.")

    df = load_csv(features_path)
    if "accident" not in df.columns:
        raise ValueError("Expected an `accident` column in the feature dataset.")

    X = df.drop(columns=["accident"])
    y = df["accident"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = train_model(X_train, y_train)
    metrics = evaluate_model(model, X_test, y_test)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Saved model to {model_path}")
    print(f"ROC-AUC: {metrics['roc_auc']:.4f}")


if __name__ == "__main__":
    main()
