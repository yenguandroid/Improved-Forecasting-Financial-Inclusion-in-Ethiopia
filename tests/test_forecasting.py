"""
Tests for src/forecasting.py: trend fitting, the degenerate-CI case with
n=2, incremental event effects, and the two scenario-building functions.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_loader import load_all_task4  # noqa: E402
from impact_model import build_event_effects, EventEffect  # noqa: E402
from forecasting import (  # noqa: E402
    fit_linear_trend, fit_log_trend, incremental_event_effect,
    scenario_table, growth_rate_scenario,
)


@pytest.fixture(scope="module")
def task4_data():
    return load_all_task4()


# ----------------------------------------------------------------------
# Trend fitting
# ----------------------------------------------------------------------

def test_linear_trend_recovers_a_known_line():
    dates = [pd.Timestamp(f"{y}-01-01") for y in [2014, 2017, 2021, 2024]]
    # perfectly linear: 10 units per year from a 2014 baseline of 20
    values = [20 + 10 * (y - 2014) for y in [2014, 2017, 2021, 2024]]
    trend = fit_linear_trend(dates, values)
    pred = trend.predict([pd.Timestamp("2025-01-01")])
    assert pred["point"].iloc[0] == pytest.approx(20 + 10 * 11, abs=0.5)


def test_log_trend_is_concave_relative_to_linear_for_decelerating_data(task4_data):
    """The real Access series decelerates -- the log trend's 2027 forecast
    should be materially lower than the linear trend's, since log trend
    captures diminishing growth and linear does not."""
    main, links, _ = task4_data
    obs = main[main["record_type"] == "observation"]
    ownership = obs[(obs["indicator_code"] == "ACC_OWNERSHIP") & (obs["gender"] == "all")].sort_values("observation_date")
    dates = list(ownership["observation_date"])
    values = list(ownership["value_numeric"])

    linear = fit_linear_trend(dates, values)
    log = fit_log_trend(dates, values)

    forecast_2027 = pd.Timestamp("2027-12-31")
    lin_2027 = linear.predict([forecast_2027])["point"].iloc[0]
    log_2027 = log.predict([forecast_2027])["point"].iloc[0]

    assert log_2027 < lin_2027


def test_linear_trend_ci_is_degenerate_with_two_points():
    """With n=2 (zero residual degrees of freedom), no valid prediction
    interval exists -- statsmodels should return NaN, not a fabricated
    narrow interval."""
    dates = [pd.Timestamp("2021-01-01"), pd.Timestamp("2024-01-01")]
    values = [20.0, 21.0]
    trend = fit_linear_trend(dates, values)
    pred = trend.predict([pd.Timestamp("2025-01-01")])
    assert np.isnan(pred["ci_lower"].iloc[0])
    assert np.isnan(pred["ci_upper"].iloc[0])


# ----------------------------------------------------------------------
# Incremental event effects (no double-counting)
# ----------------------------------------------------------------------

def test_incremental_effect_is_zero_for_fully_realized_historical_event():
    """An event whose lag+ramp completed well before the 'last observation'
    date contributes zero incremental effect -- it's already in the trend."""
    effect = EventEffect(
        link_id="X", event_id="E", event_name="test", event_date=pd.Timestamp("2015-01-01"),
        full_effect=15.0, lag_months=12, ramp_months=3, used_fallback_magnitude=False,
    )
    last_obs = pd.Timestamp("2024-01-01")  # long after full ramp completed
    forecast_date = pd.Timestamp("2026-01-01")
    incr = incremental_event_effect([effect], last_obs, forecast_date)
    assert incr == pytest.approx(0.0, abs=1e-6)


def test_incremental_effect_captures_still_ramping_event():
    """An event whose ramp completes AFTER the last observation should
    contribute its full not-yet-realized effect by the forecast date."""
    effect = EventEffect(
        link_id="X", event_id="E", event_name="test", event_date=pd.Timestamp("2024-01-01"),
        full_effect=10.0, lag_months=24, ramp_months=12, used_fallback_magnitude=False,
    )
    last_obs = pd.Timestamp("2024-11-29")  # before lag even ends (2026-01-01)
    forecast_2027 = pd.Timestamp("2027-12-31")  # well after full ramp (2027-01-01)
    incr = incremental_event_effect([effect], last_obs, forecast_2027)
    assert incr == pytest.approx(10.0, abs=0.1)


