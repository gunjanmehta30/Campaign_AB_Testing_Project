-- =====================================================================
-- Campaign A/B SQL analysis (SQLite; works in PostgreSQL with small tweaks)
-- Table: campaign_daily(campaign_group, campaign_name, date, spend, impressions, reach,
--        clicks, searches, view_content, add_to_cart, purchases, weekday, is_weekend, has_missing_metrics)
-- Grain: one row per campaign per day (daily totals, NOT user-level)
-- =====================================================================

-- Q1. DATA QUALITY: rows and missing days per group
SELECT campaign_group,
       COUNT(*) AS days,
       SUM(has_missing_metrics) AS days_with_missing_metrics,
       MIN(date) AS first_day, MAX(date) AS last_day
FROM campaign_daily
GROUP BY campaign_group;

-- Q2. CLEAN VIEW: complete days only (used by the queries below)
DROP VIEW IF EXISTS complete_days;
CREATE VIEW complete_days AS
SELECT * FROM campaign_daily WHERE has_missing_metrics = 0;

-- Q3. HEADLINE KPIs BY GROUP (ratio of sums, not average of daily ratios)
SELECT campaign_group,
       COUNT(*)                                                    AS days,
       SUM(spend)                                                  AS spend,
       SUM(impressions)                                            AS impressions,
       SUM(clicks)                                                 AS clicks,
       SUM(add_to_cart)                                            AS add_to_cart,
       SUM(purchases)                                              AS purchases,
       ROUND(100.0 * SUM(clicks) / SUM(impressions), 2)            AS ctr_pct,
       ROUND(1.0 * SUM(spend) / SUM(clicks), 3)                    AS cost_per_click,
       ROUND(1000.0 * SUM(spend) / SUM(impressions), 2)            AS cpm,
       ROUND(1.0 * SUM(spend) / SUM(add_to_cart), 2)               AS cost_per_add_to_cart,
       ROUND(1.0 * SUM(spend) / SUM(purchases), 2)                 AS cost_per_purchase,
       ROUND(1000.0 * SUM(purchases) / SUM(spend), 1)              AS purchases_per_1k_usd
FROM complete_days
GROUP BY campaign_group;

-- Q4. FUNNEL WITH STEP CONVERSION (UNION ALL to unpivot, LAG window function)
WITH totals AS (
  SELECT campaign_group,
         SUM(impressions) AS impressions, SUM(clicks) AS clicks, SUM(searches) AS searches,
         SUM(view_content) AS view_content, SUM(add_to_cart) AS add_to_cart, SUM(purchases) AS purchases
  FROM complete_days GROUP BY campaign_group
),
long AS (
  SELECT campaign_group, 1 AS step, 'impressions'  AS stage, impressions  AS n FROM totals UNION ALL
  SELECT campaign_group, 2, 'clicks',       clicks       FROM totals UNION ALL
  SELECT campaign_group, 3, 'searches',     searches     FROM totals UNION ALL
  SELECT campaign_group, 4, 'view_content', view_content FROM totals UNION ALL
  SELECT campaign_group, 5, 'add_to_cart',  add_to_cart  FROM totals UNION ALL
  SELECT campaign_group, 6, 'purchases',    purchases    FROM totals
)
SELECT campaign_group, step, stage, n,
       ROUND(100.0 * n / LAG(n) OVER (PARTITION BY campaign_group ORDER BY step), 2) AS pct_of_previous_stage,
       ROUND(100.0 * n / FIRST_VALUE(n) OVER (PARTITION BY campaign_group ORDER BY step), 3) AS pct_of_impressions
FROM long
ORDER BY campaign_group, step;

