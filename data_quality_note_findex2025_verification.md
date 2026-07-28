# Data Quality Note — Findex 2025 Primary-Table Verification for USG_DIGITAL_PAYMENT

**Task:** Attempt to access the primary Global Findex 2025 country table for
Ethiopia's Digital Payment Usage indicator, to verify or refute `REC_0043`
(2024 value, 21.0%, confidence: medium), which — per
`data_enrichment_log_task4.md` — was **derived**, not directly quoted, from an
AfricaNenda blog post that reported only a relative growth rate ("~5%") and an
absolute change ("1 percentage point") for 2021→2024, not the 2024 level
itself.

## What was attempted

1. **World Bank Microdata Library** (`ETH_2024_FINDEX_v02_M`, DOI
   `10.48529/ma45-0608`) — the actual respondent-level 2024 Ethiopia Findex
   microdata (1,001 cases, 199 variables) is catalogued and confirmed to
   exist. However, the underlying data file and the country PDF report both
   require an authenticated/agreement-gated download; both attempts returned
   opaque binary content that could not be parsed with available tooling.
2. **World Bank official country-level download page**
   (`worldbank.org/en/publication/globalfindex/download-data`) — confirms
   country-level Findex indicators (including the "made or received a digital
   payment" series) are published for 2011/2014/2017/2021/2024 as Excel/CSV/
   Stata files and via World Bank Databank. The direct Excel download
   (`digitalfinance.worldbank.org/download/countrydata/162`, Ethiopia's
   snapshot) was reachable but returned a binary `.xls` file this environment
   cannot open/parse.
3. **`digitalfinance.worldbank.org/country/ethiopia`** (World Bank's own
   Inclusive Digital Financial Services dashboard) — confirms a "Digital
   payments" indicator exists for Ethiopia, explicitly defined as "% of adults
   (age 15+) who used mobile money, a debit or credit card, or a mobile phone
   to make a payment from an account... in the past year," sourced to Findex,
   2024, with data availability across 98 countries. This is the *correct*
   indicator definition (matching `USG_DIGITAL_PAYMENT`'s intent) and its
   presence on Ethiopia's page indicates Ethiopia has a populated 2024 value —
   but the number itself is rendered client-side via JavaScript and was not
   present in the fetched page content.
4. **G20 Financial Inclusion Indicators dashboard**
   (`datatopics.worldbank.org/g20fidata/country/ethiopia`) — lists "Made or
   received digital payments in the past year (% age 15+)" as a tracked
   indicator for Ethiopia, but the page displays "N/A" for every indicator and
   every country checked (Ethiopia and Benin both). This dashboard is a
   legacy, Flash-dependent tool and appears stale/unmaintained; **it is not a
   usable source** and should not be treated as evidence of missing data at
   the primary-database level.

## Outcome (initial attempt)

**Direct read of the primary Findex 2025 country-table number for Ethiopia's
Digital Payment Usage indicator was not achieved** through automated fetches
in this environment — every route to the authoritative figure led to either
an access-gated file, a binary spreadsheet this environment can't parse, or a
JavaScript-rendered dashboard value. This was a genuine tooling limitation,
not evidence that the figure doesn't exist or that the existing derived
estimate was wrong.

## RESOLVED (update): primary table obtained

The user subsequently supplied the CSV export from
`digitalfinance.worldbank.org/country/ethiopia` — the World Bank's Inclusive
Digital Financial Services (IDFS) country-snapshot download, the exact file
the earlier binary/JS-rendering attempts couldn't get through. It contains
the primary Findex 2025 country table directly, including:

```
Indicator: Formal saving, borrowing, and payments
Subindicator: Used digital payments
Year: 2024
Value: 20.65645673
Unit: %
Source: Findex
Description: Percentage of adults (age 15+) who used mobile money, a debit
or credit card, or a mobile phone to make a payment from an account—or
report using the internet to pay bills or to buy something online or in a
store—in the past year.
```

The `Description` field is a direct match — word for word — to
`USG_DIGITAL_PAYMENT`'s intended definition. This is a **direct citation from
the primary Findex source**, not a derivation.

## Resolution on REC_0042 / REC_0043

- **REC_0043 value: updated from 21.0% (derived) to 20.7%** (20.65645673%,
  rounded to 1 decimal for consistency with the sheet's convention). This
  supersedes the AfricaNenda-derived estimate.
- **REC_0043 confidence: upgraded from "medium" to "high"** — this is now a
  direct read of the primary table rather than an algebra-based inference
  from a secondary blog post's relative-growth and pp-change figures.
- **The old derivation held up well**: 21.0% (derived) vs. 20.7% (primary) is
  only a 0.3pp difference, within the "equally defensible range"
  (20.5–21.5%) flagged in the original derivation note. The correction is
  small but real.
- **REC_0042 (2021, 20.0%) is unchanged** — it remains a secondary
  restatement (World Bank blog), medium confidence. No primary-table value
  for the 2021 wave was available in the supplied file (a country-snapshot
  export, not a time series), so this task only resolves the 2024 point.
- **Source updated** to
  `https://digitalfinance.worldbank.org/country/ethiopia`, the IDFS Ethiopia
  country-snapshot dashboard/download, in place of the AfricaNenda blog post.

## Effect on Task 4 forecast

Re-running `build_task4_targets.py` and `notebooks/task4_forecasting.ipynb`
with the corrected value/confidence shifts the entire base-scenario curve
down by a flat 0.3pp (a pure level-shift, since the base-scenario growth rate
is a hardcoded assumption, not recomputed from the data — see caveat below):

| Year | Usage — Pessimistic | Usage — Base (old → new) | Usage — Optimistic |
|------|---------------------|----------------------------|----------------------|
| 2025 | 20.7% | 21.4% → **21.1%** | 22.3% |
| 2026 | 20.7% | 21.7% → **21.4%** | 23.8% |
| 2027 | 20.7% | 22.1% → **21.8%** | 25.3% |

**Consistency caveat:** `notebooks/task4_forecasting.ipynb`'s base scenario
uses a hardcoded `annual_growth_pp["base"] = 0.35`, explicitly commented as
*"continues at the same ~0.35pp/year pace observed 2021-2024."* With the
corrected data, the actually-observed 2021→2024 pace is now **0.24pp/year**
(down from 0.34pp/year), so that hardcoded value no longer matches its own
stated rationale. This was left unchanged in this task, since recalibrating a
scenario-design assumption is a separate decision from correcting a data
observation — but if consistency with the notebook's own stated logic is
wanted, the base scenario would come out closer to 21.0% / 21.2% / 21.4% for
2025–2027 instead.
