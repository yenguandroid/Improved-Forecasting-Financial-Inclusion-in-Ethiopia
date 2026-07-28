"""
config.py

Dataclasses for configuration objects, replacing loose dicts/kwargs that
were previously passed around as plain arguments -- part of the Engineering
Excellence refactor. Each groups related settings for one part of the
pipeline so a caller can construct, inspect, and pass around one typed
object instead of several loose parameters.
"""
from dataclasses import dataclass, field
from typing import Optional

from constants import (
    DEFAULT_OPTIMISTIC_MULTIPLIER, DEFAULT_PESSIMISTIC_MULTIPLIER,
    PERCENTAGE_CLIP_RANGE, DEFAULT_PREDICTION_ALPHA, SHARED_CEILING_PCT,
    SHAP_RANDOM_STATE, SHAP_N_ESTIMATORS, SHAP_MAX_DEPTH,
)


@dataclass(frozen=True)
class ScenarioConfig:
    """Settings controlling how optimistic/base/pessimistic scenarios are
    built on top of a fitted trend (see forecasting.scenario_table)."""
    optimistic_multiplier: float = DEFAULT_OPTIMISTIC_MULTIPLIER
    pessimistic_multiplier: float = DEFAULT_PESSIMISTIC_MULTIPLIER
    clip_range: tuple = PERCENTAGE_CLIP_RANGE
    prediction_alpha: float = DEFAULT_PREDICTION_ALPHA


@dataclass(frozen=True)
class GrowthRateScenarioConfig:
    """Explicit, stated annual growth-rate assumptions (percentage points
    per year) for indicators with too few points for a real OLS prediction
    interval -- see forecasting.growth_rate_scenario. Replaces the
    previously ad-hoc {"pessimistic": .., "base": .., "optimistic": ..}
    dict literal that was inlined in the forecasting notebook."""
    pessimistic_pp_per_year: float
    base_pp_per_year: float
    optimistic_pp_per_year: float
    clip_range: tuple = PERCENTAGE_CLIP_RANGE

    def as_dict(self) -> dict:
        return {
            "pessimistic": self.pessimistic_pp_per_year,
            "base": self.base_pp_per_year,
            "optimistic": self.optimistic_pp_per_year,
        }


# The Usage scenario's growth-rate assumptions, previously a bare dict
# literal inlined in notebooks/task4_forecasting.ipynb. Recalibrated to the
# observed 2021-2024 pace after the Enhancement 1 Findex correction (see
# data_quality_note_findex2025_verification.md for why 0.24, not the older
# 0.35, is now the historically-accurate "base" rate).
USAGE_SCENARIO_CONFIG = GrowthRateScenarioConfig(
    pessimistic_pp_per_year=0.0,
    base_pp_per_year=0.24,
    optimistic_pp_per_year=1.5,
)


@dataclass(frozen=True)
class RampConfig:
    """How an event's effect ramps in over time (see impact_model.EventEffect).
    Groups lag/ramp-window settings that were previously separate loose
    fields on every call site."""
    lag_months: float = 0.0
    ramp_months: float = 6.0


@dataclass(frozen=True)
class CombinationConfig:
    """Settings for how multiple events' effects on the same indicator are
    combined (see impact_model.combine_effects)."""
    indicator_code: Optional[str] = None
    ceiling: float = SHARED_CEILING_PCT


@dataclass(frozen=True)
class ExplainerConfig:
    """Settings for the SHAP explainer model (see explainability.py)."""
    random_state: int = SHAP_RANDOM_STATE
    n_estimators: int = SHAP_N_ESTIMATORS
    max_depth: int = SHAP_MAX_DEPTH
