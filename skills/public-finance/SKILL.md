---
name: public-finance
description: >-
  Municipal budget structure, fund accounting, revenue and expenditure
  categories, bond and debt instruments, and how to identify significant
  budget changes. Relevant when analyzing government financial documents,
  budget proposals, audits, or contract award amounts.
metadata:
  author: sidekick-pipeline
  version: "1.0"
  sources:
    - "Handbook of Independent Journalism (Deborah Potter)"
    - "The Data Journalism Handbook (collaborative)"
---

## When this knowledge applies

When reading a government budget document, financial statement, audit,
or contract award; when comparing financial figures across years or across
departments; when assessing whether a dollar figure is material; or when
determining what a financial action means for public services.

## Domain knowledge

### Municipal budget structure

A government budget is not a single document — it is a system of funds. Each
fund has its own revenues and expenditures that must balance. The funds
do not simply aggregate into one number.

**General fund**: the primary operating fund. Pays for most day-to-day
services — police, fire, parks, planning, administration. Property taxes,
sales taxes, and fees are typical revenue sources. When people talk about
"the city budget," they often mean the general fund.

**Special revenue funds**: restricted to specific purposes defined by law
or grant conditions. A gas tax fund may only be spent on roads. A housing
trust fund may only be spent on affordable housing. These funds cannot be
raided to balance the general fund.

