"""
dashboard/app.py

Interactive Streamlit dashboard for the Ethiopia Financial Inclusion
Forecast project. Reuses the tested src/ modules directly (data_loader,
impact_model, forecasting) rather than reimplementing any logic, so the
dashboard always reflects the same numbers as the project notebooks.

Run locally:
    cd dashboard
    streamlit run app.py
(see README.md "Task 5" section for full setup instructions)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_loader import load_all_task4  # noqa: E402
from impact_model import build_event_effects  # noqa: E402
from forecasting import (  # noqa: E402
    fit_linear_trend, fit_log_trend, scenario_table,
    growth_rate_scenario, incremental_event_effect,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import refresh_data  # noqa: E402

ACCENT = "#1F4E5A"
ACCENT2 = "#B5502A"
GREEN = "#1E7A34"
RED = "#B5342A"
GOLD = "#C79A00"

st.set_page_config(
    page_title="Ethiopia Financial Inclusion Forecast",
    page_icon=":bar_chart:",
    layout="wide",
)

FORECAST_DATES = [pd.Timestamp("2025-12-31"), pd.Timestamp("2026-12-31"), pd.Timestamp("2027-12-31")]


# ----------------------------------------------------------------------
# Cached data loading
# ----------------------------------------------------------------------

@st.cache_data
def get_data():
    main, links, ref = load_all_task4()
    obs = main[main["record_type"] == "observation"].copy()
    events = main[main["record_type"] == "event"].copy().sort_values("observation_date")
    targets = main[main["record_type"] == "target"].copy()
    return obs, events, targets, links


@st.cache_resource
def get_explainability_result():
    """Cached SHAP explainability result for ACC_MM_ACCOUNT -- st.cache_resource
    (not cache_data) since this bundles a fitted sklearn model, which
    cache_data can't hash/serialize safely."""
    from explainability import explain_indicator

    main, links, ref = load_all_task4()
    events = main[main["record_type"] == "event"]
    effects = build_event_effects(links, events, "ACC_MM_ACCOUNT")
    return explain_indicator(
        effects, pd.Timestamp("2021-05-17"), pd.Timestamp("2027-12-31"),
        indicator_code="ACC_MM_ACCOUNT",
    )


@st.cache_data
def get_access_forecast():
    obs, events, targets, links = get_data()
    ownership = obs[(obs["indicator_code"] == "ACC_OWNERSHIP") & (obs["gender"] == "all")].sort_values("observation_date")
    dates = list(ownership["observation_date"])
    values = list(ownership["value_numeric"])

    linear = fit_linear_trend(dates, values)
    log = fit_log_trend(dates, values)
    effects = build_event_effects(links, events, "ACC_OWNERSHIP")
    last_obs = dates[-1]

    scenarios = scenario_table(log, FORECAST_DATES, last_obs, events_effects=effects,
                                optimistic_multiplier=1.5, pessimistic_multiplier=0.5)
    return dict(dates=dates, values=values, linear=linear, log=log,
                effects=effects, last_obs=last_obs, scenarios=scenarios)


@st.cache_data
def get_usage_forecast():
    obs, events, targets, links = get_data()
    dp = obs[obs["indicator_code"] == "USG_DIGITAL_PAYMENT"].sort_values("observation_date")
    dates = list(dp["observation_date"])
    values = list(dp["value_numeric"])
    base_value = values[-1]
    base_date = dates[-1]

    scenarios = growth_rate_scenario(
        base_value, base_date, FORECAST_DATES,
        annual_growth_pp={"pessimistic": 0.0, "base": 0.35, "optimistic": 1.5},
    )
    return dict(dates=dates, values=values, base_value=base_value, base_date=base_date, scenarios=scenarios)


def indicator_series(obs, code, gender="all"):
    sub = obs[obs["indicator_code"] == code]
    if "gender" in sub.columns and gender is not None:
        sub_g = sub[sub["gender"] == gender]
        if len(sub_g) > 0:
            sub = sub_g
    return sub.sort_values("observation_date")


def download_button_for(df: pd.DataFrame, label: str, filename: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label=label, data=csv, file_name=filename, mime="text/csv")


# ----------------------------------------------------------------------
# Page: Overview
# ----------------------------------------------------------------------

