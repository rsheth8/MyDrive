# MyDrive

**Chicagoland route planner with ML accident-risk scoring — compare drives by time, tolls, calm, safety, and weather-aware trends, then open Google or Apple Maps.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Desktop-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![OSM](https://img.shields.io/badge/Roads-OpenStreetMap-7EBC6F?logo=openstreetmap&logoColor=white)](https://www.openstreetmap.org/)

Plan a trip from **The Loop to O'Hare**, **Naperville to downtown**, or any Chicagoland address. MyDrive downloads real streets from OpenStreetMap, scores every segment with an **XGBoost accident model** (crash history + weather features), adjusts risk for **departure time and conditions** (night, rush hour, rain, visibility), and returns **up to 8 comparable routes** — fastest, cheapest, calmest, safest, and more.

> **Safety scores are predictions, not guarantees.** Always drive alert. Park before using the phone UI.

---

## What it does

| Capability | Details |
|------------|---------|
| **Multi-route comparison** | **7 presets** + **Your pick** (custom priority): time, tolls, stress, ML risk, reliability, parking |
| **Accident-risk prediction** | **7 features** → XGBoost `P(accident)` per location; mapped onto road segments |
| **Weather + trend layer** | Departure time + precip / visibility / wind / traffic → risk multiplier (**0.6×–2.5×**) with plain-English factors |
| **Chicagoland focus** | **5** popular trips, **6** destination shortcuts, OSM drive network via OSMnx |
| **Mobile + desktop** | PWA (`:8000`), Streamlit (`:8501`), optional Expo Go shell |
| **Handoff to Maps** | One tap to Google or Apple Maps; optional in-app turn-by-turn (OSRM / Mapbox) |

---

## Quick start

```bash
git clone https://github.com/rsheth8/MyDrive.git
cd MyDrive
./scripts/dev.sh setup      # once: venv, packages, demo data, Expo deps
./scripts/dev.sh mobile     # API + phone PWA → http://localhost:8000
./scripts/dev.sh desktop    # Streamlit dashboard → http://localhost:8501
```

**Health check:** `./scripts/dev.sh check`

| Command | Port | Best for |
|---------|------|----------|
| `./scripts/dev.sh mobile` | **8000** | Phone PWA, passenger mode, voice |
| `./scripts/dev.sh desktop` | **8501** | Laptop demos, full comparison table |
| `./scripts/dev.sh expo` | Expo | Native shell (API should be running) |

More: **[MOBILE.md](MOBILE.md)** · Deploy: **[DEPLOY.md](DEPLOY.md)**

---

## How risk scoring works

```text
Crash + weather CSVs  →  fuse by hour  →  7 ML features  →  XGBoost risk_score (0–1)
                                                              ↓
OpenStreetMap graph  →  nearest-segment risk  ×  weather/time multiplier  →  route "Safest" path
```

**ML features:** hour, day of week, month, precipitation, visibility, wind speed, traffic volume.

**Weather / time multipliers (examples):**

| Factor | Effect |
|--------|--------|
| Night (10pm–5am) | +18% |
| Rush (7–9am, 4–6pm) | +12% |
| Heavy rain (≥ 3 mm/hr) | +45% |
| Low visibility (≤ 3 km) | +28% |
| High traffic proxy (≥ 4000) | +10% |

Demo data: **720 hours** of synthetic Chicagoland crash + weather (regenerate with `scripts/generate_sample_data.py`). Model trains on first run via `./scripts/dev.sh setup`.

---

## Route presets

| Preset | Optimizes for |
|--------|----------------|
| Fastest | Drive time |
| Cheapest | Toll cost (OSM + `config/toll_rates.yaml`) |
| Calm | Lower-stress road types (fewer highways) |
| **Safest** | **ML risk exposure** (weather-adjusted) |
| Steady ETA | More predictable road types |
| Balanced | Mix of all factors |
| Parking-friendly | Near destination parking (OSM) |
| Your pick | Sidebar / API priority (Streamlit & mobile) |

**UI labels (route totals):**

- **Safety:** Low &lt; 0.15 · Moderate 0.15–0.35 · Higher ≥ 0.35 (`risk_exposure`)
- **Feel:** Easy &lt; 0.5 · Mixed 0.5–1.2 · Highway-heavy ≥ 1.2 (`stress_index`)

---

## API

FastAPI on port **8000** — key endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/routes/compare` | POST | Compare routes + `risk` context block |
| `/api/places/autocomplete` | GET | Address suggestions |
| `/api/geocode` | POST | Resolve place → coordinates |
| `/api/navigation/directions` | POST | Turn-by-turn (OSRM / Mapbox) |
| `/api/config` | GET | Presets + brand |

Optional env: copy `.env.example` → `.env` for `MAPBOX_ACCESS_TOKEN`, `TOLLGURU_API_KEY`.

---

## Project structure

```text
MyDrive/
├── config/           # brand, Chicagoland presets, toll rates
├── data/sample/      # demo crash + weather CSVs (committed)
├── mobile/           # PWA (HTML/JS)
├── mobile-native/    # Expo Go app
├── scripts/dev.sh    # main entry: setup | mobile | desktop | expo | check
├── src/
│   ├── api/          # FastAPI
│   ├── app.py        # Streamlit UI
│   ├── risk_engine.py
│   ├── model.py      # XGBoost training
│   └── routing/      # OSMnx graph, scorers, multi-route
└── streamlit_app.py
```

---

## Stack

Python · **XGBoost** · scikit-learn · **OSMnx** · NetworkX · GeoPandas · **FastAPI** · **Streamlit** · Leaflet · Expo

**Data sources:** OpenStreetMap (roads), Photon/Nominatim (geocoding), OSRM (directions), optional Mapbox & TollGuru.

**Not connected yet:** live traffic (`GET /api/traffic/status`), live weather forecasts (uses typical historical or manual inputs).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No virtualenv` | `./scripts/dev.sh setup` |
| Phone can't reach API | Same Wi‑Fi; use your computer's LAN IP, not `localhost` |
| Routes look incomplete | Increase road network buffer (1–8 km) in preferences |
| Expo can't reach API | Run `./scripts/dev.sh mobile` first |

---

## License

See repository license. Built as a portfolio/demo project for Chicagoland driving decisions — not a substitute for professional navigation or safety systems.
