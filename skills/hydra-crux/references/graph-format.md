# Review graph format

The graph lives at `<project>/.agents/review-graph.toml`. It is a topology
index, not a copy of the stance or surface prose. Keep it small enough to read
in one sitting.

## Top level

```toml
version = 1
project = "example"
```

`project` is used for the generated registry name
(`<project>-stance-registry`) and for metadata.

## Stakes

```toml
[[stake]]
id = "S1"
objective = "What the project would sacrifice other things to keep."
evidence = ["docs/product.md#value-tests", "docs/design.md#rejected-alternatives"]
status = "represented" # represented | unopposed | unrepresented | missing
```

A `represented` stake must be named by at least one stance. An `unopposed` or
`unrepresented` stake must not be named by a stance. `missing` is for a theme
that is known but not yet articulated as a stake.

## Surfaces

```toml
[[surface]]
id = "example-boundary-review"
title = "Example boundary review"
trigger = ["path validation", "atomic writes"]
owner_documents = ["docs/reference.md#writes"]
skill = ".agents/skills/example-boundary-review/SKILL.md"
phase = "review" # review | before-write | release
contends = ["proof-vs-cost"]
paths = ["src/example/filesystem.py", "tests/filesystem/**"]
keywords = ["symlink", "atomic"]
unopposed_stake = "S9" # optional; may coexist with stance links
```

A surface must have at least one stance that reads it or an `unopposed_stake`.
It may have both: a check can protect a represented interest and an unopposed
one at the same time.

`contends` is the route's causal claim. It names the axes this surface actually
exercises. The route adds both sides of those axes. It does not add every axis a
selected stance happens to touch; those appear under `unclosed_axes` for an
explicit decision.

`phase` keeps prevention steps out of the review route. A `before-write` surface
is selected with `route --phase before-write`, not by a normal review route.

## Stances

```toml
[[stance]]
id = "example-proof-stance"
title = "Example proof stance"
objective = "Nothing is written without a fresh boundary read."
skill = ".agents/skills/example-proof-stance/SKILL.md"
surfaces = ["example-boundary-review"]
stakes = ["S1"]

[[stance.accepted_harm]]
payer = "example-cost-stance"
payer_stance = "example-cost-stance"
cost = "the fresh read costs latency"
resource = "latency"
```

`payer_stance` is optional. If present, it must be an opponent in an
opposition. If absent, the payer is **latent**: a named person, role, or
interest with no stance yet. Latent payers are visible in the registry but are
not routed. They are the correct place for a real interest that has not been
argued into a stance.

## Oppositions

```toml
[[opposition]]
id = "proof-vs-cost"
stances = ["example-proof-stance", "example-cost-stance"]
contended_resource = "latency of one whole-profile apply"
recorded_sacrifice = "Cost won on later actions; proof won on the first write."
state = "decided" # open | buffered | decided | deferred
```

Each stance in the opposition must name at least one other member as a payer
with `payer_stance`. The `recorded_sacrifice` must cite a real decision, limit,
or rejected alternative, not a hypothetical.

## Decisions

```toml
[[resolved]]
conflict = "C-1: the plan reports a narrow mode for a wide file"
resolution = "Disclose the live mode in the projection."
serves = "both: exposure gets the fact, proof keeps the guarantee"
evidence = "docs/decisions/c-1.md"
owner_document = "docs/decisions/c-1.md"
status = "decided_not_implemented" # decided | decided_not_implemented | implemented | verified | reopened
reopen_when = "the projection or the skipped contract changes"
axes = ["proof-vs-cost"]
stances = ["example-exposure-stance", "example-proof-stance"]
surfaces = ["example-confidentiality-review"]

[[open_conflict]]
conflict = "C-2: plan-time verdict versus boundary-time read"
pair = "example-proof-stance vs example-cost-stance"
status = "measurement blocked"
owner = "repair the benchmark, then run attempt 1"
reopen_when = "one digest read per action is measured"
axes = ["proof-vs-cost"]
stances = ["example-proof-stance", "example-cost-stance"]
surfaces = ["example-boundary-review"]

[[sacrifice]]
decision = "Per-action desired-bytes re-render dropped"
sacrificed = "example-proof-stance"
given_up = "whole-profile proof of later actions"
why = "loop cost"
owner_document = "docs/status.md#limits"
status = "implemented"
reopen_when = "a later action can write a value the first write did not prove"
axes = ["proof-vs-cost"]
stances = ["example-proof-stance"]
surfaces = ["example-boundary-review"]
```

Every decision needs `owner_document`, `status`, and `reopen_when`, plus
`stances` or `surfaces` so a route can find it. `status` is not decoration:
`decided_not_implemented` is the state that prevents a document decision from
being mistaken for a design change.

`axes` is optional and narrows the route: when present, the decision is included
only if the route selected that axis. Without it, the route falls back to the
decision's `stances` and `surfaces`, which can pull a shared stance's unrelated
history into a local change.

## Unrepresented and deferred

```toml
[[unrepresented]]
stake = "platform reach"
where = "docs/design.md#rejected-alternatives"
why = "no value test or non-goal defends it"

[[deferred_axis]]
axis = "authority-vs-completion"
stakes = ["S5", "S6"]
reason = "no owner document records a sacrifice on this axis yet"
forge_when = "a decision record names what completion gave up"
```

`unrepresented` is a first-class result. Do not invent a stance to remove it.
`deferred_axis` needs a semantic reason and a forge condition; a stance count is
not a reason.

## What the lint reads

`lint_review_graph.py` reads two things:

- the structured metadata in `.agents/review-graph.toml`;
- the generated registry and discovery map, to check they match the graph.

It does **not** read `*-stance/SKILL.md` or `*-review/SKILL.md`. Those are
authored prose, and a string or regex match cannot decide whether a surface has
taken back a verdict, whether a stance is seeded with its author's findings, or
whether an axis is genuinely contended. Those are semantic review questions for
`hydra-crux-review` or the migration prose audit.

## What the validator checks

- ids are unique and references exist;
- every stance is in at least one opposition and names its opponents as payers;
- every surface has a stance or an unopposed stake;
- every represented stake is named by a stance, and every unopposed stake is not;
- every opposition has a recorded sacrifice and both sides;
- every decision has an owner, status, reopen condition, and route scope;
- generated registry and discovery map match the graph.

It does **not** read stance or surface prose. Whether a payer is real, whether a
sacrifice is acceptable, whether a surface check is good, whether a surface has
taken back a verdict, or whether an axis is genuinely contended are semantic
review questions. Do not add string or regex rules for them to the lint.
