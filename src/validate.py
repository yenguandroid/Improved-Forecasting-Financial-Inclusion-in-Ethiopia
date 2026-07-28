"""
src/validate.py

Reusable data-quality validation for the main sheet + impact_links, shared
by `refresh_data.py` and the test suite. Generalizes checks that were
previously scattered as one-off assertions across tests/test_data_loader.py,
tests/test_eda_findings.py, and tests/test_quality_trust_enrichment.py into
a single, reusable pass that can run against *any* processed workbook on
demand -- not just the specific fixtures those tests happen to load.

Every check function returns a list of human-readable error strings (empty
list = passed). `validate_workbook()` runs all of them and returns a
combined report.
"""
from dataclasses import dataclass, field
import pandas as pd

from data_loader import valid_codes
from constants import KNOWN_MISSING_SOURCE_URL

# Fields on the main sheet that are restricted to reference_codes.xlsx
# enumerations, per field name there.
RESTRICTED_MAIN_FIELDS = [
    "record_type", "category", "pillar", "indicator_direction",
    "value_type", "gender", "location", "source_type", "confidence",
]
RESTRICTED_LINK_FIELDS = [
    "relationship_type", "impact_direction", "impact_magnitude", "evidence_basis",
]
REQUIRED_MAIN_FIELDS_BY_TYPE = {
    # Hard errors: missing these would silently break forecasting/impact-model
    # code downstream (e.g. sorting by observation_date, joining on indicator_code).
    "observation": ["record_id", "pillar", "indicator", "indicator_code",
                     "value_numeric", "observation_date"],
    "event": ["record_id", "category", "indicator", "observation_date"],
    "target": ["record_id", "pillar", "indicator", "indicator_code", "value_numeric"],
}
# Soft warnings: desirable for provenance/citability, but a known, deliberately
# undocumented-not-corrected gap exists in the starter data itself (5 records --
# see data_enrichment_log.md's "Data quality finding" section) -- flagging this
# every single refresh as a hard failure would be noise, not signal. New
# additions are still expected to have this populated (see Task 1's own
# "every added record has a real source_url" convention); a REGRESSION beyond
# the currently-known set is what this is meant to catch, not the existing gap.
SOFT_REQUIRED_MAIN_FIELDS_BY_TYPE = {
    "observation": ["source_url"],
}


@dataclass
class ValidationReport:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    record_counts: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return dict(passed=self.passed, errors=self.errors, warnings=self.warnings,
                    record_counts=self.record_counts)


def _check_restricted_fields(df: pd.DataFrame, fields: list, ref: pd.DataFrame, label: str) -> list:
    errors = []
    for f in fields:
        if f not in df.columns:
            continue
        allowed = set(valid_codes(ref, f))
        if not allowed:
            continue  # field not governed by reference_codes (shouldn't happen, but don't false-positive)
        present = set(df[f].dropna().unique())
        bad = present - allowed
        if bad:
            errors.append(f"{label}: invalid value(s) {sorted(bad)} in column '{f}' "
                           f"(allowed: {sorted(allowed)})")
    return errors


def _check_duplicate_record_ids(main: pd.DataFrame) -> list:
    dupes = main["record_id"][main["record_id"].duplicated(keep=False)]
    if len(dupes):
        return [f"Duplicate record_id(s) found: {sorted(dupes.unique())}"]
    return []


def _check_impact_links_resolve(main: pd.DataFrame, links: pd.DataFrame) -> list:
    event_ids = set(main.loc[main["record_type"] == "event", "record_id"])
    orphaned = links.loc[~links["parent_id"].isin(event_ids), "parent_id"].unique()
    if len(orphaned):
        return [f"impact_link parent_id(s) that don't resolve to any event record: {sorted(orphaned)}"]
    return []


def _check_required_fields_populated(main: pd.DataFrame) -> list:
    errors = []
    for record_type, required in REQUIRED_MAIN_FIELDS_BY_TYPE.items():
        subset = main[main["record_type"] == record_type]
        for f in required:
            if f not in subset.columns:
                continue
            missing = subset[subset[f].isna()]
            if len(missing):
                errors.append(f"{len(missing)} '{record_type}' record(s) missing required field "
                               f"'{f}': {sorted(missing['record_id'].tolist())}")
    return errors


def _check_soft_required_fields(main: pd.DataFrame) -> list:
    """Warnings (not errors) for desirable-but-not-critical fields. Only
    flags gaps BEYOND the known, already-documented starter-data set --
    see KNOWN_MISSING_SOURCE_URL and data_enrichment_log.md."""
    warnings = []
    for record_type, fields in SOFT_REQUIRED_MAIN_FIELDS_BY_TYPE.items():
        subset = main[main["record_type"] == record_type]
        for f in fields:
            if f not in subset.columns:
                continue
            missing_ids = set(subset[subset[f].isna()]["record_id"])
            known = KNOWN_MISSING_SOURCE_URL if f == "source_url" else set()
            new_gaps = missing_ids - known
            still_known = missing_ids & known
            if still_known:
                warnings.append(f"{len(still_known)} '{record_type}' record(s) missing '{f}' "
                                 f"(pre-existing, documented starter-data gap -- see "
                                 f"data_enrichment_log.md): {sorted(still_known)}")
            if new_gaps:
                warnings.append(f"NEW: {len(new_gaps)} '{record_type}' record(s) missing '{f}' "
                                 f"beyond the known starter-data gap -- this looks like a "
                                 f"regression, worth investigating: {sorted(new_gaps)}")
    return warnings


def _check_events_have_blank_pillar(main: pd.DataFrame) -> list:
    events = main[main["record_type"] == "event"]
    non_blank = events[events["pillar"].notna()]
    if len(non_blank):
        return [f"{len(non_blank)} event record(s) have a non-blank pillar "
                f"(should be blank -- see schema notes): {sorted(non_blank['record_id'].tolist())}"]
    return []


def validate_workbook(main: pd.DataFrame, links: pd.DataFrame, ref: pd.DataFrame) -> ValidationReport:
    """Run the full validation suite against one loaded (main, links, ref)
    triple. Does not raise -- callers check `.passed` / inspect `.errors`."""
    report = ValidationReport()

    report.errors += _check_duplicate_record_ids(main)
    report.errors += _check_restricted_fields(main, RESTRICTED_MAIN_FIELDS, ref, "main sheet")
    report.errors += _check_restricted_fields(links, RESTRICTED_LINK_FIELDS, ref, "impact_links")
    report.errors += _check_impact_links_resolve(main, links)
    report.errors += _check_required_fields_populated(main)
    report.errors += _check_events_have_blank_pillar(main)
    report.warnings += _check_soft_required_fields(main)

    report.record_counts = {
        "total": len(main),
        "observations": int((main["record_type"] == "observation").sum()),
        "events": int((main["record_type"] == "event").sum()),
        "targets": int((main["record_type"] == "target").sum()),
        "impact_links": len(links),
    }
    return report
