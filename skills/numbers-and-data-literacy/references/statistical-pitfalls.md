# Statistical Pitfalls

Common numerical errors in government reporting, with examples and correctives.

---

## 1. Percentage vs. percentage point confusion

**The error**: conflating a change measured in percentage points with a change expressed as a percentage of the original value.

**Example**: A city's sales tax rate increases from 8% to 9%.
- Incorrect: "Sales tax increased by 1%"
- Correct options:
  - "Sales tax increased by 1 percentage point" (the arithmetic difference)
  - "Sales tax increased by 12.5%" (the relative change: 1/8 = 12.5%)

Both the percentage-point and the relative-change statements are accurate — but they communicate different things. The relative change is usually more meaningful for the audience.

**In government documents**: budget discussions routinely conflate these. "Our investment in public safety increased by 2%" may mean 2 percentage points of the total budget (a large shift) or 2% of the public safety budget (a much smaller one). Always clarify the base.

---

## 2. Misleading base selection (cherry-picked comparisons)

**The error**: choosing a starting point for a trend that makes the trend look more (or less) dramatic than a representative baseline would show.

**Example**: A city's crime statistics:
- 2020: 150 incidents (elevated due to civil unrest)
- 2021: 120 incidents
- 2022: 110 incidents
- 2023: 105 incidents
- 2024: 100 incidents
- 2025: 98 incidents

From a 2020 base: "Crime down 35%!" (accurate but misleading — 2020 was an outlier)
From a 2022 base: "Crime down 11%" (more representative of the trend)
From 2019 (pre-2020): depends on 2019's figure — may show a different picture entirely

**Corrective**: always ask what the "normal" baseline is. When an agency cites a favorable trend, check whether the base year was selected for its unfavorability. Look at a multi-year series, not just the endpoint comparison the agency prefers.

---

## 3. Raw counts without population denominators

**The error**: comparing raw counts across jurisdictions or time periods without adjusting for the size of the underlying population.

**Example**: City A (population 50,000) reported 100 property crimes. City B (population 200,000) reported 150 property crimes.
- Raw count: City B has 50% more property crime
- Rate: City A = 2.0 per 1,000 residents; City B = 0.75 per 1,000 residents
- Correct conclusion: City A has nearly three times City B's property crime rate

**Common in government reporting**: budget amounts without per-capita context; school discipline incidents without per-enrollment context; permit applications without per-capita context.

---

## 4. Mean vs. median confusion

**The error**: using the mean when the median is more appropriate, or vice versa.

**The mean is distorted by outliers**: one $10 million contract in a dataset of 20 contracts averaging $200,000 each produces a mean of $700,000 that is not representative of any individual contract.

**The median is robust to outliers**: the median of the same dataset would be closer to $200,000.

**When to use each**:
- Mean: when all values are relevant to the total (total budget impact; total program cost)
- Median: when describing what is typical (median contract value; median salary; median household income)

**In government documents**: salary disclosures often use averages that are pulled up by a small number of high-earning executives. The median salary tells a more representative story about typical employees.

---

## 5. Omitted denominator in "% of budget" claims

**The error**: expressing something as a percentage of "the budget" without specifying which budget.

**Example**: "The parks department represents 3% of the city's budget."
- Is this 3% of the general fund only?
- 3% of total appropriations including all funds?
- 3% of total expenditures including enterprise funds?

These can differ significantly. A city with a large enterprise fund (water, sewer) has a much larger total budget than its general fund alone — making any department appear to be a smaller percentage.

**Corrective**: specify the denominator precisely. "Parks represents 3% of the general fund appropriations" is a precise statement.

---

## 6. Confusing absolute and relative significance

**The error**: treating a large percentage change as important when the absolute amount is small, or a small percentage change as insignificant when the absolute amount is large.

**Example A**: "Youth after-school program funding increased 100% — doubled!" From $5,000 to $10,000. A 100% increase of a $5,000 program is still $5,000.

**Example B**: "Pension costs increased only 2%." On a $100 million obligation, 2% is $2 million — a very significant amount.

**Corrective**: always report both the percentage and the absolute dollar amounts. Let readers assess scale for themselves.

---

## 7. Ignoring margin of error in surveys and polls

**The error**: treating a poll result as a precise figure when the margin of error makes the result statistically ambiguous.

**Example**: "56% of residents support the proposed tax measure, according to a survey with a ±5% margin of error."
- The true value could be anywhere from 51% to 61%
- More importantly: the result is consistent with a majority and consistent with a strong majority — both very different political situations
- If the result were 52% ± 5%, the range would include 47% — meaning the poll cannot rule out majority opposition

**In government documents**: agency-commissioned public satisfaction surveys often do not report methodology or margin of error. A survey showing "82% customer satisfaction" from a self-selected response pool is meaningless without knowing who was surveyed and how.

---

## 8. Mixing nominal and real (inflation-adjusted) figures in the same comparison

**The error**: comparing a dollar figure from one year (nominal) directly to a figure from another year without adjustment.

**Example**: "City spending on infrastructure is at a 20-year high of $25 million."
- In nominal dollars, this may be true
- In real (inflation-adjusted) dollars, $25 million in 2026 may be less than $20 million in 2006 was worth

A 20-year nominal "high" that is actually a real-terms decline misrepresents the situation.

**Corrective**: always note whether figures are nominal or inflation-adjusted. For comparisons across more than 3-4 years, inflation adjustment is usually necessary for accuracy.

---

## 9. Treating correlation as causation in program evaluations

**The error**: attributing an observed change to a program because the change occurred while the program was running.

**Example**: "After the city implemented the Safe Streets program, pedestrian injuries decreased 30%."
- Possible explanations: the program worked; pedestrian patterns changed due to the pandemic; a larger statewide safety trend; road construction that reduced pedestrian exposure; reporting methodology changed

**Standard to apply**: does the claimed causal mechanism make logical sense? Is there a comparison group (a similar city that did not implement the program) that showed a different result? Was the change statistically significant and large enough to rule out chance variation?

**In government reports**: program success is almost always described in terms that imply causation. The agency's incentive is to claim credit for positive outcomes. The journalist's role is to ask what alternative explanations would also fit the data.
