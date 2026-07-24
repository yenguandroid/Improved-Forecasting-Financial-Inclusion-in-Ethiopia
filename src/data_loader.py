"""
data_loader.py

Utilities for loading the Ethiopia Financial Inclusion unified dataset:
the main data sheet (observations, events, targets), the impact_links
sheet, and the reference_codes lookup table.
"""
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

UNIFIED_WORKBOOK = RAW_DIR / "ethiopia_fi_unified_data.xlsx"
REFERENCE_CODES = RAW_DIR / "reference_codes.xlsx"

DATE_COLS = ["observation_date", "period_start", "period_end", "collection_date"]


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in DATE_COLS:
        if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], errors="coerce", format="ISO8601")
    return df


def load_main_data(path: Path = UNIFIED_WORKBOOK) -> pd.DataFrame:
    """
    Load the main data sheet: observation / event / target records.
    """
    df = pd.read_excel(path, sheet_name="ethiopia_fi_unified_data")
    return _parse_dates(df)


def load_impact_links(path: Path = UNIFIED_WORKBOOK) -> pd.DataFrame:
    """
    Load the impact_links sheet: modeled relationships between events
    (via parent_id, referencing an event's record_id in the main sheet)
    and indicators.
    """
    df = pd.read_excel(path, sheet_name="Impact_sheet")
    return _parse_dates(df)


def load_reference_codes(path: Path = REFERENCE_CODES) -> pd.DataFrame:
    """
    Load the reference_codes lookup table: valid values for every
    categorical field used in the main data and impact_links sheets.
    """
    return pd.read_excel(path, sheet_name="reference_codes")


def valid_codes(reference_codes: pd.DataFrame, field: str) -> list:
    """Return the list of valid codes for a given field (e.g. 'pillar')."""
    return reference_codes.loc[reference_codes["field"] == field, "code"].tolist()


def load_all(raw_dir: Path = RAW_DIR):
    """Convenience loader returning (main_data, impact_links, reference_codes)."""
    wb = raw_dir / "ethiopia_fi_unified_data.xlsx"
    ref = raw_dir / "reference_codes.xlsx"
    return load_main_data(wb), load_impact_links(wb), load_reference_codes(ref)
