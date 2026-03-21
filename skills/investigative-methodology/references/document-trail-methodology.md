# Document Trail Methodology

Building evidence chains via document lineage and detecting significant gaps in the record.

---

## The complete document chain concept

Every government action of consequence generates a predictable chain of documents. The chain is the evidence trail. A complete chain supports a complete finding; a gap in the chain is either a normal stage of the process or a significant absence.

The investigator's task is to:
1. Map the expected document chain for the type of action being investigated
2. Identify which documents exist in the record
3. For missing documents: determine whether their absence is expected, delayed, or significant

---

## Document chains by action type

### Contract award (competitive procurement)

Expected chain:
1. Board/council authorization to issue a solicitation
2. **Request for Proposals (RFP) or Invitation for Bids (IFB)** — the public solicitation
3. **Pre-bid meeting notes** or addenda (if any)
4. **Bids or proposals received** — list of respondents and their amounts
5. **Evaluation report** — how the agency scored and compared responses
6. **Staff recommendation** — who the award is recommended to and why
7. **Award resolution** — the council vote to award the contract
8. **Executed contract** — the signed agreement with the final terms
9. **Invoices and payments** — evidence of delivery and payment
10. **Final report or deliverable** — the product the agency received

**Significant gaps**:
- No solicitation → sole-source; was it authorized and documented as such?
- No evaluation report → how was the recommendation justified?
- Award resolution amount ≠ executed contract amount → scope changed between authorization and execution; was this re-approved?
- No invoices or final deliverable → was the work actually performed?

### Contract award (sole-source/emergency)

When competitive bidding is waived, the expected chain is shorter but the documentation requirements are higher:
1. **Emergency or sole-source determination** — written finding justifying the waiver
2. **Authorization** — who has authority to authorize sole-source, and at what dollar threshold?
3. **Council ratification** (if authorized by staff without council approval, due to emergency)
4. **Executed contract**
5. **Invoices and deliverables**

**Significant gap**: a sole-source award above the competitive bidding threshold with no documented justification.

### Land use decision (discretionary permit)

1. **Application** — filing by the applicant with required information
2. **Completeness determination** — agency finding that the application is complete
3. **Environmental review** — CEQA/NEPA analysis (may be extensive or an exemption finding)
4. **Notice of public hearing** — posted and mailed as required by law
5. **Staff report** — analysis and recommendation
6. **Public hearing record** — all testimony received (written and oral)
7. **Decision document** — the planning commission or council action
8. **Findings** — the written findings required by law to support the decision
9. **Conditions of approval** — any conditions attached to the approval
10. **Appeal period** — whether an appeal was filed
11. **Building permit** — subsequent ministerial approval to actually construct

**Significant gaps**:
- No environmental review or exemption finding → required but missing
- Decision document without required legal findings → potentially legally vulnerable
- No notice of public hearing in record → legally required; absence may invalidate the decision
- Long gap between application and completeness determination → may indicate a deliberate hold

### Budget adoption

1. **Department budget requests** — individual department submissions
2. **Executive budget proposal** — the manager's/mayor's recommended budget
3. **Budget hearings** — public process required before adoption
4. **Budget amendments** — council changes to the executive's proposal
5. **Adopted budget resolution** — the legal appropriation authority
6. **Mid-year budget adjustments** — amendments made during the fiscal year
7. **Quarterly financial reports** — actual vs. budget tracking
8. **Annual financial report (CAFR/ACFR)** — audited actuals

**Significant gaps**:
- No department budget requests in the record → process was not transparent
- Large variance between quarterly actuals and adopted budget → something significant changed during the year
- Missing CAFR → required filing obligation not met

---

## Gap classification

Not all gaps are equal. Classify each missing document:

**Expected gap** (normal part of the process):
- A building permit that hasn't been issued yet because the applicant hasn't applied
- Quarterly financials that aren't yet due
- A contract that's in negotiation and hasn't been executed yet

**Delayed gap** (may become significant if delay continues):
- A required annual audit that is 30 days past its due date
- Board minutes from a meeting that was held six weeks ago but haven't been approved
- Environmental review that was required before a decision but was promised "shortly after"

**Significant gap** (the absence itself is a finding):
- A competitive bidding process that should have occurred and left no documentation
- A public hearing notice that state law required but cannot be found in the record
- Annual financial reports that have not been filed for a period where the obligation exists
- A deliverable on a completed, paid contract that cannot be identified

**Deliberate gap** (potential obstruction or concealment):
- Documents that should exist but are specifically not responsive to a FOIA/public records request
- Emails about a decision that do not appear in a records response (absence from a comprehensive production)
- A decision that was made in closed session when the topic was not permissible for closed session

---

## Building the evidence chain in the artifact store

The artifact store's `derived_from` lineage system enables evidence chain construction programmatically:

**Forward traversal**: starting from a raw document (a council agenda, a contract PDF), trace all processed and analysis artifacts derived from it. If a summary artifact lacks information that appears in the raw document, the chain has lost information — the raw source should be consulted directly.

**Backward traversal**: starting from a claim in a beat brief or story draft, trace back through the lineage chain to the source document. The chain should terminate at a Tier 1 or Tier 2 primary source, not at another analysis artifact.

**Cross-artifact chain construction**: for a contract investigation, link:
- The raw agenda item (source: agenda PDF)
- The processed summary of the staff report (derived from the staff report)
- The entity extract identifying the contractor
- The award resolution (derived from the minutes)
- The contract document (separate artifact)

Any gap in this chain — a missing staff report, a contract not in the store — is a documentary gap that corresponds to a gap in the document trail.

---

## The gap detection algorithm (conceptual)

For any government action type, the expected document chain can be codified:

1. Define the expected chain for this action type (see above)
2. Query the artifact store for all artifacts with matching `event_group` or entity tags
3. Map existing artifacts to expected chain positions
4. Identify positions with no corresponding artifact
5. For each gap: classify as expected, delayed, or significant
6. Surface significant gaps as flag items

This algorithm can be run whenever a new document in a known chain arrives — checking whether the rest of the chain is in the store, and flagging what is missing.
