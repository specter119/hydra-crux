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
find them.

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

| Conflict | Pair | Status | Decision record |
| --- | --- | --- | --- |
| <id> | <pair> | open / decided | <path or pending> |

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
