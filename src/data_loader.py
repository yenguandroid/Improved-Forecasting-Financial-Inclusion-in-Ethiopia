"""
data_loader.py

Utilities for loading the Ethiopia Financial Inclusion unified dataset:
the main data sheet (observations, events, targets), the impact_links
sheet, and the reference_codes lookup table.
"""
from pathlib import Path
from typing import List, Tuple
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

UNIFIED_WORKBOOK = RAW_DIR / "ethiopia_fi_unified_data.xlsx"
REFERENCE_CODES = RAW_DIR / "reference_codes.xlsx"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ENRICHED_WORKBOOK = PROCESSED_DIR / "ethiopia_fi_unified_data_enriched.xlsx"

DATE_COLS = ["observation_date", "period_start", "period_end", "collection_date"]


def _safe_timestamp(v) -> pd.Timestamp:
    """Convert a single cell to a Timestamp, or NaT if it isn't a valid date.
    Some starter-data rows have column-shifted metadata (see
    data_enrichment_log.md / the EDA notebook's data quality section for
    REC_0006), so a handful of 'date' cells actually contain free text --
    this must degrade to NaT, not crash the whole load."""
    if pd.isna(v):
        return pd.NaT
    try:
        return pd.Timestamp(v)
    except (ValueError, TypeError):
        return pd.NaT


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Robustly coerce every date column to real Timestamps, regardless of
    whether the underlying cells are already datetime (native Excel date
    formatting), plain ISO strings (e.g. newly-appended enrichment rows), or
    a *mix* of both within the same column (which is what happens when new
    string-typed rows are appended below existing datetime-typed rows via
    pandas -- the column dtype degrades to 'object' and a single vectorized
    pd.to_datetime() call can raise instead of coercing cleanly). A few
    starter-data rows also have column-shifted metadata where a 'date'
    column actually holds free text (e.g. REC_0006) -- those cells are
    coerced to NaT rather than raising.
    """
    for col in DATE_COLS:
        if col not in df.columns:
            continue
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        df[col] = df[col].apply(_safe_timestamp)
    return df


def load_main_data(path: Path = UNIFIED_WORKBOOK, sheet_name: str = "ethiopia_fi_unified_data") -> pd.DataFrame:
    """
    Load the main data sheet: observation / event / target records.
    """
    df = pd.read_excel(path, sheet_name=sheet_name)
    return _parse_dates(df)


def load_impact_links(path: Path = UNIFIED_WORKBOOK, sheet_name: str = "Impact_sheet") -> pd.DataFrame:
    """
    Load the impact_links sheet: modeled relationships between events
    (via parent_id, referencing an event's record_id in the main sheet)
    and indicators.
    """
    df = pd.read_excel(path, sheet_name=sheet_name)
    return _parse_dates(df)


def load_reference_codes(path: Path = REFERENCE_CODES) -> pd.DataFrame:
    """
    Load the reference_codes lookup table: valid values for every
    categorical field used in the main data and impact_links sheets.
    """
    return pd.read_excel(path, sheet_name="reference_codes")


def valid_codes(reference_codes: pd.DataFrame, field: str) -> List[str]:
    """Return the list of valid codes for a given field (e.g. 'pillar')."""
    return reference_codes.loc[reference_codes["field"] == field, "code"].tolist()


def load_all(raw_dir: Path = RAW_DIR) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convenience loader returning (main_data, impact_links, reference_codes)
    from the original STARTER workbook (Task 1 input, unmodified)."""
    wb = raw_dir / "ethiopia_fi_unified_data.xlsx"
    ref = raw_dir / "reference_codes.xlsx"
    return load_main_data(wb), load_impact_links(wb), load_reference_codes(ref)


def load_all_enriched(processed_dir: Path = PROCESSED_DIR, raw_dir: Path = RAW_DIR) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convenience loader returning (main_data, impact_links, reference_codes)
    from the ENRICHED workbook produced by build_enrichment.py (Task 1 output).
    This is what Task 2 EDA should use, since it includes the enrichment
    additions on top of the starter data."""
    wb = processed_dir / "ethiopia_fi_unified_data_enriched.xlsx"
    ref = raw_dir / "reference_codes.xlsx"
    return load_main_data(wb), load_impact_links(wb), load_reference_codes(ref)


def load_all_final(processed_dir: Path = PROCESSED_DIR, raw_dir: Path = RAW_DIR) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convenience loader returning (main_data, impact_links, reference_codes)
    from the FINAL workbook produced by build_impact_refinements.py (Task 3
    output), which adds the calibrated Telebirr -> ACC_MM_ACCOUNT link on top
    of the Task 1 enrichment. This is what Task 3 impact modeling should use."""
    wb = processed_dir / "ethiopia_fi_unified_data_final.xlsx"
    ref = raw_dir / "reference_codes.xlsx"
    return load_main_data(wb), load_impact_links(wb), load_reference_codes(ref)


def load_all_task4(processed_dir: Path = PROCESSED_DIR, raw_dir: Path = RAW_DIR) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convenience loader returning (main_data, impact_links, reference_codes)
    from the TASK 4 workbook produced by build_task4_targets.py, which adds
    the real, Findex-defined Digital Payment Usage observations (distinct
    from ACC_MM_ACCOUNT) on top of the Task 3 final dataset. This is what
    Task 4 forecasting should use."""
    wb = processed_dir / "ethiopia_fi_unified_data_task4.xlsx"
    ref = raw_dir / "reference_codes.xlsx"
    return load_main_data(wb), load_impact_links(wb), load_reference_codes(ref)
