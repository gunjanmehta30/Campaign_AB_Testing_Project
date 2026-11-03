# Marketing Campaign A/B Test: Analysis Report

**Question:** Did the test campaign outperform the control campaign at turning ad spend into purchases?
**Answer:** **No clear winner on cost-efficiency.** Both campaigns produced the same number of purchases, but the test campaign spent about 11% more to get them. The test changes *where* the funnel loses people, but not the bottom line.
**Recommendation:** Do not switch to the test approach on this evidence. Keep control as the default and run a longer, equal-budget follow-up.

## 1. Data and method
- Real data from Kaggle: 30 days (1-30 Aug 2019) per campaign, daily totals. See `docs/DATA_DICTIONARY.md`.
- One control day was empty and was dropped (29 control days vs 30 test days). Filling it in changes no conclusion.
- Because the data are daily totals and not users, **the day is the unit of analysis.** I used permutation tests (10,000 label shuffles) and 95% bootstrap intervals that resample days, with Benjamini-Hochberg correction across 11 metrics.
- Why not a normal two-proportion test? Day-to-day variation is hundreds of times larger than pure binomial noise (click-through rate: 955x in control, 3,715x in test), so a standard chi-square test returns p near 0 for almost everything. It would badly overstate certainty.

## 2. Headline results
| Metric | Control | Test | Difference | 95% CI | Verdict |
|---|---|---|---|---|---|
| Mean daily purchases | 522.8 | 521.2 | -0.3% | | no difference (p = 0.96) |
| Mean daily spend | $2,304 | $2,563 | +11.2% | | test spends more (p = 0.007) |
| **Cost per purchase** | **$4.41** | **$4.92** | **+11.6%** | **-9.6% to +35.1%** | **inconclusive** |
| Purchases per $1,000 | 226.9 | 203.4 | -10% | | |
| Click-through rate | 4.86% | 8.09% | +66.5% | +33% to +105% | **test better** |
| Cost per click | $0.433 | $0.425 | -1.9% | -20% to +16% | no difference |
| Cost per 1,000 impressions | $21.03 | $34.36 | +63% | +40% to +94% | control cheaper |

## 3. Where the funnel changed
| Stage rate | Control | Test | Verdict (corrected) |
|---|---|---|---|
| Click-through (clicks / impressions) | 4.9% | 8.1% | test higher |
| Searches / clicks | 41.7% | 40.1% | no clear difference |
| View content / searches | 87.5% | 76.8% | control higher |
| Add to cart / view content | 66.9% | 47.4% | control higher |
| Purchases / add to cart | 40.2% | 59.1% | test higher |
| Purchases / clicks | 9.8% | 8.6% | no clear difference |

**Reading the pattern:** the test campaign attracts more clicks per impression, but fewer of those visitors add items to the cart.
The ones who do add to cart are more likely to buy. A plausible hypothesis is that the test ads attract more curious clicks and a smaller, more purchase-ready audience.
That is a hypothesis to test, not a finding from this data. Stage rates here come from daily totals, so they are not per-user conversion rates.

## 3b. Impressions vs cost
The test campaign got 32% fewer impressions per day but paid 63% more per thousand impressions, so it bought a different, more expensive audience.
It converts impressions to purchases better (+46%), and this is exactly offset by the higher price of those impressions, which is why cost per purchase ends up roughly level.

## 4. Robustness checks
- Dropping vs interpolating the empty control day: **same conclusion for all 11 metrics.**
- Day-level resampling and permutation tests used throughout, not user-level tests.
- Weekday vs weekend: both campaigns sell about 25% fewer purchases on weekends and cost more per purchase on weekends, so the pattern is shared.
- Power: with about 30 days per arm, only differences of roughly **28% in daily purchases** could be detected reliably. A 10% difference would need roughly 8x as many days. This is why cost per purchase is inconclusive rather than "no difference".

## 5. Recommendations
1. **Keep the control campaign as the default.** The test did not add purchases and cost more per purchase on average (not statistically certain).
2. **Re-run with equal budgets and the same targeting windows**, so spend differences do not muddy the comparison.
3. **Investigate the add-to-cart drop** in the test campaign (-29%). Check whether ad messaging sets expectations the product page does not meet.
4. **Study the test's cart-to-purchase strength (+47%).** If that audience is more purchase-ready, test it as a retargeting or high-intent segment rather than a replacement.
5. **Capture revenue and user-level data** in the next test so ROI, return on ad spend and customer value can be measured.
6. **Fix tracking:** stage counts that exceed earlier stages on the same day suggest events are counted inconsistently.

## 6. Limitations
- Small sample (about 30 days per arm); several differences are directionally clear but imprecise.
- No revenue, so ROI is not available. Cost per purchase is a proxy for efficiency.
- Campaign assignment and audience selection are unknown, so differences may reflect targeting, not just creative.
- One empty control day.