def test_fayda_id_is_the_dominant_incremental_driver_for_access(task4_data):
    """Regression test for this project's central Task 4 finding: the
    Fayda ID rollout (EVT_0004) contributes the entire incremental
    event effect on ACC_OWNERSHIP for 2026-2027, since Telebirr's effect
    is already fully realized by the last observation date."""
    main, links, _ = task4_data
    events = main[main["record_type"] == "event"]
    effects = build_event_effects(links, events, "ACC_OWNERSHIP")
    last_obs = pd.Timestamp("2024-11-29")

    incr_2025 = incremental_event_effect(effects, last_obs, pd.Timestamp("2025-12-31"))
    incr_2027 = incremental_event_effect(effects, last_obs, pd.Timestamp("2027-12-31"))

    assert incr_2025 == pytest.approx(0.0, abs=0.5)
    assert incr_2027 == pytest.approx(10.0, abs=0.5)


# ----------------------------------------------------------------------
# Scenario builders
# ----------------------------------------------------------------------

def test_scenario_table_orders_pessimistic_base_optimistic():
    dates = [pd.Timestamp(f"{y}-01-01") for y in [2014, 2017, 2021, 2024]]
    values = [22.0, 35.0, 46.0, 49.0]
    trend = fit_log_trend(dates, values)
    forecast_dates = [pd.Timestamp("2025-12-31"), pd.Timestamp("2027-12-31")]
    table = scenario_table(trend, forecast_dates, dates[-1], events_effects=[])
    for _, row in table.iterrows():
        assert row["pessimistic"] <= row["with_events_base_scenario"] <= row["optimistic"]


def test_scenario_table_clips_to_bounds():
    # 4 points (not 2) so the CI is non-degenerate; values pushed near the
    # upper bound with a steep slope so the optimistic projection would
    # exceed 100 without clipping.
    dates = [pd.Timestamp(f"{y}-01-01") for y in [2018, 2020, 2022, 2024]]
    values = [90.0, 94.0, 97.0, 99.0]
    trend = fit_linear_trend(dates, values)
    forecast_dates = [pd.Timestamp("2030-01-01")]
    table = scenario_table(trend, forecast_dates, dates[-1], events_effects=[],
                            optimistic_multiplier=5.0, clip=(0, 100))
    assert not np.isnan(table["optimistic"].iloc[0])
    assert table["optimistic"].iloc[0] <= 100.0


def test_growth_rate_scenario_basic_arithmetic():
    base_date = pd.Timestamp("2024-01-01")
    forecast_dates = [pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-01")]
    table = growth_rate_scenario(20.0, base_date, forecast_dates,
                                  annual_growth_pp={"flat": 0.0, "up": 1.0})
    assert table["flat"].iloc[0] == pytest.approx(20.0, abs=0.05)
    assert table["up"].iloc[0] == pytest.approx(21.0, abs=0.05)
    assert table["up"].iloc[1] == pytest.approx(22.0, abs=0.05)


def test_growth_rate_scenario_respects_clip():
    base_date = pd.Timestamp("2024-01-01")
    forecast_dates = [pd.Timestamp("2030-01-01")]
    table = growth_rate_scenario(90.0, base_date, forecast_dates,
                                  annual_growth_pp={"aggressive": 10.0}, clip=(0, 100))
    assert table["aggressive"].iloc[0] == 100.0


# ----------------------------------------------------------------------
# Task 4 target data integrity
# ----------------------------------------------------------------------

def test_digital_payment_usage_distinct_from_mobile_money_account_rate(task4_data):
    """Guards against the exact mistake this project caught: conflating
    ACC_MM_ACCOUNT with the real Digital Payment Usage target."""
    main, _, _ = task4_data
    obs = main[main["record_type"] == "observation"]
    dp = obs[obs["indicator_code"] == "USG_DIGITAL_PAYMENT"].sort_values("observation_date")
    mm = obs[obs["indicator_code"] == "ACC_MM_ACCOUNT"].sort_values("observation_date")

    assert len(dp) == 2
    assert dp["value_numeric"].tolist() == [20.0, 20.7]
    # confirm these are genuinely different trajectories, not duplicated data
    assert dp["value_numeric"].tolist() != mm["value_numeric"].tolist()


def test_access_has_four_ethiopia_specific_points_not_five(task4_data):
    """Documents the resolved '5 points over 13 years' ambiguity: Ethiopia
    has 4 real Findex points (2014-2024), not 5 (2011-2024)."""
    main, _, _ = task4_data
    obs = main[main["record_type"] == "observation"]
    ownership = obs[(obs["indicator_code"] == "ACC_OWNERSHIP") & (obs["gender"] == "all")]
    assert len(ownership) == 4
    assert ownership["observation_date"].min().year == 2014
