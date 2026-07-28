import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import constants  # noqa: E402
from config import ScenarioConfig, GrowthRateScenarioConfig, RampConfig, ExplainerConfig  # noqa: E402
from utils import load_workbook_sheets, write_workbook_sheets, blank_record  # noqa: E402
from data_loader import load_all_task4  # noqa: E402
from impact_model import build_event_effects  # noqa: E402
from explainability import (  # noqa: E402
    build_feature_matrix, train_surrogate_model, surrogate_r_squared, explain_indicator,
)


# ----------------------------------------------------------------------
# constants.py / config.py -- refactor correctness
# ----------------------------------------------------------------------

def test_impact_model_reexports_constants_module_values():
    """impact_model.py must use the SAME values as constants.py, not a
    silently-diverged local copy -- this is the whole point of extracting
    them in the first place."""
    import impact_model
    assert impact_model.RAMP_MONTHS_BY_RELATIONSHIP == constants.RAMP_MONTHS_BY_RELATIONSHIP
    assert impact_model.COMPETING_LINK_GROUPS == constants.COMPETING_LINK_GROUPS


def test_growth_rate_scenario_config_as_dict_matches_fields():
    cfg = GrowthRateScenarioConfig(pessimistic_pp_per_year=0.0, base_pp_per_year=0.24, optimistic_pp_per_year=1.5)
    d = cfg.as_dict()
    assert d == {"pessimistic": 0.0, "base": 0.24, "optimistic": 1.5}


def test_config_dataclasses_are_frozen():
    """Config objects should be immutable -- accidentally mutating a shared
    config instance in one place shouldn't silently affect every other
    caller holding a reference to it."""
    cfg = ScenarioConfig()
    with pytest.raises(Exception):
        cfg.optimistic_multiplier = 99.0


def test_ramp_config_defaults_match_constants():
    cfg = RampConfig()
    assert cfg.ramp_months == constants.DEFAULT_RAMP_MONTHS


# ----------------------------------------------------------------------
# utils.py -- extracted I/O logic
# ----------------------------------------------------------------------

def test_blank_record_has_every_column_as_none():
    columns = ["a", "b", "c"]
    row = blank_record(columns)
    assert row == {"a": None, "b": None, "c": None}


def test_write_then_load_workbook_roundtrips(tmp_path):
    main_df = pd.DataFrame({"record_id": ["REC_0001"], "value": [1.5]})
    links_df = pd.DataFrame({"record_id": ["IMP_0001"], "parent_id": ["EVT_0001"]})
    path = tmp_path / "test_workbook.xlsx"

    write_workbook_sheets(path, main_df, links_df)
    assert path.exists()

    loaded_main, loaded_links = load_workbook_sheets(path)
    pd.testing.assert_frame_equal(loaded_main, main_df)
    pd.testing.assert_frame_equal(loaded_links, links_df)


def test_write_workbook_sheets_creates_parent_directory(tmp_path):
    nested_path = tmp_path / "nested" / "dir" / "workbook.xlsx"
    write_workbook_sheets(nested_path, pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [2]}))
    assert nested_path.exists()


# ----------------------------------------------------------------------
# explainability.py -- SHAP surrogate model
# ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def acc_mm_effects():
    main, links, ref = load_all_task4()
    events = main[main["record_type"] == "event"]
    return build_event_effects(links, events, "ACC_MM_ACCOUNT")


def test_feature_matrix_uses_real_combine_effects_not_plain_addition(acc_mm_effects):
    """Regression test for a real bug caught during development: the
    feature matrix must call the actual combine_effects() (respecting the
    Enhancement 2 shared-ceiling interaction term for Telebirr/M-Pesa), not
    a hand-rolled plain sum that would silently explain the superseded
    additive-only model instead of the current one."""
    from impact_model import combine_effects

    feature_df, feature_cols = build_feature_matrix(
        acc_mm_effects, pd.Timestamp("2021-05-17"), pd.Timestamp("2024-11-29"),
        indicator_code="ACC_MM_ACCOUNT",
    )
    last_row = feature_df.iloc[-1]
    expected = combine_effects(acc_mm_effects, last_row["date"], indicator_code="ACC_MM_ACCOUNT")
    assert last_row["predicted_value"] == pytest.approx(expected)

    # and that this is NOT the same as plain (superseded) addition when they'd differ
    plain_sum = sum(e.effect_at(last_row["date"]) for e in acc_mm_effects)
    if plain_sum != expected:
        assert last_row["predicted_value"] != pytest.approx(plain_sum)


