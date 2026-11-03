"""
01_clean_data.py
Reads the two raw Kaggle files (semicolon-separated), standardises them, runs data-quality
checks, and writes data/processed/campaign_daily.csv.

Source: Kaggle "amirmotefaker/ab-testing-dataset" (control_group.csv, test_group.csv)
Grain : one row per campaign per day (1-30 Aug 2019). These are DAILY TOTALS, not user-level rows.
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

RENAME = {"Campaign Name": "campaign_name", "Date": "date", "Spend [USD]": "spend",
          "# of Impressions": "impressions", "Reach": "reach", "# of Website Clicks": "clicks",
          "# of Searches": "searches", "# of View Content": "view_content",
          "# of Add to Cart": "add_to_cart", "# of Purchase": "purchases"}
STAGES = ["impressions", "clicks", "searches", "view_content", "add_to_cart", "purchases"]

frames = []
for grp, fname in [("control", "control_group.csv"), ("test", "test_group.csv")]:
    d = pd.read_csv(RAW / fname, sep=";").rename(columns=RENAME)
    d.insert(0, "campaign_group", grp)
    frames.append(d)
df = pd.concat(frames, ignore_index=True)

df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
df["weekday"] = df["date"].dt.day_name()
df["is_weekend"] = df["date"].dt.dayofweek >= 5
metric_cols = [c for c in RENAME.values() if c not in ("campaign_name", "date", "spend")]
df["has_missing_metrics"] = df[metric_cols].isna().any(axis=1)

# ---- data-quality checks
dq = {"rows": df.groupby("campaign_group").size().to_dict(),
      "date_range": [str(df.date.min().date()), str(df.date.max().date())],
      "days_per_group_match": bool(df[df.campaign_group=="control"].date.tolist() == df[df.campaign_group=="test"].date.tolist()),
      "missing_days": df.loc[df.has_missing_metrics, ["campaign_group", "date"]].astype(str).to_dict("records"),
      "duplicate_group_dates": int(df.duplicated(["campaign_group", "date"]).sum())}
viol = []
for i in range(len(STAGES) - 1):
    a, b = STAGES[i], STAGES[i + 1]
    bad = df[df[b] > df[a]]
    if len(bad):
        viol.append({"earlier": a, "later": b, "days": int(len(bad)),
                     "groups": bad.campaign_group.value_counts().to_dict()})
dq["stage_order_violations"] = viol
dq["reach_gt_impressions_days"] = int((df.reach > df.impressions).sum())
dq["note"] = ("Later stages can exceed earlier ones on a given day (e.g. purchases > add-to-cart) because the "
              "data are daily totals, not a per-user funnel. Stage rates are therefore computed on pooled totals.")

df.to_csv(OUT / "campaign_daily.csv", index=False)
(OUT / "data_quality.json").write_text(json.dumps(dq, indent=2, default=str))
print(json.dumps(dq, indent=2, default=str))
print("\nSaved", OUT / "campaign_daily.csv", df.shape)
