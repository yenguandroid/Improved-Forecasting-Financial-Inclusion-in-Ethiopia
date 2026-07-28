"""
Tests validating the key quantitative claims used in the Task 2 EDA
notebook (notebooks/task2_eda.ipynb), so that if the enriched dataset ever
changes, a broken assumption behind a written insight fails loudly here
rather than silently going stale in prose.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_loader import load_all_enriched  # noqa: E402


@pytest.fixture(scope="module")
def enriched():
    return load_all_enriched()


def test_account_ownership_growth_deceleration(enriched):
    """The central Task 2 finding: ownership growth rate decelerated across
    the three Findex survey intervals."""
    main, _, _ = enriched
    obs = main[main["record_type"] == "observation"]
    ownership = (
        obs[(obs["indicator_code"] == "ACC_OWNERSHIP") & (obs["gender"] == "all")]
        .sort_values("observation_date")
    )
    assert len(ownership) == 4
    values = ownership["value_numeric"].tolist()
    assert values == [22.0, 35.0, 46.0, 49.0]

    years = ownership["observation_date"].dt.year.tolist()
    rates = [(values[i] - values[i - 1]) / (years[i] - years[i - 1]) for i in range(1, 4)]
    # strictly decelerating each period
    assert rates[0] > rates[1] > rates[2]
    assert rates[2] == pytest.approx(1.0, abs=0.01)


def test_registered_mobile_money_users_combined(enriched):
    """The ~65.6M combined registered-user figure cited throughout the notebook."""
    main, _, _ = enriched
    obs = main[main["record_type"] == "observation"]
    telebirr = obs.loc[obs["indicator_code"] == "USG_TELEBIRR_USERS", "value_numeric"].iloc[0]
    mpesa = obs.loc[obs["indicator_code"] == "USG_MPESA_USERS", "value_numeric"].iloc[0]
    assert (telebirr + mpesa) == pytest.approx(65_640_000, rel=1e-6)


def test_mpesa_active_rate(enriched):
    main, _, _ = enriched
    obs = main[main["record_type"] == "observation"]
    registered = obs.loc[obs["indicator_code"] == "USG_MPESA_USERS", "value_numeric"].iloc[0]
    active = obs.loc[obs["indicator_code"] == "USG_MPESA_ACTIVE", "value_numeric"].iloc[0]
    assert active / registered == pytest.approx(0.6574, abs=0.001)


def test_gender_gap_narrowing(enriched):
    main, _, _ = enriched
    obs = main[main["record_type"] == "observation"]
    gap = obs[obs["indicator_code"] == "GEN_GAP_ACC"].sort_values("observation_date")
    assert gap["value_numeric"].tolist() == [20.0, 18.0]


def test_impact_links_evidence_basis_distribution(enriched):
    """Guards the exact evidence_basis split cited in the notebook's
    correlation-analysis section (7 literature / 7 empirical / 6 theoretical)."""
    _, links, _ = enriched
    counts = links["evidence_basis"].value_counts()
    assert counts["literature"] == 7
    assert counts["empirical"] == 7
    assert counts["theoretical"] == 6
    assert len(links) == 20


def test_confidence_share_high(enriched):
    """Guards the 76% high-confidence figure cited in the data quality section."""
    main, _, _ = enriched
    counts = main["confidence"].value_counts()
    share_high = counts["high"] / counts.sum()
    assert share_high == pytest.approx(0.7636, abs=0.001)


def test_no_rural_urban_disaggregation_flagged_correctly(enriched):
    """Confirms the data-gap claim: every observation's location is 'national'."""
    main, _, _ = enriched
    obs = main[main["record_type"] == "observation"]
    assert set(obs["location"].dropna().unique()) == {"national"}


def test_pillars_with_zero_or_minimal_coverage(enriched):
    main, _, _ = enriched
    obs = main[main["record_type"] == "observation"]
    counts = obs["pillar"].value_counts()
    assert "QUALITY" not in counts.index
    assert "TRUST" not in counts.index
    assert counts["AFFORDABILITY"] == 1
    assert counts["DEPTH"] == 1
