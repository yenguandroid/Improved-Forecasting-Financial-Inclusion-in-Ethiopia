"""
build_task4_targets.py

Task 4 forecasts two indicators: Account Ownership Rate (Access) and
Digital Payment Usage (Usage). ACC_OWNERSHIP already exists in the dataset
with 4 real Findex points (2014, 2017, 2021, 2024). However, no indicator
in the existing dataset matches Findex's actual "Digital Payment Usage"
definition (% of adults who made or received a digital payment in the past
year) -- the closest existing indicator, ACC_MM_ACCOUNT (Mobile Money
Account Rate), measures something related but different (having a mobile
money account, not having made/received ANY digital payment through any
channel).

Using ACC_MM_ACCOUNT as a stand-in for "Digital Payment Usage" would
materially overstate the forecast (it is on a much steeper trajectory:
4.7% -> 9.45%, 2021-2024). This script instead adds the real,
Findex-defined Digital Payment Usage figures for Ethiopia, researched and
cited below, so Task 4 forecasts the actual target the task specifies.

Sources (see full citations in data_enrichment_log_task4.md):
  - 2021: ~20% of Ethiopian adults made or received a digital payment
    (World Bank Africa Can End Poverty blog, based on Global Findex 2021).
  - 2024: ~21% (derived: AfricaNenda's Global Findex 2025 analysis reports
    Ethiopia's digital payment adoption grew "5%" in relative terms and by
    "just 1 percentage point" in absolute terms between 2021 and 2024 --
    solving for a base consistent with both figures gives ~20% -> ~21%).

Run from the project root (after build_impact_refinements.py has already run):
    python build_task4_targets.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from utils import load_workbook_sheets, write_workbook_sheets, blank_record  # noqa: E402

PROCESSED_DIR = Path("data/processed")
FINAL_PATH = PROCESSED_DIR / "ethiopia_fi_unified_data_final.xlsx"
TASK4_PATH = PROCESSED_DIR / "ethiopia_fi_unified_data_task4.xlsx"

COLLECTED_BY = "Yengusie Demilie Alene"
COLLECTION_DATE = "2026-07-21"


def main() -> None:
    main_df, links = load_workbook_sheets(FINAL_PATH)

    cols = main_df.columns.tolist()

    def blank_row() -> dict:
        return blank_record(cols)

    def digital_payment_obs(record_id, observation_date, value_numeric, source_url,
                             original_text, confidence, notes):
        row = blank_row()
        row.update(dict(
            record_id=record_id, record_type="observation", pillar="USAGE",
            indicator="Digital Payment Usage", indicator_code="USG_DIGITAL_PAYMENT",
            indicator_direction="higher_better", value_numeric=value_numeric,
            value_type="percentage", unit="%",
            observation_date=pd.Timestamp(observation_date),
            fiscal_year=pd.Timestamp(observation_date).year,
            gender="all", location="national",
            source_name="World Bank Global Findex (via secondary analysis)",
            source_type="research", source_url=source_url, confidence=confidence,
            collected_by=COLLECTED_BY, collection_date=COLLECTION_DATE,
            original_text=original_text, notes=notes,
        ))
        return row

    new_rows = [
        digital_payment_obs(
            "REC_0042", "2021-12-31", 20.0,
            "https://blogs.worldbank.org/en/africacan/mobile-phone-technology-could-expand-equitable-access-financial-services-ethiopia",
            "Only 42% of account holders -- 20% of adults -- used their accounts for "
            "digital payments in the year prior to the Global Findex survey",
            "medium",
            "This is the Findex-defined 'Digital Payment Usage' target for Task 4 "
            "(% of adults who made or received a digital payment), NOT the same as "
            "ACC_MM_ACCOUNT (Mobile Money Account Rate). Distinguishing these matters: "
            "ACC_MM_ACCOUNT rose from 4.7% (2021) to 9.45% (2024), a much steeper "
            "trajectory than Digital Payment Usage's near-flat 20% -> ~21%. Confidence "
            "medium: figure is stated directly in a World Bank blog post but is itself "
            "a secondary restatement of the underlying 2021 Findex microdata, not a "
            "direct World Bank Findex table citation.",
        ),
        digital_payment_obs(
            "REC_0043", "2024-11-29", 20.7,
            "https://digitalfinance.worldbank.org/country/ethiopia",
            "Used digital payments: 20.65645673% (2024) -- row from the World Bank's "
            "Inclusive Digital Financial Services (IDFS) Ethiopia country snapshot "
            "export, indicator group 'Formal saving, borrowing, and payments', "
            "sourced directly to Findex, with the description field defining it as "
            "'Percentage of adults (age 15+) who used mobile money, a debit or credit "
            "card, or a mobile phone to make a payment from an account\u2014or report "
            "using the internet to pay bills or to buy something online or in a "
            "store\u2014in the past year' -- an exact match to USG_DIGITAL_PAYMENT's "
            "definition.",
            "high",
            "SUPERSEDES the prior derived estimate of 21.0%. Task 1 re-verification "
            "originally could not read the primary Findex 2025 table directly (gated "
            "microdata download, unparsable binary spreadsheet, JS-rendered "
            "dashboard); a user-supplied CSV export of the World Bank's own "
            "digitalfinance.worldbank.org/country/ethiopia country-snapshot download "
            "made the underlying table readable. The value there (20.66%, rounded to "
            "20.7% for consistency with this sheet's 1-decimal convention) is a DIRECT "
            "citation from the primary Findex source, not a derivation -- an upgrade "
            "from the previous algebra-based estimate (x*1.05 - x = 1pp on a blog "
            "post's relative-growth and pp-change figures). Confidence raised from "
            "medium to high accordingly. The new value (20.7%) is close to but not "
            "identical to the old derived estimate (21.0%, a 0.3pp difference), which "
            "is within the 'equally defensible range' (20.5-21.5%) previously flagged "
            "-- i.e. the derivation method held up reasonably well, but the primary "
            "figure is preferred wherever available. REC_0042's 2021 figure (20.0%, "
            "medium confidence, still a secondary restatement) is unchanged by this "
            "update; only the 2024 point has primary-table confirmation. See "
            "data_quality_note_findex2025_verification.md for full detail and update "
            "history.",
        ),
    ]

    main_task4 = pd.concat([main_df, pd.DataFrame(new_rows)[cols]], ignore_index=True)

    write_workbook_sheets(TASK4_PATH, main_task4, links)
    main_task4.to_csv(PROCESSED_DIR / "data.csv", index=False)

    print(f"Main sheet: {len(main_df)} -> {len(main_task4)} records (+{len(new_rows)} Digital Payment Usage observations)")
    print(f"Written to {TASK4_PATH}")


if __name__ == "__main__":
    main()