-- Q5. DAILY COST PER PURCHASE WITH 7-DAY MOVING AVERAGE (window frame)
SELECT campaign_group, date, spend, purchases,
       ROUND(1.0 * spend / purchases, 2) AS cpa,
       ROUND(AVG(1.0 * spend / purchases) OVER (
             PARTITION BY campaign_group ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS cpa_7d_avg
FROM complete_days
ORDER BY campaign_group, date;

-- Q6. HEAD-TO-HEAD BY DATE (self-join): did the test campaign beat control on each day?
SELECT c.date,
       c.purchases AS control_purchases, t.purchases AS test_purchases,
       t.purchases - c.purchases AS purchase_diff,
       ROUND(1.0 * c.spend / c.purchases, 2) AS control_cpa,
       ROUND(1.0 * t.spend / t.purchases, 2) AS test_cpa,
       CASE WHEN 1.0 * t.spend / t.purchases < 1.0 * c.spend / c.purchases THEN 'test' ELSE 'control' END AS cheaper_purchase
FROM complete_days c
JOIN complete_days t ON t.date = c.date AND t.campaign_group = 'test'
WHERE c.campaign_group = 'control'
ORDER BY c.date;

-- Q7. DAYS WON BY EACH GROUP (cost per purchase)
WITH h2h AS (
  SELECT c.date,
         CASE WHEN 1.0 * t.spend / t.purchases < 1.0 * c.spend / c.purchases THEN 'test' ELSE 'control' END AS cheaper
  FROM complete_days c
  JOIN complete_days t ON t.date = c.date AND t.campaign_group = 'test'
  WHERE c.campaign_group = 'control'
)
SELECT cheaper AS group_with_lower_cpa, COUNT(*) AS days FROM h2h GROUP BY cheaper;

-- Q8. WEEKDAY VS WEEKEND PATTERN BY GROUP
SELECT campaign_group,
       CASE WHEN is_weekend = 1 THEN 'weekend' ELSE 'weekday' END AS day_type,
       COUNT(*) AS days,
       ROUND(AVG(purchases), 1) AS avg_daily_purchases,
       ROUND(AVG(spend), 0)     AS avg_daily_spend,
       ROUND(1.0 * SUM(spend) / SUM(purchases), 2) AS cost_per_purchase
FROM complete_days
GROUP BY campaign_group, is_weekend
ORDER BY campaign_group, is_weekend;

-- Q9. CUMULATIVE SPEND, PURCHASES AND RUNNING COST PER PURCHASE (SUM OVER)
SELECT campaign_group, date,
       SUM(spend)     OVER (PARTITION BY campaign_group ORDER BY date) AS cum_spend,
       SUM(purchases) OVER (PARTITION BY campaign_group ORDER BY date) AS cum_purchases,
       ROUND(1.0 * SUM(spend) OVER (PARTITION BY campaign_group ORDER BY date)
             / SUM(purchases) OVER (PARTITION BY campaign_group ORDER BY date), 2) AS running_cpa
FROM complete_days
ORDER BY campaign_group, date;

-- Q10. BEST 3 DAYS PER GROUP BY COST PER PURCHASE (ROW_NUMBER, partitioned)
WITH ranked AS (
  SELECT campaign_group, date, spend, purchases,
         ROUND(1.0 * spend / purchases, 2) AS cpa,
         ROW_NUMBER() OVER (PARTITION BY campaign_group ORDER BY 1.0 * spend / purchases) AS rn
  FROM complete_days
)
SELECT campaign_group, rn AS rank, date, spend, purchases, cpa FROM ranked WHERE rn <= 3 ORDER BY campaign_group, rn;

-- Q11. COST-EFFICIENCY QUARTILES (NTILE): how are the cheapest and priciest days distributed by group?
WITH q AS (
  SELECT campaign_group, 1.0 * spend / purchases AS cpa,
         NTILE(4) OVER (ORDER BY 1.0 * spend / purchases) AS quartile
  FROM complete_days
)
SELECT quartile,
       SUM(CASE WHEN campaign_group = 'control' THEN 1 ELSE 0 END) AS control_days,
       SUM(CASE WHEN campaign_group = 'test'    THEN 1 ELSE 0 END) AS test_days,
       ROUND(MIN(cpa), 2) AS min_cpa, ROUND(MAX(cpa), 2) AS max_cpa
FROM q GROUP BY quartile ORDER BY quartile;

-- Q12. DATA-QUALITY: days where a later funnel stage exceeds an earlier one
SELECT campaign_group, date, view_content, add_to_cart, purchases,
       CASE WHEN add_to_cart > view_content THEN 'add_to_cart > view_content'
            WHEN purchases   > add_to_cart  THEN 'purchases > add_to_cart'
            WHEN searches    > clicks       THEN 'searches > clicks' END AS issue
FROM complete_days
WHERE add_to_cart > view_content OR purchases > add_to_cart OR searches > clicks
ORDER BY campaign_group, date;
