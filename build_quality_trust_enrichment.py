"""
build_quality_trust_enrichment.py

Task 3 ("Source and add one new Quality or Trust pillar indicator"):
adds the FIRST QUALITY- or TRUST-pillar observation in the entire dataset.
Both pillars are defined in reference_codes.xlsx (QUALITY: "Do services
work? Success rates uptime"; TRUST: "Do people trust it? Complaints fraud")
but had zero observations even after Task 1 enrichment (see
data_enrichment_log.md's pillar coverage table).

Chosen indicator: the share of mobile-money NON-adopters in rural Ethiopia
who cite lack of trust as their reason for not adopting -- a direct,
demand-side TRUST metric, sourced from a peer-reviewed 2025 academic study
of CBE Birr / Telebirr adoption in the Kembata Tambaro Zone. Full sourcing
detail, quote, and honesty caveats are in
data_enrichment_log_task3_quality_trust.md, following the same
source/quote/confidence/notes format used in Task 1's log.

Chains onto the fullest current dataset (Task 4's output), so the result
includes every prior task's additions.

Run from the project root (after build_task4_targets.py has already run):
    python build_quality_trust_enrichment.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from utils import load_workbook_sheets, write_workbook_sheets, blank_record  # noqa: E402

PROCESSED_DIR = Path("data/processed")
TASK4_PATH = PROCESSED_DIR / "ethiopia_fi_unified_data_task4.xlsx"
OUT_PATH = PROCESSED_DIR / "ethiopia_fi_unified_data_quality_trust.xlsx"

COLLECTED_BY = "Yengusie Demilie Alene"
COLLECTION_DATE = "2026-07-25"


def main() -> None:
    main_df, links = load_workbook_sheets(TASK4_PATH)
    cols = main_df.columns.tolist()

    row = blank_record(cols)
    row.update(dict(
        record_id="REC_0044", record_type="observation", pillar="TRUST",
        indicator="Lack of Trust Cited as Barrier to Mobile Money Non-Adoption",
        indicator_code="TRU_MM_TRUST_BARRIER",
        indicator_direction="lower_better",
        value_numeric=55.78, value_text=None, value_type="percentage", unit="%",
        observation_date=pd.Timestamp("2025-08-19"),
        fiscal_year=2025,
        gender="all", location="rural",
        source_name="Cogent Social Sciences (peer-reviewed journal article, "
                     "Univ. of Pretoria-affiliated authors)",
        source_type="research",
        source_url="https://doi.org/10.1080/2157930X.2025.2542637",
        confidence="medium",
        collected_by=COLLECTED_BY, collection_date=COLLECTION_DATE,
        original_text=(
            "Lack of trust emerged as the most cited reason for non-adoption "
            "(55.78%), followed by difficulties in using mobile accounts "
            "(19.73%) and limited knowledge of digital finance services "
            "(15.9%)."
        ),
        notes=(
            "FIRST TRUST-pillar observation in the entire dataset (QUALITY "
            "and TRUST both had zero observations after Task 1 enrichment -- "
            "see data_enrichment_log.md's pillar coverage table). Survey of "
            "399 respondents in the Kembata Tambaro Zone, southern Ethiopia, "
            "studying CBE Birr and Telebirr adoption via a UTAUT2-based "
            "double-hurdle model; multistage random sampling (districts -> "
            "kebeles -> individuals via PPS). Received 20 Feb 2025, accepted "
            "29 Jul 2025, published online 19 Aug 2025 -- observation_date "
            "set to the publication date since the exact survey fielding "
            "date is not stated in the sections of the article accessible "
            "here (paywalled; only abstract and excerpts available, not the "
            "full text). Confidence set to medium rather than high for two "
            "compounding reasons: (1) the survey covers one rural zone, not "
            "a nationally representative sample -- location is marked "
            "'rural' accordingly, not 'national'; (2) full-text access was "
            "not available, so this cites the abstract/excerpt figure "
            "without being able to verify methodology details (e.g. exact "
            "question wording, whether 55.78% is of all non-adopters or a "
            "subsample) against the complete paper. See "
            "data_enrichment_log_task3_quality_trust.md for the full writeup "
            "and the reasoning for choosing TRUST over QUALITY."
        ),
    ))

    main_out = pd.concat([main_df, pd.DataFrame([row])], ignore_index=True)

    write_workbook_sheets(OUT_PATH, main_out, links)

    print(f"Main sheet: {len(main_df)} -> {len(main_out)} records (+1 TRUST-pillar observation)")
    print(f"Written to {OUT_PATH}")


if __name__ == "__main__":
    main()
