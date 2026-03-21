# Entity Taxonomy: Local Government Coverage

Full hierarchy of entity types encountered in local government document corpora, with role subtypes and significance indicators for each.

---

## Person

### Elected officials

Officials who hold their positions by virtue of a public vote. Their actions are on the public record; accountability is high.

| Subtype | Examples | Tracking notes |
|---|---|---|
| **Mayor / Chair / President** | City mayor, county board chair, school board president | Sets agenda; casting vote in ties; typically has veto authority |
| **Council / Board member** | City council member, county supervisor, school board trustee | Vote on every item; attendance and voting pattern are trackable |
| **Elected department head** | Sheriff, assessor, district attorney, superintendent (elected) | Runs a department independently of council; has own budget authority |

**Key tracking**: vote record by item type; attendance rate; motions initiated; campaign finance connections.

### Appointed officials

Officials who serve at the pleasure of an elected body or executive. Professional rather than political orientation.

| Subtype | Examples | Tracking notes |
|---|---|---|
| **Manager / Administrator** | City manager, county administrator | Runs day-to-day operations; recommends budget; hires department heads |
| **City / County Attorney** | Varies by jurisdiction | Advises the body; represents the agency; authorized to settle litigation |
| **Clerk** | City clerk, board clerk | Maintains official records; administers elections; produces minutes |
| **Department director** | Finance director, planning director, police chief, fire chief | Heads a major operational department |

**Key tracking**: tenure; prior positions; relationship to appointing body; recommendations vs. decisions.

### Staff

Professional employees of the agency. Typically appear as authors of staff reports, presenters at meetings, or signatories on correspondence.

| Subtype | Examples | Tracking notes |
|---|---|---|
| **Planner / analyst** | Associate planner, budget analyst | Prepares staff reports; may testify at hearings |
| **Engineer / technical expert** | Civil engineer, environmental consultant | Technical signatory on public works and environmental items |
| **Inspector / enforcement** | Building inspector, code enforcement officer | Appears in permit and violation records |

**Key tracking**: consistency of technical conclusions; recurrence on similar project types; potential relationships with applicants.

### Applicants and petitioners

People or entities seeking something from the government body. Have a direct stake in the outcome.

| Subtype | Examples | Tracking notes |
|---|---|---|
| **Developer / property owner** | Individual or entity seeking a permit, entitlement, or variance | Prior applications before this and other bodies; ownership structure |
| **Business owner** | License or permit applicant | Prior licensing history; corporate structure |
| **Resident / petitioner** | Individual seeking a variance, appeal, or exception | May represent a neighborhood group |

### Public commenters

People who participate in public comment. Not decision-makers; their appearances signal organized positions or community sentiment.

| Subtype | Examples | Tracking notes |
|---|---|---|
| **Organized advocate** | Neighborhood association representative, housing advocacy group | Recurring; position is predictable and attributable |
| **Lobbyist / paid advocate** | Registered lobbyist appearing for a client | Disclosure required in many jurisdictions; client relationship matters |
| **Individual resident** | Unaffiliated member of the public | Less predictable; significant when many appear on one item |

### Contractors and vendors

Companies or individuals receiving public money through a contract for goods or services.

| Subtype | Examples | Tracking notes |
|---|---|---|
| **Professional services firm** | Engineering firm, law firm, planning consultant | May hold multiple simultaneous contracts |
| **Construction contractor** | General contractor, subcontractor | Licensing; bonding; prior government projects |
| **Technology vendor** | Software, hardware, IT services | Recurring multi-year contracts common |

**Key tracking**: total contract value across all contracts; sole-source awards; prior work history; principal names (who are the owners?).

---

## Organization

### Government bodies

The decision-making entities. Their actions are the core subject of local government coverage.

| Subtype | Examples |
|---|---|
| **Legislative body** | City council, county board of supervisors, school board, special district board |
| **Advisory commission** | Planning commission, design review board, environmental commission |
| **Joint powers authority** | Multi-agency body formed for a specific purpose (transit, water, fire) |
| **State agency** | Acts on local matters (permits, grants, environmental review) |

### Government agencies and departments

The implementing arm of the government body. Produces documents; prepares recommendations; executes decisions.

| Subtype | Examples |
|---|---|
| **Planning / Community development** | Land use applications, environmental review, building permits |
| **Finance / Budget** | Budget documents, financial reports, contract processing |
| **Public works / Engineering** | Infrastructure projects, maintenance contracts, capital plans |
| **Public safety** | Police, fire, emergency services |
| **Human services / Social services** | Housing assistance, public health, social programs |

### Private-sector organizations

| Subtype | Examples | Tracking notes |
|---|---|
| **Developer / Builder** | Real estate development company | Track across planning, zoning, and council items |
| **Engineering / Planning firm** | Consulting firm contracted for services | May appear as both a consultant and an applicant |
| **Law firm** | Representing applicants or bidding on city attorney work | Connections to elected officials' campaigns |
| **Financial institution** | Bond underwriter, lender on public financing | Appears in debt and finance documents |

### Nonprofits

May receive public funding, use public facilities, or advocate on policy issues.

| Subtype | Examples | Tracking notes |
|---|---|
| **Social services nonprofit** | Receives city grants; runs programs on city contract | Grant history; leadership connections to officials |
| **Advocacy organization** | Appears in public comment; may fund campaigns | Position and interest are declarable |
| **Foundation** | May make grants to city programs or fund studies | Funder relationships |

---

## Place

| Type | Examples | Tracking notes |
|---|---|
| **Parcel / Address** | 123 Main St., APN 0123-456-789 | The specific property in a land use decision; ties to ownership records |
| **Neighborhood / District** | Downtown, Westside, Council District 4 | Affected community area; demographic context |
| **Facility** | Roosevelt Elementary, Central Park, Library Branch 3 | Subject of capital projects, service decisions, closures |
| **Corridor / Right-of-way** | Main Street corridor, I-10 frontage road | Infrastructure and transportation planning |
| **Jurisdiction** | City of Springfield, Springfield Unified School District | The governing area; boundary matters for permit and service questions |

---

## Document entities

Documents referenced within other documents are themselves trackable entities. A reference to a prior ordinance in a current staff report means the prior ordinance is being implemented, amended, or relied upon.

| Type | Examples | Tracking notes |
|---|---|
| **Ordinance** | Ordinance 2026-14 | Has a number, an effective date, and a subject; may be amended by later ordinances |
| **Resolution** | Resolution 2026-07 | Expresses intent or approves an action; formally numbered |
| **Contract** | Contract No. 2026-112 | Parties, amount, term; may be amended |
| **Report** | 2026 Annual Audit, FY2027 Budget Proposal | Produced by staff or consultant; informational |
| **Application** | Planning Application PA2026-019 | The formal filing for a permit or entitlement; has a case number and a history |
| **Grant** | CDBG Round 2026-A | Federal or state funding award; amount, purpose, conditions |
