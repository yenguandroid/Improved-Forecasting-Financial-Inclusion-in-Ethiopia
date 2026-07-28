# Data Enrichment Log — Task 4

Documents the 2 new observations added specifically for Task 4 forecasting
(`build_task4_targets.py`), on top of the Task 1/3 enriched/final dataset.


## Why this addition was necessary

Task 4 requires forecasting "Digital Payment Usage: % of adults who made
or received a digital payment." No indicator in the dataset through Task 3
actually measures this — the closest existing indicator, `ACC_MM_ACCOUNT`
(Mobile Money Account Rate), measures a related but different thing:
whether someone has a mobile money account, not whether they made or
received *any* digital payment through *any* channel (mobile money, card,
or online).

The difference matters a great deal for a forecast: `ACC_MM_ACCOUNT` rose
from 4.7% to 9.45% (2021–2024, roughly doubling), while Ethiopia's actual
Digital Payment Usage moved from approximately 20% to approximately 21%
over the same window — a far flatter trajectory. Forecasting
`ACC_MM_ACCOUNT` under the label "Digital Payment Usage" would have
produced a materially over-optimistic Usage forecast for the wrong target.

## New Observations

### REC_0042 — Digital Payment Usage, 2021
- **Pillar / Indicator:** USAGE / `USG_DIGITAL_PAYMENT`
- **Value:** 20.0%, 2021-12-31, national
- **Source:** World Bank, "Mobile Phone Technology Could Expand Equitable
  Access to Financial Services in Ethiopia" (Africa Can End Poverty blog) —
  https://blogs.worldbank.org/en/africacan/mobile-phone-technology-could-expand-equitable-access-financial-services-ethiopia
- **Original text:** *"Only 42% of account holders — 20% of adults — used
  their accounts for digital payments in the year prior to the Global
  Findex survey"*
- **Confidence:** medium — the figure is stated directly, but the source
  is a secondary restatement of the underlying 2021 Findex microdata
  rather than a direct World Bank Findex data-table citation.
- **Why useful:** the correct, Findex-defined Usage target baseline for
  Task 4's 2021 data point.

### REC_0043 — Digital Payment Usage, 2024
- **Pillar / Indicator:** USAGE / `USG_DIGITAL_PAYMENT`
- **Value:** 21.0%, 2024-11-29, national
- **Source:** AfricaNenda, "The Global Findex 2025: Could Instant Payments
  be Driving Financial Inclusion in Africa?" —
  https://www.africanenda.org/en/blog/2025/the-global-findex-2025-could-instant-payments-be-driving-financial-inclusion-in-africa
- **Original text:** *"Ethiopia ... saw more modest growth of 5% in
  account ownership and 5% in digital payment adoption in the years after
  the launch of its IPS, EthSwitch ... the change appeared as a difference
  of just 1 percentage point between 2021 and 2024"*
- **Confidence:** medium — this value is **derived, not directly quoted**.
  The source reports both a ~5% relative growth rate and a 1
  percentage-point absolute change for the same 2021→2024 period. Solving
  `x * 1.05 − x = 1pp` gives `x ≈ 20pp` (2021) and `≈21pp` (2024) —
  consistent with REC_0042's independently-sourced 2021 figure. Two
  independent sources triangulating on the same ~20% starting point
  increases confidence in the estimate, but the 2024 figure specifically
  should be read as approximate (20.5–21.5% would be an equally defensible
  reading of the same source).

## Methodological note

Unlike Task 1's enrichment (which added several observations across many
indicators), this addition is narrowly scoped to exactly the two data
points needed to forecast the task's actual specified target correctly.
No attempt was made to backfill a 2014 or 2017 Digital Payment Usage figure
for Ethiopia — a search for one did not turn up a reliable, directly
citable source, and fabricating an estimate to create a longer series
would undermine the honesty this project has maintained throughout. The
resulting 2-point series is a genuine data limitation, explicitly
addressed in `notebooks/task4_forecasting.ipynb` (Section 3.4) rather than
hidden behind a false sense of statistical confidence.

## A related, resolved discrepancy: "5 Findex points over 13 years"

The Task 4 brief describes Ethiopia's Access data as "5 Findex points over
13 years." Research for this task confirmed Ethiopia's real Findex series
begins in **2014**, not 2011 — Ethiopia was not included in the first
(2011) global Findex survey round. The dataset's 4 real Ethiopia-specific
Account Ownership points (2014, 2017, 2021, 2024) are correct and complete;
no 2011 figure was added, since doing so would require fabricating a data
point that does not exist for this country. This is confirmed against
multiple independent sources (see notebook Section 1 for a fuller
discussion) rather than assumed.
