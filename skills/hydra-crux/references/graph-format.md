# Review graph format

The graph lives at `<project>/.agents/review-graph.toml`. It is a topology
index, not a copy of stance or surface prose. This file is the single reference
for graph fields, decision semantics, pass documents, and lint behavior.

## Top level

```toml
version = 2
project = "example"
reviews_dir = ".agents/reviews" # optional; this is the default
skills_dir = ".agents/skills"   # optional; this is the default
```

`project` names the generated `<project>-stance-registry`. `generate` reads
`skills_dir` and writes that registry. Registry links come from each row's
`skill` path, and decisions render by `id` and `kind`.

Ids are globally unique across all graph tables. Unknown tables, fields, ids,
and enum values are errors. Paths are structured metadata: strip any `#anchor`
before checking existence.

## Stakes

```toml
[[stake]]
id = "S1"
objective = "What the project would sacrifice other things to keep."
evidence = ["docs/product.md#value-tests", "docs/design.md#rejected-alternatives"]
```

Every stake has exactly one owner shape: at least one stance references it, or
one surface names it as `unopposed_stake`, never both. A stake without an
opponent is not evidence that a stance must be invented.

## Surfaces

```toml
[[surface]]
id = "example-boundary-review"
title = "Example boundary review"
trigger = ["path validation", "atomic writes"]
owner_documents = ["docs/reference.md#writes"]
skill = ".agents/skills/example-boundary-review/SKILL.md"
contends = ["proof-vs-cost"]
paths = ["src/example/filesystem.py", "tests/filesystem/**"]
exclude_paths = ["tests/filesystem/generated/**"]
keywords = ["symlink", "atomic"]
unopposed_stake = "S9" # optional
```

A surface needs a stance reader or an `unopposed_stake`. A surface read by a
stance must declare `contends`. `exclude_paths` filters files for this surface
before any other match. Prevention skills that run before writing remain
ordinary skills outside the graph.

Checks, required evidence, and scope boundaries belong in the surface's
authored `SKILL.md`, not in graph fields.

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

`payer_stance` is optional. If present, it names an opponent in an opposition.
If absent, `payer` names a latent person, role, or interest that is visible but
not routed. Do not invent a stance for a latent payer.

## Oppositions

```toml
[[opposition]]
id = "proof-vs-cost"
stances = ["example-proof-stance", "example-cost-stance"]
contended_resource = "latency of one whole-profile apply"
```

An opposition has only `id`, `stances`, and `contended_resource`. Each stance
must name another member as a payer. At least one decision's `axes` must
reference the opposition; the decision, not an extra opposition field, records
what the project chose or still owes.

## Decisions

All decisions use `[[decision]]` and share:

- `id`, `kind` (`joint`, `sacrifice`, or `open`), `summary`, `owner_document`,
  and `reopen_when`;
- optional `stances`;
- `axes`, `surfaces`, or both, with at least one present.

### Joint

```toml
[[decision]]
id = "C-1"
kind = "joint"
summary = "Disclose the live mode while retaining the fresh-read guarantee."
owner_document = "docs/decisions/c-1.md"
reopen_when = "the projection or the skipped contract changes"
axes = ["proof-vs-cost"]
stances = ["example-exposure-stance", "example-proof-stance"]
surfaces = ["example-boundary-review"]
```

Use `joint` only when both sides confirm that the same concrete design fully
serves their objectives. It requires `axes`, and `stances` must cover both
sides of every named axis. Agreement to stop arguing, nominal satisfaction, or
an uncontested proposal is not a joint decision.

### Sacrifice

```toml
[[decision]]
id = "C-2"
kind = "sacrifice"
summary = "Drop per-action re-rendering to keep whole-profile cost bounded."
given_up = "whole-profile proof of later actions"
decided_by = "user" # user | orchestrator
sacrificed = "example-proof-stance" # stance or unrepresented id
status = "implemented" # decided | implemented | verified
owner_document = "docs/status.md#limits"
reopen_when = "a later action can write an unproven value"
axes = ["proof-vs-cost"]
stances = ["example-proof-stance"]
surfaces = ["example-boundary-review"]
```

A sacrifice names the losing stance or unrepresented interest in `sacrificed`,
what it loses in `given_up`, and who chose in `decided_by`. If `sacrificed` is a
stance and `axes` is present, that stance must belong to one of those axes.
`status` distinguishes a choice (`decided`), an implemented change
(`implemented`), and verified behavior (`verified`); never collapse them.

The user decides irreconcilable, irreversible, contract-changing, and cost-only
choices. An orchestrator may decide a reversible non-cost choice, but must use
`decided_by="orchestrator"` and report it at delivery. Prefer a joint design
before recording a sacrifice.

### Open

```toml
[[decision]]
id = "C-3"
kind = "open"
summary = "The joint design is plausible but its digest cost is unmeasured."
owner = "performance maintainer"
next_action = "repair and run the digest benchmark"
owner_document = "docs/decisions/c-3.md"
reopen_when = "one digest read per action has been measured"
axes = ["proof-vs-cost"]
stances = ["example-proof-stance", "example-cost-stance"]
surfaces = ["example-boundary-review"]
```

Use `open` while evidence is insufficient or the user has not answered. Name
`owner` and `next_action`; for a measurement, make the measurement and its end
condition explicit. An unanswered user decision uses `owner="user"`. A
cost-only difference stays open for the user rather than becoming an
orchestrator's silent tiebreak. An open row without an owner and action lets the
status quo win by default.

A decision without `axes` can only be `sacrifice` or `open`; do not invent an
axis merely to make routing more convenient.

