---
name: investigative-methodology
description: >-
  The systematic investigation mindset — hypothesis formulation, evidence
  gathering, document trail analysis, following the money, gap detection,
  and the standards for claiming a connection vs. a coincidence. Relevant
  when conducting or evaluating investigations that span multiple documents,
  sources, or time periods.
metadata:
  author: sidekick-pipeline
  version: "1.0"
  sources:
    - "Intro to Journalism (Michael Downing, 5th Ed.)"
    - "The Data Journalism Handbook (collaborative)"
---

## When this knowledge applies

When analyzing patterns across multiple documents or data points, when
assessing whether a connection between entities or events is documented
or speculative, when identifying gaps in the documentary record, or when
building an evidence chain from raw documents through to a demonstrable
finding.

## Domain knowledge

### The investigation mindset

Investigative journalism differs from event journalism in time horizon and
method. Event journalism documents what happened at a specific moment.
Investigative journalism asks: what is happening systematically, and can I
prove it with evidence?

Downing's investigative checklist framework: before claiming a finding,
a reporter must work through:
1. What is the hypothesis? (What are you trying to show or test?)
2. What evidence would confirm or refute it?
3. Where does that evidence live?
4. What is missing from the record, and why?
5. Have alternative explanations been considered and ruled out?

A finding is not an allegation. An allegation is what a source told you.
A finding is what the documents show, independently of what anyone said.

### Hypothesis formulation

Good investigative hypotheses are:
- **Specific**: "The city is awarding contracts to firms connected to elected
  officials" is testable. "There might be corruption" is not.
- **Falsifiable**: if the hypothesis is true, specific documents should exist;
  if false, they should not.
- **Grounded**: derived from a tip, an anomaly, or a pattern — not invented
  from nothing.

The hypothesis drives the document search. Without a clear hypothesis,
document collection is random and the analysis will not converge.

**The working hypothesis changes**: as evidence accumulates, revise the
hypothesis to reflect what the documents actually show. Committing to an
initial hypothesis against the evidence is confirmation bias, not investigation.

### Document trail methodology

Every government action leaves a document trail. The investigation is the
reconstruction of that trail:

**For a contract**: procurement notice → bids received (or sole-source
justification) → evaluation criteria → award resolution → executed contract
→ invoices and payments → amendments → final deliverable.

**For a land use decision**: pre-application meeting notes → formal application
→ environmental review → staff report → public hearing transcript → decision
document → appeal (if any) → any subsequent permits.

**For a budget decision**: department request → executive budget proposal →
budget hearings transcript → amendments → adopted budget → quarterly financial
reports → final actual expenditures.

Each link in the chain is a document. A gap in the chain — a missing invoice,
an undocumented amendment, a final deliverable that does not exist — is
a finding in itself.

### Following the money

The Data Journalism Handbook on "following the money" as a cross-border
investigation technique: financial flows connect decision-makers to
beneficiaries in ways that no single document fully reveals. The technique:

1. **Identify the public expenditure** (a contract award, a grant, a budget
   appropriation)
2. **Trace the recipient** (who received the money? What entity is it,
   ultimately? Who are its principals?)
3. **Identify the decision-makers** (who approved the expenditure? Who had
   influence over the decision?)
4. **Look for connections** (do the recipient's principals have relationships
   — financial, political, personal — with the decision-makers?)
5. **Document the connection** (a connection that exists only in inference
   is not a finding; it must appear in the record)

**The beneficial ownership problem**: contracts are awarded to legal entities,
but the economic benefit flows to natural persons. An LLC named "Springfield
Development Partners" may ultimately be owned by individuals with connections
to the approving officials. Beneficial ownership disclosure requirements vary
widely; this is a gap in the public record that is often significant.

### Gap detection as an investigation technique

The absence of expected records is as significant as the presence of unexpected
ones. Gaps in the documentary record can indicate:

- **Non-compliance**: a required document was never created (a bidding process
  that was legally required but never conducted)
- **Concealment**: a record that should exist has not been made available (an
  email chain about a decision, responsive to a FOIA request, that is missing)
- **Administrative failure**: a required reporting obligation was not met
  (a quarterly financial report not filed on time)
- **Implicit decision**: a decision was effectively made without a formal record
  (a policy implemented without a vote or a written directive)

**Method**: map the expected document chain for a given action or period.
Identify which documents exist and which are absent. For absent documents,
determine: was the document required? Did it exist and has it not been
disclosed? Or was the underlying action itself irregular (no bidding process,
hence no bid record)?

### Evidence chain standards

**What constitutes a documented connection** (publishable finding):
- A document explicitly links two entities in a relevant way
- Records from multiple independent sources corroborate the same connection
- A pattern of transactions is statistically improbable as random chance
- A named source with direct knowledge confirms the connection on the record

**What constitutes speculative inference** (not yet a finding):
- Timing alone: two events occurred close together in time
- Common social network: two people know each other through a third party
- Single-source allegation without documentary corroboration
- A pattern that is consistent with the hypothesis but has an equally
  plausible innocent explanation

The standard: would a reasonable person looking at this evidence, without
knowing the hypothesis, conclude that the connection is demonstrated? If
not, more documentation is needed.

### The European structural funds model

The Data Journalism Handbook describes a nine-month investigation into
European structural fund expenditures — a large-scale public finance
investigation conducted across multiple countries and data sources. The
methodology:

1. Identify a large government financial program with public data
2. Download the complete expenditure dataset
3. Identify anomalies in the data (unusual recipients, unusual amounts,
   unusual patterns compared to baseline expectations)
4. Cross-reference recipients against other databases (business registries,
   ownership records, political disclosure)
5. Narrow to the most significant anomalies with cross-reference confirmation
6. Document the trail for selected cases through underlying procurement and
   approval records

The scale is different for local government, but the methodology is the same:
start with the data, find anomalies, cross-reference, document. The local
government equivalent: contract expenditure data → anomalous recipients →
ownership research → procurement records → approval records.

### Alternate explanations

A core discipline of investigative methodology is actively seeking
explanations that would refute the hypothesis. Before publishing a finding:

- What is the innocent explanation for this pattern?
- Have all the parties involved been given an opportunity to explain?
- Does the documentary evidence exclude the innocent explanation, or only
  make it less likely?
- Is this pattern specific to the entities under investigation, or is it
  common practice across similar agencies?

A finding that survives rigorous alternate-explanation testing is much stronger
than one that has not been tested.

## Gotchas

**Tips are starting points, not findings.** A source's allegation points
toward evidence to look for; it does not substitute for that evidence.
Treat tips as hypotheses, not conclusions.

**A relationship is not a conflict of interest.** People in the same
community know each other. A contractor who played golf with a council member
once is not a finding. The question is whether the relationship created an
actual advantage in a specific transaction — and that must be documented.

**Pattern significance requires a comparison baseline.** "This firm received
10 sole-source awards" is only meaningful against: how many sole-source
awards were issued in total? To how many firms? Over what period? Without
the baseline, the pattern has no scale.

**Access to records ≠ analysis of records.** Obtaining documents is the
beginning, not the conclusion. A FOIA response may contain the relevant
document or it may require locating a needle in a very large haystack.

See [references/follow-the-money-guide.md](references/follow-the-money-guide.md)
for a structured methodology for tracing financial flows from public expenditure
to ultimate beneficiary.

See [references/document-trail-methodology.md](references/document-trail-methodology.md)
for building evidence chains and detecting significant gaps in the record.
