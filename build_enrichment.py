"""
build_enrichment.py

Adds new observation, event, and impact_link records to the Ethiopia
Financial Inclusion dataset, following the exact schema of the starter
data, each backed by a real, cited source (see data_enrichment_log.md
for the full writeup of each addition).

Run from the project root:
    python build_enrichment.py
"""
import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

COLLECTED_BY = "Yengusie Demilie Alene"  
COLLECTION_DATE = "2026-07-15"

# ----------------------------------------------------------------------
# Load starter data
# ----------------------------------------------------------------------
main = pd.read_excel(RAW_DIR / "ethiopia_fi_unified_data.xlsx", sheet_name="ethiopia_fi_unified_data")
links = pd.read_excel(RAW_DIR / "ethiopia_fi_unified_data.xlsx", sheet_name="Impact_sheet")

MAIN_COLS = main.columns.tolist()
LINK_COLS = links.columns.tolist()


def blank_row(cols):
    return {c: None for c in cols}


# ----------------------------------------------------------------------
# NEW OBSERVATIONS (8)
# ----------------------------------------------------------------------
new_observations = []

def obs(record_id, pillar, indicator, indicator_code, indicator_direction,
        value_numeric, value_type, unit, observation_date, gender, location,
        source_name, source_type, source_url, confidence,
        original_text, notes, value_text=None):
    observation_date = pd.Timestamp(observation_date)
    row = blank_row(MAIN_COLS)
    row.update(dict(
        record_id=record_id, record_type="observation", pillar=pillar,
        indicator=indicator, indicator_code=indicator_code,
        indicator_direction=indicator_direction,
        value_numeric=value_numeric, value_text=value_text, value_type=value_type, unit=unit,
        observation_date=observation_date, fiscal_year=pd.to_datetime(observation_date).year,
        gender=gender, location=location, source_name=source_name,
        source_type=source_type, source_url=source_url, confidence=confidence,
        collected_by=COLLECTED_BY, collection_date=COLLECTION_DATE,
        original_text=original_text, notes=notes,
    ))
    return row

new_observations.append(obs(
    "REC_0034", "ACCESS", "Mobile Money Agent Count", "ACC_MM_AGENTS", "higher_better",
    200000, "count", "agents", "2022-09-30", "all", "national",
    "NBE (via GSMA/FSD Ethiopia)", "research",
    "https://fsdethiopia.org/wp-content/pdf/Financial%20Sector%20Deepening%20Ethiopia%20Blog%20_%20Mobile%20Money%20in%20Ethiopia.pdf",
    "medium",
    "mobile money agents grew by 200% in the year to September 2022 to over 200,000",
    "Agent network density is a direct correlate of financial access (per Additional_Data_Points_Guide, item B.3); no agent-count indicator existed in the starter data at all.",
))

new_observations.append(obs(
    "REC_0035", "ACCESS", "Telebirr Agent Count", "ACC_TELEBIRR_AGENTS", "higher_better",
    111000, "count", "agents", "2023-07-01", "all", "national",
    "GSMA / FSD Ethiopia", "research",
    "https://fsdethiopia.org/wp-content/pdf/Financial%20Sector%20Deepening%20Ethiopia%20Blog%20_%20Mobile%20Money%20in%20Ethiopia.pdf",
    "medium",
    "incumbent Telebirr has 111,000+ agents with a 20% active rate on a weekly basis",
    "Complements REC_0034 with provider-level detail; the 20% weekly active rate (noted here, not modeled as a separate indicator) highlights an agent-quality gap worth tracking alongside raw agent counts.",
))

new_observations.append(obs(
    "REC_0036", "GENDER", "Mobile Money Awareness Rate", "GEN_MM_AWARENESS", "higher_better",
    49.0, "percentage", "%", "2023-06-30", "male", "national",
    "GSMA (survey fieldwork in Ethiopia)", "research",
    "https://fsdethiopia.org/wp-content/pdf/Financial%20Sector%20Deepening%20Ethiopia%20Blog%20_%20Mobile%20Money%20in%20Ethiopia.pdf",
    "medium",
    "only 35% of female respondents reported being aware of mobile money compared to 49% of male respondents",
    "New GENDER-pillar indicator distinct from GEN_GAP_ACC (ownership gap): awareness is an upstream barrier before account opening, useful as a leading indicator.",
))

