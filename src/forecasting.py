"""
forecasting.py

Trend regression (linear and log) with prediction intervals, plus
event-augmented and scenario forecasting, built for Task 4's two targets:
Account Ownership Rate (Access) and Digital Payment Usage (Usage).

Design notes (see notebooks/task4_forecasting.ipynb for full discussion):
  - With only 4 (Access) or 2 (Usage) historical points, classical OLS
    prediction intervals are used where they are at least computable
    (Access, df=2) but are explicitly flagged as approximate/optimistic
    given so few degrees of freedom. For Usage (n=2, df=0), no valid
    statistical interval exists at all -- a scenario range is used instead
    and this is stated plainly rather than a fake interval being shown.
  - "Event-augmented" forecasts add only the INCREMENTAL portion of an
    event's effect that has not yet materialized as of the last real
    observation -- i.e. effect_at(forecast_date) - effect_at(last_obs_date)
    for each relevant event -- so that already-realized historical effects
    (baked into the trend line the regression already fits) are not
    double-counted on top of themselves.
"""
from dataclasses import dataclass
from typing import List, Optional, Sequence
import numpy as np
import pandas as pd
import statsmodels.api as sm

from constants import DAYS_PER_YEAR, DEFAULT_PREDICTION_ALPHA, PERCENTAGE_CLIP_RANGE
from config import ScenarioConfig


def _decimal_year(date: pd.Timestamp) -> float:
    year_start = pd.Timestamp(year=date.year, month=1, day=1)
    year_end = pd.Timestamp(year=date.year + 1, month=1, day=1)
    return date.year + (date - year_start) / (year_end - year_start)


@dataclass
class TrendFit:
    kind: str                 # "linear" or "log"
    model: object              # fitted statsmodels OLS results
    x0: float                  # reference x-value (first observation's decimal year)

    def _x_for(self, date: pd.Timestamp) -> float:
        dy = _decimal_year(date)
        if self.kind == "linear":
            return dy
        # log-linear: x = log(years since first observation + 1)
        return np.log(max(dy - self.x0, 0) + 1)

    def predict(self, dates: Sequence[pd.Timestamp], alpha: float = DEFAULT_PREDICTION_ALPHA) -> pd.DataFrame:
        """Point forecast + (1-alpha) prediction interval for each date."""
        xs = [self._x_for(d) for d in dates]
        X = sm.add_constant(np.array(xs), has_constant="add")
        pred = self.model.get_prediction(X)
        frame = pred.summary_frame(alpha=alpha)
        return pd.DataFrame({
            "date": dates,
            "point": frame["mean"].values,
            "ci_lower": frame["obs_ci_lower"].values,
            "ci_upper": frame["obs_ci_upper"].values,
        })


def fit_linear_trend(dates: Sequence[pd.Timestamp], values: Sequence[float]) -> TrendFit:
    """OLS of value ~ decimal_year."""
    dates = list(dates)
    x0 = _decimal_year(dates[0])
    xs = np.array([_decimal_year(d) for d in dates])
    X = sm.add_constant(xs)
    model = sm.OLS(np.array(values), X).fit()
    return TrendFit(kind="linear", model=model, x0=x0)


def fit_log_trend(dates: Sequence[pd.Timestamp], values: Sequence[float]) -> TrendFit:
    """OLS of value ~ log(years_since_first_observation + 1) -- a
    concave (diminishing-returns) trend shape, consistent with observed
    deceleration in Access growth."""
    dates = list(dates)
    x0 = _decimal_year(dates[0])
    xs = np.array([np.log(max(_decimal_year(d) - x0, 0) + 1) for d in dates])
    X = sm.add_constant(xs)
    model = sm.OLS(np.array(values), X).fit()
    return TrendFit(kind="log", model=model, x0=x0)


def incremental_event_effect(effects: List, last_obs_date: pd.Timestamp, forecast_date: pd.Timestamp) -> float:
    """
    The portion of an event's effect that materializes AFTER last_obs_date
    and by forecast_date -- i.e. effect not yet visible in the historical
    data the trend was fit on, so it can be safely added on top of the
    trend forecast without double-counting.
    """
    total = 0.0
    for e in effects:
        already_realized = e.effect_at(last_obs_date)
        by_forecast = e.effect_at(forecast_date)
        total += (by_forecast - already_realized)
    return total


def growth_rate_scenario(base_value: float, base_date: pd.Timestamp, forecast_dates: Sequence[pd.Timestamp],
                          annual_growth_pp: dict, clip: Optional[tuple] = PERCENTAGE_CLIP_RANGE) -> pd.DataFrame:
    """
    For indicators with too few historical points for a meaningful OLS
    prediction interval (e.g. n=2, zero residual degrees of freedom --
    statsmodels will return NaN/undefined intervals in this case, correctly
    signaling that no valid interval exists), build a scenario range from
    explicit, documented annual growth-rate assumptions instead of a
    fabricated statistical interval.

    annual_growth_pp: dict with keys "pessimistic", "base", "optimistic",
    each a flat percentage-point-per-year growth assumption.
    """
    rows = []
    for d in forecast_dates:
        years_elapsed = (d - base_date).days / DAYS_PER_YEAR
        row = {"date": d}
        for label, rate in annual_growth_pp.items():
            v = base_value + rate * years_elapsed
            if clip is not None:
                v = float(np.clip(v, *clip))
            row[label] = v
        rows.append(row)
    return pd.DataFrame(rows)


def scenario_table(trend: TrendFit, forecast_dates: Sequence[pd.Timestamp], last_obs_date: pd.Timestamp,
                    events_effects: Optional[List] = None, optimistic_multiplier: float = ScenarioConfig().optimistic_multiplier,
                    pessimistic_multiplier: float = ScenarioConfig().pessimistic_multiplier,
                    clip: Optional[tuple] = PERCENTAGE_CLIP_RANGE) -> pd.DataFrame:
    """
    Build baseline / with-events / optimistic / base / pessimistic
    forecasts for a set of forecast_dates.

    - Baseline: trend continuation only (regression point + CI), no events.
    - With-events: baseline point forecast + incremental event effects.
    - Base scenario: same as with-events (this project's central estimate).
    - Optimistic: with-events + optimistic_multiplier x the event effect,
      using the trend's upper CI bound as the starting point.
    - Pessimistic: with-events using pessimistic_multiplier x the event
      effect (partial realization), using the trend's lower CI bound.
    """
    events_effects = events_effects or []
    base_pred = trend.predict(forecast_dates)

    rows = []
    for i, d in enumerate(forecast_dates):
        point = base_pred["point"].iloc[i]
        lo = base_pred["ci_lower"].iloc[i]
        hi = base_pred["ci_upper"].iloc[i]
        incr = incremental_event_effect(events_effects, last_obs_date, d)

        baseline = point
        with_events = point + incr
        optimistic = hi + incr * optimistic_multiplier
        pessimistic = lo + incr * pessimistic_multiplier

        if clip is not None:
            baseline, with_events, optimistic, pessimistic = [
                float(np.clip(v, *clip)) for v in (baseline, with_events, optimistic, pessimistic)
            ]
            lo, hi = float(np.clip(lo, *clip)), float(np.clip(hi, *clip))

        rows.append({
            "date": d, "baseline_trend": baseline, "trend_ci_lower": lo, "trend_ci_upper": hi,
            "incremental_event_effect": incr, "with_events_base_scenario": with_events,
            "optimistic": optimistic, "pessimistic": pessimistic,
        })
    return pd.DataFrame(rows)
