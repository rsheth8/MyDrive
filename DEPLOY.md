# Deploy MyDrive to Streamlit Community Cloud

## One-time setup

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect the repo.
3. Set **Main file path** to `streamlit_app.py`.
4. (Optional) In **Secrets**, add:
   ```toml
   TOLLGURU_API_KEY = "your-key-here"
   ```

## What runs on first load

The app calls `ensure_demo_pipeline()` which:

- Uses committed files in `data/sample/` if present
- Otherwise generates synthetic data
- Runs ingest → features → model when `fused.csv` / `risk_model.joblib` are missing

First startup may take 1–2 minutes while the model trains on sample data.

## Local deploy test

```bash
./scripts/run_demo.sh
streamlit run streamlit_app.py
```

## Route comparison CLI (resume metrics)

```bash
python scripts/compare_routes.py
python scripts/compare_routes.py --live-tolls   # needs TOLLGURU_API_KEY
python scripts/compare_routes.py --output reports/route_comparison.csv
```

## Notes

- OSMnx downloads OpenStreetMap tiles on first route request (needs network).
- Streamlit Cloud free tier may sleep; cold starts re-run bootstrap.
- For faster cold starts, run `scripts/setup_demo_data.py` locally and commit
  `data/processed/` + `models/` (adjust `.gitignore` if you choose that path).
