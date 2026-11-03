# Data Dictionary

**Source:** Kaggle, `amirmotefaker/ab-testing-dataset` (`control_group.csv`, `test_group.csv`). Real campaign data, 1-30 Aug 2019.
Files are semicolon-separated, dates are `d.mm.yyyy`.

**Grain:** one row per campaign per day (daily totals). There are **no user-level rows**, no revenue and no audience attributes.

| Raw column | Clean name | Meaning |
|---|---|---|
| Campaign Name | campaign_name | "Control Campaign" or "Test Campaign" |
| Date | date | Day of the campaign |
| Spend [USD] | spend | Amount spent that day |
| # of Impressions | impressions | Ad views |
| Reach | reach | Unique people reached |
| # of Website Clicks | clicks | Clicks to the website |
| # of Searches | searches | Searches performed on the site |
| # of View Content | view_content | Product pages viewed |
| # of Add to Cart | add_to_cart | Items added to cart |
| # of Purchase | purchases | Purchases |

Added by cleaning: `campaign_group` (control/test), `weekday`, `is_weekend`, `has_missing_metrics`.

## Data quality findings (see `data/processed/data_quality.json`)
- 30 rows per campaign, same 30 dates in both, no duplicate rows.
- **One empty day:** control, 5 Aug 2019 (spend present, all other metrics blank). Dropped in the primary analysis; filling it by interpolation changes no conclusion.
- **Funnel stages are not strictly nested on a given day**: add-to-cart exceeds view-content on 8 days, searches exceed clicks on 1 day, purchases exceed add-to-cart on 1 day. These are daily totals, not a per-user journey, so stage rates are computed on pooled totals.
- Reach never exceeds impressions.

## Limitations
- Only 30 days per campaign, so only large differences can be detected.
- No revenue, so ROI cannot be computed. We report cost per click, add-to-cart and purchase instead.
- The two campaigns did not receive the same spend or impressions, so volume differences are part of the comparison.
- We cannot verify how users were assigned to the campaigns, so results describe the campaigns, not a randomised user experiment.
