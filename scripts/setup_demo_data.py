#!/usr/bin/env python3
"""Copy sample CSVs into data/ and run ingest → features → model."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def main() -> None:
    if not (SAMPLE / "crash.csv").exists():
        run([sys.executable, "scripts/generate_sample_data.py"])

    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    shutil.copy(SAMPLE / "crash.csv", data / "crash.csv")
    shutil.copy(SAMPLE / "weather.csv", data / "weather.csv")
    print("Copied sample data → data/")

    run([sys.executable, "src/ingest.py"])
    run([sys.executable, "src/features.py"])
    run([sys.executable, "src/model.py"])
    print("Demo pipeline complete.")


if __name__ == "__main__":
    main()
