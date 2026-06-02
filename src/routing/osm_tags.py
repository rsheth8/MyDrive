from __future__ import annotations

import re
from typing import Any

import numpy as np


def first_str(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else ""
    return str(value)


def is_toll_edge(data: dict[str, Any]) -> bool:
    toll = first_str(data.get("toll", "")).lower()
    return toll in {"yes", "true", "1"}


def parse_maxspeed_kph(value: Any) -> float | None:
    raw = first_str(value).strip().lower()
    if not raw:
        return None
    if raw in {"signals", "variable", "walk", "none"}:
        return None
    mph_match = re.search(r"(\d+(?:\.\d+)?)\s*mph", raw)
    if mph_match:
        return float(mph_match.group(1)) * 1.60934
    kph_match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if kph_match:
        return float(kph_match.group(1))
    return None
