# Cross-Reference Methodology

Methods for corroborating claims across multiple documents or sources. A single-source claim is an assertion; corroboration elevates it on the verification spectrum.

---

## The corroboration ladder

| Level | How to achieve it |
|---|---|
| Assertion | One source makes the claim |
| Internally consistent | The claim coheres with other facts in the same document |
| Corroborated | The claim appears in at least two independent sources |
| Documented | The claim is supported by a primary source document |
| Established fact | Indisputable; no attribution needed |

The goal of cross-reference work is to move claims from the top of the ladder toward the bottom.

---

## Core cross-reference types

### 1. Document-to-document within an event

For any government action, multiple documents typically exist about the same event. Cross-reference them:

| Document A | Document B | What to compare |
|---|---|---|
| Agenda | Minutes | Were all agenda items actually taken up? In what order? |
| Minutes | Resolution/Ordinance | Does the vote recorded in the minutes match the resolution text? |
| Staff report | Minutes | Did the council accept staff's recommendation or diverge? |
| Budget proposal | Adopted budget | What changed between proposal and adoption? |
| Press release | Meeting minutes | Does the city's announcement accurately reflect the vote? |

**Method**: read both documents for the same item; note any discrepancy in vote tallies, dollar figures, effective dates, or described outcomes. A discrepancy is not automatically an error — versions may reflect different stages of a process — but it requires explanation.

### 2. Document-to-document across time (longitudinal)

For recurring events (council meetings, budget cycles, quarterly reports), compare the current document against prior periods:

- Does this year's budget baseline match last year's adopted figure?
- Does this meeting's minutes note carry over items from the prior meeting?
- Does the quarterly report's figure match the annual report for the same period?
- Has the same contract amount appeared in two amendment documents, suggesting double-counting?

**Method**: locate the prior-period version of the same document; compare directly for the specific claim being checked.

### 3. Cross-source entity verification

When a person, organization, or property appears in a document, verify their identifying information against independent sources:

| Entity type | Independent verification source |
|---|---|
| Elected official | Official roster on the jurisdiction's website |
| Business/contractor | Secretary of State business registry; license database |
| Property | County assessor parcel database |
| Nonprofit | IRS Form 990; state charity registration |
| Contract value | Vendor payment records if available via open data |

**Method**: do not rely solely on the document's description of the entity. A company's legal name in a contract may differ from the trade name used in staff reports.

### 4. Claim-to-record corroboration

When a document makes a factual claim (a rate increase, a prior vote, a statutory requirement), locate the underlying record that either confirms or challenges it:

- "The council approved this contract at its January meeting" → check January minutes
- "This expenditure is within the approved budget" → check the adopted budget line
- "State law requires agencies to conduct this review" → locate the statute or regulation cited
- "No competitive bids were received" → check if a solicitation was actually published

**Method**: treat every factual claim in a document as unverified until the underlying record is located. A staff report's description of prior council action is not a substitute for the minutes of that action.

---

## Cross-document discrepancies: when they matter

Not all discrepancies are errors. Some are expected features of a multi-stage process:

**Expected discrepancy**:
- Staff report published Monday recommends denial; council approved the item Wednesday → reflects deliberation, not an error
- Budget proposal differs from adopted budget → the council amended it, as expected

**Unexpected discrepancy** (investigate further):
- Two official records from the same body contradict each other on an established fact
- A resolution states the vote was unanimous; the minutes record a dissent
- The contract amount in the award notice differs from the amount in the executed contract
- A document cites an ordinance that, when located, says something different than claimed

**Method**: when a discrepancy cannot be explained by stage differences or document vintage, flag it. The discrepancy itself may be the story.

---

## Using the artifact lineage graph for cross-reference

In the pipeline, every processed artifact carries `derived_from` links back to its source. This enables systematic cross-reference:

1. **Forward traversal**: from a raw document, find all processed artifacts derived from it. If two summaries conflict about the same document, the raw text is the authoritative source.

2. **Backward traversal**: from a claim in a beat brief or story draft, trace back through the lineage chain to the source document that supports it. If the lineage chain terminates at a secondary source (a press release rather than the minutes), the claim needs corroboration from a primary source.

3. **Cross-artifact comparison**: find all `entity-extract` artifacts for a given entity across different time periods or document types. Discrepancies in role, affiliation, or status are corroboration targets.

---

## When cross-reference is not possible

Sometimes an independent corroborating source does not exist or cannot be located. In those cases:

- State the claim with explicit attribution to the single source ("according to the staff report")
- Note the level of corroboration in any confidence assessment
- Flag the claim as needing follow-up verification before reliance
- Do not treat internal consistency (the claim coheres with other parts of the same document) as equivalent to cross-source corroboration
