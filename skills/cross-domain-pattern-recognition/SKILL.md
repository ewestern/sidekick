---
name: cross-domain-pattern-recognition
description: >-
  What non-obvious connections look like across beats, jurisdictions, and
  time periods — thematic clustering, entity cross-referencing, systemic
  patterns, and the distinction between a genuine connection and a coincidence.
  Relevant when analyzing whether separate developments share an underlying
  pattern.
metadata:
  author: sidekick-pipeline
  version: "1.0"
  sources:
    - "The Data Journalism Handbook (collaborative)"
---

## When this knowledge applies

When analyzing whether separate developments across different beats,
jurisdictions, or document types share an underlying pattern. When an entity
appearing in an unexpected context is a signal worth investigating. When
thematic similarity across otherwise unconnected stories suggests a systemic
issue.

## Domain knowledge

### Why cross-domain patterns matter

A beat reporter covering city council sees one set of facts. A reporter
covering the school board sees another. A reporter covering the budget sees
a third. No single reporter sees the full picture. Patterns that span these
domains — a developer active in zoning who also appears in the budget as a
vendor, or budget cuts that hit the same departments simultaneously across
multiple neighboring jurisdictions — are invisible to any single-beat view.

The Data Journalism Handbook documents multiple investigations that were
possible only because data from multiple jurisdictions or domains was
combined: European structural funds spent across member states, UK riots
analyzed across police force boundaries, cross-border money flows invisible
to any single national regulator.

The same principle applies at the local level. A local government pipeline
that covers multiple beats and accumulates a longitudinal record is positioned
to see these patterns — if it looks for them.

### Types of cross-domain patterns

**Entity cross-beat appearance**

An entity (person, organization, property) appears in more than one coverage
domain simultaneously or in sequence. Significance depends on whether the
appearance is expected or unexpected.

- *Expected*: the city attorney appears in contract approvals and litigation
  settlements — both are legal matters
- *Unexpected*: a developer who primarily operates in the planning/zoning
  domain appears as a recipient of an economic development grant from the
  city council; the same developer's principals appear as campaign contributors
  to the approving council members

Detection: entity registry cross-referenced against beat tags on artifacts.

**Thematic clustering**

Separate events in different domains share a common underlying theme —
even when their surface subjects differ.

- Budget cuts to the parks department, school closures, and library hour
  reductions all reflect a shared theme: reduced public services in a
  specific neighborhood
- Three separate sole-source contract awards in different departments all
  awarded to firms with connections to the same consultant
- Multiple agenda items across several months all advance a single
  developer's project incrementally (entitlement, development agreement,
  tax abatement, naming rights)

Detection: semantic similarity across beat-brief and summary artifacts;
recurring entity appearances; topic clustering.

**Policy diffusion across jurisdictions**

A policy change in one jurisdiction is adopted in neighboring jurisdictions
in a compressed time period. May reflect:
- Coordinated advocacy by a shared interest group
- State-level mandate being implemented simultaneously
- Network effects among local officials (what worked in City A is being
  tried in City B)
- A shared financial pressure producing similar responses

Detection: same topic/content-type artifacts appearing across multiple geo
tags within a similar time window.

**Temporal clustering**

Events that seem unrelated are concentrated in time in a way that suggests
a common trigger.

- Multiple resignations from the same city department within three months
- Multiple contract amendments (from the same or different contractors)
  concentrated around a budget review period
- Multiple permit applications for the same block or corridor filed within
  a short period

Detection: event_group or topic clustering by time period across artifacts.

**Reversal patterns**

A policy, decision, or commitment is reversed — and the reversal follows the
arrival of a new actor, a new funding source, or a new administration.

- A planning moratorium lifted when a new council majority is seated
- A contract that was previously rejected approved after a change in the
  department director
- Environmental review exemptions granted for a project type that previously
  required full review

Detection: artifact lineage showing a prior decision being amended or
rescinded; entity tracking around the timing of the reversal.

### The connection vs. coincidence standard

Not every cross-domain co-appearance is significant. Apply this framework:

**Coincidence**: two events share a common feature (timing, entity, topic)
by chance. No mechanism connects them beyond the shared feature.

**Correlation**: two events co-occur more frequently than would be expected
by chance. Requires a comparison baseline to assess ("is this entity appearing
across beats more frequently than comparable entities?").

**Connection**: a documented mechanism explains why the events co-occur. A
campaign contribution before a contract award; a shared ownership structure
between a development company and a city vendor; a lobbying relationship
that predates a policy change.

**Investigation trigger**: a cross-domain pattern rises to the level of
investigation trigger when:
- It repeats more than twice across independent instances
- The co-occurring entities have an independently documented relationship
- The timing alignment is too precise to be explained by general trends
- An alternative explanation would require more coincidences than the
  connection explanation

### The Mapa76 and UK riots methodology

The Data Journalism Handbook documents two cases of algorithmic pattern
detection across large corpora:

**Mapa76** (Argentina): entity extraction from large volumes of documents
(names, dates, places) produced a network graph of relationships invisible
in any individual document. The same technique applied to a local government
document corpus reveals networks of relationships — between developers and
officials, between contractors and council members, between policy changes
and their beneficiaries — that no individual meeting or document would expose.

**UK riots analysis**: analyzing police data across multiple force boundaries
revealed patterns about where riots spread and what factors predicted
escalation — patterns that were invisible within any single force's dataset.
The cross-boundary aggregation was the analytical breakthrough.

Both cases illustrate the same principle: the analytical value lies not in
any individual data point but in the relationships that emerge when data
points are combined across domains.

### Distinguishing signal from noise

Cross-domain analysis generates false positives. Filters that improve
precision:

- **Entity specificity**: a very common entity (a major law firm that represents
  many clients before the city) appearing across beats is less significant than
  a specific entity (a small LLC with one principal) appearing across beats
- **Unexpectedness**: the pattern is significant only if the cross-domain
  appearance is unexpected given what is known about the entity's normal
  role
- **Recurrence**: one cross-domain co-appearance may be coincidence; three is
  a pattern
- **Proximity to decision moments**: cross-domain appearances that cluster
  around specific decisions (budget adoption, major contract awards, policy
  changes) are more significant than distributed appearances

## Gotchas

**Correlation is not the story; it is the beginning of the investigation.**
A pattern is a hypothesis, not a finding. Cross-domain pattern detection
points toward documents to obtain, sources to interview, and chains to trace.
It does not substitute for those steps.

**Large entities appear everywhere.** The city's largest engineering firm will
appear in public works, planning, capital projects, and possibly city council
items. This is not a pattern — it is the consequence of being a dominant
vendor. The signal is when an entity appears where it would not normally be
expected.

**Time alignment needs a baseline.** "These events happened in the same
month" is significant only if similar events in prior months did not also
co-occur. Establish what the base rate of co-occurrence is before treating
a specific instance as anomalous.

See [references/cross-domain-investigation-patterns.md](references/cross-domain-investigation-patterns.md)
for a catalog of common cross-beat patterns worth flagging, with examples
from local government coverage.
