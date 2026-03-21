# Vote Tracking Guide

Schema and methodology for recording government body votes with enough context to support longitudinal tracking and significance assessment.

---

## Vote record schema

For each action item that comes to a vote, record:

```
Meeting body:       [City Council / Planning Commission / School Board / etc.]
Meeting date:       [YYYY-MM-DD]
Item number:        [As listed on the agenda, e.g., "Item 5B" or "Resolution 2026-07"]
Item description:   [Brief description of what was being decided]
Staff recommendation: [Approve / Deny / Continue / No recommendation]

Motion:
  Made by:          [Member name]
  Seconded by:      [Member name]
  Motion text:      [The exact motion language, especially for amendments]

Vote tally:
  Aye:              [Names of members who voted yes]
  Nay:              [Names of members who voted no]
  Abstain:          [Names of members who abstained — note reason if stated]
  Absent:           [Names of members who were absent]
  Total attending:  [Number of members present]
  Total seated:     [Number of filled seats on the body]

Outcome:            [Approved / Denied / Continued / Tabled / Failed — no action]
Effective date:     [For ordinances: 30 days after adoption, or immediate if urgency]
```

---

## Interpreting vote tallies

### Majority types

| Outcome needed | How to calculate | When it applies |
|---|---|---|
| Simple majority of those voting | More than half of aye + nay | Most routine actions |
| Majority of full membership | More than half of total seated | Some state laws require this for specific actions |
| Two-thirds of those voting | 2/3 of aye + nay | Urgency ordinances, supermajority items |
| Two-thirds of full membership | 2/3 of total seated | Override of veto; some charter provisions |

**Important**: abstentions are typically excluded from the denominator in a majority of those voting calculation, but included in a majority of full membership calculation. Confirm local rules.

### When does a motion fail?

A motion fails when the ayes do not reach the required threshold. A 3-3 tie means the motion failed — the body did not achieve a majority. A failed motion means the proposed action does not happen; it does not mean the body voted to take the opposite action.

Exception: some governing bodies have rules that treat a tie as passing a motion to continue or refer the item. Check local rules.

### Abstentions in land use decisions

In some states (notably California under the Subdivision Map Act), a planning commissioner's abstention on a discretionary permit application is treated as a vote in favor of the project. Confirm whether this rule applies to the jurisdiction being covered; it can produce surprising outcomes when a member abstains to avoid appearing to vote for a project they privately support.

---

## Longitudinal vote tracking

Track voting patterns across meetings to identify:

**Consistent alignments**: members who consistently vote together on a particular class of items (development projects, public safety spending, labor relations). Alignments that cross the usual coalition lines are worth noting.

**Outlier votes**: a member who usually votes with the majority voting against — or a member who usually votes against voting in favor. Outlier votes often reflect either a policy concern or a relationship concern worth investigating.

**Split on consent**: a non-unanimous vote on a consent calendar item is unusual and warrants attention. A member who votes against a consent item (or pulls it from consent) is signaling a concern they want on the record.

**Recusals**: a member who recuses themselves from a vote on a specific item has declared a conflict of interest. Track recusals across items: does the same member recuse frequently on items involving the same contractor, developer, or industry? Multiple recusals by the same member on the same type of item may indicate a relationship that warrants examination.

---

## Recording motions accurately

The exact text of a motion matters when:

- The motion includes conditions of approval (a developer permit with conditions attached)
- The motion departs from staff's recommendation
- The motion amends a prior action
- The motion is a substitute for an earlier motion

**Common motion types and their significance**:

| Motion type | Significance |
|---|---|
| Approve as recommended | Aligns with staff; unremarkable |
| Approve with modifications | Council changed something from staff's proposal |
| Approve with findings | Legal findings are part of the action; findings have legal significance |
| Continue to [date] | Item unresolved; watch for return |
| Table indefinitely | Effectively killed without a denial vote |
| Refer to committee/staff | Deferred; watch for return with findings |
| Deny | Applicant may have appeal rights; denial triggers reconsideration period |
| Rescind / Revoke | Prior action being undone; rare and significant |

---

## What to flag from the vote record

| Signal | Why it matters |
|---|---|
| 4-3 or closer vote | Contested outcome; dissent is on the record |
| Any nay vote with a stated reason | Member's position is articulated and attributable |
| Outcome contradicts staff recommendation | Council exercised independent judgment; may indicate political pressure or policy disagreement |
| Urgency finding | Action took immediate effect; normal public deliberation period bypassed |
| Member recusal | Conflict of interest declared; track the pattern |
| Failed motion followed by a substitute | The first motion's defeat and the substitute's passage reveals what the body was willing and unwilling to do |
| Item returned from prior meeting with changed outcome | Something changed between meetings; what? |
