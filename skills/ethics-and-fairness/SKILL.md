---
name: ethics-and-fairness
description: >-
  The four core journalistic principles — accuracy, fairness, independence,
  accountability — what minimizing harm means in local reporting, conflict-
  of-interest indicators, balanced framing, and the public interest test.
  Relevant when evaluating whether coverage decisions reflect ethical practice.
metadata:
  author: sidekick-pipeline
  version: "1.0"
  sources:
    - "Handbook of Independent Journalism (Deborah Potter)"
    - "Intro to Journalism (Michael Downing, 5th Ed.)"
---

## When this knowledge applies

When assessing whether a coverage decision, a story framing, or an analytical
judgment reflects ethical journalistic practice. When an entity being covered
is a private individual (vs. a public official). When a potential story
involves harm to specific people. When assessing whether coverage is fair to
all significant parties.

## Domain knowledge

### The four core principles

Potter's ethical framework for journalism rests on four principles that
sometimes conflict with each other and require judgment to balance:

**Accuracy**: the commitment to getting it right. Every factual claim should
be verifiable. Errors undermine credibility — and credibility is the asset
that makes journalism valuable. Accuracy extends beyond facts to include
fairness of tone and framing: a story can be factually accurate but convey
a misleading impression.

**Fairness**: giving all significant parties an opportunity to respond, and
representing their positions proportionally. Fairness does not mean false
equivalence — giving equal weight to a well-documented finding and an
unsupported denial is not fair to readers. Fairness means ensuring that the
positions of all parties with legitimate stakes are represented with fidelity
to what they actually said and meant.

**Independence**: maintaining freedom from the influence of those being covered.
A journalist (or reporting system) that acts as a mouthpiece for a government
agency fails in its accountability function. Independence means following
evidence wherever it leads, even when the conclusion is inconvenient for
powerful entities.

**Accountability**: the obligation to hold power responsible. Local government
accountability journalism is the primary check on decisions made with public
money and public authority. This principle is the reason this pipeline exists.

### Minimizing harm

The public interest in disclosure must be weighed against the potential harm
to individuals. Potter's framework for harm minimization:

**Public officials in their official capacity**: the public interest in
accountability for their official actions is high. The right to privacy is
correspondingly lower. A council member's vote, a department head's contract
recommendation, and an agency's expenditures are legitimate subjects of
public scrutiny.

**Private individuals who appear in public proceedings**: a member of the
public who testifies at a hearing, a property owner whose parcel is the subject
of a zoning decision, a business owner who is a contract recipient. Their
involvement in public proceedings is legitimately reportable; their private
lives are not.

**Vulnerable populations**: children, crime victims, individuals in mental
health or substance abuse situations appearing in public records — the public
interest in the information must be weighed against the harm of identification.
For minors: strong presumption against naming. For crime victims: specific
circumstances and the nature of the crime matter.

**The proportionality test**: is the potential harm to the individual
proportional to the public benefit of the disclosure? A sole-source contract
to a council member's relative is significant public interest; naming that
relative's personal address in the story is not.

### Conflict of interest

Conflicts of interest in journalistic or analytical work arise when:
- A financial interest of the analyst/reporter aligns with a particular
  conclusion about the subject being covered
- A personal relationship with a source or subject creates pressure toward
  a favorable or unfavorable characterization
- An institutional interest (advertiser, funder, political ally) creates
  pressure to avoid or favor certain coverage

Downing: conflicts are obvious (an editor who owns stock in a company being
covered) and less obvious (a reporter who has a personal friendship with a
source; a publication that relies on a major advertiser who is the subject
of negative coverage).

For an automated pipeline, the relevant analog: are the agents' training
and prompting creating systematic biases toward or against particular entity
types, ideological positions, or institutional interests? Independence requires
examining not just individual decisions but systematic patterns.

### Balanced framing

Fairness requires that coverage represent all significant viewpoints
proportionally. What "proportionally" means:

**Not mechanical equality**: giving a fringe position the same prominence as
a well-documented consensus is misleading, not balanced. A unanimous scientific
finding and a single dissenter do not deserve equal treatment. A staff
recommendation supported by extensive analysis and a council member's personal
opinion that contradicts it are not equally authoritative.

**Proportional representation**: significant stakeholder positions should be
represented. A zoning story that quotes only the developer, not affected
neighbors, is unbalanced. A budget story that presents only the administration's
perspective, without the alternatives the council considered, is incomplete.

**All affected parties**: in local government coverage, "all parties" typically
includes: the decision-making body, staff, applicants or affected entities,
public commenters representing organized positions, and — when available —
independent experts who can provide context the parties themselves cannot.

### The public interest test

When disclosure of information may cause harm, apply the public interest test:

1. **Is the information newsworthy?** Does it satisfy news value criteria
   that would justify public attention?
2. **Does the public have a right to know?** Government action conducted in
   the public's name, with public money, at public meetings is presumptively
   subject to public scrutiny.
3. **Is disclosure proportional?** Is the extent of disclosure proportional
   to the public interest? A contract recipient's name and the amount are
   proportional; their home address is not.
4. **Is the harm unavoidable?** Could the story be told with the same public
   interest value while causing less harm?
5. **Are there other obligations?** Legal requirements (court-ordered sealing,
   statutory confidentiality), not just ethical preferences.

### Accountability coverage and fairness

Accountability journalism — investigating potential wrongdoing or failure by
public officials — requires the highest commitment to fairness precisely because
the stakes for the individuals covered are high.

**The right of response**: before publishing an investigation that reflects
negatively on a specific person or institution, that person or institution
should have a meaningful opportunity to respond. Not a pro forma question at
the last minute — a genuine opportunity to review the specific allegations and
provide their account.

**Separating findings from characterizations**: a finding (the contract was
awarded without competitive bidding) is a factual claim. A characterization
(the award was corrupt) is an interpretation that requires a higher evidentiary
standard. Report findings; draw characterizations only when the evidence
clearly supports them.

**The presumption of explanation**: unusual or anomalous actions often have
explanations. An emergency contract that appears irregular may have been
genuinely urgent. A sole-source award may reflect a legitimate vendor
relationship. The investigation should exhaust reasonable explanations before
concluding that something improper occurred.

## Gotchas

**Accuracy and fairness can conflict.** A story that is factually accurate
about one party's position while omitting another party's accurate response
may be technically accurate but unfair. Fairness requires actively seeking
out the positions of all significant parties, not just recording the loudest voice.

**Naming private individuals who appear in public records.** The fact that
a person's name appears in a public document does not automatically mean
the name should be published. A crime victim's name in a police report may
be public record; publishing it may cause harm disproportionate to the public
interest. Judgment is required.

**Independence requires process, not just outcome.** A story that reaches
the right conclusion through a compromised process — ignoring contrary
evidence, accepting a self-interested source uncritically — is not ethically
sound even if the conclusion happens to be correct.

See [references/ethical-principles-reference.md](references/ethical-principles-reference.md)
for extended treatment of each principle with local government examples.

See [references/harm-minimization-checklist.md](references/harm-minimization-checklist.md)
for a decision framework for including or excluding identifying information.
