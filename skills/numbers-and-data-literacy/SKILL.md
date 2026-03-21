---
name: numbers-and-data-literacy
description: >-
  What numbers mean in context — percentages, rates of change, per-capita
  figures, inflation-adjusted comparisons, margin of error, and common
  ways numbers mislead. Relevant when extracting, characterizing, or
  assessing the significance of quantitative information in government
  documents or data.
metadata:
  author: sidekick-pipeline
  version: "1.0"
  sources:
    - "Handbook of Independent Journalism (Deborah Potter)"
    - "The Data Journalism Handbook (collaborative)"
---

## When this knowledge applies

When a document contains numerical claims — budget figures, vote tallies,
population counts, rate changes, contract amounts, poll results, or any
statistical assertion — and when characterizing whether a number is
significant, accurate, or properly contextualized.

## Domain knowledge

### The core problem: numbers without context mislead

Potter: "Most reporters got into the business because they liked words, not
numbers. But the audience deserves better." A raw number without context is
almost meaningless. $4 million sounds like a lot; whether it is significant
depends on what it is being spent on, by which entity, in relation to what
baseline, compared to what alternative.

The journalist's job with numbers is not arithmetic — it is contextualization.
What does this number mean in relation to something the audience already
understands?

### Percentages and rates of change

**Percentage vs. percentage point**: if a tax rate increases from 10% to 12%,
it increased by 2 percentage points but by 20 percent. These are both correct
statements; they mean very different things.

**Base matters**: a 50% increase from a base of 2 yields 3. The same percentage
from a base of 2,000 yields 3,000. Always establish the base before the
percentage is meaningful.

**Denominator selection**: "crime is up 50%" sounds alarming. If the base was 4
incidents and the new figure is 6, that is still a small absolute number.
Conversely, a "small" 3% increase in a large category (total city budget,
school enrollment) can represent a very large absolute change.

**Cherry-picked time periods**: a trend can look alarming or reassuring
depending on the start date chosen. "Crime is down 20% since [worst year]"
and "crime is up 8% since [lowest year]" may both be accurate for the same
dataset. Note what time period is being used and whether it was selected
to support a conclusion.

### Rates, not counts

Raw counts ignore the size of the underlying population. Use rates when
comparing across jurisdictions or time periods where the underlying population
has changed.

- 100 crimes in a city of 10,000 = 10 per 1,000 residents
- 100 crimes in a city of 100,000 = 1 per 1,000 residents

These are the same count but very different rates. Always normalize counts
to a common population base (per 1,000, per 100,000, per household, per
school) before comparing across entities or time.

**Common denominators**:
- Crime: per 1,000 residents or per 100,000 residents
- School outcomes: per 100 students; per school
- Budget: per capita (per resident); per pupil (for school budgets)
- Health: per 100,000 population

### Inflation adjustment

Dollar figures from different years are not directly comparable. A contract
for $1 million in 2010 is not the same as a $1 million contract in 2026.
Inflation erodes the purchasing power of money over time.

To compare dollar figures across years:
1. Choose an index: Consumer Price Index (CPI) for general comparisons;
   specific indices exist for construction, healthcare, etc.
2. Identify the base year (the year you want to express values in)
3. Multiply the original figure by: CPI[base year] / CPI[original year]

The Data Journalism Handbook's "£32 loaf of bread" example: nominal prices
can make historical comparisons look absurd without inflation adjustment.
A salary that seems high in historical dollars may represent a real-terms
pay cut after adjustment.

**Rule**: whenever comparing dollar figures across more than two or three
years, note whether figures are inflation-adjusted or nominal, and if nominal,
the comparison may be misleading.

### Averages and what they hide

**Mean**: the sum divided by the count. Sensitive to extreme values.
An average contract value of $500,000 across 10 contracts may reflect
9 contracts at $50,000 and one at $4.55 million.

**Median**: the middle value when sorted. More robust to extreme values.
The median income in a neighborhood where most residents earn $40,000 but a
few households earn $1 million is still close to $40,000.

**Which average is the city using?** Government documents often use the mean
because it is easier to calculate and can be made to look more favorable.
Ask: is this the mean or the median? If mean, are there outliers pulling it?

### Polls and surveys

Potter on polls: the only useful poll is one where the methodology is disclosed.
Key questions for any survey:

- **Sample size**: larger is more reliable, but only if the sample is
  representative. 1,000 random responses is more useful than 10,000 self-selected
  online responses.
- **Margin of error**: a poll showing 52% support with a ±4% margin of error
  cannot distinguish between 48% and 56% support — the result is statistically
  indistinguishable from 50-50.
- **Question wording**: leading questions produce biased results. The order
  of questions can also affect answers.
- **Who conducted it**: a poll commissioned by a party with an interest in the
  outcome should be treated with extra skepticism even if the methodology
  appears sound.
- **Response rate**: low response rates introduce self-selection bias.

### Correlation vs. causation

Two things that move together are correlated. That does not mean one caused
the other. Both may be caused by a third factor; the correlation may be
coincidental; the relationship may run in the opposite direction to what
is claimed.

Government agencies frequently imply causation from correlation in program
evaluations: "After implementing this program, crime fell 15%." Alternative
explanations (economic conditions, demographic change, policing levels,
national trends) must be considered before attributing the change to the
program.

**The policy implication test**: if the claimed causal relationship implies
a policy, check whether the policy makes logical sense and whether it is
supported by evidence beyond the correlation.

### Significant figures and false precision

A budget figure of $4,382,916 implies a level of precision that is almost
never meaningful in a news context. Round to the appropriate level:
- Under $10,000: to the nearest hundred
- Under $1 million: to the nearest thousand
- Over $1 million: "about $4.4 million" or "nearly $4.4 million"

**False precision** creates a misleading impression of accuracy. An estimate
reported as "$4,382,916" invites readers to treat it as an audited figure
when it may be a rough estimate carried to the penny.

### Making numbers meaningful

The Data Journalism Handbook technique: anchor unfamiliar large numbers to
familiar ones.

- $4 million is "roughly the cost of maintaining every mile of the city's
  road network for a year" (if true)
- $400 per household
- The equivalent of 8 police officers for a year
- Half the annual cost of the parks department

These translations make numbers concrete without distorting them. The anchor
should be relevant to the decision being reported.

## Gotchas

**Year-over-year comparisons hide multi-year trends.** A 3% increase this
year that follows five years of cuts may represent net decline. Always check
whether a year-over-year comparison is the right window.

**"Largest in history" / "record" claims need a baseline.** Records are
broken constantly when a system is growing. The record high budget in 2026
may be less significant than the record real-terms (inflation-adjusted)
budget in 1998.

**Zero-based vs. prior-year budgeting.** A "10% increase" in a budget line
is relative to whatever was in that line last year. If last year's figure was
itself an anomaly (a one-time expenditure, an emergency appropriation), the
comparison is misleading.

**Sample size and statistical significance are different things.** A study
can have a large sample and still produce a result that is not statistically
significant. Statistical significance (p < 0.05) means the result is unlikely
to have occurred by chance at that threshold — it does not mean the result
is practically meaningful or large in magnitude.

See [references/statistical-pitfalls.md](references/statistical-pitfalls.md)
for a catalog of common numerical errors with examples from government reporting.

See [references/presenting-numbers.md](references/presenting-numbers.md)
for methods of translating raw figures into audience-accessible context.