## Unrepresented interests

```toml
[[unrepresented]]
id = "U-1"
stake = "platform reach"
where = "docs/design.md#rejected-alternatives"
why = "no value test or non-goal represents this user"
forge_when = "the loss recurs and has an independent payer" # optional
```

This is a first-class outcome, not a validation gap to fill with an invented
stance. Assign every row an id so a decision can name it as `sacrificed`.

## Pass documents

`route --pass SLUG` requires route status `ok`, a lowercase kebab-case slug, and
a change selection other than `--all`. It writes
`<reviews_dir>/<YYYY-MM-DD>-<slug>.md` with TOML front matter enclosed by `+++`:

```toml
status = "draft" # draft | survey | record | abandoned
target = ""
changed = ["src/example.py"]
baseline = { "src/example.py" = "<blob-sha1>" }
dirty_at_bind = { "docs/other.md" = "<blob-sha1>" }
axes = ["proof-vs-cost"]
stances = ["example-proof-stance", "example-cost-stance"]
included = [{ axis = "proof-vs-cost", reason = "changed contract" }]
skipped = [{ axis = "other-axis", reason = "not reviewed" }]
decisions = []
reason = ""
rebaselined = []
```

`baseline` contains each changed path's blob SHA-1, or `"absent"` when the path
does not exist. `dirty_at_bind` records other dirty files outside `reviews_dir`,
so a later stash does not make them look new. The body starts with four empty
sections:

```markdown
## Findings

## Ledger

## Map candidates

## Counterexample candidates
```

### Status and target changes

- `draft` is bound but unfinished.
- `survey` is finished without target changes or graph decisions.
- `record` is finished after a target change or with at least one decision.
- `abandoned` stops the pass and requires `reason`.

The target has changed when a `changed` path's current blob differs from
`baseline`, or a new dirty path appears outside `changed`, `dirty_at_bind`, and
`reviews_dir`. Blobs recorded in `dirty_at_bind` do not themselves count as a
later change.

Rebinding an unchanged draft rewrites its route selections while preserving the
body and baseline. For a newly added changed path, use its `dirty_at_bind` blob,
or its current blob when clean; if it is currently dirty and was not recorded,
the target has changed. Rebinding a non-draft or changed target is rejected, and
a rebind cannot shrink `changed`.

`--pass` needs a non-empty `changed` list of files, not directories, and cannot
be combined with `--project-root`.

`--rebaseline REASON` deliberately establishes a new baseline for an existing
pass document that is not in HEAD. It preserves status and body, refreshes
`baseline` and `dirty_at_bind`, and appends `{reason, date}` to `rebaselined`.
A document already in HEAD cannot be rebound or rebaselined. Rebaselining leaves
an audit trail; it does not make target edits disappear.

## Install the lint hook

The repository ships a hook manifest, so a project declares the hook instead of
copying its command:

```yaml
repos:
  - repo: https://github.com/specter119/hydra-crux
    rev: 0.1.0
    hooks:
      - id: hydra-crux-lint
```

`prek.toml` takes the same fields:

```toml
[[repos]]
repo = "https://github.com/specter119/hydra-crux"
rev = "0.1.0"
hooks = [{ id = "hydra-crux-lint" }]
```

The hook runs `hydra_graph.py lint` from the pinned checkout, so it needs no
global skill install and ignores `HYDRA_CRUX_SKILL`. It runs on every commit
because the graph, the registry, and the pass documents are checked as a whole.
The consumer's `python3` must be 3.11 or newer, the same floor as the bundled
scripts. To lint a graph outside the default discovery path, override `args`
with `["--graph", "<path>", "lint"]`.

The hook is a backstop; the agent still runs lint itself.

## What lint checks

Run:

```sh
python3 "$HYDRA/scripts/hydra_graph.py" --graph .agents/review-graph.toml lint
```

Lint finds and validates the graph, then checks:

1. **Schema:** global ids, known fields and references, enum values, stance and
   surface ownership, opposition decisions, and kind-specific decision rules.
2. **Structured paths:** stake evidence, surface owner documents, stance and
   surface skills, and decision owner documents exist after stripping anchors
   and are not ignored by git. `reviews_dir` must not be ignored.
3. **Registry:** the generated registry matches the graph and skill paths.
4. **Pass documents:** every `.md` directly inside `reviews_dir`, without
   recursion, has parseable TOML front matter.

For a pass document already in HEAD whose HEAD version was not `draft`, lint
only parses it and rejects a current return to `draft`. For a new document, or
one whose HEAD version was `draft`, lint performs the full check:

- fields, enums, and referenced ids are valid;
- HEAD and current versions both being `draft` is a committed-draft error;
- a changed target requires current status `record` or `abandoned`;
- `record` requires a changed target or a non-empty `decisions` list, and
  `survey` requires an empty one;
- `survey` and `record` require non-empty `target` and `## Ledger`;
- `abandoned` requires `reason`, and a changed target produces a warning;
- every `rebaselined` entry is printed.

A formatting-induced target change is repaired deliberately with
`route --pass SLUG --rebaseline REASON`, not by hiding the change. Outside a git
work tree, lint compares blobs for drafts, only parses other statuses, and
prints the reduced-check notice.

Exit codes are 0 for success, 1 for a lint violation, and 2 for no graph or a
usage error. Lint reads graph metadata, generated output, structured paths, and
pass documents. It does not classify stance or surface prose: whether a payer is
real, a stance is preloaded, a check is useful, or a surface contains a verdict
requires semantic review, never a string or regex verdict.
