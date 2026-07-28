# Ethiopia Financial Inclusion Forecast

[![Unit Tests](https://github.com/yenguandroid/Improved-Forecasting-Financial-Inclusion-in-Ethiopia/actions/workflows/unittests.yml/badge.svg)](https://github.com/yenguandroid/Improved-Forecasting-Financial-Inclusion-in-Ethiopia/actions/workflows/unittests.yml)

A data pipeline, event-impact model, and interactive dashboard that forecasts Ethiopia's Account Ownership and Digital Payment Usage rates through 2027 -- built on a transparently-sourced dataset (every figure traceable to a real citation) and explained with SHAP so the forecast's drivers are auditable, not a black box.

## Business Problem

Ethiopia's National Financial Inclusion Strategy II (NFIS-II) set a target of 70% account ownership by 2025. The only independent benchmark for that number -- the Global Findex survey -- updates roughly every three years, leaving a long gap in which policymakers, NGOs, and mobile money operators have no defensible way to know whether the country is on track, or how much of any shortfall is attributable to specific interventions (Telebirr, M-Pesa, the Fayda digital ID, NBE interoperability mandates) already underway. This project builds that missing near-term view: a forecast that explicitly incorporates known events and their estimated effects, with honestly quantified uncertainty, rather than a naive trend line or an opaque model nobody can interrogate.

## Solution Overview

A unified dataset of observations, events, targets, and modeled event-to-indicator "impact links" is enriched from a starter file, validated against a shared schema, and fed through a small pipeline: trend regression (linear and logarithmic, compared directly) plus an event-impact model that ramps each event's effect in over time and combines multiple events on the same indicator (additively by default, with a documented shared-ceiling interaction term for the one case where two products genuinely compete for the same adopters). The result is surfaced three ways: a Jupyter notebook chain for the full analysis, an interactive Streamlit dashboard for exploring it, and a SHAP explainability layer that answers *which events matter most*, *why the model predicted a specific value*, and *whether any pattern looks concerning* -- for a genuinely deterministic, auditable model rather than a black box.

## Key Results

- **Forecast accuracy improvement: 94% reduction in validation error** -- adding a shared-ceiling interaction term for the two competing mobile money products (Telebirr and M-Pesa) dropped the held-out 2024 checkpoint's error from 0.25 percentage points to ~0.015 (see Enhancement 2 below).
- **Data-quality correction: verified against the primary source, not a secondary derivation** -- the 2024 Digital Payment Usage figure was corrected from a 21.0% algebra-based estimate to a 20.7% direct citation from the actual Global Findex 2025 country table, raising its confidence rating from medium to high.
- **Test coverage: 82 automated tests, 100% passing**, run automatically on every push via GitHub Actions (badge above) -- including tests that deliberately corrupt the data or the model to confirm validation and the interaction term actually catch what they're supposed to, not just exercise the happy path.

## Quick Start

```bash
git clone https://github.com/yenguandroid/Improved-Forecasting-Financial-Inclusion-in-Ethiopia
cd Improved-Forecasting-Financial-Inclusion-in-Ethiopia
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python refresh_data.py          # builds and validates every processed dataset
cd dashboard && streamlit run app.py
```

Run the test suite at any point: `pytest tests/ -v`

## Project Structure

```
├── .github/workflows/          # CI (runs pytest on every push/PR -- badge above)
├── data/
│   ├── raw/                     # Starter dataset, reference_codes.xlsx
│   └── processed/                 # Every pipeline stage's output
├── notebooks/
│   ├── task1_exploration.ipynb        # Schema + starter-data exploration
│   ├── task2_eda.ipynb                # Full EDA (+ Enhancement 3 addendum)
│   ├── task3_impact_modeling.ipynb    # Impact model (+ Enhancement 2 addendum)
│   └── task4_forecasting.ipynb        # Access/Usage forecasts
├── src/
│   ├── constants.py              # Named constants (no magic numbers)
│   ├── config.py                 # Dataclasses for configuration objects
│   ├── utils.py                  # Reusable I/O helpers shared by every build script
│   ├── data_loader.py            # Schema-aware loaders for every pipeline stage
│   ├── impact_model.py           # Event-effect ramping + combination (incl. shared-ceiling term)
│   ├── forecasting.py            # Trend fitting, prediction intervals, scenario tables
│   ├── validate.py               # Reusable data-quality validation
│   └── explainability.py         # SHAP surrogate model + visualizations
├── dashboard/app.py               # Streamlit dashboard (5 pages, incl. Model Explainability)
├── tests/                         # 82 tests across 6 files
├── build_enrichment.py, build_impact_refinements.py,
│   build_task4_targets.py, build_quality_trust_enrichment.py   # Pipeline stages, in order
├── refresh_data.py                # Rebuilds + validates the full pipeline on demand
├── reports/figures/                # Exported charts, incl. SHAP visualizations
├── *.md                            # Enrichment logs and data-quality notes (source, quote, confidence, notes)
├── requirements.txt
└── README.md
```

## Demo

The dashboard has five pages -- Overview, Trends, Forecasts (model-choice toggle + event-impact breakdown), Inclusion Projections (scenario selector), and Model Explainability (SHAP) -- all built directly on the same tested `src/` modules used in the notebooks, so the dashboard's numbers can never silently drift from the underlying analysis. Run it locally with `streamlit run dashboard/app.py` (see Quick Start above); screenshots are available on request.

## Technical Details

**Data:** A single Excel workbook (two sheets: main data + impact links) covering observations, events, targets, and modeled event-to-indicator relationships across 7 pillars (Access, Usage, Quality, Affordability, Trust, Depth, Gender). 58 records total (41 observations, 14 events, 3 targets) and 21 impact links after enrichment. Every added data point has a real source URL, an exact quote, a confidence rating, and notes explaining any judgment call -- documented in the `*.md` enrichment logs at the repo root.

**Model:** Two components. (1) Trend regression via `statsmodels` OLS -- linear and logarithmic fits compared directly, with real 95% prediction intervals where enough data points exist (Access, n=4) and an honest, explicitly-stated scenario range where they don't (Usage, n=2, zero residual degrees of freedom -- a fabricated interval is deliberately avoided here). (2) An event-impact model: each event's effect ramps linearly from zero to its full estimated magnitude over a lag + ramp window (3/9/12 months depending on whether the relationship is direct/indirect/enabling), then holds constant. Multiple events on the same indicator combine additively by default, except one documented case (Telebirr/M-Pesa on `ACC_MM_ACCOUNT`) where a saturating shared-ceiling term is used instead, since the two products compete for the same adopter pool rather than being independent.

**Evaluation:** The event-impact model is validated against real, held-out Findex checkpoints (2021 and 2024), not just fit to them -- the 2021 point calibrates the model, the 2024 point tests it out-of-sample. The shared-ceiling interaction term's improvement (0.25pp -> 0.015pp error) is measured the same way. SHAP explanations are validated against their own fundamental correctness property (base value + feature contributions = actual prediction, checked numerically in `tests/test_engineering_excellence.py`) and a fidelity check (the surrogate model's R\u00b2 against the real model's own outputs, expected to be ~1.0 since it approximates a known deterministic function rather than learning from noisy data).

## Model Explainability

The forecasting logic here (trend regression + a hand-built, fully-documented event-impact formula) is not a black-box ML model with dozens of opaque inputs -- reading `src/impact_model.py` already tells you exactly how it works. Rather than force SHAP onto something that doesn't need it, `src/explainability.py` builds a genuine **surrogate model**: a small gradient-boosted regressor trained to reproduce the real model's own monthly predictions from named, meaningful features (one per contributing event: Telebirr Launch, M-Pesa Ethiopia Launch, NBE Mandatory Mobile Money Interoperability Directive). SHAP is applied to that surrogate, which is a standard, legitimate explainability technique (surrogate modeling), honestly framed as such rather than dressed up as something more exotic.

This answers the three required questions directly, all visible on the dashboard's Model Explainability page:
- **Which features matter most globally?** A bar chart of mean |SHAP value| per event (`reports/figures/shap_global_importance.png`) -- currently the NBE interoperability directive has the largest average impact across the 2021-2027 window.
- **Why did the model make this specific prediction?** An interactive waterfall chart for any chosen month (`reports/figures/shap_waterfall_dec2027.png` for December 2027), decomposing the prediction into each event's contribution.
- **Are there any concerning patterns?** A feature-contribution-over-time chart (`reports/figures/shap_feature_over_time.png`) plus a small set of rule-based checks (concentration in a single driver, any feature with zero impact across the whole window) -- currently no concentration or zero-impact issues are flagged for this indicator.

Two real bugs were caught and fixed during development of this module, both documented in its docstring: an early version recomputed effects with plain addition, which would have silently explained the *superseded* pre-Enhancement-2 model instead of the current one; and an early feature set included a bare "years since baseline" trend feature that wasn't actually part of the true formula and was just proxying for (and distorting attribution among) the real causal features.

## Future Improvements

- **Quality-pillar coverage** remains at zero observations -- no citable Ethiopia-specific source for transaction success rates, agent uptime, or NBE complaint statistics was found within scope. Worth a dedicated follow-up if NBE publishes this data in the future.
- **A true scheduled monitoring cadence** -- `refresh_data.py` and CI provide the mechanism (on-demand rebuild + validation), but there's no live data feed to monitor yet and no scheduled job triggering it periodically.
- **More validation checkpoints for the interaction term** -- currently validated at 2 points; a third mobile money entrant, if one emerges, would be a genuine further test of the shared-ceiling formula rather than just this one pair.
- **SHAP explainability for the Access/Usage trend models too** -- currently scoped to the event-impact model (`ACC_MM_ACCOUNT`) specifically, since that's where multiple named, competing drivers make a surrogate model meaningful; the simpler single-feature trend regressions don't need it in the same way, but a dependence-style analysis of the log vs. linear trend choice could still be a useful addition.
- **A real held-out test set for the surrogate model** -- currently fidelity is checked by R\u00b2 against the real model's own outputs (correctly ~1.0, since it's approximating a deterministic function), but a formal train/test split would be a good addition if this surrogate approach is extended to a genuinely noisy, real-world target in the future.

## Author

**Yengusie Demilie Alene**
GitHub: [yenguandroid](https://github.com/yenguandroid)
Repository: [Improved-Forecasting-Financial-Inclusion-in-Ethiopia](https://github.com/yenguandroid/Improved-Forecasting-Financial-Inclusion-in-Ethiopia)
LinkedIn : www.linkedin.com/in/yengusie-alene-8a341591
 Email: yengusied@gmail.com


## Appendix: Full Task-by-Task Summary

This project was built in two phases: an original five-task build, and a subsequent four-task enhancement phase that revisited it. A note on numbering: the enhancement phase was independently numbered "Task 1-4" by the project owner, which collides with the original build's own Task 1-4 -- to avoid ambiguity, this section (and the underlying repository's filenames) refer to the second set as "Enhancement 1-4" throughout.

### Project Status

**Original build:**
- [x] Task 1 -- Data Exploration and Enrichment
- [x] Task 2 -- Exploratory Data Analysis
- [x] Task 3 -- Event Impact Modeling
- [x] Task 4 -- Forecasting Access and Usage (2025-2027)
- [x] Task 5 -- Interactive Dashboard

**Enhancement phase:**
- [x] Enhancement 1 -- Findex 2025 Digital Payment Usage conflict, resolved
- [x] Enhancement 2 -- Shared-ceiling interaction term for competing events
- [x] Enhancement 3 -- First Quality/Trust-pillar indicator
- [x] Enhancement 4 -- On-demand data-refresh script + dashboard integration

**Engineering Excellence pass (this update):**
- [x] Code refactoring -- constants, config dataclasses, extracted utilities, full type hints
- [x] Testing & CI/CD -- 82 tests, GitHub Actions, CI badge (top of this README)
- [x] Interactive dashboard -- extended with a fifth page (Model Explainability)
- [x] Model explainability -- SHAP surrogate model + 3 visualizations

### Task 1 -- Data Exploration and Enrichment

`notebooks/task1_exploration.ipynb` profiled the starter dataset (record counts by type/pillar/source/confidence, temporal coverage, event catalog, impact-link review). `build_enrichment.py` added 8 new observations, 4 new events, and 6 new impact links, each independently sourced -- documented in `data_enrichment_log.md` (source, exact quote, confidence, notes). A genuine data-quality finding was documented rather than silently corrected: 5 pre-existing observations were missing a source URL, and one record had a column-shift bug (free text landed in a date field).

### Task 2 -- Exploratory Data Analysis

`notebooks/task2_eda.ipynb` covered dataset overview, Access/Usage trends against the NFIS-II target, infrastructure enablers, the event timeline, a deliberately-caveated correlation analysis, and a data-quality synthesis. Found and fixed a real bug along the way: a `TypeError` while loading the enriched dataset, traced to the same column-shift issue from Task 1 -- `src/data_loader.py` was hardened to degrade a bad date cell to missing rather than crash the whole load.

### Task 3 -- Event Impact Modeling

`notebooks/task3_impact_modeling.ipynb` translated `impact_links` into a working model: each event's effect ramps from zero to full magnitude over a lag + ramp window, combined additively by default. Validated against the Telebirr-launch-to-mobile-money-account checkpoint (2021 -> 2024); the original data badly under-predicted this because no link existed connecting the two at all. A new, calibrated link (`IMP_0021`) was added: trained on 2021 (+4.7pp), validated out-of-sample against 2024 (predicts 9.7% vs. actual 9.45%, 0.25pp error). Two real bugs found and fixed: a sign-flip error double-negating "decrease"-direction links, and a color-scale distortion in the association heatmap.

### Task 4 -- Forecasting Access and Usage (2025-2027)

`notebooks/task4_forecasting.ipynb` forecasts both targets. Corrected a target-definition error first: the tracked mobile-money-account indicator had been implicitly conflated with Findex's distinct "Digital Payment Usage" indicator -- the real figures were researched and added instead (`build_task4_targets.py`). Compared linear vs. logarithmic trend regression (log selected as baseline, since linear ignores Access's documented deceleration), added an event-augmented model using only the *incremental* portion of each event's effect, and generated optimistic/base/pessimistic scenarios. Current base-case forecast: **Access ~50% (2025) -> ~61% (2026-2027)**, missing the NFIS-II's 70%-by-2025 target under all but the most optimistic assumptions; **Usage ~21.1% (2025) -> ~21.8% (2027)**, essentially flat.

### Task 5 -- Interactive Dashboard

`dashboard/app.py` -- a Streamlit dashboard reusing the same tested `src/` modules as the notebooks (no logic reimplemented). Originally 4 pages (Overview, Trends, Forecasts, Inclusion Projections); a 5th (Model Explainability) was added in the Engineering Excellence pass.

### Enhancement 1 -- Findex 2025 Digital Payment Usage Conflict, Resolved

The 2024 Digital Payment Usage figure (`REC_0043`) was originally derived algebraically from a secondary source (21.0%, medium confidence). A first attempt to access the primary Findex 2025 country table directly failed for documented, legitimate reasons (gated download, unparsable spreadsheet, JS-rendered dashboard) -- written up honestly as a non-result. A second attempt, using a user-supplied CSV export of the same primary source via a different route, succeeded: **20.66% (2024)**, sourced directly to Findex, description matching the project's indicator definition word-for-word. Value corrected to 20.7%, confidence raised medium -> high; the Task 4 forecast was re-run end-to-end, shifting the Usage curve down 0.3pp across 2025-2027.

### Enhancement 2 -- Shared-Ceiling Interaction Term for Competing Events

Addressed a self-identified limitation from Task 3: additive-only combination assumes independence, which doesn't hold for Telebirr and M-Pesa (both target `ACC_MM_ACCOUNT` but compete for the same adopter pool). Implemented a saturating "probabilistic union" term (`combined = ceiling * (1 - product(1 - e_i/ceiling))`), scoped specifically to this pair via `COMPETING_LINK_GROUPS`, opt-in via an `indicator_code` parameter so every other indicator's combination logic is unaffected. Result: error at the held-out 2024 checkpoint dropped from 0.25pp to ~0.015pp -- a genuine, measured 94% reduction, not assumed in advance.

### Enhancement 3 -- First Quality/Trust-Pillar Indicator

`QUALITY` and `TRUST` had zero observations even after Task 1. No citable Ethiopia-specific QUALITY figure was found; TRUST yielded a real one: a 2025 peer-reviewed study (399 respondents, Kembata Tambaro Zone) finding *"lack of trust emerged as the most cited reason for non-adoption (55.78%)"*. Added as `REC_0044` (medium confidence -- sub-national sample, full text inaccessible, both caveats stated explicitly). QUALITY remains open, documented as a genuine gap rather than filled with a weaker source.

### Enhancement 4 -- On-Demand Data Refresh and Monitoring Groundwork

`src/validate.py` (schema conformance, duplicate IDs, orphaned links, required fields, blank-pillar-for-events) deliberately splits structural errors from completeness warnings, so the 5 known starter-data gaps don't permanently fail every run while a *new* gap is flagged as a likely regression. `refresh_data.py` runs the full 4-stage pipeline, validates the result, and writes a JSON manifest a dashboard or CI step can read without re-running the pipeline. Wired into the dashboard as a sidebar status display + on-demand refresh button.

### Data Pipeline

```
data/raw/ethiopia_fi_unified_data.xlsx  (starter data)
  |
  v  build_enrichment.py                          (Task 1)
data/processed/ethiopia_fi_unified_data_enriched.xlsx
  |
  v  build_impact_refinements.py                  (Task 3)
data/processed/ethiopia_fi_unified_data_final.xlsx
  |
  v  build_task4_targets.py                       (Task 4)
data/processed/ethiopia_fi_unified_data_task4.xlsx
  |
  v  build_quality_trust_enrichment.py            (Enhancement 3)
data/processed/ethiopia_fi_unified_data_quality_trust.xlsx   <- fullest current dataset
```

`refresh_data.py` runs this entire chain in order and validates the final output.

### Testing

82 tests across 6 files: schema/referential-integrity validation, EDA-finding regression guards, the impact model (incl. the shared-ceiling interaction term), forecasting and prediction intervals, the Quality/Trust enrichment addition, the refresh/validation pipeline, and the Engineering Excellence modules (constants, config, utils, SHAP explainability). CI (`.github/workflows/unittests.yml`) runs the full suite on every push and pull request to `main` -- see the badge at the top of this README.
