"""
impact_model.py

Translates impact_link records (event -> indicator relationships) into a
simple, transparent time-dynamic model that can predict how an indicator
moves in response to one or more events.

Modeling convention (documented in notebooks/task3_impact_modeling.ipynb):
  - `impact_estimate` is interpreted as an absolute change in the indicator's
    own unit: percentage points for `percentage`/`gap_pp` value_types, and
    absolute counts/currency for `count`/`currency_etb` value_types.
  - An event's effect on an indicator does NOT appear immediately. It is
    zero until `lag_months` after the event date, then ramps up LINEARLY
    over a `ramp_months` window to its full estimated value, and holds at
    that full value afterward (a "ramped step" function). This reflects
    behavioral/adoption responses building gradually rather than jumping
    instantly, while still respecting the lag before any effect begins.
  - `ramp_months` defaults to 6, but is shortened for `direct` relationships
    (effects show up faster) and lengthened for `enabling` relationships
    (effects require a downstream product/behavior change first).
  - Effects from multiple events on the same indicator are combined
    ADDITIVELY by default (independent, no interaction/saturation terms) --
    a deliberate simplification, documented as a limitation.
  - EXCEPTION: effects explicitly flagged as "competing" for the same
    indicator (see `COMPETING_LINK_GROUPS`) are combined via a saturating
    shared-ceiling term instead of raw addition -- see `combine_effects()`.
    Implemented so far for exactly one pair: the Telebirr (IMP_0021) and
    M-Pesa (IMP_0007) links on ACC_MM_ACCOUNT, which compete for the same
    underlying pool of adults adopting mobile money rather than being
    independent, additive drivers.
"""
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd

from constants import (
    DEFAULT_RAMP_MONTHS, RAMP_MONTHS_BY_RELATIONSHIP, MAGNITUDE_FALLBACK_PP,
    DEFAULT_MAGNITUDE_FALLBACK_PP, DAYS_PER_MONTH, SHARED_CEILING_PCT,
    COMPETING_LINK_GROUPS,
)
from config import RampConfig, CombinationConfig  # noqa: F401 -- re-exported for callers


def months_between(start: pd.Timestamp, end: pd.Timestamp) -> float:
    """Fractional number of months from `start` to `end` (can be negative)."""
    return (end - start).days / DAYS_PER_MONTH


def ramp_fraction(months_since_lag_end: float, ramp_months: float) -> float:
    """
    Fraction (0 to 1) of an event's full effect that has materialized.
    0 before the lag ends, linearly increasing to 1 over `ramp_months`,
    held at 1 thereafter.
    """
    if months_since_lag_end <= 0:
        return 0.0
    if ramp_months <= 0:
        return 1.0
    return min(1.0, months_since_lag_end / ramp_months)


def resolve_ramp_months(relationship_type: str) -> float:
    return RAMP_MONTHS_BY_RELATIONSHIP.get(relationship_type, DEFAULT_RAMP_MONTHS)


def resolve_effect_size(link_row: pd.Series) -> float:
    """
    Full (fully-ramped) effect size in the target indicator's own units,
    signed by impact_direction. Uses `impact_estimate` when present;
    otherwise falls back to a magnitude-based heuristic (documented as
    lower-confidence in the notebook).
    """
    sign = 1.0 if link_row["impact_direction"] == "increase" else -1.0
    if pd.notna(link_row.get("impact_estimate")):
        return abs(link_row["impact_estimate"]) * sign
    magnitude = link_row.get("impact_magnitude", "medium")
    return MAGNITUDE_FALLBACK_PP.get(magnitude, DEFAULT_MAGNITUDE_FALLBACK_PP) * sign


@dataclass
class EventEffect:
    link_id: str
    event_id: str
    event_name: str
    event_date: pd.Timestamp
    full_effect: float
    lag_months: float
    ramp_months: float
    used_fallback_magnitude: bool

    def effect_at(self, as_of: pd.Timestamp) -> float:
        t = months_between(self.event_date, as_of)
        months_since_lag_end = t - self.lag_months
        return self.full_effect * ramp_fraction(months_since_lag_end, self.ramp_months)


def build_event_effects(links: pd.DataFrame, events: pd.DataFrame, indicator_code: str) -> List["EventEffect"]:
    """
    Return a list of EventEffect objects for every impact_link targeting
    `indicator_code`, joined against the events table for event dates/names.
    """
    sub = links[links["related_indicator"] == indicator_code].merge(
        events[["record_id", "indicator", "observation_date"]],
        left_on="parent_id", right_on="record_id", suffixes=("", "_event"),
    )
    effects = []
    for _, row in sub.iterrows():
        effects.append(EventEffect(
            link_id=row["record_id"],
            event_id=row["parent_id"],
            event_name=row["indicator_event"],
            event_date=row["observation_date_event"],
            full_effect=resolve_effect_size(row),
            lag_months=row["lag_months"] if pd.notna(row["lag_months"]) else 0,
            ramp_months=resolve_ramp_months(row["relationship_type"]),
            used_fallback_magnitude=pd.isna(row.get("impact_estimate")),
        ))
    return effects


