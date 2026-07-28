"""
utils.py

Reusable helpers extracted from logic that was duplicated across every
build_*.py pipeline stage (each one loaded the same two-sheet workbook
layout and wrote it back out the same way) -- part of the Engineering
Excellence refactor's "extract reusable logic into utility functions" pass.
"""
from pathlib import Path
from typing import Tuple
import pandas as pd

MAIN_SHEET_NAME: str = "ethiopia_fi_unified_data"
IMPACT_LINKS_SHEET_NAME: str = "Impact_sheet"


def load_workbook_sheets(path: Path,
                          main_sheet: str = MAIN_SHEET_NAME,
                          links_sheet: str = IMPACT_LINKS_SHEET_NAME) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load the (main_data, impact_links) pair from a two-sheet workbook.
    Every build_*.py pipeline stage reads its upstream file this same way."""
    main_df = pd.read_excel(path, sheet_name=main_sheet)
    links_df = pd.read_excel(path, sheet_name=links_sheet)
    return main_df, links_df


def write_workbook_sheets(path: Path, main_df: pd.DataFrame, links_df: pd.DataFrame,
                           main_sheet: str = MAIN_SHEET_NAME,
                           links_sheet: str = IMPACT_LINKS_SHEET_NAME) -> None:
    """Write the (main_data, impact_links) pair back out to a two-sheet
    workbook, creating the parent directory if needed. Every build_*.py
    pipeline stage writes its output this same way."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        main_df.to_excel(writer, sheet_name=main_sheet, index=False)
        links_df.to_excel(writer, sheet_name=links_sheet, index=False)


def blank_record(columns) -> dict:
    """An empty record dict with every column present and set to None --
    the safe starting point for building one new row to append to a sheet
    that may have columns a given build stage doesn't need to populate."""
    return {c: None for c in columns}
