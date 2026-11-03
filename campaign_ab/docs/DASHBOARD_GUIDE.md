# Dashboard Guide (Power BI or Tableau)

Files in `dashboard_data/`:

| File | Use for |
|---|---|
| campaign_daily_enriched.csv | Daily line charts, slicers (one row per campaign per day, with cost per purchase, CTR, cost per click) |
| funnel_totals.csv | Funnel bars (`stage_order` sorts the stages) |
| stage_conversion.csv | Stage-to-stage conversion, control vs test |
| metric_results.csv | Results table: control, test, % difference, CI, corrected p-value, winner |
| daily_volume_results.csv | Mean daily spend, impressions, purchases |

Tip: the control campaign has one empty day (5 Aug). In the daily file filter `has_missing_metrics = False` on the visuals that use ratios.

## Suggested layout (3 pages)
**Page 1: Verdict.** KPI cards: purchases per day, spend per day, cost per purchase, click-through rate (control vs test). Text box: "No clear winner on cost per purchase; test spends ~11% more for the same purchases."
**Page 2: Funnel.** Clustered bars of stage-to-stage conversion (control vs test). A second bar chart of totals by stage.
**Page 3: Trend and evidence.** Line chart of daily purchases by campaign, line chart of daily cost per purchase, and the `metric_results` table with conditional formatting on `winner`.

## Power BI Desktop (Windows)
1. Home > Get data > Text/CSV. Load the five files.
2. In Transform data, set `date` to Date type, then Close & Apply.
3. Measures (on `campaign_daily_enriched`):
   - `Spend = SUM(campaign_daily_enriched[spend])`
   - `Purchases = SUM(campaign_daily_enriched[purchases])`
   - `Cost per Purchase = DIVIDE([Spend], CALCULATE([Purchases], campaign_daily_enriched[has_missing_metrics] = FALSE()))`
   - `CTR % = DIVIDE(SUM(campaign_daily_enriched[clicks]), SUM(campaign_daily_enriched[impressions]))`
4. Page 1: four Card visuals, each broken out by `campaign_group` (use the Multi-row card or a small clustered column).
5. Page 2: Clustered bar chart, Axis = `stage_conversion[step]`, Values = `control` and `test`.
6. Page 3: Line chart, Axis = `date`, Values = `Purchases`, Legend = `campaign_group`. Add a Table visual from `metric_results` with `metric`, `control`, `test`, `rel_diff_pct`, `p_adj_BH`, `winner`.
7. Add a slicer for `is_weekend` and `campaign_group`.
8. Export to PDF and add screenshots to `docs/screenshots/`.

## Tableau Public (Windows or Mac)
1. Connect > Text file > `campaign_daily_enriched.csv`. Add the other files as new data sources.
2. Convert `date` to Date. Drag `campaign_group` to Color throughout.
3. Funnel: use `funnel_totals`; Columns = `total`, Rows = `stage` (sort manually by `stage_order`), Color = `campaign_group`.
4. Trend: Columns = `date` (continuous), Rows = `purchases` (SUM), Color = `campaign_group`. Add a table calculation > Moving average (last 6 + current) for a 7-day average.
5. Results table: use `metric_results`; put `metric` on Rows and `control`, `test`, `rel_diff_pct`, `winner` as text.
6. Build a Dashboard with the three sheets and a text box with the verdict, then File > Save to Tableau Public.
