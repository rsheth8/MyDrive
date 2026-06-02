from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND_PATH = ROOT / "config" / "brand.json"


def load_brand() -> dict[str, str]:
    return json.loads(BRAND_PATH.read_text())


def page_title() -> str:
    b = load_brand()
    return f"{b['name']} · Chicagoland"