new_observations.append(obs(
    "REC_0037", "GENDER", "Mobile Money Awareness Rate", "GEN_MM_AWARENESS", "higher_better",
    35.0, "percentage", "%", "2023-06-30", "female", "national",
    "GSMA (survey fieldwork in Ethiopia)", "research",
    "https://fsdethiopia.org/wp-content/pdf/Financial%20Sector%20Deepening%20Ethiopia%20Blog%20_%20Mobile%20Money%20in%20Ethiopia.pdf",
    "medium",
    "only 35% of female respondents reported being aware of mobile money compared to 49% of male respondents",
    "Paired with REC_0036 (male). A 14pp awareness gap partly explains the account-ownership gender gap already tracked in GEN_GAP_ACC.",
))

new_observations.append(obs(
    "REC_0038", "DEPTH", "Telebirr Cumulative Microloans Disbursed", "DEPTH_TELEBIRR_LOANS", "higher_better",
    1000000, "count", "loans", "2023-07-01", "all", "national",
    "GSMA / FSD Ethiopia (citing Telebirr)", "research",
    "https://fsdethiopia.org/wp-content/pdf/Financial%20Sector%20Deepening%20Ethiopia%20Blog%20_%20Mobile%20Money%20in%20Ethiopia.pdf",
    "medium",
    "Telebirr states that it has disbursed 1million+ microloans",
    "First DEPTH-pillar observation in the dataset (savings/credit/insurance were entirely uncovered). Figure is provider-reported ('1 million+'), hence medium rather than high confidence.",
))

new_observations.append(obs(
    "REC_0039", "ACCESS", "Internet Penetration Rate", "ACC_INTERNET_PEN", "higher_better",
    16.7, "percentage", "%", "2023-01-15", "all", "national",
    "DataReportal (Kepios, citing ITU)", "research",
    "https://freedomhouse.org/country/ethiopia/freedom-net/2024",
    "medium",
    "As of January 2023, DataReportal reported that Ethiopia's internet penetration rate was 16.7 percent of the total population. The International Telecommunication Union (ITU) also cites the same 16.7 percent figure",
    "Distinct from ACC_4G_COV (population coverage/availability): this measures actual usage, a better proxy for the connectivity on-ramp to DFS (guide item C.1).",
))

new_observations.append(obs(
    "REC_0040", "ACCESS", "Internet Penetration Rate", "ACC_INTERNET_PEN", "higher_better",
    19.4, "percentage", "%", "2024-01-15", "all", "national",
    "DataReportal (Kepios, citing ITU)", "research",
    "https://datareportal.com/reports/digital-2024-ethiopia",
    "medium",
    "Ethiopia's internet penetration rate stood at 19.4 percent of the total population at the start of 2024",
    "Second data point for ACC_INTERNET_PEN, giving this new indicator an actual trend (16.7% -> 19.4%) rather than a single snapshot.",
))

new_observations.append(obs(
    "REC_0041", "GENDER", "Banks Improving Women's Financial Inclusion Score (YoY)", "GEN_BANK_SCORECARD_IMPROVE",
    "higher_better", 66.0, "percentage", "%", "2026-07-12", "all", "national",
    "National Bank of Ethiopia", "regulator",
    "https://nbe.gov.et/nbe_news/nbe-launches-second-womens-financial-inclusion-scorecard-and-celebrates-1000-newfin-graduates/",
    "medium",
    "This year's edition covers all 32 banks and provides the first year-on-year assessment. The findings show broad-based progress, with nearly two-thirds of participating institutions improving their performance.",
    "NBE's own Women's Financial Inclusion Scorecard (2nd edition, all 32 banks) is a primary, official supply-side gender metric. '~66%' approximates the reported 'nearly two-thirds' -- confidence set to medium (not high) because the source itself uses an approximate figure, not an exact percentage.",
))

# ----------------------------------------------------------------------
# NEW EVENTS (4) -- category filled, pillar deliberately left blank
# ----------------------------------------------------------------------
new_events = []

def event(record_id, category, indicator, observation_date, source_name,
          source_type, source_url, confidence, original_text, notes):
    observation_date = pd.Timestamp(observation_date)
    row = blank_row(MAIN_COLS)
    row.update(dict(
        record_id=record_id, record_type="event", category=category, pillar=None,
        indicator=indicator, observation_date=observation_date,
        fiscal_year=pd.to_datetime(observation_date).year,
        source_name=source_name, source_type=source_type, source_url=source_url,
        confidence=confidence, collected_by=COLLECTED_BY, collection_date=COLLECTION_DATE,
        original_text=original_text, notes=notes,
    ))
    return row

