import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from data_loader import load_reference_codes  # noqa: E402
from validate import validate_workbook, ValidationReport  # noqa: E402
import refresh_data  # noqa: E402


@pytest.fixture(scope="module")
def loaded_final():
    """The fullest current dataset, loaded once for the read-only validation
    tests below (does NOT trigger a pipeline rebuild)."""
    path = PROJECT_ROOT / "data" / "processed" / refresh_data.FINAL_OUTPUT
    main = pd.read_excel(path, sheet_name="ethiopia_fi_unified_data")
    links = pd.read_excel(path, sheet_name="Impact_sheet")
    ref = load_reference_codes(PROJECT_ROOT / "data" / "raw" / "reference_codes.xlsx")
    return main, links, ref


# ----------------------------------------------------------------------
# validate.py -- does it actually catch breakage, not just pass the happy path?
# ----------------------------------------------------------------------

def test_valid_current_dataset_passes(loaded_final):
    main, links, ref = loaded_final
    report = validate_workbook(main, links, ref)
    assert report.passed, f"Unexpected validation errors on the current dataset: {report.errors}"


def test_catches_invalid_pillar_code(loaded_final):
    """The core 'does validation actually validate' test: corrupt one field
    with a value that doesn't exist in reference_codes.xlsx and confirm it's
    caught, not silently accepted."""
    main, links, ref = loaded_final
    broken = main.copy()
    broken.loc[broken["record_type"] == "observation", "pillar"] = (
        broken.loc[broken["record_type"] == "observation", "pillar"].iloc[:1].values[0]
    )
    # Corrupt just one row with a pillar value that doesn't exist anywhere in reference_codes
    idx = broken[broken["record_type"] == "observation"].index[0]
    broken.loc[idx, "pillar"] = "NOT_A_REAL_PILLAR"

    report = validate_workbook(broken, links, ref)
    assert not report.passed
    assert any("NOT_A_REAL_PILLAR" in e for e in report.errors)


def test_catches_duplicate_record_id(loaded_final):
    main, links, ref = loaded_final
    broken = pd.concat([main, main.iloc[[0]]], ignore_index=True)  # duplicate the first row's record_id
    report = validate_workbook(broken, links, ref)
    assert not report.passed
    assert any("Duplicate record_id" in e for e in report.errors)


def test_catches_orphaned_impact_link(loaded_final):
    main, links, ref = loaded_final
    broken_links = links.copy()
    broken_links.loc[broken_links.index[0], "parent_id"] = "EVT_9999_DOES_NOT_EXIST"
    report = validate_workbook(main, broken_links, ref)
    assert not report.passed
    assert any("EVT_9999_DOES_NOT_EXIST" in e for e in report.errors)


def test_catches_missing_critical_field(loaded_final):
    main, links, ref = loaded_final
    broken = main.copy()
    obs_idx = broken[broken["record_type"] == "observation"].index[0]
    broken.loc[obs_idx, "value_numeric"] = None
    report = validate_workbook(broken, links, ref)
    assert not report.passed
    assert any("value_numeric" in e for e in report.errors)


def test_known_starter_data_gap_is_a_warning_not_an_error(loaded_final):
    """The 5 pre-existing missing-source_url records (documented in
    data_enrichment_log.md, deliberately not retrofitted) must be reported
    as warnings, not hard failures -- otherwise every single refresh would
    permanently fail on a known, accepted, already-flagged gap."""
    main, links, ref = loaded_final
    report = validate_workbook(main, links, ref)
    assert not any("source_url" in e for e in report.errors)
    assert any("source_url" in w and "pre-existing" in w for w in report.warnings)


def test_new_source_url_gap_would_be_flagged_as_regression(loaded_final):
    """A NEW record missing source_url (beyond the known 5) should be
    flagged distinctly as a likely regression, not silently absorbed into
    the same known-gap bucket."""
    main, links, ref = loaded_final
    broken = main.copy()
    obs_idx = broken[broken["record_type"] == "observation"].index[-1]  # a record NOT in the known-gap set
    assert broken.loc[obs_idx, "record_id"] not in {"REC_0013", "REC_0020", "REC_0023", "REC_0024", "REC_0025"}
    broken.loc[obs_idx, "source_url"] = None
    report = validate_workbook(broken, links, ref)
    assert any("NEW" in w and "regression" in w for w in report.warnings)


def test_events_have_blank_pillar_violation_is_caught(loaded_final):
    main, links, ref = loaded_final
    broken = main.copy()
    event_idx = broken[broken["record_type"] == "event"].index[0]
    broken.loc[event_idx, "pillar"] = "ACCESS"
    report = validate_workbook(broken, links, ref)
    assert not report.passed
    assert any("blank pillar" in e for e in report.errors)


# ----------------------------------------------------------------------
# refresh_data.py -- full pipeline integration
# ----------------------------------------------------------------------

def test_full_refresh_runs_and_passes():
    """Integration test: actually runs the full 4-stage pipeline and
    confirms it exits clean. Slower than the unit tests above, but this is
    the thing that actually needs to work end-to-end."""
    manifest = refresh_data.refresh(quiet=True)
    assert manifest["validation_passed"], manifest["validation_errors"]
    assert manifest["record_counts"]["total"] == 58
    assert manifest["pipeline_stages"] == [s for s, _ in refresh_data.PIPELINE]


def test_refresh_is_idempotent():
    """Running the pipeline twice in a row must not accumulate duplicate
    records -- each stage reads from its immediate upstream file, which is
    itself freshly regenerated every run, not appended to."""
    manifest_1 = refresh_data.refresh(quiet=True)
    manifest_2 = refresh_data.refresh(quiet=True)
    assert manifest_1["record_counts"] == manifest_2["record_counts"]


def test_refresh_writes_readable_manifest():
    refresh_data.refresh(quiet=True)
    assert refresh_data.MANIFEST_PATH.exists()
    manifest = refresh_data.load_last_manifest()
    assert manifest is not None
    assert set(manifest.keys()) >= {
        "refreshed_at", "pipeline_stages", "final_output",
        "validation_passed", "validation_errors", "validation_warnings", "record_counts",
    }
    # round-trip through the actual file on disk, not just the in-memory return value
    on_disk = json.loads(refresh_data.MANIFEST_PATH.read_text())
    assert on_disk == manifest


def test_load_last_manifest_returns_none_if_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh_data, "MANIFEST_PATH", tmp_path / "does_not_exist.json")
    assert refresh_data.load_last_manifest() is None
