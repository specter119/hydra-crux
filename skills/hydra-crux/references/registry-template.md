# Registry template

The registry is generated from `.agents/review-graph.toml`:

```sh
HYDRA="${HYDRA_CRUX_SKILL:-$HOME/.agents/skills/hydra-crux}"

python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml generate \
  --out .agents/skills --docs-out docs
```

Do not hand-edit the generated registry. Edit the graph, then regenerate. The
template below shows the shape the generator produces; it is not a second source
of truth.

`docs/stances.md` is generated too. Its links are computed from `--docs-out` to
`--out`, so they resolve from the directory where the map is written. Do not
replace it with a hand-written guide; put narrative in `AGENTS.md` and link to
the generated map.

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
that finds no conflict must name the axes it checked and why the design already
satisfies them. Do not invent a conflict to satisfy the map.

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
both stances' `metadata.opposes`, and every stance must be in at least one row.
A stance may participate in several axes. A stance that opposes many others is a
hub worth examining, not a hard error: either it is one objective that several
surfaces contend, or it is several objectives that should be split.

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

| Conflict | Pair | Status | Owner and next action | Reopen when | Decision record |
| --- | --- | --- | --- | --- | --- |
| <id> | <pair> | open / decided / measured | <who decides, and what they must do> | <the evidence that reopens it> | <path or pending> |

A row with no owner is the deferred conflict: the current design wins by default.

## Decisions that sacrificed a stance

When the user resolves an essential conflict, the losing stance is not deleted.
Record the sacrifice so the next reviewer sees the cost.

| Decision | Sacrificed stance | What was given up | Status | Owner document | Reopen when | Why |
| --- | --- | --- | --- | --- | --- | --- |
| <decision> | `<stance>` | <the objective it lost> | decided / implemented / verified | <path> | <condition> | <the user's reason> |

## Evidence

Proof that the set is alive. Not a log of every review — only `record` passes
that changed something. A `survey` or `draft` pass does not appear here. The
review doc links to the row by `date` + `pass`; the graph row also carries the
optional `doc` and `skipped` fields, which this navigation table does not show.

| Date | Pass | Conflict found | Effect on design or set |
| --- | --- | --- | --- |
| <date> | <scope> | <pair and crux> | <merged / escalated / stance edited / stance retired> |

## Counterexamples harvested

Project-specific instances the pass caught. The `Pattern` column is a short
name, not the full prose; the general library is
[counterexamples.md](counterexamples.md). A full pattern definition has one
home; this table links to it.

| Pattern (short name) | Caught by | Status |
| --- | --- | --- |
| <the shape that looked reasonable> | `<surface or stance>` | <fixed / survey / open> |

## Unrepresented stakes

Objectives the project holds that no stance represents, and the reason each is
left out. This table is the set's own list of blind spots; a finding that lands
here is a missing stance, not a missing check.

| Stake | Evidence | Why no stance |
| --- | --- | --- |
| <objective> | `<path>#<section>` | <no opponent found / deliberately out of scope> |

## Deferred axes

Axes that were considered and not forged. The reason must be semantic, never a
stance count. The forge condition is the evidence that would make the axis real.

| Axis | Stakes | Reason | Forge when |
| --- | --- | --- | --- |
| <axis> | <stakes> | <missing evidence or owner> | <the evidence that would forge it> |
```

## Registry rules

- The registry is the only file that lists every stance. A stance that is not
  in the table does not exist for reviewers.
- Every stance appears in at least one opposition row. An unopposed stake is a
  check or an `unrepresented` row, not a stance.
- `Resolved without escalation` grows over time. That growth is the measure of
  whether the buffer space is being found rather than the tradeoff being
  surrendered.
- `Decisions that sacrificed a stance` is append-only. Deleting a sacrifice
  hides the cost of the current design. Keep `decided`, `implemented`, and
  `verified` distinct.
- Keep the tables short. If a table needs more than a screen, the conflict has
  outgrown the registry and belongs in a decision record with a link here.
- `Unrepresented stakes` is read at every pass. A finding no stance could have
  made is evidence for a row here; a row that survives two passes is the set's
  known blind spot and belongs in the pass result.