new_events.append(event(
    "EVT_0011", "regulation", "NBE Payment Instrument Issuer Directive Revision (Balance Cap Raise)",
    "2023-10-09", "National Bank of Ethiopia", "regulator",
    "https://nbe.gov.et/nbe_news/the-national-bank-of-ethiopia-has-issued-a-revised-directive-for-mobile-money-providers-to-promote-safety-competition-and-innovation/",
    "high",
    "Raises the daily electronic account balance limit from Birr 30,000 to 75,000. Introduces a new daily aggregate transaction limit of Birr 150,000... Enables banks to establish subsidiaries focused on providing mobile money services",
    "Primary NBE source. A regulatory loosening plausibly enabling higher-value digital transactions -- linked via a new impact_link to USG_TELEBIRR_VALUE.",
))

new_events.append(event(
    "EVT_0012", "regulation", "NBE Mandatory Mobile Money Interoperability Directive (ONPS/10/2025)",
    "2025-05-27", "National Bank of Ethiopia (reported by Addis Insight)", "news",
    "https://addisinsight.net/2025/05/27/national-bank-of-ethiopia-issues-new-directive-to-strengthen-digital-payment-ecosystem/",
    "medium",
    "The directive mandates all mobile money operators to ensure wallet-to-wallet interoperability through the National Switch... All financial institutions offering digital payments are now required to integrate into the Ethiopian Instant Payment System (EIPS)",
    "Secondary news source (medium confidence) reporting a primary NBE directive; the primary NBE announcement could not be independently located at collection time. Plausible regulatory enabler that precedes the already-catalogued EVT_0007 (M-Pesa EthSwitch Integration, Oct 2025) by ~5 months.",
))

new_events.append(event(
    "EVT_0013", "infrastructure", "Ethio Telecom Commercial 5G Launch",
    "2023-09-01", "Freedom House (Freedom on the Net 2024, citing Ethio Telecom)", "research",
    "https://freedomhouse.org/country/ethiopia/freedom-net/2024",
    "medium",
    "In September 2023, Ethio Telecom launched commercial fifth-generation (5G) mobile network technology at 145 sites",
    "Infrastructure milestone not previously captured; complements the existing ACC_4G_COV observations with a distinct 5G rollout event, linked to ACC_INTERNET_PEN via a new impact_link.",
))

new_events.append(event(
    "EVT_0014", "policy", "NBE Second Women's Financial Inclusion Scorecard Launch",
    "2026-07-12", "National Bank of Ethiopia", "regulator",
    "https://nbe.gov.et/nbe_news/nbe-launches-second-womens-financial-inclusion-scorecard-and-celebrates-1000-newfin-graduates/",
    "high",
    "the National Bank of Ethiopia launched the second Women's Financial Inclusion Scorecard and celebrated the graduation of 1,000 participants from the NEWFin Young Professionals Program",
    "Primary NBE source. A GENDER-pillar policy milestone with no prior representation in the events catalog (all 5 existing GENDER observations are outcome measures, not policy actions).",
))

# ----------------------------------------------------------------------
# NEW IMPACT_LINKS (6)
# ----------------------------------------------------------------------
new_links = []

def impact_link(record_id, parent_id, pillar, indicator_label, related_indicator,
                 relationship_type, impact_direction, impact_magnitude, impact_estimate,
                 lag_months, evidence_basis, comparable_country,
                 source_url, confidence, notes):
    row = blank_row(LINK_COLS)
    row.update(dict(
        record_id=record_id, parent_id=parent_id, record_type="impact_link",
        pillar=pillar, indicator=indicator_label,
        related_indicator=related_indicator, relationship_type=relationship_type,
        impact_direction=impact_direction, impact_magnitude=impact_magnitude,
        impact_estimate=impact_estimate, lag_months=lag_months,
        evidence_basis=evidence_basis, comparable_country=comparable_country,
        source_url=source_url, confidence=confidence,
        collected_by=COLLECTED_BY, collection_date=COLLECTION_DATE, notes=notes,
    ))
    return row

new_links.append(impact_link(
    "IMP_0015", "EVT_0011", "USAGE", "Balance Cap Raise effect on Telebirr Transaction Value",
    "USG_TELEBIRR_VALUE", "enabling", "increase", "medium", 10, 6, "theoretical", None,
    "https://nbe.gov.et/nbe_news/the-national-bank-of-ethiopia-has-issued-a-revised-directive-for-mobile-money-providers-to-promote-safety-competition-and-innovation/",
    "medium",
    "Higher per-transaction and daily balance ceilings mechanically raise the size of transactions the system can process; a plausible but not-yet-empirically-verified enabling relationship.",
))

