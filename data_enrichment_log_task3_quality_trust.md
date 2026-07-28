# Data Enrichment Log — Task 3 (Quality/Trust Pillar)

This log documents the one new record added to `ethiopia_fi_unified_data`
by `build_quality_trust_enrichment.py`, following the exact per-record
format used in `data_enrichment_log.md` (Task 1): source, quote,
confidence, notes. Chains onto the fullest current dataset
(`ethiopia_fi_unified_data_task4.xlsx`, i.e. Task 1 + Task 3-impact-model +
Task 4's additions all included).

**Collected by:** Yengusie Demilie Alene
**Collection date:** 2026-07-25

## Why this pillar, why this indicator

Task 1's own enrichment log flagged `QUALITY` and `TRUST` as the two
pillars with **zero** observations in the dataset, even after enrichment
(see its pillar coverage table). Both are defined in `reference_codes.xlsx`:

| Pillar | Description |
|---|---|
| QUALITY | Do services work? Success rates, uptime |
| TRUST | Do people trust it? Complaints, fraud |

I searched for citable, Ethiopia-specific figures for both. QUALITY
candidates (transaction success rates, agent liquidity/uptime, network
downtime) were the kind of operational metric that providers/NBE don't
appear to publish externally — I could not find one with a real, checkable
citation within scope. TRUST turned up a genuine, specific, sourced figure
from a 2025 peer-reviewed academic study on rural Ethiopian mobile money
adoption, so that's the pillar I went with.

## New Observation

### REC_0044 — Lack of Trust Cited as Barrier to Mobile Money Non-Adoption
- **Pillar / Indicator:** TRUST / `TRU_MM_TRUST_BARRIER`
- **Value:** 55.78%, 2025-08-19 (publication date — see caveat below), rural, all genders
- **Source:** Peer-reviewed article, *Cogent Social Sciences* (Taylor & Francis), authors affiliated with the University of Pretoria's Dept. of Agricultural Economics, Extension, and Rural Development — https://doi.org/10.1080/2157930X.2025.2542637 ("What drives digital finance use in rural Africa? Insights from Ethiopia"). Received 20 Feb 2025, accepted 29 Jul 2025, published online 19 Aug 2025.
- **Original text:** *"Lack of trust emerged as the most cited reason for non-adoption (55.78%), followed by difficulties in using mobile accounts (19.73%) and limited knowledge of digital finance services (15.9%)."*
- **Confidence:** medium — two compounding reasons, neither individually disqualifying but stacking to below "high":
  1. **Not nationally representative.** The survey covers 399 respondents in the Kembata Tambaro Zone (southern Ethiopia) only, via a multistage random sample (3 districts → 3 kebeles per district → individuals via probability-proportional-to-size sampling). `location` is set to `rural`, not `national`, to be explicit about this.
  2. **Full text was not accessible.** The article is paywalled; I could only read the abstract and the excerpts surfaced by search, not the complete paper. I'm confident the 55.78% figure and its framing ("most cited reason for non-adoption") are accurate — it's a directly quotable sentence, not something I inferred — but I could not independently verify finer methodology details (exact question wording used to elicit "reasons for non-adoption," whether respondents could select multiple reasons, the precise denominator).
- **Why useful:** The **first TRUST-pillar (and first QUALITY-or-TRUST-pillar) observation in the entire dataset**. Distinct from — and plausibly a contributing factor behind — the already-tracked `ACC_MM_ACCOUNT` and `USG_DIGITAL_PAYMENT` indicators: this measures a *stated barrier* on the demand side rather than an adoption outcome, giving the project its first direct look at *why* Ethiopian mobile money adoption lags rather than just *how much* it has grown. It's also a useful cross-check against the existing academic literature this project has already engaged with elsewhere (the broader Ethiopian financial-inclusion research consistently identifies "lack of trust" as a top-3 barrier alongside cost/distance/documentation, which this figure is directly consistent with, even though those other studies weren't specific enough to cite a number from).

---

## Notes on methodology and honesty

- Consistent with Task 1's convention: a real, checkable `source_url` and an
  exact quote in `original_text` — nothing here was fabricated or
  extrapolated without a citation.
- Consistent with Task 1's convention (see REC_0041's precedent): confidence
  is downgraded from what an otherwise-credible peer-reviewed source would
  normally warrant, because of specific, named caveats about the figure
  itself (sub-national sample, inability to verify full methodology) — the
  imprecision/scope-limitation belongs to what I could confirm about the
  *figure*, not a judgment that the *source* is untrustworthy.
- `location` is explicitly set to `rural`, not `national` — this is a real,
  material distinction (Ethiopia's rural/urban digital divide is
  substantial, per the `ACC_INTERNET_PEN` and phone-ownership data already
  in this project), and marking it `national` would overstate what this
  figure actually represents.
- **What I did not do:** I did not extrapolate this rural-zone figure to a
  national estimate, and did not average it against the general "lack of
  trust is a top-3 barrier" findings from the broader literature search
  (several other Ethiopia-focused papers were found making similar
  qualitative claims without a comparably specific number — see search
  history) to produce a synthetic "more confident" figure. Only the one
  paper that had a specific, quotable percentage was used, cited as exactly
  what it is: one rural-zone study's finding, not a national statistic.

## Candidate QUALITY-pillar indicators considered but not included

Searched for: mobile money transaction success/failure rates, agent
liquidity/cash-out failure rates, network uptime, and NBE-published
consumer-complaint or fraud statistics. None of these turned up a
citable, Ethiopia-specific figure accessible within the scope of this task
— providers and NBE don't appear to publish this kind of operational data
externally (or I wasn't able to locate where they do). This remains a good
candidate for a future enrichment pass, and would be the natural next
addition to bring QUALITY off zero as well.
