# Campaign A/B: Funnel, Cost-Efficiency & Statistical Testing of a Marketing Campaign

An end-to-end analysis of a **real Kaggle dataset**: two online-retail ad campaigns (control vs test) run for 30 days.
SQL funnel analysis, permutation tests and bootstrap intervals on daily data, and a Power BI / Tableau dashboard.

> **Question:** Did the test campaign turn ad spend into purchases more efficiently than the control campaign?
> **Answer:** No clear winner. Purchases were identical (about 522 per day each), the test spent about 11% more, and cost per purchase ($4.92 vs $4.41) is statistically inconclusive (95% CI -10% to +35%). The test shifted the funnel (+66% click-through, -29% add-to-cart, +47% cart-to-purchase) without improving the outcome.

**Data:** Kaggle `amirmotefaker/ab-testing-dataset` (https://www.kaggle.com/datasets/amirmotefaker/ab-testing-dataset). Daily totals, 1-30 Aug 2019, 30 rows per campaign.

## Skills demonstrated
SQL (CTEs, views, UNION ALL unpivot, LAG / FIRST_VALUE, moving averages, SUM OVER, ROW_NUMBER, NTILE, self-joins) | Python (pandas, SciPy, statsmodels) |
Permutation tests and bootstrap CIs | Multiple-testing correction (Benjamini-Hochberg) | Data-quality auditing | Sensitivity analysis | Power / MDE |
Funnel and unit-economics analysis | Power BI / Tableau dashboarding

## Why the statistics are not a standard A/B test
The data are **daily totals, not users**, so a normal z-test would overstate certainty (day-to-day variation is hundreds of times the binomial noise).
The unit of analysis is the day, using permutation tests and bootstrap intervals that resample days. See `docs/REPORT.md` section 1.

## Structure
```
campaign_ab/
├── data/raw/                 control_group.csv, test_group.csv (original Kaggle files, untouched)
├── data/processed/           campaign_daily.csv, data_quality.json
├── sql/campaign_queries.sql  12 documented queries
├── src/                      01_clean_data.py, 02_load_and_run_sql.py, 03_ab_analysis.py
├── charts/                   5 PNGs
├── dashboard_data/           CSVs for Power BI / Tableau (+ sql_results/)
├── docs/                     REPORT.md, DATA_DICTIONARY.md, DASHBOARD_GUIDE.md, INTERVIEW_QA.md
├── results.json              all headline numbers
└── run_all.sh
```

## Run it
```bash
pip install -r requirements.txt
bash run_all.sh      # or run the three scripts in src/ in order
```

## Key results
| Metric | Control | Test | Verdict |
|---|---|---|---|
| Mean daily purchases | 522.8 | 521.2 | no difference |
| Mean daily spend | $2,304 | $2,563 | test +11% |
| Cost per purchase | $4.41 | $4.92 | inconclusive (CI -10% to +35%) |
| Click-through rate | 4.86% | 8.09% | test higher |
| Add-to-cart rate | 66.9% | 47.4% | control higher |
| Purchases / add-to-cart | 40.2% | 59.1% | test higher |

## Limitations
About 30 days per campaign, no revenue (so no ROI), unknown audience assignment, one empty control day. Details in `docs/REPORT.md`.

## Resume bullets
- Analysed a real 30-day paid-marketing A/B test (control vs test campaigns) end to end: data-quality audit, SQL funnel analysis, and statistical testing; found equal purchase volume but about 11% higher spend in the test campaign.
- Recognised that daily-total data breaks standard z-tests (dispersion up to about 3,700x binomial noise) and used permutation tests, day-level bootstrap CIs and Benjamini-Hochberg correction across 11 metrics.
- Diagnosed a shifted funnel (+66% CTR, -29% add-to-cart, +47% cart-to-purchase) and a +63% CPM gap, and recommended an equal-budget, revenue-tracked follow-up test.
- Built a 3-page Power BI / Tableau dashboard and a decision report with 6 recommendations.
