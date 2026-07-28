"""
explainability.py

SHAP-based explainability for the ACC_MM_ACCOUNT event-impact forecast.

Honesty note on approach: this project's forecasting logic (impact_model.py
+ forecasting.py) is a transparent, deterministic formula -- a trend fit
plus named, ramped event effects -- not a black-box ML model with dozens of
opaque input features. SHAP is designed for the latter. Rather than force
SHAP onto something that doesn't need it, or skip the requirement, this
module builds a genuine SURROGATE model: a small gradient-boosted regressor
trained to reproduce the deterministic model's own monthly predictions from
named, meaningful features (one per contributing event, plus a time trend).
SHAP is then applied to that surrogate. This is a standard, legitimate
explainability technique (surrogate modeling) -- it gives a business
audience an accessible, visual answer to "which known drivers matter most"
and "why did the model predict this value for this month", without
pretending the underlying logic is more opaque than it actually is.
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from config import ExplainerConfig
from impact_model import EventEffect, months_between, ramp_fraction


def _feature_name(effect: EventEffect) -> str:
    """A short, dashboard-friendly feature name derived from an event's
    display name (e.g. "M-Pesa Ethiopia Launch" -> "mpesa_ethiopia_launch")."""
    return (
        effect.event_name.lower()
        .replace("(onps/10/2025)", "")
        .replace("-", " ")
        .replace("/", " ")
        .strip()
        .replace(" ", "_")
        .strip("_")
    )


def build_feature_matrix(effects: List[EventEffect], baseline_date: pd.Timestamp,
                          end_date: pd.Timestamp, indicator_code: str = None,
                          freq: str = "MS") -> Tuple[pd.DataFrame, List[str]]:
    """
    Build a monthly (date, feature..., target) DataFrame: one ramp-fraction
    feature per event (0-1, how much of that event's full effect has
    materialized by that month), and the target column ("predicted_value")
    computed via the REAL combine_effects() -- not a hand-rolled sum -- so
    that the surrogate explains the actual current model, including the
    Enhancement 2 shared-ceiling interaction term where applicable (e.g.
    ACC_MM_ACCOUNT's Telebirr/M-Pesa pair). Passing the wrong indicator_code,
    or omitting it, would silently explain the superseded additive-only
    model instead -- this is the one place that distinction matters most.

    Deliberately does NOT include a raw "years since baseline" trend
    feature: for indicators like ACC_MM_ACCOUNT, the combined prediction is
    a pure function of the named event ramp-fractions with no separate
    organic-growth term, so a bare time feature would be collinear with
    (and merely proxy for) the real causal features, distorting SHAP
    attribution rather than adding a genuine driver.
    """
    from impact_model import combine_effects

    dates = pd.date_range(baseline_date, end_date, freq=freq)
    feature_names = [_feature_name(e) for e in effects]

    rows = []
    for d in dates:
        row = {"date": d}
        for e, fname in zip(effects, feature_names):
            t = months_between(e.event_date, d)
            row[fname] = ramp_fraction(t - e.lag_months, e.ramp_months)
        row["predicted_value"] = combine_effects(effects, d, indicator_code=indicator_code)
        rows.append(row)

    return pd.DataFrame(rows), feature_names


def train_surrogate_model(feature_df: pd.DataFrame, feature_cols: List[str],
                           target_col: str = "predicted_value",
                           config: ExplainerConfig = ExplainerConfig()) -> GradientBoostingRegressor:
    """Fit a small gradient-boosted regressor to reproduce the deterministic
    model's own predictions from the named features. Expected to achieve a
    very high R^2, since it is approximating a known deterministic function,
    not learning from noisy real-world data -- a low R^2 here would signal a
    bug in the feature engineering, not genuine unlearnable noise."""
    X = feature_df[feature_cols].values
    y = feature_df[target_col].values
    model = GradientBoostingRegressor(
        n_estimators=config.n_estimators, max_depth=config.max_depth,
        random_state=config.random_state,
    )
    model.fit(X, y)
    return model


def surrogate_r_squared(model: GradientBoostingRegressor, feature_df: pd.DataFrame,
                         feature_cols: List[str], target_col: str = "predicted_value") -> float:
    """R^2 of the surrogate against the deterministic model's own outputs --
    a fidelity check, not a real-world accuracy metric."""
    X = feature_df[feature_cols].values
    y = feature_df[target_col].values
    return float(model.score(X, y))


@dataclass
class ExplainabilityResult:
    """Bundles everything the dashboard/report needs: the fitted surrogate,
    its SHAP values, the feature matrix, and derived summaries."""
    feature_df: pd.DataFrame
    feature_cols: List[str]
    model: GradientBoostingRegressor
    shap_values: np.ndarray
    base_value: float

    def global_importance(self) -> pd.DataFrame:
        """Mean absolute SHAP value per feature, sorted descending --
        answers 'which features matter most globally'."""
        mean_abs = np.abs(self.shap_values).mean(axis=0)
        out = pd.DataFrame({"feature": self.feature_cols, "mean_abs_shap": mean_abs})
        return out.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    def explain_row(self, row_index: int) -> pd.DataFrame:
        """Per-feature SHAP contribution for one specific month's prediction
        -- answers 'why did the model make this specific prediction'."""
        contributions = self.shap_values[row_index]
        out = pd.DataFrame({"feature": self.feature_cols, "shap_value": contributions})
        out["abs_shap"] = out["shap_value"].abs()
        return out.sort_values("abs_shap", ascending=False).drop(columns="abs_shap").reset_index(drop=True)

    def concerning_patterns(self) -> List[str]:
        """Rule-based, honestly-scoped checks for patterns worth a second
        look -- answers 'are there any concerning patterns'. Deliberately
        simple and auditable rather than another opaque model."""
        findings = []
        importance = self.global_importance()
        total = importance["mean_abs_shap"].sum()
        if total > 0:
            top_share = importance.iloc[0]["mean_abs_shap"] / total
            if top_share > 0.75:
                findings.append(
                    f"'{importance.iloc[0]['feature']}' alone accounts for "
                    f"{top_share:.0%} of total feature impact -- the forecast is "
                    f"heavily concentrated in a single driver, which is a "
                    f"concentration risk if that specific event's real-world "
                    f"effect turns out to be smaller than modeled."
                )
        for _, r in importance.iterrows():
            if r["mean_abs_shap"] == 0:
                findings.append(
                    f"'{r['feature']}' has zero impact across the entire "
                    f"forecast window -- check whether its lag/ramp window "
                    f"places it entirely before or after the window being explained."
                )
        if not findings:
            findings.append(
                "No concentration or zero-impact issues detected -- feature "
                "impact is distributed across multiple events rather than "
                "dominated by one."
            )
        return findings


def explain_indicator(effects: List[EventEffect], baseline_date: pd.Timestamp,
                       end_date: pd.Timestamp, indicator_code: str,
                       freq: str = "MS",
                       config: ExplainerConfig = ExplainerConfig()) -> ExplainabilityResult:
    """End-to-end: build features (using the real combine_effects for
    `indicator_code`, respecting any shared-ceiling interaction term),
    train the surrogate, compute SHAP values. `indicator_code` is required
    (not defaulted to None) specifically so this can't silently explain the
    wrong (plain-additive) combination for an indicator like ACC_MM_ACCOUNT
    that has a documented interaction-term exception."""
    import shap  # local import -- optional heavy dependency, only needed here

    feature_df, feature_cols = build_feature_matrix(effects, baseline_date, end_date,
                                                     indicator_code=indicator_code, freq=freq)
    model = train_surrogate_model(feature_df, feature_cols, config=config)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(feature_df[feature_cols].values)
    expected_value = explainer.expected_value
    base_value = float(np.ravel(expected_value)[0])

    return ExplainabilityResult(
        feature_df=feature_df, feature_cols=feature_cols, model=model,
        shap_values=shap_values, base_value=base_value,
    )


# ---------------------------------------------------------------------
# Visualization (plotly, so the same functions serve both the dashboard
# and static PNG export for reports -- see scripts/generate_shap_figures.py)
# ---------------------------------------------------------------------

def _display_name(feature: str) -> str:
    return feature.replace("_", " ").title()


def plot_global_importance(result: ExplainabilityResult):
    """Bar chart: which events matter most globally. Answers requirement 1
    of Task 2's Model Explainability section."""
    import plotly.graph_objects as go

    imp = result.global_importance().iloc[::-1]  # smallest-to-largest for a top-down horizontal bar
    fig = go.Figure(go.Bar(
        x=imp["mean_abs_shap"], y=[_display_name(f) for f in imp["feature"]],
        orientation="h", marker_color="#2E75B6",
    ))
    fig.update_layout(
        title="Which events matter most globally?",
        xaxis_title="Mean |SHAP value| (percentage points)",
        margin=dict(l=10, r=10, t=50, b=10), height=320,
    )
    return fig


def plot_prediction_waterfall(result: ExplainabilityResult, row_index: int = -1):
    """Waterfall chart: why the model predicted this specific value for one
    specific month. Answers requirement 2 of Task 2's Model Explainability
    section."""
    import plotly.graph_objects as go

    if row_index < 0:
        row_index = len(result.feature_df) + row_index
    row = result.explain_row(row_index)
    date_label = pd.Timestamp(result.feature_df.iloc[row_index]["date"]).strftime("%B %Y")
    actual = result.feature_df.iloc[row_index]["predicted_value"]

    labels = ["Base value"] + [_display_name(f) for f in row["feature"]] + ["Total prediction"]
    values = [result.base_value] + row["shap_value"].tolist() + [actual]
    measures = ["absolute"] + ["relative"] * len(row) + ["total"]

    fig = go.Figure(go.Waterfall(
        x=labels, y=values, measure=measures,
        increasing={"marker": {"color": "#2E9E5B"}},
        decreasing={"marker": {"color": "#C0392B"}},
        totals={"marker": {"color": "#2E75B6"}},
    ))
    fig.update_layout(
        title=f"Why did the model predict {actual:.1f} for {date_label}?",
        yaxis_title="Mobile Money Account Rate (pp contribution)",
        margin=dict(l=10, r=10, t=50, b=10), height=380, showlegend=False,
    )
    return fig


def plot_feature_over_time(result: ExplainabilityResult):
    """Line chart of every feature's SHAP contribution across the whole
    forecast window -- surfaces patterns like one driver's contribution
    plateauing (saturating) while another's is still rising. Answers
    requirement 3 of Task 2's Model Explainability section ('are there any
    concerning patterns')."""
    import plotly.graph_objects as go

    fig = go.Figure()
    for i, feature in enumerate(result.feature_cols):
        fig.add_trace(go.Scatter(
            x=result.feature_df["date"], y=result.shap_values[:, i],
            mode="lines", name=_display_name(feature),
        ))
    fig.update_layout(
        title="Feature contributions over time",
        yaxis_title="SHAP contribution (pp)", xaxis_title="Date",
        margin=dict(l=10, r=10, t=50, b=10), height=360,
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


# ---------------------------------------------------------------------
# Static (matplotlib) equivalents for PNG export in reports/blog posts --
# the plotly figures above render fine live in Streamlit (no browser
# needed there), but exporting a plotly figure to a static PNG requires a
# headless Chrome install via kaleido, which isn't always available in
# every environment. These matplotlib versions have no such dependency.
# ---------------------------------------------------------------------

def savefig_global_importance(result: ExplainabilityResult, path: str) -> None:
    import matplotlib.pyplot as plt

    imp = result.global_importance().iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.barh([_display_name(f) for f in imp["feature"]], imp["mean_abs_shap"], color="#2E75B6")
    ax.set_xlabel("Mean |SHAP value| (percentage points)")
    ax.set_title("Which events matter most globally?")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def savefig_prediction_waterfall(result: ExplainabilityResult, path: str, row_index: int = -1) -> None:
    import matplotlib.pyplot as plt

    if row_index < 0:
        row_index = len(result.feature_df) + row_index
    row = result.explain_row(row_index)
    date_label = pd.Timestamp(result.feature_df.iloc[row_index]["date"]).strftime("%B %Y")
    actual = result.feature_df.iloc[row_index]["predicted_value"]

    labels = ["Base value"] + [_display_name(f) for f in row["feature"]] + ["Total"]
    values = [result.base_value] + row["shap_value"].tolist() + [actual]
    running = np.cumsum([result.base_value] + row["shap_value"].tolist())
    bottoms = [0] + list(running[:-1])
    colors = ["#2E75B6"] + ["#2E9E5B" if v >= 0 else "#C0392B" for v in row["shap_value"]] + ["#2E75B6"]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels[:-1], values[:-1], bottom=bottoms, color=colors[:-1])
    ax.bar(labels[-1], actual, color=colors[-1])
    ax.set_ylabel("Mobile Money Account Rate (pp)")
    ax.set_title(f"Why did the model predict {actual:.1f} for {date_label}?")
    plt.xticks(rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def savefig_feature_over_time(result: ExplainabilityResult, path: str) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 3.6))
    for i, feature in enumerate(result.feature_cols):
        ax.plot(result.feature_df["date"], result.shap_values[:, i], label=_display_name(feature))
    ax.set_ylabel("SHAP contribution (pp)")
    ax.set_title("Feature contributions over time")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
