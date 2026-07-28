"""
constants.py

Named constants used across src/ and the build pipeline, pulled out of
inline "magic numbers" as part of the Engineering Excellence refactor.
Grouped by the module/concept they originally lived in, so the origin of
each constant is traceable.
"""

# ---------------------------------------------------------------------
# impact_model.py -- ramping / combination
# ---------------------------------------------------------------------
DEFAULT_RAMP_MONTHS: float = 6.0
RAMP_MONTHS_BY_RELATIONSHIP: dict = {
    "direct": 3.0,
    "indirect": 9.0,
    "enabling": 12.0,
}
MAGNITUDE_FALLBACK_PP: dict = {"low": 2.0, "medium": 6.0, "high": 12.0}
DEFAULT_MAGNITUDE_FALLBACK_PP: float = 6.0
DAYS_PER_MONTH: float = 30.4375  # 365.25 / 12, accounts for leap years
SHARED_CEILING_PCT: float = 100.0  # default saturation ceiling for combine_effects()

# Groups of impact_link record_ids that compete for the same underlying
# adopter pool on a given target indicator (see impact_model.combine_effects).
COMPETING_LINK_GROUPS: dict = {
    "ACC_MM_ACCOUNT": [("IMP_0021", "IMP_0007")],  # Telebirr vs. M-Pesa
}

# ---------------------------------------------------------------------
# forecasting.py -- trend fitting / scenarios
# ---------------------------------------------------------------------
DAYS_PER_YEAR: float = 365.25
DEFAULT_PREDICTION_ALPHA: float = 0.05  # 95% prediction interval
DEFAULT_OPTIMISTIC_MULTIPLIER: float = 1.5
DEFAULT_PESSIMISTIC_MULTIPLIER: float = 0.5
PERCENTAGE_CLIP_RANGE: tuple = (0.0, 100.0)

# ---------------------------------------------------------------------
# Policy targets / business context
# ---------------------------------------------------------------------
NFIS2_ACCESS_TARGET_PCT: float = 70.0
NFIS2_TARGET_YEAR: int = 2025

# ---------------------------------------------------------------------
# validate.py
# ---------------------------------------------------------------------
KNOWN_MISSING_SOURCE_URL: set = {"REC_0013", "REC_0020", "REC_0023", "REC_0024", "REC_0025"}

# ---------------------------------------------------------------------
# refresh_data.py
# ---------------------------------------------------------------------
PIPELINE_STAGE_SCRIPTS: list = [
    ("build_enrichment.py", "ethiopia_fi_unified_data_enriched.xlsx"),
    ("build_impact_refinements.py", "ethiopia_fi_unified_data_final.xlsx"),
    ("build_task4_targets.py", "ethiopia_fi_unified_data_task4.xlsx"),
    ("build_quality_trust_enrichment.py", "ethiopia_fi_unified_data_quality_trust.xlsx"),
]
FINAL_DATASET_FILENAME: str = "ethiopia_fi_unified_data_quality_trust.xlsx"

# ---------------------------------------------------------------------
# explainability.py
# ---------------------------------------------------------------------
SHAP_RANDOM_STATE: int = 42
SHAP_N_ESTIMATORS: int = 200
SHAP_MAX_DEPTH: int = 3