new_links.append(impact_link(
    "IMP_0016", "EVT_0012", "ACCESS", "Interoperability Mandate effect on Mobile Money Account Rate",
    "ACC_MM_ACCOUNT", "enabling", "increase", "medium", 8, 6, "theoretical", "Tanzania",
    "https://addisinsight.net/2025/05/27/national-bank-of-ethiopia-issues-new-directive-to-strengthen-digital-payment-ecosystem/",
    "medium",
    "Mirrors the Tanzania interoperability precedent already cited for IMP_0011/IMP_0012 (M-Pesa EthSwitch): mandating interoperability tends to raise account registration, not just usage of existing accounts.",
))

new_links.append(impact_link(
    "IMP_0017", "EVT_0013", "ACCESS", "5G Launch effect on Internet Penetration Rate",
    "ACC_INTERNET_PEN", "direct", "increase", "medium", 15, 12, "theoretical", None,
    "https://freedomhouse.org/country/ethiopia/freedom-net/2024",
    "medium",
    "Higher-speed network availability is a plausible direct driver of the internet-penetration trend already observed rising from 16.7% (Jan 2023) to 19.4% (Jan 2024) in REC_0039/REC_0040.",
))

new_links.append(impact_link(
    "IMP_0018", "EVT_0014", "GENDER", "Women's Scorecard effect on Account Ownership Gender Gap",
    "GEN_GAP_ACC", "indirect", "decrease", "low", -3, 12, "theoretical", None,
    "https://nbe.gov.et/nbe_news/nbe-launches-second-womens-financial-inclusion-scorecard-and-celebrates-1000-newfin-graduates/",
    "medium",
    "A bank-performance benchmarking tool is an indirect lever (via institutional incentives), not a direct product change, hence 'indirect' relationship_type and 'low' magnitude.",
))

new_links.append(impact_link(
    "IMP_0019", "EVT_0001", "DEPTH", "Telebirr Launch effect on Telebirr Microloans Disbursed",
    "DEPTH_TELEBIRR_LOANS", "direct", "increase", "high", 1000000, 24, "empirical", None,
    "https://fsdethiopia.org/wp-content/pdf/Financial%20Sector%20Deepening%20Ethiopia%20Blog%20_%20Mobile%20Money%20in%20Ethiopia.pdf",
    "medium",
    "Telebirr's own credit product (Mela) launched after the base wallet; the >1 million cumulative microloans figure (REC_0038) is a direct, empirically observed downstream effect of the original 2021 launch, arriving with a multi-year lag as adjacent products rolled out.",
))

new_links.append(impact_link(
    "IMP_0020", "EVT_0003", "ACCESS", "M-Pesa Launch effect on Mobile Money Agent Count",
    "ACC_MM_AGENTS", "direct", "increase", "medium", 15, 6, "theoretical", "Kenya",
    "https://fsdethiopia.org/wp-content/pdf/Financial%20Sector%20Deepening%20Ethiopia%20Blog%20_%20Mobile%20Money%20in%20Ethiopia.pdf",
    "medium",
    "A second major provider building its own agent network plausibly adds to the market-wide agent count (REC_0034/REC_0035), consistent with Safaricom's Kenya build-out pattern.",
))

# ----------------------------------------------------------------------
# Merge and save
# ----------------------------------------------------------------------
main_enriched = pd.concat([main, pd.DataFrame(new_observations)[MAIN_COLS],
                            pd.DataFrame(new_events)[MAIN_COLS]], ignore_index=True)
links_enriched = pd.concat([links, pd.DataFrame(new_links)[LINK_COLS]], ignore_index=True)

with pd.ExcelWriter(OUT_DIR / "ethiopia_fi_unified_data_enriched.xlsx", engine="openpyxl") as writer:
    main_enriched.to_excel(writer, sheet_name="ethiopia_fi_unified_data", index=False)
    links_enriched.to_excel(writer, sheet_name="Impact_sheet", index=False)

main_enriched.to_csv(OUT_DIR / "data.csv", index=False)
links_enriched.to_csv(OUT_DIR / "impact_links.csv", index=False)

print(f"Main sheet: {len(main)} -> {len(main_enriched)} records "
      f"(+{len(new_observations)} observations, +{len(new_events)} events)")
print(f"Impact_links: {len(links)} -> {len(links_enriched)} records (+{len(new_links)})")
print("Written to data/processed/")
