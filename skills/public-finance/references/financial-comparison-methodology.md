# Financial Comparison Methodology

Methods for making government financial figures comparable across time periods, jurisdictions, and scales. Raw dollar figures without adjustment are rarely meaningful comparisons.

---

## Year-over-year comparison

The most common comparison in budget reporting. Basics:

**What to compare**:
- Proposed budget (current year) vs. adopted budget (prior year)
- Adopted budget (current year) vs. adopted budget (prior year)
- Actual expenditures (current year, from financial report) vs. actual expenditures (prior year)
- Actual vs. budget (current year): how well did the agency forecast?

**Why the comparison type matters**: comparing the current proposed budget to the prior year's actuals can make the proposal appear conservative even when it represents significant growth (because actuals are often below budget). Always use the same type of figure (proposed, adopted, or actual) on both sides of the comparison.

**Compound multi-year change**: year-over-year shows change from one year to the next. Multi-year change shows the cumulative effect. A department that grows 3% per year for 5 years has grown about 16% in total. Use multi-year perspective when a single year looks unremarkable but the trend is significant.

---

## Inflation adjustment

Dollar figures from different years are not directly comparable. To adjust:

**Consumer Price Index (CPI) method**:

```
Inflation-adjusted value = Nominal value × (CPI[target year] / CPI[original year])
```

**Data source**: U.S. Bureau of Labor Statistics, CPI-U (all urban consumers), available at bls.gov

**Example**: A $10 million budget in 2015, expressed in 2026 dollars
- CPI 2015 ≈ 237
- CPI 2026 ≈ 320 (approximate)
- Adjusted: $10M × (320/237) = approximately $13.5M

A budget that grew from $10M to $12M (2015 to 2026 nominal) shrank in real terms.

**Which index to use**:
- General spending: CPI-U (consumer price index)
- Construction and infrastructure: Engineering News-Record Construction Cost Index
- Healthcare: Medical CPI component
- Education: Higher Education Price Index or similar

Using the right index matters: construction costs have often inflated faster than general CPI, so a construction budget that kept pace with CPI may have lost real purchasing power.

---

## Per-capita normalization

When comparing across jurisdictions of different size, or when tracking a jurisdiction's spending per resident over time.

**Formula**: Per-capita expenditure = Total expenditure / Population

**Data source**: U.S. Census Bureau, American Community Survey for population estimates between decennial censuses.

**Applications**:
- "Springfield spends $X per resident on parks, compared to the state average of $Y"
- "Per-capita school funding in the district declined by 8% over five years" (even if nominal funding increased, if enrollment grew faster)
- "Per-capita debt in the city is $X — the highest in the county"

**Caution**: per-capita figures can be distorted when population changes are uneven. A city that absorbed a large annexation may show a per-capita drop in spending without any actual service cut.

---

## Per-unit normalization

For services where the relevant denominator is not population:

| Service | Appropriate denominator |
|---|---|
| School spending | Per-pupil (enrolled students) |
| Housing assistance | Per-unit or per-household served |
| Road maintenance | Per lane-mile |
| Water/sewer | Per connection or per metered unit |
| Policing | Per 1,000 residents or per sworn officer |

Using a service-appropriate denominator makes comparison more meaningful and harder to manipulate.

---

## Cross-jurisdictional comparison

Comparing budget figures across different cities, counties, or districts. Additional considerations:

**Service scope varies**: one city may operate its own water and sewer utility; another may contract it to a regional authority. Their "city budgets" are structurally different even before any efficiency comparison.

**Fund accounting differences**: one jurisdiction may include enterprise funds in its total budget; another may report only the general fund. Clarify what is included before comparing totals.

**Cost of living adjustment**: salaries and contracted service costs differ significantly by region. A per-capita spending comparison between a high-cost coastal city and a lower-cost inland city may reflect labor markets, not efficiency.

**Comparable peer selection**: the most meaningful comparisons are with jurisdictions of similar size, demographics, service scope, and regional context. State municipal leagues and the Census of Governments data are standard sources for peer comparisons.

---

## Budget vs. actual: variance analysis

Comparing what was budgeted to what was actually spent reveals forecasting accuracy and execution quality.

**Significant variances to flag**:
- Any line item where actual expenditure exceeded budget by more than 10%
  (overspent — why? Emergency? Miscalculation?)
- Any line item where actual revenue fell short of budget by more than 5%
  (revenue shortfall — structural or one-time?)
- Large positive variances (spending significantly below budget) — savings or
  service reductions?

**The structural vs. one-time question**: a variance that repeats year after year is structural — the budget assumptions are systematically wrong, or a revenue source is consistently overestimated. A one-time variance has a specific explanation (a delayed project, an emergency expenditure, an unexpected grant).

---

## Summary table: which method to use when

| Comparison goal | Method |
|---|---|
| Same jurisdiction, same metric, different years | Year-over-year (nominal); multi-year with inflation adjustment |
| Same jurisdiction, track real change over time | Inflation-adjusted (CPI or appropriate index) |
| Different jurisdictions, different sizes | Per-capita normalization; same unit (adopted budget, general fund only) |
| Same service across jurisdictions | Per-unit normalization (per-pupil, per-mile, per-connection) |
| Fiscal health trends | Reserve ratio, debt service ratio, pension funded ratio |
| Program effectiveness | Budget vs. actual; per-unit cost over time |
