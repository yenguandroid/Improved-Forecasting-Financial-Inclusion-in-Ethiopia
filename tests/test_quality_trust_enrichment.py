import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_loader import load_reference_codes, valid_codes  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QT_PATH = PROJECT_ROOT / "data" / "processed" / "ethiopia_fi_unified_data_quality_trust.xlsx"


@pytest.fixture(scope="module")
def quality_trust_data():
    main = pd.read_excel(QT_PATH, sheet_name="ethiopia_fi_unified_data")
    links = pd.read_excel(QT_PATH, sheet_name="Impact_sheet")
    ref = load_reference_codes(PROJECT_ROOT / "data" / "raw" / "reference_codes.xlsx")
    return main, links, ref


def test_quality_or_trust_pillar_now_has_at_least_one_observation(quality_trust_data):
    """The core Task 3 requirement: QUALITY or TRUST must go from 0 to >=1
    observations. Task 1's own log documented both pillars at 0 even after
    enrichment -- this is the first record for either."""
    main, _, _ = quality_trust_data
    obs = main[main["record_type"] == "observation"]
    qt_obs = obs[obs["pillar"].isin(["QUALITY", "TRUST"])]
    assert len(qt_obs) >= 1


def test_new_record_has_required_enrichment_fields_populated(quality_trust_data):
    """Mirrors Task 1's own honesty convention: every added record needs a
    real source_url and an exact quote in original_text -- nothing
    fabricated or extrapolated without a citation."""
    main, _, _ = quality_trust_data
    rec = main[main["record_id"] == "REC_0044"].iloc[0]
    assert rec["source_url"] and str(rec["source_url"]).startswith("http")
    assert rec["original_text"] and len(str(rec["original_text"])) > 20
    assert rec["notes"] and len(str(rec["notes"])) > 20


def test_new_record_field_values_are_schema_valid(quality_trust_data):
    """Every restricted field on the new record must use a code that
    actually exists in reference_codes.xlsx."""
    main, _, ref = quality_trust_data
    rec = main[main["record_id"] == "REC_0044"].iloc[0]
    for field in ["record_type", "pillar", "indicator_direction", "value_type",
                  "gender", "location", "source_type", "confidence"]:
        assert rec[field] in valid_codes(ref, field), f"{field}={rec[field]!r} not in reference_codes"


def test_new_record_confidence_reflects_stated_caveats(quality_trust_data):
    """The record's own notes flag two separate reasons confidence isn't
    'high' (sub-national sample; full text inaccessible) -- confidence
    should therefore not be 'high', consistent with the project's existing
    convention of downgrading confidence for imprecision/representativeness
    caveats even from otherwise-credible sources (see REC_0041 in
    data_enrichment_log.md for the precedent)."""
    main, _, _ = quality_trust_data
    rec = main[main["record_id"] == "REC_0044"].iloc[0]
    assert rec["confidence"] != "high"


def test_full_dataset_still_passes_basic_schema_checks(quality_trust_data):
    """Adding this one record shouldn't have broken anything else in the
    chained dataset (58 records expected: 57 from Task 4's output + 1)."""
    main, links, _ = quality_trust_data
    assert len(main) == 58
    event_ids = set(main.loc[main["record_type"] == "event", "record_id"])
    assert links["parent_id"].isin(event_ids).all()
