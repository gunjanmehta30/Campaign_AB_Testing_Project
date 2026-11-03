# Interview Q&A for this project

**1. What was the business question and your answer?**
Did the test campaign convert ad spend to purchases more efficiently than control? Purchases were identical (about 522 per day each), the test spent about 11% more per day, and cost per purchase was $4.92 vs $4.41, which is inconclusive statistically (95% CI -10% to +35%). I recommended keeping control and re-running with equal budgets.

**2. Why didn't you use a standard z-test or chi-square on the totals?**
The data are daily totals, not users. Day-to-day variation was hundreds of times bigger than binomial noise (CTR dispersion about 955x in control), so a naive test gives p near 0 for everything. I treated each day as the unit and used permutation tests and bootstrap intervals.

**3. How did you handle the missing day?**
One control day had all metrics blank. My primary analysis drops it; the sensitivity analysis interpolates it. All 11 metric conclusions were identical.

**4. You tested 11 metrics. How did you avoid false positives?**
Benjamini-Hochberg false discovery rate correction across the whole family, applied to permutation p-values.

**5. Why couldn't you calculate ROI?**
The dataset has no revenue. I used cost per click, cost per add-to-cart and cost per purchase instead, and listed revenue capture as a recommendation.

**6. What's the most interesting finding?**
The test campaign had a much higher click-through rate (+66%) and a much higher cart-to-purchase rate (+47%), but a lower add-to-cart rate (-29%) and a much higher cost per 1,000 impressions (+63%). The funnel shifted but the outcome did not.

**7. What data-quality problems did you find?**
An empty day, and stage counts that exceed earlier stages in 10 day-level cases (e.g. add-to-cart greater than view-content). That means these are not strict per-user funnels, so I computed rates on pooled totals.

**8. What would you do next?**
An equal-budget, longer (or user-randomised) test with revenue tracking, plus an investigation of the add-to-cart drop in the test campaign.

**9. Which SQL features did you use?**
CTEs, views, UNION ALL to unpivot, LAG and FIRST_VALUE for funnel steps, moving-average window frames, SUM OVER for cumulative CPA, ROW_NUMBER, NTILE, and a self-join for head-to-head daily comparisons.