def page_overview():
    st.title("Ethiopia Financial Inclusion Dashboard")
    st.caption("Prepared for the Selam Analytics Financial Inclusion Forecasting Consortium "
               "(development finance institutions, mobile money operators, National Bank of Ethiopia)")

    obs, events, targets, links = get_data()

    ownership = indicator_series(obs, "ACC_OWNERSHIP")
    mm_account = indicator_series(obs, "ACC_MM_ACCOUNT")
    digital_payment = indicator_series(obs, "USG_DIGITAL_PAYMENT")
    crossover = indicator_series(obs, "USG_CROSSOVER")

    st.subheader("Key Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        latest = ownership.iloc[-1]
        prev = ownership.iloc[-2]
        st.metric("Account Ownership (Access)", f"{latest['value_numeric']:.0f}%",
                  f"{latest['value_numeric'] - prev['value_numeric']:+.0f}pp vs. {prev['observation_date'].year}",
                  help=f"As of {latest['observation_date'].date()}. Findex-measured share of adults "
                       "with an account at a financial institution or mobile money provider.")
    with c2:
        latest = mm_account.iloc[-1]
        prev = mm_account.iloc[-2]
        st.metric("Mobile Money Account Rate", f"{latest['value_numeric']:.1f}%",
                  f"{latest['value_numeric'] - prev['value_numeric']:+.1f}pp vs. {prev['observation_date'].year}",
                  help=f"As of {latest['observation_date'].date()}. NOT the same as Digital Payment Usage -- "
                       "this measures having a mobile money account specifically.")
    with c3:
        latest = digital_payment.iloc[-1]
        prev = digital_payment.iloc[-2]
        st.metric("Digital Payment Usage", f"{latest['value_numeric']:.0f}%",
                  f"{latest['value_numeric'] - prev['value_numeric']:+.0f}pp vs. {prev['observation_date'].year}",
                  help=f"As of {latest['observation_date'].date()}. Share of adults who made or received "
                       "a digital payment in the past year -- the task's actual Usage target.")
    with c4:
        latest = crossover.iloc[-1] if len(crossover) else None
        if latest is not None:
            st.metric("P2P / ATM Crossover Ratio", f"{latest['value_numeric']:.2f}",
                      "P2P transactions now exceed ATM transactions" if latest["value_numeric"] > 1 else "ATM still leads",
                      help=f"As of {latest['observation_date'].date()}. Ratio > 1 means P2P digital transfer "
                           "volume has overtaken ATM withdrawal volume.")

    st.divider()

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Access Growth Rate Is Decelerating")
        st.caption("Percentage-point growth per year, between successive Findex survey waves -- "
                   "Visualization 1 of this dashboard.")
        waves = ownership[["observation_date", "value_numeric"]].reset_index(drop=True)
        waves["year"] = waves["observation_date"].dt.year
        waves["pp_per_year"] = waves["value_numeric"].diff() / waves["year"].diff()
        plot_df = waves.dropna(subset=["pp_per_year"])
        labels = [f"{int(waves['year'].iloc[i-1])}\u2192{int(waves['year'].iloc[i])}"
                  for i in range(1, len(waves))]

        fig = go.Figure()
        colors = [GREEN if v >= 2 else GOLD if v >= 1 else RED for v in plot_df["pp_per_year"]]
        fig.add_bar(x=labels, y=plot_df["pp_per_year"], marker_color=colors,
                    text=[f"{v:.2f}pp/yr" for v in plot_df["pp_per_year"]], textposition="outside")
        fig.update_layout(yaxis_title="pp gained per year", height=360, margin=dict(t=10, b=10))
        st.plotly_chart(fig, width='stretch')
        st.caption("Growth fell roughly fourfold across the three intervals shown -- from "
                   "+4.33pp/year (2014-2017) to +1.00pp/year (2021-2024) -- despite this being the "
                   "window of heaviest mobile money expansion. See the Forecasts page for what this "
                   "implies going forward.")

    with col_right:
        st.subheader("Registered vs. Genuinely Included")
        st.caption("Why the headline numbers can look contradictory")
        st.markdown(
            "- **65.6M+** combined registered mobile money users (Telebirr + M-Pesa)\n"
            f"- **{mm_account.iloc[-1]['value_numeric']:.1f}%** of adults have a mobile money account (Findex)\n"
            f"- **{digital_payment.iloc[-1]['value_numeric']:.0f}%** of adults actually made/received a "
            "digital payment (Findex) -- the real Usage figure\n\n"
            "Registration counts vastly overstate genuine financial inclusion -- roughly a third of "
            "registered mobile money accounts show no measurable activity in a given period."
        )

    download_button_for(ownership, "Download Account Ownership data (CSV)", "account_ownership.csv")


# ----------------------------------------------------------------------
# Page: Trends
# ----------------------------------------------------------------------

def page_trends():
    st.title("Trends")
    st.caption("Explore the historical data behind this dashboard's metrics.")

    obs, events, targets, links = get_data()

    indicator_options = {
        "Account Ownership Rate (Access)": "ACC_OWNERSHIP",
        "Mobile Money Account Rate": "ACC_MM_ACCOUNT",
        "Digital Payment Usage": "USG_DIGITAL_PAYMENT",
        "4G Population Coverage": "ACC_4G_COV",
        "Internet Penetration Rate": "ACC_INTERNET_PEN",
        "Fayda Digital ID Enrollment": "ACC_FAYDA",
    }

    st.subheader("Interactive Time Series")
    st.caption("Visualization 2 of this dashboard -- select an indicator and date range.")
    col1, col2 = st.columns([2, 2])
    with col1:
        choice_label = st.selectbox("Indicator", list(indicator_options.keys()))
    code = indicator_options[choice_label]
    series = indicator_series(obs, code)

    min_date = series["observation_date"].min().to_pydatetime()
    max_date = pd.Timestamp("2027-12-31").to_pydatetime()
    with col2:
        date_range = st.slider("Date range", min_value=min_date, max_value=max_date,
                                value=(min_date, max_date), format="YYYY-MM-DD")

    show_events = st.checkbox("Overlay events", value=True)

    mask = (series["observation_date"] >= date_range[0]) & (series["observation_date"] <= date_range[1])
    plot_series = series[mask]

    fig = go.Figure()
    fig.add_scatter(x=plot_series["observation_date"], y=plot_series["value_numeric"],
                     mode="lines+markers", line=dict(color=ACCENT, width=2.5), marker=dict(size=9),
                     name=choice_label)
    if show_events:
        events_in_range = events[(events["observation_date"] >= date_range[0]) & (events["observation_date"] <= date_range[1])]
        for _, row in events_in_range.iterrows():
            fig.add_vline(x=row["observation_date"], line_dash="dash", line_color="gray", opacity=0.4)
    fig.update_layout(yaxis_title=choice_label, height=420, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width='stretch')
    download_button_for(plot_series, f"Download {choice_label} data (CSV)", f"{code.lower()}.csv")

    st.divider()

    st.subheader("Channel Comparison: P2P vs. ATM Transaction Volume")
    st.caption("Visualization 3 of this dashboard -- the transaction-channel crossover documented "
               "in Task 2's EDA.")
    p2p = indicator_series(obs, "USG_P2P_COUNT")
    atm = indicator_series(obs, "USG_ATM_COUNT")

    fig2 = go.Figure()
    fig2.add_bar(x=[d.strftime("%Y-%m") for d in p2p["observation_date"]],
                 y=p2p["value_numeric"] / 1e6, name="P2P transactions (millions)", marker_color=ACCENT)
    fig2.add_bar(x=[d.strftime("%Y-%m") for d in atm["observation_date"]],
                 y=atm["value_numeric"] / 1e6, name="ATM transactions (millions)", marker_color=ACCENT2)
    fig2.update_layout(barmode="group", yaxis_title="Transactions (millions)", height=380, margin=dict(t=10, b=10))
    st.plotly_chart(fig2, width='stretch')
    crossover = indicator_series(obs, "USG_CROSSOVER").iloc[-1]
    st.caption(f"Latest P2P/ATM crossover ratio: **{crossover['value_numeric']:.2f}** "
               f"(as of {crossover['observation_date'].date()}) -- P2P digital transfers have overtaken "
               "ATM withdrawals in transaction volume.")


# ----------------------------------------------------------------------
# Page: Forecasts
# ----------------------------------------------------------------------

def page_forecasts():
    st.title("Forecasts (2025-2027)")
    st.caption("Access and Usage forecasts. See Task 4 notebook for full methodology.")

    access = get_access_forecast()
    usage = get_usage_forecast()

    st.subheader("Access: Account Ownership Rate")
    st.caption("Visualization 4 of this dashboard -- choose a trend model to compare.")
    model_choice = st.radio("Trend model", ["Log trend (recommended)", "Linear trend"], horizontal=True)
    trend = access["log"] if model_choice.startswith("Log") else access["linear"]

    extended_dates = pd.date_range(access["dates"][0], pd.Timestamp("2027-12-31"), freq="MS")
    curve = trend.predict(list(extended_dates))

    fig = go.Figure()
    fig.add_scatter(x=access["dates"], y=access["values"], mode="markers", marker=dict(size=12, color="black"),
                     name="Actual (Findex)")
    fig.add_scatter(x=extended_dates, y=curve["point"], mode="lines", line=dict(color=ACCENT, width=2.5),
                     name=f"{model_choice} forecast")
    if not curve["ci_lower"].isna().all():
        fig.add_scatter(x=list(extended_dates) + list(extended_dates[::-1]),
                         y=list(curve["ci_upper"]) + list(curve["ci_lower"][::-1]),
                         fill="toself", fillcolor="rgba(31,78,90,0.12)", line=dict(color="rgba(0,0,0,0)"),
                         name="95% prediction interval", showlegend=True)
    fig.add_hline(y=70, line_dash="dot", line_color=GOLD, annotation_text="NFIS-II 2025 target (70%)")
    fig.update_layout(yaxis_title="% of adults with an account", height=440, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width='stretch')

    if model_choice.startswith("Linear"):
        st.warning("The linear trend extrapolates Access's early, steepest growth period forward "
                   "indefinitely, ignoring the well-documented deceleration (+4.33 \u2192 +2.75 \u2192 "
                   "+1.00 pp/year across the three real survey intervals). The log trend is used as "
                   "this project's baseline for exactly this reason.")

    st.divider()

    st.subheader("Which Events Matter for This Forecast?")
    effects = access["effects"]
    rows = []
    for e in effects:
        incr_2027 = incremental_event_effect([e], access["last_obs"], pd.Timestamp("2027-12-31"))
        rows.append({"Event": e.event_name, "Event date": e.event_date.date(),
                     "Full estimated effect (pp)": e.full_effect,
                     "Already realized by last observation?": "Yes" if abs(incr_2027) < 0.1 else "No -- still materializing",
                     "Incremental effect added by 2027": round(incr_2027, 1)})
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
    st.caption("Telebirr's effect is already fully baked into the historical trend line above (its ramp "
               "completed by mid-2022). The Fayda Digital ID rollout is the one event whose effect is "
               "still materializing -- landing almost entirely in 2026 -- making it the single largest "
               "lever in this forecast.")

    st.divider()

    st.subheader("Key Projected Milestones")
    m1, m2, m3 = st.columns(3)
    base_2025 = access["scenarios"][access["scenarios"]["date"] == FORECAST_DATES[0]]["with_events_base_scenario"].iloc[0]
    base_2027 = access["scenarios"][access["scenarios"]["date"] == FORECAST_DATES[2]]["with_events_base_scenario"].iloc[0]
    with m1:
        st.metric("Access, base case, 2025", f"{base_2025:.0f}%", help="Log trend + incremental event effects")
    with m2:
        st.metric("Access, base case, 2027", f"{base_2027:.0f}%")
    with m3:
        gap = 70 - base_2025
        st.metric("Gap to NFIS-II 2025 target", f"{gap:.0f}pp short", delta_color="inverse")

    download_button_for(access["scenarios"], "Download Access scenario forecast (CSV)", "access_forecast.csv")


# ----------------------------------------------------------------------
# Page: Inclusion Projections
# ----------------------------------------------------------------------

def page_inclusion_projections():
    st.title("Financial Inclusion Projections")
    st.caption("Scenario-based projections and answers to the consortium's key questions.")

    access = get_access_forecast()
    usage = get_usage_forecast()

    st.subheader("Progress Toward Financial Inclusion Targets")
    st.caption("Visualization 5 of this dashboard -- select a scenario below.")
    scenario_choice = st.selectbox("Scenario", ["Pessimistic", "Base", "Optimistic"], index=1)
    col_map = {"Pessimistic": "pessimistic", "Base": "with_events_base_scenario", "Optimistic": "optimistic"}
    col = col_map[scenario_choice]

    fig = go.Figure()
    fig.add_scatter(x=access["dates"], y=access["values"], mode="markers", marker=dict(size=12, color="black"),
                     name="Actual (Findex)")
    fig.add_scatter(x=access["scenarios"]["date"], y=access["scenarios"][col], mode="lines+markers",
                     line=dict(color=ACCENT, width=2.5), marker=dict(size=9), name=f"{scenario_choice} scenario")
    fig.add_hline(y=70, line_dash="dot", line_color=GOLD,
                  annotation_text="NFIS-II 2025 target: 70%")
    fig.add_hline(y=60, line_dash="dash", line_color=ACCENT2,
                  annotation_text="60% milestone")
    fig.update_layout(yaxis_title="% of adults with an account", height=440, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width='stretch')
    st.caption("Note: this project's own tracked official target (NFIS-II) is 70% by end-2025, shown "
               "as the gold dotted line. A separate 60% reference line is also shown, since Task 5's "
               "brief specifically asks for progress toward a 60% milestone -- both are displayed "
               "explicitly labeled so there is no ambiguity about which is the official target.")

    year_60 = None
    for _, row in access["scenarios"].iterrows():
        if row[col] >= 60:
            year_60 = row["date"].year
            break
    if year_60:
        st.success(f"Under the **{scenario_choice.lower()}** scenario, the 60% milestone is projected "
                   f"to be reached by **{year_60}**.")
    else:
        st.warning(f"Under the **{scenario_choice.lower()}** scenario, the 60% milestone is **not** "
                   "projected to be reached by 2027.")

    st.divider()

    st.subheader("Consortium Key Questions")
    with st.expander("What does the model predict for Access and Usage through 2027?", expanded=True):
        st.markdown(
            "**Access** (base scenario): ~50% in 2025, rising to ~61% by 2026-2027 once the Fayda "
            "Digital ID rollout's effect fully materializes. **Usage**: essentially flat, ~21-22% "
            "through 2027 under every scenario -- mirroring the gap between rapid mobile money "
            "registration growth and comparatively flat genuine usage documented throughout this project."
        )
    with st.expander("What events have the largest potential impact?"):
        st.markdown(
            "The **Fayda Digital ID rollout** is the single largest lever for Access -- its long lag "
            "means its effect is almost entirely still ahead of us, landing in 2026. This estimate "
            "rests on cross-country literature (comparable to India's Aadhaar/Jan Dhan experience), "
            "not yet on Ethiopia-specific confirmation. For Usage, no cataloged event has a *direct*, "
            "quantified link to the indicator at all -- a real gap in the current impact model."
        )
    with st.expander("What are the key uncertainties?"):
        st.markdown(
            "- Whether the Fayda ID effect materializes as estimated (unconfirmed for Ethiopia)\n"
            "- Whether the deceleration pattern continues smoothly or a new shock breaks the trend\n"
            "- Whether Usage's flat trajectory is structural or an artifact of only 2 data points\n"
            "- Whether registration-based indicators continue to diverge from genuine survey-measured "
            "usage at the same rate, or whether that gap starts to close as the market matures"
        )
    with st.expander("Is Ethiopia on track for its NFIS-II 70% by 2025 target?"):
        st.markdown(
            f"On current evidence, **most likely not**. The base-case forecast for 2025 is "
            f"**{access['scenarios'][access['scenarios']['date']==FORECAST_DATES[0]]['with_events_base_scenario'].iloc[0]:.0f}%**, "
            "roughly 20 percentage points short of the target. Even the optimistic scenario falls "
            "short in 2025 and only clears 70% by 2027 under a favorable combination of assumptions."
        )

    download_button_for(access["scenarios"], "Download full Access scenario table (CSV)", "inclusion_projections.csv")


# ----------------------------------------------------------------------
# Page: Model Explainability (SHAP)
# ----------------------------------------------------------------------

def page_explainability():
    from explainability import plot_global_importance, plot_prediction_waterfall, plot_feature_over_time

    st.title("Model Explainability")
    st.caption(
        "SHAP explanations for the ACC_MM_ACCOUNT event-impact model. This model is a "
        "transparent, deterministic formula (see the Forecasts page), not a black-box ML "
        "model -- so what's explained here is a small surrogate model trained to reproduce "
        "its outputs from named, meaningful features (one per contributing event). SHAP is "
        "applied to that surrogate. See the README's Model Explainability section for the "
        "full rationale."
    )

    result = get_explainability_result()

    st.subheader("Which features matter most globally?")
    st.plotly_chart(plot_global_importance(result), width='stretch')
    top = result.global_importance().iloc[0]
    st.caption(f"**{top['feature'].replace('_', ' ').title()}** has the largest average impact "
               f"across the full 2021-2027 window.")

    st.divider()

    st.subheader("Why did the model make this specific prediction?")
    month_options = result.feature_df["date"].dt.strftime("%B %Y").tolist()
    selected = st.select_slider("Choose a month to explain", options=month_options,
                                 value=month_options[-1])
    row_index = month_options.index(selected)
    st.plotly_chart(plot_prediction_waterfall(result, row_index=row_index), width='stretch')

    st.divider()

    st.subheader("Are there any concerning patterns?")
    st.plotly_chart(plot_feature_over_time(result), width='stretch')
    for finding in result.concerning_patterns():
        st.info(finding)

    with st.expander("Surrogate model fidelity (technical detail)"):
        from explainability import surrogate_r_squared
        r2 = surrogate_r_squared(result.model, result.feature_df, result.feature_cols)
        st.write(f"R\u00b2 of the surrogate against the real model's own outputs: **{r2:.6f}**")
        st.caption("Expected to be extremely close to 1.0 -- the surrogate is approximating a "
                   "known deterministic function, not learning from noisy real-world data. A "
                   "meaningfully lower value here would indicate a feature-engineering bug, not "
                   "genuine unlearnable noise.")


# ----------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------

PAGES = {
    "Overview": page_overview,
    "Trends": page_trends,
    "Forecasts": page_forecasts,
    "Inclusion Projections": page_inclusion_projections,
    "Model Explainability": page_explainability,
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", list(PAGES.keys()))
st.sidebar.divider()

# ----------------------------------------------------------------------
# Data refresh status (Task 4) -- reads the manifest refresh_data.py
# writes; never rebuilds automatically on page load, since that would make
# every dashboard visit pay the full pipeline-rebuild cost. The button
# below triggers an explicit, on-demand refresh instead.
# ----------------------------------------------------------------------
st.sidebar.subheader("Data status")
manifest = refresh_data.load_last_manifest()
if manifest is None:
    st.sidebar.caption("No refresh has been run yet in this environment.")
else:
    refreshed_at = pd.Timestamp(manifest["refreshed_at"])
    if manifest["validation_passed"]:
        st.sidebar.success(f"Refreshed {refreshed_at.strftime('%Y-%m-%d %H:%M UTC')} -- "
                            f"{manifest['record_counts']['total']} records, validation passed")
    else:
        st.sidebar.error(f"Refreshed {refreshed_at.strftime('%Y-%m-%d %H:%M UTC')} -- "
                          f"validation FAILED ({len(manifest['validation_errors'])} error(s))")
    if manifest["validation_warnings"]:
        with st.sidebar.expander(f"{len(manifest['validation_warnings'])} warning(s)"):
            for w in manifest["validation_warnings"]:
                st.caption(w)

if st.sidebar.button("Refresh data now", help="Re-runs the full build pipeline and re-validates "
                                                "the output (build_enrichment.py through "
                                                "build_quality_trust_enrichment.py)."):
    with st.spinner("Rebuilding and validating data/processed/ outputs..."):
        try:
            new_manifest = refresh_data.refresh(quiet=True)
        except Exception as e:  # noqa: BLE001 -- surface any build-stage failure to the user directly
            st.sidebar.error(f"Refresh failed: {e}")
        else:
            get_data.clear()
            get_access_forecast.clear()
            get_usage_forecast.clear()
            if new_manifest["validation_passed"]:
                st.sidebar.success("Refresh complete -- validation passed.")
            else:
                st.sidebar.error(f"Refresh complete, but validation found "
                                  f"{len(new_manifest['validation_errors'])} error(s) -- see below.")
            st.rerun()

st.sidebar.divider()
st.sidebar.caption(
    "Ethiopia Financial Inclusion Forecast\n\n"
    "Data: enriched Findex + operator/regulator observations, 1987-2026.\n\n"
    "Forecasts: trend regression + event-augmented modeling (Tasks 1-4)."
)

PAGES[selection]()
