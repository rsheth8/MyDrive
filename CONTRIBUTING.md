# Contributing to MyDrive

## Prerequisites
- Python 3.10+
- Node (only if you run the Expo app)

## Run
```bash
./scripts/dev.sh setup
./scripts/dev.sh desktop    # Streamlit :8501
./scripts/dev.sh mobile     # FastAPI + PWA :8000
./scripts/dev.sh check
```

First run generates synthetic Chicagoland crash/weather data and trains the demo model. No paid API keys required.

## Tests / verify
```bash
./scripts/dev.sh check
```

## Secrets
Optional `.env`: TollGuru, Mapbox. Do not commit keys.
Parked-only if you demo the phone UI.
