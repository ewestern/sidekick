# Cross-Domain Investigation Patterns

Common cross-beat patterns worth flagging, with examples from local government coverage and detection indicators.

---

## Pattern 1: Developer in multiple approval domains

**What it looks like**: A developer or development company that appears across several distinct approval processes for projects that are related or concurrent.

**Example**: A company submits a zoning application for a large residential project, appears on the council agenda for a development agreement with tax abatements, has a related project in the planning commission pipeline, and its principals appear in campaign finance records for council members who will vote on the agreements.

**Why it matters**: each approval may look routine in isolation. Together they represent a coordinated strategy to extract public value (zoning approvals, tax breaks, infrastructure commitments) for a single set of beneficiaries. The sum is more than the parts.

**Detection indicators**:
- Same company or related entities appearing in `housing_zoning`, `budget_finance`, and `government:city_council` beat artifacts within a 12-month window
- Entity cross-reference: common principal names across different entity registrations
- Timing: zoning application, development agreement, and tax incentive request clustered in a single budget cycle

---

## Pattern 2: Budget cuts with concentrated neighborhood impact

**What it looks like**: Reductions in services that, individually, appear to be cost-saving measures, but which collectively impact a specific geographic area or demographic group disproportionately.

**Example**: The parks department reduces staffing at facilities in lower-income neighborhoods while maintaining services in wealthier ones. The school district closes schools in the same neighborhoods. The library system reduces hours at the branches in those neighborhoods. Each decision is presented as based on utilization or efficiency.

**Why it matters**: no single decision appears discriminatory or unusual. The pattern across domains reveals a systemic allocation of service reductions that follows demographic lines.

**Detection indicators**:
- Facility closures, hour reductions, or staffing cuts concentrated in artifacts tagged with the same geographic area across different beats
- Entity/place tracking: the same neighborhood or facility name appearing in negative-outcome artifacts across `education:school_board`, `government:city_council`, and parks/recreation beats
- Temporal clustering within a budget cycle

---

## Pattern 3: Sole-source contractor web

**What it looks like**: Multiple departments or agencies award sole-source contracts to firms that share common principals, a common address, or a common referral source.

**Example**: Three city departments each award sole-source contracts in the same fiscal year to different LLCs that, on investigation, share a registered agent and a principal with ties to a department director.

**Why it matters**: each sole-source award may be below the threshold that triggers council review. Aggregated, they represent a significant bypass of competitive bidding that benefits a common set of beneficiaries.

**Detection indicators**:
- Multiple sole-source awards across departments in entity-extract artifacts
- Common contractor names or addresses across separate contract artifacts
- Cross-referencing award dates with the serving period of a common official who had influence across those departments

---

## Pattern 4: Policy change velocity after personnel change

**What it looks like**: A cluster of policy reversals, new approvals, or departures from established precedent that follows the appointment of a new official or the election of a new majority.

**Example**: After a new planning director is appointed, the department begins recommending approval for projects it previously recommended denying. After a council election changes the majority, previously stalled projects receive expedited consideration. After a new city attorney is hired, the agency begins settling litigation that had previously been vigorously defended.

**Why it matters**: some policy change after personnel change is expected and legitimate — new officials bring new priorities. The signal is when the changes systematically benefit the same class of entities or the same specific relationships.

**Detection indicators**:
- Cluster of reversal/approval artifacts in a specific beat following a personnel change in entity-tracking records
- Previously denied applications appearing again after the change
- Entities that were inactive in the artifact store becoming active again post-change

---

## Pattern 5: Cross-jurisdictional policy coordination

**What it looks like**: Similar policy changes adopted in neighboring jurisdictions within a compressed time period, suggesting coordinated advocacy or a common sponsor.

**Example**: Three cities in the same region adopt similar amendments to their development impact fee schedules within six months, each using nearly identical language. A regional developer association lobbied each city council.

**Why it matters**: individual jurisdictions may not know what their neighbors are doing. Coordinated advocacy that produces similar outcomes across multiple bodies is a significant finding about the infrastructure of policy influence.

**Detection indicators**:
- Similar content-type artifacts (ordinance summaries, policy-diff artifacts) across multiple geo tags within a short time window
- Shared language in the text of ordinances across jurisdictions
- Common entities (lobbyists, consultants, advocacy organizations) appearing in the public comment record across multiple jurisdictions

---

## Pattern 6: Incomplete disclosure web

**What it looks like**: Information that is nominally disclosed but structured to make the full picture difficult to assemble — split across multiple documents, in different formats, with gaps that prevent easy aggregation.

**Example**: A city's contract payments to a firm appear in three different budget line items, across two fiscal years, with one portion approved in closed session. No single document shows the full relationship. Only aggregating across all three disclosures reveals the total value of the relationship.

**Why it matters**: agencies are sometimes sophisticated about how they structure disclosure to technically comply with requirements while making the full picture difficult to see. Aggregation across documents reveals what individual disclosures conceal.

**Detection indicators**:
- The same contractor or recipient appearing in multiple artifact sources with different stated amounts that, when totaled, exceed a threshold that would require additional disclosure or approval
- Related artifacts whose lineage links suggest they were produced in separate proceedings that addressed parts of the same underlying relationship

---

## Pattern 7: Recurring emergency or urgency designations

**What it looks like**: An agency routinely uses emergency powers or urgency designations to bypass normal deliberative processes for a class of actions.

**Example**: A county consistently designates its largest contracts as "emergency" or "urgent" to avoid competitive bidding. Over a two-year period, emergency designations account for 30% of sole-source awards above the threshold, concentrated in one department.

**Why it matters**: emergency powers exist for genuine emergencies. Systematic use of emergency designations to circumvent competitive bidding or normal public notice is itself an accountability issue.

**Detection indicators**:
- High frequency of "urgency," "emergency," or "waiver" flags in document-assessment artifacts for a specific agency or department
- Emergency designations that cluster around the same department director or the same class of vendors

---

## Detection and escalation thresholds

| Number of instances | Appropriate response |
|---|---|
| 1 cross-domain co-appearance | Note in entity registry; no action |
| 2 co-appearances | Trend note; watch for recurrence |
| 3 co-appearances | Flag for editorial attention; brief investigation warranted |
| 4+ or high-value co-appearances | Connection memo; full investigation may be warranted |

These thresholds are guidelines, not rules. A single cross-domain co-appearance involving a very large dollar amount, a very specific relationship, or timing immediately before a significant decision may warrant immediate escalation.