**Capital projects fund**: accounts for major asset construction and
acquisition. Funded by bonds, grants, or transfers from operating funds.
Does not include ongoing maintenance (that is the general fund's job).

**Debt service fund**: holds the revenues dedicated to paying principal
and interest on bonds. Required by law to be funded before other expenditures
in most states.

**Enterprise funds**: for government activities run like a business — water,
sewer, transit, electric utilities. Revenue comes from rates charged to users,
not taxes. Enterprise fund deficits are covered by rate increases, not general
fund subsidies (usually).

**Trust and agency funds**: funds held on behalf of others (pension funds,
developer deposits, fees collected for state remittance).

### Operating vs. capital budgets

**Operating budget**: recurring expenditures for ongoing services — salaries,
benefits, supplies, contracted services. Financed by recurring revenues
(taxes, fees, grants). Must balance annually.

**Capital budget / Capital Improvement Plan (CIP)**: expenditures for
long-lived assets (buildings, infrastructure, equipment with multi-year
life). Financed by bonds, grants, development fees, or transfers from
operating funds. Projects span multiple years.

The distinction matters because:
- Cutting a capital project delays it; cutting operating spending reduces
  a current service
- Capital projects are financed differently and their cost is spread over time
- A balanced operating budget that defers capital maintenance is
  financially fragile — the deferred maintenance accumulates

### Revenue sources

**Own-source revenues** (agency controls rate/base):
- Property tax: stable, predictable; requires voter approval to increase
  above caps in many states
- Sales tax: volatile, tracks economic cycles; also subject to cap in many states
- Utility rates: typically set by the agency's own governing board
- Development fees and charges: tied to construction activity
- Fines and forfeitures: small and unpredictable

**Intergovernmental revenues** (agency does not control):
- State shared revenues (motor vehicle fees, sales tax sharing)
- Federal grants (formula grants and competitive grants)
- Redevelopment or special district pass-through

**Significance**: agencies with high intergovernmental revenue dependence are
vulnerable to state or federal policy changes. A 10% cut in state shared
revenues may require a larger cut in local services than a 10% decline in
local tax revenue, because intergovernmental revenue often funds specific
programs.

### Expenditure categories

**Personnel services**: salaries, wages, and benefits (including pensions
and health insurance). Typically 60-75% of the general fund in service-heavy
agencies. Changes here indicate headcount or compensation changes.

**Contracted services / professional services**: payments to outside
vendors for ongoing services (janitorial, legal, consulting, IT). Increases
here may substitute for hiring staff; the contract is public record.

**Supplies and materials**: consumables. Small in most budgets.

**Capital outlay**: equipment and small capital purchases below the
threshold for the capital budget (varies by agency, typically $5K–$25K).

**Debt service**: principal and interest payments. Non-discretionary
once bonds are issued — the agency must make these payments.

**Transfers**: internal movements between funds. A transfer from a reserve
fund to the general fund to cover a deficit is significant. Transfers to
the capital fund represent the operating budget's contribution to capital.

### Reserves

Reserves are accumulated surpluses — money not spent in prior years. Government
finance standards (GFOA) recommend an operating reserve of 15-25% of annual
expenditures. Below 10% is considered inadequate; below 5% is a fiscal distress
signal.

**Using reserves to balance the budget** is sometimes described as a "one-time
measure." In practice, relying on reserves year after year depletes them
without addressing structural imbalance between recurring revenues and
recurring expenditures. A budget that uses reserves every year for three years
is in structural deficit even if it is technically "balanced" each year.

### Bonds and debt

**General obligation (GO) bonds**: backed by the full faith and credit
of the issuing agency, typically repaid from property taxes. Require voter
approval in most states.

**Revenue bonds**: backed by a specific revenue stream (water rates, toll
revenue). Do not require voter approval but may have higher interest rates.

**Certificates of participation (COPs) / lease-revenue bonds**: a financing
structure that avoids voter approval requirements by structuring the
obligation as a lease. Used for public buildings and equipment. Controversial
because it circumvents the voter approval requirement for debt.

**Refunding bonds**: issued to refinance existing debt at lower interest
rates. Not new debt; may or may not produce savings.

**Key figures**:
- **Debt service ratio**: annual debt payments as a percentage of total
  revenues. Above 15% is a warning sign; above 20% is stress.
- **Per-capita debt**: total outstanding debt divided by population.
  Useful for comparing across jurisdictions of different sizes.

### Identifying significant budget changes

Numbers to focus on when comparing budget periods:

- Any department with year-over-year change > ±10%
- Any department where position count (FTEs) changed by more than 1
- Any new fund, fund elimination, or significant fund transfer
- Reserve fund balance change: is the agency drawing down reserves to balance?
- Debt service as a share of total expenditures: is it growing?
- Any line item labeled "one-time" or "non-recurring" — these may mask structural problems

### The Data Journalism Handbook on public finance

The Data Journalism Handbook emphasizes using open government financial data
(OpenSpending.org, USASpending.gov, state transparency portals) to track
public expenditure across levels of government. Key technique: filter
contract and payment data to find the same vendor appearing across multiple
agencies, or to find large single-vendor relationships that represent
outsourced government functions worth examining.

Following the money often means following transfers between funds, between
agencies, and between levels of government — each transfer is a step in
the chain that connects a public decision to an ultimate recipient.

## Gotchas

**"Balanced budget" is not a meaningful standard on its own.** A budget that
uses one-time measures (reserve draws, asset sales, deferred maintenance)
to cover a structural gap is balanced on paper but financially fragile.
Look at recurring revenues vs. recurring expenditures, not just totals.

**Pension liabilities are usually not on the balance sheet.** Most
government financial statements show pension costs as annual contributions,
not the full unfunded liability. The full liability appears in notes to
financial statements and in actuarial reports. A city can make its required
contributions every year and still have a growing unfunded liability.

**Adopted ≠ actual.** Budget documents describe what was authorized. Actual
expenditures (found in the CAFR/ACFR or quarterly financial reports) may
differ. Comparing adopted to actual reveals over- or under-spending by
department — sometimes significantly.

**"No taxpayer cost" claims often hide other costs.** A project described as
"self-funding" through developer fees, grants, or revenue bonds may shift
risk to ratepayers, future councils, or service recipients even if it
doesn't directly increase the tax levy today.

See [references/budget-analysis-guide.md](references/budget-analysis-guide.md)
for how to read a municipal budget document from scratch.

See [references/financial-comparison-methodology.md](references/financial-comparison-methodology.md)
for year-over-year comparison, inflation adjustment, and per-capita normalization methods.
