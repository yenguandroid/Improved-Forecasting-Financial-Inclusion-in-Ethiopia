"""
Tests for src/impact_model.py: the functional form itself, and the
specific validated Telebirr/mobile-money case documented in
notebooks/task3_impact_modeling.ipynb.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_loader import load_all_enriched, load_all_final  # noqa: E402
from impact_model import (  # noqa: E402
    ramp_fraction, resolve_ramp_months, resolve_effect_size,
    build_event_effects, predict_indicator, predict_trajectory,
    combine_effects, RAMP_MONTHS_BY_RELATIONSHIP,
)


# ----------------------------------------------------------------------
# Functional form unit tests
# ----------------------------------------------------------------------

def test_ramp_fraction_zero_before_lag_ends():
    assert ramp_fraction(-5, 6) == 0.0
    assert ramp_fraction(0, 6) == 0.0


def test_ramp_fraction_linear_partway():
    assert ramp_fraction(3, 6) == pytest.approx(0.5)


def test_ramp_fraction_full_after_ramp_window():
    assert ramp_fraction(6, 6) == 1.0
    assert ramp_fraction(100, 6) == 1.0


def test_resolve_ramp_months_by_relationship_type():
    assert resolve_ramp_months("direct") == 3
    assert resolve_ramp_months("indirect") == 9
    assert resolve_ramp_months("enabling") == 12
    assert resolve_ramp_months("unknown_type") == 6  # falls back to default


def test_resolve_effect_size_uses_impact_estimate_when_present():
    row = pd.Series({"impact_direction": "increase", "impact_estimate": 12.0, "impact_magnitude": "low"})
    assert resolve_effect_size(row) == 12.0

    row_dec = pd.Series({"impact_direction": "decrease", "impact_estimate": 12.0, "impact_magnitude": "low"})
    assert resolve_effect_size(row_dec) == -12.0


def test_resolve_effect_size_falls_back_to_magnitude():
    row = pd.Series({"impact_direction": "increase", "impact_estimate": None, "impact_magnitude": "high"})
    assert resolve_effect_size(row) == 12.0


def test_predict_indicator_before_any_event_is_baseline():
    """No events yet applicable -> prediction equals the baseline exactly."""
    baseline_date = pd.Timestamp("2020-01-01")
    value = predict_indicator(10.0, baseline_date, pd.Timestamp("2019-01-01"), effects=[])
    assert value == 10.0


def test_predict_trajectory_shape():
    from impact_model import EventEffect
    effect = EventEffect(
        link_id="X", event_id="E", event_name="test", event_date=pd.Timestamp("2021-01-01"),
        full_effect=10.0, lag_months=0, ramp_months=6, used_fallback_magnitude=False,
    )
    traj = predict_trajectory(0.0, pd.Timestamp("2021-01-01"), [effect], pd.Timestamp("2021-12-01"))
    assert len(traj) == 12
    assert traj["predicted_value"].iloc[0] == 0.0
    assert traj["predicted_value"].iloc[-1] == pytest.approx(10.0, abs=0.01)
    # monotonically non-decreasing for a single positive effect
    assert traj["predicted_value"].is_monotonic_increasing


# ----------------------------------------------------------------------
# Validated case study: Telebirr / Mobile Money Account Rate
# ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def final_data():
    return load_all_final()


def test_calibrated_telebirr_link_exists(final_data):
    main, links, _ = final_data
    row = links[links["record_id"] == "IMP_0021"]
    assert len(row) == 1
    assert row["parent_id"].iloc[0] == "EVT_0001"
    assert row["related_indicator"].iloc[0] == "ACC_MM_ACCOUNT"
    assert row["impact_estimate"].iloc[0] == pytest.approx(4.7)


def test_refined_model_matches_2021_checkpoint(final_data):
    main, links, _ = final_data
    events = main[main["record_type"] == "event"]
    effects = build_event_effects(links, events, "ACC_MM_ACCOUNT")
    telebirr_date = events.loc[events["record_id"] == "EVT_0001", "observation_date"].iloc[0]

    pred = predict_indicator(0.0, telebirr_date, pd.Timestamp("2021-12-31"), effects)
    assert pred == pytest.approx(4.7, abs=0.01)


def test_refined_model_matches_2024_checkpoint_within_tolerance(final_data):
    """The key Task 3 validation result: refined model predicts within
    0.5pp of the actual, held-out 2024 Findex reading (9.45%)."""
    main, links, _ = final_data
    events = main[main["record_type"] == "event"]
    effects = build_event_effects(links, events, "ACC_MM_ACCOUNT")
    telebirr_date = events.loc[events["record_id"] == "EVT_0001", "observation_date"].iloc[0]

    pred = predict_indicator(0.0, telebirr_date, pd.Timestamp("2024-11-29"), effects)
    actual = 9.45
    assert abs(pred - actual) < 0.5


def test_pre_refinement_model_underpredicts_significantly():
    """Documents the gap this refinement closed: without the calibrated
    Telebirr link, the enriched (pre-Task-3) dataset badly under-predicts
    both checkpoints."""
    main, links, _ = load_all_enriched()
    events = main[main["record_type"] == "event"]
    effects = build_event_effects(links, events, "ACC_MM_ACCOUNT")
    telebirr_date = events.loc[events["record_id"] == "EVT_0001", "observation_date"].iloc[0]

    pred_2021 = predict_indicator(0.0, telebirr_date, pd.Timestamp("2021-12-31"), effects)
    pred_2024 = predict_indicator(0.0, telebirr_date, pd.Timestamp("2024-11-29"), effects)

    assert pred_2021 == 0.0  # no link at all covers this early
    assert pred_2024 < 9.45 - 3  # under-predicts by more than 3pp


def test_association_matrix_signs_match_impact_direction(final_data):
    """Regression test for a real bug caught during Task 3 notebook review:
    impact_estimate is already signed to match impact_direction in this
    dataset -- re-applying a sign flip double-negates 'decrease' links."""
    _, links, _ = final_data
    quantified = links[links["impact_estimate"].notna()]
    for _, row in quantified.iterrows():
        if row["impact_direction"] == "increase":
            assert row["impact_estimate"] >= 0
        else:
            assert row["impact_estimate"] <= 0


# ----------------------------------------------------------------------
# Task 2: shared-ceiling interaction term for competing events
# (Telebirr IMP_0021 vs. M-Pesa IMP_0007, both targeting ACC_MM_ACCOUNT)
# ----------------------------------------------------------------------

def test_combine_effects_defaults_to_additive_without_indicator_code(final_data):
    """Omitting indicator_code must reproduce the original, purely-additive
    behavior exactly -- backward compatibility for every other indicator
    and every existing call site."""
    main, links, _ = final_data
    events = main[main["record_type"] == "event"]
    effects = build_event_effects(links, events, "ACC_MM_ACCOUNT")
    as_of = pd.Timestamp("2024-11-29")

    additive_explicit = sum(e.effect_at(as_of) for e in effects)
    additive_via_combine = combine_effects(effects, as_of)  # no indicator_code
    assert additive_via_combine == pytest.approx(additive_explicit)


def test_shared_ceiling_reduces_to_single_effect_when_only_one_is_active(final_data):
    """Before M-Pesa launches, only Telebirr's effect is nonzero -- the
    union formula must reduce exactly to that single effect (no phantom
    interaction discount when there's nothing to compete with)."""
    main, links, _ = final_data
    events = main[main["record_type"] == "event"]
    effects = build_event_effects(links, events, "ACC_MM_ACCOUNT")

    pred = predict_indicator(
        0.0, events.loc[events["record_id"] == "EVT_0001", "observation_date"].iloc[0],
        pd.Timestamp("2021-12-31"), effects, indicator_code="ACC_MM_ACCOUNT",
    )
    assert pred == pytest.approx(4.7, abs=0.01)


def test_shared_ceiling_improves_accuracy_at_2024_checkpoint(final_data):
    """The Task 2 validation result: combining the competing Telebirr and
    M-Pesa links via the shared-ceiling union term, instead of raw addition,
    reduces the error against the held-out 2024 Findex reading (9.45%).

    Documented honestly either way -- this asserts the *direction* we
    actually observed (improvement), not a directional assumption baked in
    ahead of time."""
    main, links, _ = final_data
    events = main[main["record_type"] == "event"]
    effects = build_event_effects(links, events, "ACC_MM_ACCOUNT")
    telebirr_date = events.loc[events["record_id"] == "EVT_0001", "observation_date"].iloc[0]
    actual = 9.45

    pred_additive = predict_indicator(0.0, telebirr_date, pd.Timestamp("2024-11-29"), effects)
    pred_shared_ceiling = predict_indicator(
        0.0, telebirr_date, pd.Timestamp("2024-11-29"), effects, indicator_code="ACC_MM_ACCOUNT",
    )

    error_additive = abs(pred_additive - actual)
    error_shared_ceiling = abs(pred_shared_ceiling - actual)

    # Exact figures as validated: additive predicts 9.7% (error 0.25pp),
    # shared-ceiling predicts ~9.465% (error ~0.015pp).
    assert pred_additive == pytest.approx(9.7, abs=0.01)
    assert pred_shared_ceiling == pytest.approx(9.465, abs=0.01)
    assert error_shared_ceiling < error_additive


def test_shared_ceiling_only_applies_to_configured_indicator(final_data):
    """Sanity check that the interaction term is scoped to ACC_MM_ACCOUNT
    only, per Task 2's instructions ('implement it for the Telebirr/M-Pesa
    pair specifically') -- an unrelated indicator's effects must still
    combine additively even when indicator_code is passed."""
    main, links, _ = final_data
    events = main[main["record_type"] == "event"]
    effects = build_event_effects(links, events, "USG_P2P_COUNT")
    as_of = pd.Timestamp("2025-06-01")

    additive = sum(e.effect_at(as_of) for e in effects)
    via_combine = combine_effects(effects, as_of, indicator_code="USG_P2P_COUNT")
    assert via_combine == pytest.approx(additive)
