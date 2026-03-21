# Longitudinal Tracking Patterns

Patterns that indicate significant entity recurrence — when an entity appearing in a new context is a signal worth noting rather than routine.

---

## The baseline problem

Most entity appearances are routine. The planning director appears in every staff report. The city attorney appears in every contract. The city's top engineering firm appears in every public works project. These are not signals — they are the background against which signals are detected.

The question is not "does this entity appear?" but "does this entity appear in a context that is unexpected, anomalous, or newly significant?"

---

## Patterns indicating significant recurrence

### Pattern 1: Cross-beat appearance

An entity that normally appears in one domain appears in another.

**Examples**:
- A developer who has multiple housing projects before the planning commission also appears on the city council agenda for a tax rebate
- A police department captain named in a personnel matter also appears as a bidder on a police services contract via a private security firm they now manage
- A nonprofit that receives city social services funding also appears as a lessor in a city property transaction

**Why it matters**: cross-beat appearances may indicate relationships that no single beat reporter would see. The planning reporter sees the developer's zoning cases; the city hall reporter sees the tax rebate; the business reporter sees the economic development grant. Only by tracking the entity across all three does the pattern emerge.

**Detection threshold**: one cross-beat appearance is interesting; two or more is a signal worth flagging.

### Pattern 2: Status change

An entity whose relationship to the government body changes significantly.

**Examples**:
- An applicant who was previously denied returns with a new application (especially if circumstances changed)
- A contractor who was found in breach of contract reappears as a bidder on a new project
- An organization that lost public funding reappears seeking a new grant under a slightly different name
- An elected official who voted against a development project later appears as a supporter of related legislation

**Why it matters**: status changes often reflect underlying processes (appeals, name changes, changed political relationships) that a single document will not fully explain.

### Pattern 3: Disappearance from the record

An entity that was previously prominent stops appearing in the record.

**Examples**:
- A contractor who held multiple city contracts stops appearing in award notices
- A firm that was the city's exclusive provider on a service type stops being referenced
- A consultant who authored multiple staff reports stops being cited
- An advocacy organization that appeared regularly in public comment stops attending

**Why it matters**: disappearances can indicate: a contract was terminated (for cause or by end of term); a relationship ended under circumstances not publicly disclosed; the entity changed its structure; or the role was brought in-house.

**Caution**: disappearances may be benign. Contracts end; firms close; advocates move on. The pattern is a question trigger, not a conclusion.

### Pattern 4: Rapid accumulation

An entity accumulates relationships with the government body in a compressed time period.

**Examples**:
- A firm receives three separate no-bid contract awards in one fiscal year
- A developer files four planning applications within a six-month period in different parts of the city
- A council member sponsors six ordinances in a single session, after introducing none in prior terms

**Why it matters**: rapid accumulation may reflect a policy change that is opening doors (new zoning rules, a new administration's relationships), or it may reflect preferential treatment. Either explanation is worth documenting.

### Pattern 5: Multi-document entity appearance (same event, multiple documents)

An entity appears in multiple documents about the same underlying matter.

**Examples**:
- The same developer appears in the staff report, the environmental review, the contract for site preparation work, and the development agreement — all for the same project
- The same law firm appears as the applicant's legal representative, as the author of the project description, and as the party that filed the public comment response
- The same nonprofit appears as the grant recipient, the lessee of city property, and the operator of a city-funded program

**Why it matters**: multi-document appearances reveal the scope of an entity's involvement in a matter. Disclosing only one layer of the relationship can create a misleading picture of arm's-length transactions.

### Pattern 6: Timing alignment

An entity's appearances cluster in time in a way that corresponds to external events.

**Examples**:
- A developer submits a major application shortly after a campaign contribution to council members who will vote on it
- A contractor's contract awards increase following a change in city administration
- A nonprofit's grant funding increases following the appointment of its board member to a city commission

**Why it matters**: timing alignment is not proof of a connection, but it is an investigation trigger. The proper response is to note the timing and seek independent corroboration before drawing conclusions.

---

## Routine recurrence vs. significant recurrence: decision rules

| Observation | Likely routine | Likely significant |
|---|---|---|
| Same entity appears in same role in same document type | City attorney in every contract | City attorney's private firm receiving contracts from the city |
| Same entity appears in same beat, different documents | Engineering firm in sequential public works projects | Engineering firm in public works + planning applications it consulted on |
| Same entity appears across multiple beats | — (always investigate) | Developer in housing, budget, and city council items |
| Entity's relationship status changes | Staff author left the city; new author | Denied applicant returns after council composition changes |
| Entity disappears | Contract term ended as scheduled | Contractor disappears after a contested council vote |
| Entity accumulates relationships quickly | Firm wins second contract in same program | Firm wins three no-bid awards in one fiscal year |

---

## Tracking infrastructure

For effective longitudinal tracking, maintain a persistent entity registry with:

- **Canonical name**: primary reference name used for deduplication
- **Aliases**: known alternative names (DBAs, abbreviations, predecessor names)
- **Role history**: each role the entity has appeared in, with document references
- **Relationship history**: each government body the entity has engaged with
- **First appearance date**: when the entity entered the record
- **Notable flags**: any cross-beat appearances, status changes, or anomalous patterns

The entity registry is the accumulated analytical memory of the beat — the difference between a one-time document processor and a beat reporter who has been on the city hall beat for years.
