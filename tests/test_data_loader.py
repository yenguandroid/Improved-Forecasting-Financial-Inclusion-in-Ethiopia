import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_loader import load_all, load_main_data, load_impact_links, load_reference_codes, valid_codes  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENRICHED_PATH = PROJECT_ROOT / "data" / "processed" / "ethiopia_fi_unified_data_enriched.xlsx"


@pytest.fixture(scope="module")
def starter():
    return load_all()


def test_load_all_returns_three_dataframes(starter):
    main, links, ref = starter
    assert isinstance(main, pd.DataFrame) and not main.empty
    assert isinstance(links, pd.DataFrame) and not links.empty
    assert isinstance(ref, pd.DataFrame) and not ref.empty


def test_main_record_types_valid(starter):
    main, _, ref = starter
    valid = set(valid_codes(ref, "record_type"))
    assert set(main["record_type"].dropna().unique()).issubset(valid)


def test_impact_links_parent_id_resolves_to_event(starter):
    main, links, _ = starter
    event_ids = set(main.loc[main["record_type"] == "event", "record_id"])
    assert links["parent_id"].isin(event_ids).all()


def test_events_have_blank_pillar(starter):
    main, _, _ = starter
    events = main[main["record_type"] == "event"]
    assert events["pillar"].isna().all()


def test_observations_have_pillar(starter):
    main, _, _ = starter
    obs = main[main["record_type"] == "observation"]
    assert obs["pillar"].notna().all()


def test_date_parsing_survives_column_shifted_rows(starter):
    """
    Regression test for REC_0006 in the starter data, which has shifted
    metadata columns (comparable_country/collected_by/collection_date/notes)
    such that 'collection_date' actually contains free text
    ("Account ownership increased from 46% to 49%") instead of a date.
    The loader must degrade this single cell to NaT rather than crashing.
    """
    main, _, _ = starter
    assert pd.api.types.is_datetime64_any_dtype(main["collection_date"])
    rec6 = main[main["record_id"] == "REC_0006"]
    assert len(rec6) == 1
    assert pd.isna(rec6["collection_date"].iloc[0])
    # the actually-important measured value must still be intact
    assert rec6["value_numeric"].iloc[0] == 49.0
    assert rec6["indicator_code"].iloc[0] == "ACC_OWNERSHIP"
class TestEnrichedDataset:
    @pytest.fixture(scope="class")
    def enriched(self):
        main = pd.read_excel(ENRICHED_PATH, sheet_name="ethiopia_fi_unified_data")
        links = pd.read_excel(ENRICHED_PATH, sheet_name="Impact_sheet")
        ref = load_reference_codes()
        return main, links, ref

    def test_record_ids_unique(self, enriched):
        main, links, _ = enriched
        assert not main["record_id"].duplicated().any()
        assert not links["record_id"].duplicated().any()

    def test_more_records_than_starter(self, enriched):
        main, links, _ = enriched
        starter_main, starter_links, _ = load_all()
        assert len(main) > len(starter_main)
        assert len(links) > len(starter_links)

    def test_categorical_fields_still_valid(self, enriched):
        main, links, ref = enriched
        for field in ["record_type", "pillar", "indicator_direction", "value_type",
                      "source_type", "confidence", "gender", "location"]:
            valid = set(valid_codes(ref, field))
            actual = set(main[field].dropna().unique())
            assert actual.issubset(valid), f"invalid values in {field}: {actual - valid}"

        for field in ["relationship_type", "impact_direction", "impact_magnitude",
                      "evidence_basis", "confidence"]:
            valid = set(valid_codes(ref, field))
            actual = set(links[field].dropna().unique())
            assert actual.issubset(valid), f"invalid values in links.{field}: {actual - valid}"

    def test_new_events_have_blank_pillar(self, enriched):
        main, _, _ = enriched
        events = main[main["record_type"] == "event"]
        assert events["pillar"].isna().all()

    def test_new_impact_links_resolve_to_real_events(self, enriched):
        main, links, _ = enriched
        event_ids = set(main.loc[main["record_type"] == "event", "record_id"])
        assert links["parent_id"].isin(event_ids).all()

    def test_new_impact_links_related_indicator_exists(self, enriched):
        main, links, _ = enriched
        indicator_codes = set(main["indicator_code"].dropna().unique())
        assert links["related_indicator"].isin(indicator_codes).all()

    def test_required_observation_fields_populated_for_new_records(self, enriched):
        """
        Only the records THIS enrichment added (REC_0034+) are checked for full
        schema completeness. Five starter-data observations (REC_0013, REC_0020,
        REC_0023, REC_0024, REC_0025) predate this enrichment and are missing
        source_url -- a pre-existing gap documented in data_enrichment_log.md,
        not something introduced here.
        """
        main, _, _ = enriched
        new_ids = [f"REC_{i:04d}" for i in range(34, 42)]
        new_obs = main[main["record_id"].isin(new_ids)]
        assert len(new_obs) == 8
        required = ["pillar", "indicator", "indicator_code", "value_numeric",
                    "observation_date", "source_name", "source_url", "confidence"]
        for field in required:
            assert new_obs[field].notna().all(), f"missing values in new observation.{field}"
