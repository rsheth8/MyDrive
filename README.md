# SafePath

**Per-road-segment accident risk prediction + risk-weighted route planning.**

SafePath fuses crash data with hour-aligned weather features, trains a gradient
boosted classifier to estimate the probability of an accident at a given
location and time, then re-weights an OpenStreetMap road graph by predicted
risk so a routing engine prefers safer paths to the destination.

The full pipeline runs end-to-end with three Python entrypoints and surfaces in
a Streamlit dashboard with a Folium risk heatmap and an interactive safe-route
planner.

---

## What's in the box

| Layer | What it does | Where |
|---|---|---|
| **Ingest** | Loads crash CSV + weather CSV, does an hourly temporal join, writes a fused dataset | `src/ingest.py` |
| **Features** | Builds the model-ready feature table (lat/lon binning, weather, time-of-day, etc.) | `src/features.py` |
| **Model** | Trains an XGBoost binary classifier (`accident` ~ features), evaluates ROC-AUC, persists with `joblib` | `src/model.py` |
| **App** | Streamlit UI: risk heatmap (Folium + `HeatMap`) and risk-weighted shortest-path routing on an OSMnx graph | `src/app.py` |

### How "safer route" actually works

`src/app.py` builds an OSMnx street graph for the area of interest, joins the
nearest model-predicted risk score onto each edge, and weights every edge as:

```
risk_weight = length × (1 + risk_score)
```

Then it runs `networkx.shortest_path(weight="risk_weight")` between origin and
destination, falling back to plain shortest-by-length if a routing exception is
raised. The result is a path that detours around high-risk segments when the
detour cost is justified.

---

## Quick start

```bash
# 1. Environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Data — drop your CSVs here:
#    data/crash.csv     timestamp, latitude, longitude, [accident]
#    data/weather.csv   timestamp, precipitation, visibility, wind_speed

# 3. Pipeline
python src/ingest.py     # → data/processed/fused.csv
python src/features.py   # → data/processed/features.csv
python src/model.py      # → models/risk_model.joblib (prints ROC-AUC)

# 4. App
streamlit run src/app.py
```

---

## Data contract

The pipeline assumes two CSVs in `data/`:

**`crash.csv`**
```
timestamp,latitude,longitude,accident
2023-01-04T08:00:00,44.9778,-93.2650,1
...
```
`accident` is optional during ingest — if missing, the dataset is treated as
"events occurred here" and the negative class is built from a contrasting
sample. With `accident` present, supervised training is direct.

**`weather.csv`**
```
timestamp,precipitation,visibility,wind_speed
2023-01-04T08:00:00,0.4,7.2,11.3
...
```
The temporal join is hour-level, so weather rows are aligned by truncating
both sides to the hour. Add spatial joins (mapping events onto road segments
with GeoPandas / OSMnx) for finer granularity.

---

## Project layout

```
SafePath/
├── data/
│   ├── crash.csv               # raw — bring your own
│   ├── weather.csv             # raw — bring your own
│   └── processed/
│       ├── fused.csv
│       └── features.csv
├── models/
│   └── risk_model.joblib       # produced by src/model.py
├── notebooks/                  # EDA + experiments
├── src/
│   ├── ingest.py               # hourly join: crash + weather → fused
│   ├── features.py             # feature engineering pipeline
│   ├── model.py                # XGBoost training + evaluation + persistence
│   ├── app.py                  # Streamlit + Folium + OSMnx + NetworkX
│   └── utils.py
├── templates/                  # optional Flask HTML scaffolding
├── requirements.txt
└── README.md
```

---

## Stack

- **Modeling**: XGBoost (`XGBClassifier`, 300 estimators, `binary:logistic`,
  `eval_metric="auc"`), scikit-learn for splits and metrics
- **Geospatial**: GeoPandas, Shapely, PyProj, OSMnx for graph construction
- **Routing**: NetworkX shortest path on a risk-weighted edge graph
- **App**: Streamlit, Folium (`HeatMap`), `streamlit-folium`
- **Explainability**: SHAP (importable; wire up per use case)

---

## Notes / known limitations

- The current `ingest.py` join is purely temporal at the hour level — no spatial
  join. Two events at different intersections in the same hour share a weather
  row. For city-scale modeling you want to map both sides onto road segments
  first.
- The fallback `networkx.shortest_path` (used if the risk-weighted path raises)
  optimizes for distance only — useful as a safety net but masks model issues
  in production. Log the fallback rate in real deployments.
- ROC-AUC alone is a thin evaluation. For routing decisions, calibration and
  per-segment precision matter more than aggregate AUC; treat the printed
  number as a sanity check, not a verdict.
