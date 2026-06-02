from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"
FUSED = ROOT / "data" / "processed" / "fused.csv"
MODEL = ROOT / "models" / "risk_model.joblib"


def ensure_sample_csvs() -> None:
    if (SAMPLE / "crash.csv").exists():
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_sample_data.py")],
        cwd=ROOT,
        check=True,
        env=env,
    )


def ensure_demo_pipeline() -> None:
    """Copy sample data and run ML pipeline if artifacts are missing."""
    if FUSED.exists() and MODEL.exists():
        return

    ensure_sample_csvs()
    (ROOT / "data").mkdir(exist_ok=True)
    shutil.copy(SAMPLE / "crash.csv", ROOT / "data" / "crash.csv")
    shutil.copy(SAMPLE / "weather.csv", ROOT / "data" / "weather.csv")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    for script in ("src/ingest.py", "src/features.py", "src/model.py"):
        subprocess.run(
            [sys.executable, str(ROOT / script)],
            cwd=ROOT,
            check=True,
            env=env,
        )
