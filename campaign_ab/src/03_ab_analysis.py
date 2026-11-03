"""
03_ab_analysis.py
Statistical comparison of the CONTROL vs TEST marketing campaigns (1-30 Aug 2019, daily totals).

Design notes (read before interpreting):
  * Unit of analysis = DAY (n = 30 per arm, 29 for control after dropping one empty day).
    Impressions/clicks/purchases are counts summed over thousands of users, but we do not see users,
    so ordinary user-level z-tests would badly overstate certainty (daily results vary far more than
    pure binomial noise). We therefore resample / permute DAYS.
  * Rates are "ratio of sums" (e.g. total purchases / total clicks) so big days count more.
  * Tests : two-sided permutation test (10,000 shuffles of campaign labels across days).
  * CIs   : 95% bootstrap interval (5,000 resamples of days within each campaign).
  * Multiple metrics -> Benjamini-Hochberg correction across the whole metric family.
  * Spend is NOT equal between campaigns (test spent more per day), so cost-efficiency metrics matter.
  * No revenue column exists -> true ROI cannot be computed; we report cost per click / add-to-cart / purchase.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import TTestIndPower

ROOT = Path(__file__).resolve().parent.parent
CH, DB = ROOT / "charts", ROOT / "dashboard_data"
CH.mkdir(exist_ok=True); DB.mkdir(exist_ok=True)
rng = np.random.default_rng(11)
C_CTRL, C_TEST = "#8d99ae", "#d97706"
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "axes.titleweight": "bold"})
B_BOOT, B_PERM = 5000, 10000
R = {}

df = pd.read_csv(ROOT / "data" / "processed" / "campaign_daily.csv", parse_dates=["date"])

# ------------------------------------------------------------------ metric definitions
# name: (numerator, denominator, scale, better)   better = "higher" or "lower"
METRICS = {
    "Click-through rate (clicks / impressions)":      ("clicks", "impressions", 100, "higher"),
    "Search rate (searches / clicks)":                ("searches", "clicks", 100, "higher"),
    "View-content rate (view content / searches)":    ("view_content", "searches", 100, "higher"),
    "Add-to-cart rate (add to cart / view content)":  ("add_to_cart", "view_content", 100, "higher"),
    "Purchase rate (purchases / add to cart)":        ("purchases", "add_to_cart", 100, "higher"),
    "Click-to-purchase (purchases / clicks)":         ("purchases", "clicks", 100, "higher"),
    "Impression-to-purchase (purchases / impressions)": ("purchases", "impressions", 100, "higher"),
    "Cost per 1,000 impressions (CPM, USD)":          ("spend", "impressions", 1000, "lower"),
    "Cost per click (USD)":                           ("spend", "clicks", 1, "lower"),
    "Cost per add-to-cart (USD)":                     ("spend", "add_to_cart", 1, "lower"),
    "Cost per purchase (USD)":                        ("spend", "purchases", 1, "lower"),
}

def ratio(d, num, den, scale):
    return scale * d[num].sum() / d[den].sum()

def analyse(frame, label):
    """Run every metric on `frame` (rows with complete data). Returns a DataFrame."""
    c = frame[frame.campaign_group == "control"].reset_index(drop=True)
    t = frame[frame.campaign_group == "test"].reset_index(drop=True)
    allrows = pd.concat([c, t], ignore_index=True)
    lab = np.r_[np.zeros(len(c), bool), np.ones(len(t), bool)]
    rows = []
    for name, (num, den, sc, better) in METRICS.items():
        pc, pt = ratio(c, num, den, sc), ratio(t, num, den, sc)
        obs = pt - pc
        # bootstrap CI for the difference (resample days within each arm)
        ci_idx_c = rng.integers(0, len(c), (B_BOOT, len(c)))
        ci_idx_t = rng.integers(0, len(t), (B_BOOT, len(t)))
        cn, cd = c[num].values[ci_idx_c].sum(1), c[den].values[ci_idx_c].sum(1)
        tn, td = t[num].values[ci_idx_t].sum(1), t[den].values[ci_idx_t].sum(1)
        diffs = sc * tn / td - sc * cn / cd
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        # permutation test (shuffle campaign labels across days)
        n_all, d_all = allrows[num].values, allrows[den].values
        cnt = 0
        for _ in range(B_PERM):
            perm = rng.permutation(lab)
            diff = sc * n_all[perm].sum() / d_all[perm].sum() - sc * n_all[~perm].sum() / d_all[~perm].sum()
            cnt += abs(diff) >= abs(obs) - 1e-12
        p = (cnt + 1) / (B_PERM + 1)
        # naive pooled 2x2 chi-square for comparison (only valid for count/count stage rates)
        naive_p = np.nan
        if sc == 100 and num != "clicks" or (num == "clicks" and den == "impressions"):
            a1, b1 = t[num].sum(), t[den].sum() - t[num].sum()
            a0, b0 = c[num].sum(), c[den].sum() - c[num].sum()
            if min(a1, b1, a0, b0) > 0:
                naive_p = stats.chi2_contingency([[a1, b1], [a0, b0]], correction=False)[1]
        rows.append({"metric": name, "better_if": better, "control": pc, "test": pt, "abs_diff": obs,
                     "rel_diff_pct": 100 * obs / pc, "ci_low": lo, "ci_high": hi,
                     "rel_ci_low_pct": 100 * lo / pc, "rel_ci_high_pct": 100 * hi / pc,
                     "p_permutation": p, "p_naive_chi2": naive_p})
    out = pd.DataFrame(rows)
    out["p_adj_BH"] = multipletests(out["p_permutation"], method="fdr_bh")[1]
    out["significant"] = out["p_adj_BH"] < 0.05
    out["winner"] = np.where(~out["significant"], "no clear difference",
                      np.where((out["abs_diff"] > 0) == (out["better_if"] == "higher"), "test", "control"))
    out.insert(0, "analysis", label)
    return out

# ------------------------------------------------------------------ 1. primary: complete-case
complete = df[~df.has_missing_metrics].copy()
res = analyse(complete, "complete-case (primary)")

# ------------------------------------------------------------------ 2. sensitivity: fill the one empty control day
filled = df.copy()
num_cols = ["impressions", "reach", "clicks", "searches", "view_content", "add_to_cart", "purchases"]
m = filled.campaign_group == "control"
filled.loc[m, num_cols] = filled.loc[m].sort_values("date")[num_cols].interpolate().values
res_s = analyse(filled, "sensitivity: empty day interpolated")
sens = res.merge(res_s[["metric", "rel_diff_pct", "p_adj_BH", "winner"]], on="metric", suffixes=("", "_interp"))
sens["same_conclusion"] = sens["winner"] == sens["winner_interp"]
R["sensitivity_same_conclusion_for_all_metrics"] = bool(sens["same_conclusion"].all())

# ------------------------------------------------------------------ 3. volume metrics (mean per day)
vol = []
for col in ["spend", "impressions", "reach", "clicks", "add_to_cart", "purchases"]:
    a = complete.loc[complete.campaign_group == "control", col]
    b = complete.loc[complete.campaign_group == "test", col]
    u, p = stats.mannwhitneyu(b, a)
    vol.append({"metric": f"Mean daily {col}", "control": a.mean(), "test": b.mean(),
                "rel_diff_pct": 100 * (b.mean() - a.mean()) / a.mean(), "p_mannwhitney": p})
vol = pd.DataFrame(vol)

# ------------------------------------------------------------------ 4. overdispersion (why naive z-tests mislead)
def dispersion(num, den):
    out = {}
    for g in ["control", "test"]:
        d = complete[complete.campaign_group == g]
        p_hat = d[num].sum() / d[den].sum()
        observed = np.var(d[num] / d[den], ddof=1)
        expected = np.mean(p_hat * (1 - p_hat) / d[den])
        out[g] = round(float(observed / expected), 1)
    return out
R["overdispersion_ratio_(observed_var/binomial_var)"] = {
    "click_through_rate": dispersion("clicks", "impressions"),
    "click_to_purchase": dispersion("purchases", "clicks")}

# ------------------------------------------------------------------ 5. power / minimum detectable effect
ctrl_c = complete[complete.campaign_group == "control"]
sd_p = complete.groupby("campaign_group")["purchases"].std().mean()
d_80 = TTestIndPower().solve_power(nobs1=29, ratio=30 / 29, alpha=0.05, power=0.8)
R["power"] = {"days_per_arm": [29, 30], "min_detectable_effect_daily_purchases_80pct_power":
              round(float(d_80 * sd_p), 1),
              "as_pct_of_control_mean": round(float(100 * d_80 * sd_p / ctrl_c["purchases"].mean()), 1),
              "note": "With ~30 days per arm only large differences (roughly 25%+ in mean daily purchases) can be detected reliably."}

# ------------------------------------------------------------------ 6. headline numbers
g = complete.groupby("campaign_group")[["spend", "impressions", "clicks", "searches", "view_content", "add_to_cart", "purchases"]].sum()
R["totals"] = g.round(0).to_dict("index")
R["data_quality"] = json.loads((ROOT / "data" / "processed" / "data_quality.json").read_text())

key = res.set_index("metric")
R["headline"] = {
    "cost_per_purchase": {"control": round(key.loc["Cost per purchase (USD)", "control"], 2),
                          "test": round(key.loc["Cost per purchase (USD)", "test"], 2),
                          "rel_diff_pct": round(key.loc["Cost per purchase (USD)", "rel_diff_pct"], 1),
                          "ci95_pct": [round(key.loc["Cost per purchase (USD)", "rel_ci_low_pct"], 1),
                                       round(key.loc["Cost per purchase (USD)", "rel_ci_high_pct"], 1)],
                          "p_adj": round(key.loc["Cost per purchase (USD)", "p_adj_BH"], 3)},
    "purchases_per_1k_usd": {"control": round(1000 * g.loc["control", "purchases"] / g.loc["control", "spend"], 1),
                             "test": round(1000 * g.loc["test", "purchases"] / g.loc["test", "spend"], 1)}}
R["significant_after_correction"] = res.loc[res.significant, ["metric", "rel_diff_pct", "winner"]].round(1).to_dict("records")
R["not_significant"] = res.loc[~res.significant, "metric"].tolist()

# ------------------------------------------------------------------ CHARTS
res_plot = res.copy()
short = {"Click-through rate (clicks / impressions)": "Click-through rate", "Search rate (searches / clicks)": "Search rate",
         "View-content rate (view content / searches)": "View-content rate",
         "Add-to-cart rate (add to cart / view content)": "Add-to-cart rate",
         "Purchase rate (purchases / add to cart)": "Purchase rate (per cart)",
         "Click-to-purchase (purchases / clicks)": "Click-to-purchase",
         "Impression-to-purchase (purchases / impressions)": "Impression-to-purchase",
         "Cost per 1,000 impressions (CPM, USD)": "CPM", "Cost per click (USD)": "Cost per click",
         "Cost per add-to-cart (USD)": "Cost per add-to-cart", "Cost per purchase (USD)": "Cost per purchase"}
res_plot["label"] = res_plot["metric"].map(short)

# 1 funnel: stage-to-stage conversion, pooled
stages = [("Click-through", "clicks", "impressions"), ("Search", "searches", "clicks"),
          ("View content", "view_content", "searches"), ("Add to cart", "add_to_cart", "view_content"),
          ("Purchase", "purchases", "add_to_cart")]
fr = pd.DataFrame([{"step": n, **{grp: 100 * g.loc[grp, a] / g.loc[grp, b] for grp in ["control", "test"]}}
                   for n, a, b in stages])
fig, ax = plt.subplots(figsize=(8.5, 4.2)); xs = np.arange(len(fr)); w = 0.38
b1 = ax.bar(xs - w / 2, fr.control, w, color=C_CTRL, label="Control")
b2 = ax.bar(xs + w / 2, fr.test, w, color=C_TEST, label="Test")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f"{b.get_height():.1f}%", ha="center", fontsize=8)
ax.set_xticks(xs); ax.set_xticklabels(fr.step); ax.set_ylabel("% of previous stage")
ax.set_title("Stage-to-stage conversion (pooled totals)"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(CH / "01_stage_conversion.png"); plt.close(fig)
fr.to_csv(DB / "stage_conversion.csv", index=False)

# 2 daily purchases + 7-day moving average
fig, ax = plt.subplots(figsize=(9, 4))
for grp, col in [("control", C_CTRL), ("test", C_TEST)]:
    d = complete[complete.campaign_group == grp].sort_values("date")
    ax.plot(d.date, d.purchases, color=col, alpha=0.35, lw=1)
    ax.plot(d.date, d.purchases.rolling(7, min_periods=3).mean(), color=col, lw=2.4, label=f"{grp} (7-day avg)")
ax.set_ylabel("Purchases per day"); ax.set_title("Daily purchases: both campaigns are nearly identical on average")
ax.legend(frameon=False); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(CH / "02_daily_purchases.png"); plt.close(fig)

# 3 cost per purchase distribution
complete = complete.assign(cpa=complete.spend / complete.purchases)
fig, ax = plt.subplots(figsize=(5.6, 4.2))
data = [complete.loc[complete.campaign_group == k, "cpa"] for k in ["control", "test"]]
bp = ax.boxplot(data, widths=0.5, patch_artist=True, showfliers=False)
for patch, col in zip(bp["boxes"], [C_CTRL, C_TEST]):
    patch.set_facecolor(col); patch.set_alpha(0.7)
for i, d in enumerate(data, 1):
    ax.scatter(rng.normal(i, 0.05, len(d)), d, s=14, color="k", alpha=0.5, zorder=3)
ax.set_xticklabels(["Control", "Test"]); ax.set_ylabel("Cost per purchase per day (USD)")
ax.set_title("Cost per purchase by day")
fig.tight_layout(); fig.savefig(CH / "03_cost_per_purchase.png"); plt.close(fig)

# 4 forest plot of relative differences
rp = res_plot.sort_values("rel_diff_pct")
fig, ax = plt.subplots(figsize=(8.5, 5.4))
cols = np.where(rp.significant, C_TEST, "#9aa0a6")
ax.errorbar(rp.rel_diff_pct, range(len(rp)), xerr=[rp.rel_diff_pct - rp.rel_ci_low_pct, rp.rel_ci_high_pct - rp.rel_diff_pct],
            fmt="none", ecolor="#c4c4c4", capsize=3, zorder=1)
ax.scatter(rp.rel_diff_pct, range(len(rp)), c=cols, s=40, zorder=2)
ax.axvline(0, color="k", ls="--", lw=0.8)
ax.set_yticks(range(len(rp))); ax.set_yticklabels(rp.label)
ax.set_xlabel("Test vs control: relative difference % (95% bootstrap CI)")
ax.set_title("What changed in the test campaign?")
fig.text(0.5, 0.005, "Orange = significant after Benjamini-Hochberg correction", ha="center", fontsize=8, color="#555")
fig.tight_layout(); fig.savefig(CH / "04_metric_differences.png"); plt.close(fig)

# 5 spend vs purchases
fig, ax = plt.subplots(figsize=(5.8, 4.2))
for grp, col in [("control", C_CTRL), ("test", C_TEST)]:
    d = complete[complete.campaign_group == grp]
    ax.scatter(d.spend, d.purchases, color=col, alpha=0.8, label=grp)
ax.set_xlabel("Daily spend (USD)"); ax.set_ylabel("Daily purchases"); ax.legend(frameon=False)
ax.set_title("Spend vs purchases (each dot = one day)")
fig.tight_layout(); fig.savefig(CH / "05_spend_vs_purchases.png"); plt.close(fig)

# ------------------------------------------------------------------ EXPORTS (Power BI / Tableau)
res.round(5).to_csv(DB / "metric_results.csv", index=False)
sens.round(5).to_csv(DB / "sensitivity_results.csv", index=False)
vol.round(4).to_csv(DB / "daily_volume_results.csv", index=False)
daily = df.copy()
daily["cost_per_purchase"] = daily.spend / daily.purchases
daily["ctr_pct"] = 100 * daily.clicks / daily.impressions
daily["cost_per_click"] = daily.spend / daily.clicks
daily["cost_per_add_to_cart"] = daily.spend / daily.add_to_cart
daily.to_csv(DB / "campaign_daily_enriched.csv", index=False)
funnel = []
order = ["impressions", "clicks", "searches", "view_content", "add_to_cart", "purchases"]
for grp in ["control", "test"]:
    for i, s in enumerate(order, 1):
        funnel.append({"campaign_group": grp, "stage_order": i, "stage": s, "total": g.loc[grp, s]})
pd.DataFrame(funnel).to_csv(DB / "funnel_totals.csv", index=False)

(ROOT / "results.json").write_text(json.dumps(R, indent=2, default=float))
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(res[["metric", "control", "test", "rel_diff_pct", "rel_ci_low_pct", "rel_ci_high_pct", "p_permutation", "p_naive_chi2", "p_adj_BH", "winner"]].round(3).to_string(index=False))
print("\nVOLUME:\n", vol.round(3).to_string(index=False))
print("\nSENS same conclusion:", R["sensitivity_same_conclusion_for_all_metrics"])
print(json.dumps({k: R[k] for k in ["overdispersion_ratio_(observed_var/binomial_var)", "power", "headline", "significant_after_correction"]}, indent=2, default=float))