def combine_effects(effects: List["EventEffect"], as_of: pd.Timestamp,
                     indicator_code: Optional[str] = None, ceiling: float = SHARED_CEILING_PCT) -> float:
    """
    Combine a list of EventEffect objects into a single total effect at
    `as_of`.

    Default behavior (indicator_code=None, or indicator_code has no entry in
    COMPETING_LINK_GROUPS): plain addition, i.e. every event's effect is
    assumed independent of every other -- see module docstring.

    Exception -- shared-ceiling / interaction term for competing events:
    if `indicator_code` has an entry in COMPETING_LINK_GROUPS, the effects
    whose `link_id` appears in one of those groups are pulled out and
    combined via a saturating "probabilistic union" instead of addition:

        combined = ceiling * (1 - product(1 - e_i / ceiling))

    Rationale: Telebirr and M-Pesa are not independent, additive drivers of
    ACC_MM_ACCOUNT -- they are two mobile money products competing for the
    same underlying pool of Ethiopian adults. Plain addition silently
    assumes every adopter counted in one link's effect is a *different*
    person from every adopter counted in the other's, i.e. zero overlap in
    who each product reaches. Treating each link's (time-ramped) effect as
    the probability an adult has adopted mobile money "via that channel",
    the standard way to combine two such probabilities into "adopted via A
    or via B" is the union formula above (independence-of-reach assumption
    across channels). It has three properties plain addition lacks: (1) it
    saturates smoothly below `ceiling` rather than growing without bound as
    more competing links pile up over time; (2) for small effects relative
    to `ceiling` it reduces to (approximately) the additive sum -- so it is
    a strict generalization, not a different regime; (3) it is symmetric
    and order-independent no matter how many competing links are combined.

    Effects not in a competing group for this indicator (if any) are still
    added on top of the combined competing term, unchanged.
    """
    if not indicator_code or indicator_code not in COMPETING_LINK_GROUPS:
        return sum(e.effect_at(as_of) for e in effects)

    competing_ids = set()
    for group in COMPETING_LINK_GROUPS[indicator_code]:
        competing_ids.update(group)

    competing = [e for e in effects if e.link_id in competing_ids]
    independent = [e for e in effects if e.link_id not in competing_ids]

    survival = 1.0
    for e in competing:
        val = max(0.0, e.effect_at(as_of))  # union formula assumes non-negative "probabilities"
        survival *= (1 - val / ceiling)
    competing_combined = ceiling * (1 - survival)

    return competing_combined + sum(e.effect_at(as_of) for e in independent)


def predict_indicator(baseline_value: float, baseline_date: pd.Timestamp,
                       as_of: pd.Timestamp, effects: List["EventEffect"],
                       clip_percentage: bool = False,
                       indicator_code: Optional[str] = None, ceiling: float = SHARED_CEILING_PCT) -> float:
    """
    Predicted indicator value at `as_of`, starting from `baseline_value` at
    `baseline_date` and adding the combined event effect.

    By default, effects are combined additively (independent events -- see
    module docstring). Pass `indicator_code` to opt in to the shared-ceiling
    interaction term for indicators with a COMPETING_LINK_GROUPS entry
    (currently just ACC_MM_ACCOUNT / Telebirr vs. M-Pesa) -- see
    combine_effects() for the functional form and rationale. Omitting
    indicator_code preserves the original, purely-additive behavior exactly,
    so existing callers are unaffected.
    """
    applicable = [e for e in effects if e.event_date >= baseline_date - pd.Timedelta(days=1)]
    total_effect = combine_effects(applicable, as_of, indicator_code=indicator_code, ceiling=ceiling)
    value = baseline_value + total_effect
    if clip_percentage:
        value = max(0.0, min(SHARED_CEILING_PCT, value))
    return value


def predict_trajectory(baseline_value: float, baseline_date: pd.Timestamp,
                        effects: List["EventEffect"], end_date: pd.Timestamp,
                        freq: str = "MS", clip_percentage: bool = False,
                        indicator_code: Optional[str] = None, ceiling: float = SHARED_CEILING_PCT) -> pd.DataFrame:
    """Monthly predicted trajectory of an indicator from baseline_date to end_date."""
    dates = pd.date_range(baseline_date, end_date, freq=freq)
    values = [predict_indicator(baseline_value, baseline_date, d, effects, clip_percentage,
                                 indicator_code=indicator_code, ceiling=ceiling) for d in dates]
    return pd.DataFrame({"date": dates, "predicted_value": values})
