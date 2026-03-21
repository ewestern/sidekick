---
name: entity-and-actor-tracking
description: >-
  Entity taxonomy for local government coverage — people, organizations, places,
  and documents — and the significance of recurring entity appearances across
  time and across coverage domains. Relevant when extracting, classifying, or
  assessing the significance of named entities in government documents.
metadata:
  author: sidekick-pipeline
  version: "1.0"
  sources:
    - "Handbook of Independent Journalism (Deborah Potter)"
    - "The Data Journalism Handbook (collaborative)"
---

## When this knowledge applies

When identifying, classifying, or reasoning about the people, organizations,
places, and documents that appear in government records. Also relevant when
assessing whether an entity's appearance in a new context is significant.

## Domain knowledge

### Entity taxonomy for local government

Local government coverage involves a specific set of entity types, each with
subtypes that carry different significance:

**Person**
- *Elected official*: council member, mayor, board trustee, superintendent —
  votes on record; public accountability is high
- *Appointed official*: city manager, city attorney, department director —
  serves at the pleasure of elected body; professional not political
- *Staff*: planners, engineers, analysts — often the substantive experts;
  appears in reports and presentations
- *Applicant/petitioner*: developer, business owner, individual seeking a
  permit — has a stake in the outcome
- *Public commenter*: resident, advocate, lobbyist — appears in public comment
  records; not a decision-maker
- *Contractor/vendor*: company or individual receiving public money through
  a contract

**Organization**
- *Government body*: city council, planning commission, school board, special
  district — the decision-making entity
- *Government agency/department*: public works, planning, finance — implements
  decisions; produces reports
- *Developer/builder*: may appear across planning, zoning, and council records
- *Nonprofit*: may receive public funding or use public facilities
- *Business/employer*: may be subject to regulation or recipient of incentives
- *Advocacy group*: appears in public comment; has a declared interest

**Place**
- *Parcel/address*: the specific property involved in a land use decision
- *Neighborhood/district*: the affected community area
- *Facility*: school, park, library, public building — often the subject of
  capital expenditures or service decisions
- *Jurisdiction*: the governing area (city, county, district boundary)

**Document**
- *Ordinance*: a law enacted by the governing body; has a number and takes
  effect on a date
- *Resolution*: a formal decision that is not a law; expresses intent or
  approves an action
- *Contract*: a binding agreement; specifies parties, amount, and term
- *Report*: produced by staff or a consultant; informational, not binding
- *Agenda item*: a matter before the body; becomes significant when acted upon

### Why recurring entities matter

Beat reporting requires understanding not just individual events but the
patterns they form over time. An entity appearing once is a fact; an entity
appearing repeatedly across different contexts is a signal.

Potter on beat reporting: the fundamental skill is "understanding the systems
and the people" who run them. A beat reporter builds an entity registry —
an ongoing record of who the key players are and how they appear in decisions.

Patterns worth tracking:
- A developer who appears on multiple planning and zoning applications
- A council member who consistently votes one way on a class of items
- A contractor who holds multiple city contracts simultaneously
- A nonprofit that receives city funding and whose leadership overlaps with
  a political campaign
- A property address that has appeared in multiple permit applications,
  violations, or disputes

### Longitudinal tracking: routine vs. significant

Not all recurring appearances are significant. The planning director
appears in every staff report — that is routine. What is significant:

- An entity appears in an *unexpected* context (a contractor who usually bids
  on public works appearing in a planning application)
- An entity's status changes (an applicant who was previously denied now
  returns with a new application)
- An entity appears across *multiple beats* (a developer in zoning, budget,
  and city council items simultaneously)
- An entity that was present disappears from the record (a contractor
  previously awarded work stops appearing in contract records)

### The Mapa76 principle

The Mapa76 project (Data Journalism Handbook Ch. 28) demonstrated that
systematic entity extraction from large document corpora — names, dates,
places — reveals patterns invisible in any individual document. The same
technique applied to a local government document corpus reveals networks
of relationships that no single meeting, report, or ordinance would expose.

The entity registry is not just metadata — it is the accumulated analytical
memory of the beat.

## Gotchas

**Same name ≠ same person.** Common names appear in multiple contexts.
"John Smith" in a planning application and "John Smith" in a council vote
are not necessarily the same individual. Context (title, role, address) is
needed to confirm identity.

**Organization names change.** A developer may operate under multiple LLCs
for different projects. The beneficial ownership may be the same entity
even when the registered name differs. Tracking addresses, principals, and
agent names helps.

**Role matters more than name.** The city attorney changes over time but
"city attorney" is a consistent entity. Tracking by role ensures continuity
even through personnel changes.

**Document references are entities too.** Ordinance 2026-14, Resolution
2026-07, Contract No. 2026-112 — these are entities with their own
significance. An ordinance referenced in a later item is being amended,
implemented, or challenged.

See [references/entity-taxonomy.md](references/entity-taxonomy.md) for the
full entity type hierarchy with role subtypes.

See [references/longitudinal-tracking-patterns.md](references/longitudinal-tracking-patterns.md)
for patterns that indicate significant entity recurrence.
