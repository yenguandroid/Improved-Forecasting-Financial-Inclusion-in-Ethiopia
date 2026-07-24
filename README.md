# Ethiopia Financial Inclusion Forecast

A project to understand, enrich, and forecast Ethiopia's financial inclusion
trajectory (Access and Usage) using a unified events/observations/targets
dataset and modeled impact relationships.

## Project Status

- [x] Task 1 — Data Exploration and Enrichment
- [ ] Task 2 — (upcoming)
- [ ] Task 3 — (upcoming)

## Project Structure

```
├── .github/workflows/     # CI
├── data/
│   ├── raw/                # Starter dataset (as provided)
│   └── processed/          # Analysis-ready data
├── notebooks/               # Exploration notebooks
├── src/                     # Reusable analysis code
├── dashboard/                # app.py (Streamlit/Dash, upcoming task)
├── tests/                    # Unit tests
├── models/                   # Trained model artifacts (upcoming task)
├── reports/figures/          # Exported charts
├── requirements.txt
└── README.md
```

## Getting Started

```bash
python -m venv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Task 1 Summary

- `notebooks/task1_exploration.ipynb` — schema understanding + exploration
  (record counts by type/pillar/source/confidence, temporal range, indicator
  coverage, event catalog, impact_link review).
- `build_enrichment.py` — adds 8 new observations, 4 new events, and 6 new
  impact_links to the starter dataset, each with a real cited source. Run it
  from the project root:
  ```bash
  python build_enrichment.py
  ```
  Output: `data/processed/ethiopia_fi_unified_data_enriched.xlsx` (+ CSV exports).
- `data_enrichment_log.md` — full documentation of every addition (source,
  exact quote, confidence, rationale), plus a data-quality finding in the
  starter data itself.
- `tests/test_data_loader.py` — validates schema compliance, referential
  integrity (`impact_link.parent_id` -> real event, `related_indicator` ->
  real indicator_code), and that new records are complete.

Run the tests:
```bash
pytest tests/ -v
```