def test_feature_matrix_excludes_noncausal_trend_feature(acc_mm_effects):
    """Regression test for the second bug caught during development: no
    bare 'years since baseline' feature should be present, since it isn't
    part of the true formula and would just proxy for the real event
    features, distorting SHAP attribution."""
    feature_df, feature_cols = build_feature_matrix(
        acc_mm_effects, pd.Timestamp("2021-05-17"), pd.Timestamp("2024-11-29"),
        indicator_code="ACC_MM_ACCOUNT",
    )
    assert not any("year" in c.lower() or "trend" in c.lower() for c in feature_cols)
    assert len(feature_cols) == len(acc_mm_effects)


def test_surrogate_model_achieves_high_fidelity(acc_mm_effects):
    """The surrogate is meant to approximate a known deterministic
    function, not learn from noisy data -- fidelity (R^2 against the real
    model's own outputs) should be very close to 1.0. A materially lower
    value would indicate a feature-engineering bug."""
    feature_df, feature_cols = build_feature_matrix(
        acc_mm_effects, pd.Timestamp("2021-05-17"), pd.Timestamp("2027-12-31"),
        indicator_code="ACC_MM_ACCOUNT",
    )
    model = train_surrogate_model(feature_df, feature_cols)
    r2 = surrogate_r_squared(model, feature_df, feature_cols)
    assert r2 > 0.999


def test_shap_values_satisfy_additivity_property(acc_mm_effects):
    """Fundamental SHAP correctness check: base_value + sum(shap contributions
    for a row) must equal that row's actual prediction, for every row."""
    result = explain_indicator(
        acc_mm_effects, pd.Timestamp("2021-05-17"), pd.Timestamp("2027-12-31"),
        indicator_code="ACC_MM_ACCOUNT",
    )
    reconstructed = result.base_value + result.shap_values.sum(axis=1)
    actual = result.feature_df["predicted_value"].values
    np.testing.assert_allclose(reconstructed, actual, atol=0.05)


def test_global_importance_sums_are_nonnegative_and_sorted(acc_mm_effects):
    result = explain_indicator(
        acc_mm_effects, pd.Timestamp("2021-05-17"), pd.Timestamp("2027-12-31"),
        indicator_code="ACC_MM_ACCOUNT",
    )
    imp = result.global_importance()
    assert (imp["mean_abs_shap"] >= 0).all()
    assert imp["mean_abs_shap"].is_monotonic_decreasing


def test_explain_row_returns_one_contribution_per_feature(acc_mm_effects):
    result = explain_indicator(
        acc_mm_effects, pd.Timestamp("2021-05-17"), pd.Timestamp("2027-12-31"),
        indicator_code="ACC_MM_ACCOUNT",
    )
    row = result.explain_row(-1)
    assert len(row) == len(result.feature_cols)
    assert set(row["feature"]) == set(result.feature_cols)


def test_concerning_patterns_returns_nonempty_list(acc_mm_effects):
    """Should always return at least one finding -- even 'nothing concerning'
    is reported explicitly, never a silent empty result."""
    result = explain_indicator(
        acc_mm_effects, pd.Timestamp("2021-05-17"), pd.Timestamp("2027-12-31"),
        indicator_code="ACC_MM_ACCOUNT",
    )
    findings = result.concerning_patterns()
    assert isinstance(findings, list)
    assert len(findings) >= 1
    assert all(isinstance(f, str) and len(f) > 10 for f in findings)


def test_explain_indicator_requires_indicator_code_explicitly(acc_mm_effects):
    """indicator_code is a required positional-ish argument (no default of
    None) specifically so a caller can't accidentally omit it and silently
    get the wrong (plain-additive) combination for an indicator that has a
    documented interaction-term exception."""
    import inspect
    sig = inspect.signature(explain_indicator)
    assert sig.parameters["indicator_code"].default is inspect.Parameter.empty
