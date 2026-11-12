# Stance template

Copy this file to `.agents/skills/<project>-<stake>-stance/SKILL.md` and replace
every placeholder. Delete the guidance comments; a stance file is read by a
reviewer that must not have to distinguish instruction from example.

```markdown
---
name: <project>-<stake>-stance
description: >-
  Load only when assigned by a stance-review orchestrator. Argues <the
  objective> for <project> and tests whether a change protects it. Do not load
  for an ordinary task, even one touching <the surfaces this stance owns>; do
  not use for <the sibling concerns this stance routes away>.
disable-model-invocation: true
metadata:
  stance-axis: <the contended resource, e.g. correctness-vs-availability>
  opposes: <project>-<other-stake>-stance
---

# <Project> <stake> stance

<One paragraph: the objective in its strongest form, and why this project in
particular needs it. Name the failure this project would suffer without it.>

## Objective

<The single thing this stance maximizes. State it so that a reviewer can point
at a diff and say "this violates it" or "this serves it". No hedging, no
"balanced approach" language.>

## Accepts this harm

<The cost this stance knowingly imposes on the objectives it opposes. Be
specific: which sibling stance loses what, and how much. This section is what
makes the stance a stance, and it is the first thing the orchestrator reads
when deciding whether a reported conflict is real.>

## Attacks

<Four to eight failure modes, phrased as shapes that survive a rename of the
mechanism they protect. Prefer "a default that silently adopts an undeclared
value" over "unclear ownership", and prefer that over "`_entry_window` returns
the plan unchanged".

An attack naming a current function, constant, or line is a finding, not an
attack. If you saw an open violation while reading the code, it belongs in the
forge's delivery report, not in this file: a stance that already contains the
answer hands the reviewer a checklist and the pass then confirms the author
instead of testing the design.>

- <failure mode>
- <failure mode>

## Evidence to demand

<What a finding from this stance must include before it is accepted: a path and
line, a command that can be rerun, a test that fails, a measured number. A
finding that cannot supply this is a hypothesis, not a finding.>

## Does not own

<The concerns this stance deliberately does not judge, and the sibling stance
that owns each. This section is what keeps the set from collapsing into
duplicated review.>

- <concern> → <project>-<sibling>-stance

## Escalates when

<The conditions under which this stance refuses to compromise locally and
requires a user decision. These are the seeds of essential conflicts. Phrase
them as observable conditions, not as feelings.>

- <condition>

## Stable core and changing contract

The stable value is: **<the objective, one sentence>**. <Name the current
implementation — modules, flags, schemas, limits — and state that these are
contract expressions of the value, not the value itself. They may change when
evidence warrants it.>

When the contract changes, <what to compare, what to preserve, what to test>.
Do not defend a current shape merely because it is current; do reject any
change that makes <the objective> implicit or unverifiable.

## Good patterns

- <A pattern this project already uses that serves the objective, with
  evidence: a path, a test, a document section.>

## Bad patterns

- <A pattern this project has actually fallen into, **and has since fixed or
  decided**, with evidence. Cite the changelog entry, the decision record, or
  the commit that closed it.>

An open violation is not a bad pattern; it is a finding, and writing it here
removes the reviewer's job. A stance with only hypothetical bad patterns is not
grounded in this project, but one seeded with open defects is worse: it makes
the next pass look productive when it is only confirming what the author already
knew.

Patterns are evidence about how the objective is violated here. The contract
that the objective protects stays owned by <the owning document>.
```
