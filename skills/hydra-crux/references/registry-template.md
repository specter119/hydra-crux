# Registry template

Copy to `.agents/skills/<project>-stance-registry/SKILL.md`. The registry is the
single place that knows the whole set. Stances never restate it.

```markdown
---
name: <project>-stance-registry
description: >-
  Use to find which stance owns a question in <project>, which stances oppose
  each other, and which conflicts are still open. Read by the orchestrator
  before assigning a stance review or recording a resolution. Do not use as a
  review stance itself, and do not hand it to a reviewer.
---

# <Project> stance registry

The stances below are first-principles objectives, not checklists. They are
deliberately opposed: each one demands something another one pays for. A pass
that finds no conflict on a change touching a listed opposition should be
re-examined, but a clean pass is a possible outcome and not evidence of a
faulty review. Do not invent a conflict to satisfy the map.

This file is read by the orchestrator. Do not hand it to a reviewer: it names
the oppositions the orchestrator expects, and a reviewer that has read it will
find them. A registry in the project's own `.agents/skills/` is discoverable by
the model, so the brief must name the one stance file to read and nothing else.

Every path this file cites must survive a fresh clone; check each with the
version-control ignore query before writing it down.

## Stances

| Stance | Axis | Objective (one line) | Accepts |
| --- | --- | --- | --- |
| `<project>-<stake>-stance` | <resource> | <objective> | <the harm it imposes> |

## Oppositions

Each row is a pair that must be reviewed together. A pass that reviews only one
side of a row is not a stance review.

| Pair | Contended resource | Where these objectives are known to compete |
| --- | --- | --- |
| `<a>-stance` vs `<b>-stance` | <resource> | <the surface where they have competed so far> |

Describe where the pair has competed, not what the pass should find. A column of
predicted conflicts becomes a checklist the orchestrator feeds back into the
brief, and the pass then confirms the prediction instead of testing the design.

This table is the authority on the set's shape. Every pair here must appear in
both stances' `metadata.opposes`, every stance must be in at least one row, and
no stance may oppose more than two others. A stance that opposes three is a hub
and the other stances are its projections: a pass then needs only the hub and
one opponent to cover every conflict, and the rest are overhead. If a stake
genuinely contends with three others, split it or move one of the pairs to a
sibling that already shares that resource.

The axis name on a pair is written once, in the direction of the first stance
in the row. Both stances copy it verbatim into `metadata.stance-axis`; naming
the same pair `a-vs-b` in one file and `b-vs-a` in the other makes the two
files disagree about which direction is the objective and which is the cost.

A stance in several pairs carries one axis per pair, comma-separated in the
one `stance-axis` field: `stance-axis: correctness-vs-throughput,
reversibility-vs-integrity`. Do not repeat the key — duplicate keys are
invalid YAML — and do not name a new pair after the resource alone, which
would give the same pair two names.

## Contract surfaces

Decisions from a stance conflict land in these places. A resolution that
cannot name its file here is incomplete.

- <path> — <what decisions it holds>

## Resolved without escalation

Buffer-space merges that both stances accepted. Recorded so the next pass does
not relitigate them. A resolution here is not a compromise of the objectives;
it is a design that serves both.

| Conflict | Resolution | Serves | Evidence |
| --- | --- | --- | --- |
| <pair> | <what was built> | both | <test, benchmark, path> |

## Open essential conflicts

Conflicts waiting on a user decision. Each must follow the format in
[escalation.md](../../hydra-crux/references/escalation.md).

| Conflict | Pair | Status | Owner and next action | Decision record |
| --- | --- | --- | --- | --- |
| <id> | <pair> | open / decided | <who decides, and what they must do> | <path or pending> |

A row with no owner is the deferred conflict: the current design wins by default.

## Decisions that sacrificed a stance

When the user resolves an essential conflict, the losing stance is not deleted.
Record the sacrifice so the next reviewer sees the cost.

| Decision | Sacrificed stance | What was given up | Why |
| --- | --- | --- | --- |
| <decision record path> | `<stance>` | <the objective it lost> | <the user's reason> |

## Evidence

Proof that the set is alive. Not a log of every review — only passes that
changed something.

| Date | Pass | Conflict found | Effect on design or set |
| --- | --- | --- | --- |
| <date> | <scope> | <pair and crux> | <merged / escalated / stance edited / stance retired> |

## Unrepresented stakes

Objectives the project holds that no stance represents, and the reason each is
left out. This table is the set's own list of blind spots; a finding that lands
here is a missing stance, not a missing check.

| Stake | Evidence | Why no stance |
| --- | --- | --- |
| <objective> | `<path>#<section>` | <no opponent found / deliberately out of scope> |
```

## Registry rules

- The registry is the only file that lists every stance. A stance that is not
  in the table does not exist for reviewers.
- Every stance appears in at least one opposition row. An unopposed stance is
  removed or given its opposition.
- `Resolved without escalation` grows over time. That growth is the measure of
  whether the buffer space is being found rather than the tradeoff being
  surrendered.
- `Decisions that sacrificed a stance` is append-only. Deleting a sacrifice
  hides the cost of the current design.
- Keep the tables short. If a table needs more than a screen, the conflict has
  outgrown the registry and belongs in a decision record with a link here.
- `Unrepresented stakes` is read at every pass. A finding no stance could have
  made is evidence for a row here; a row that survives two passes is the set's
  known blind spot and belongs in the pass result.
