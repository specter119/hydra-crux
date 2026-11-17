---
name: hydra-crux
description: >-
  Builds and maintains a project's review topology: discovers the objectives a
  project would sacrifice for, separates surface checks from partisan stances,
  records oppositions and payers, routes a change to the contention it actually
  touches, and keeps decisions binding through owner documents and reopen
  conditions. Use when a project has no review topology, when migrating
  per-domain review skills, or when a completed review showed the topology is
  wrong. Do not use to run a pass (use hydra-crux-review) or for ordinary code
  review without a stance question.
license: MIT
---

# Hydra Crux

A project has two kinds of review knowledge, and they fail differently:

- A **surface** answers *how do I inspect this?* It owns checks, evidence, and a
  scope boundary. It does not argue for a value.
- A **stance** answers *what would this project sacrifice for, and who pays when
  it wins?* It owns an objective, an accepted harm, and an escalation condition.

A domain skill that quietly acquires "never do X" or "always prefer Y" has
become a stance wearing a checklist's name. Hydra-crux separates the argument
from the checks and records the **topology** that makes both findable and
routable.

## Topology, prose, and the registry

| Artifact                     | Owns                                                                | Written by                          |
| ---------------------------- | ------------------------------------------------------------------- | ----------------------------------- |
| `.agents/review-graph.toml`  | ids, links, payers, oppositions, decisions, unrepresented interests | this skill                          |
| `*-stance/SKILL.md`          | objective, attacks, evidence, accepted harm, escalation             | a person, from the graph's topology |
| `*-review/SKILL.md`          | checks, required evidence, scope boundary                           | a person, from the domain           |
| `*-stance-registry/SKILL.md` | navigation generated from graph and skill paths                     | `hydra_graph.py generate`           |

The graph does not own prose, and the registry is never edited by hand.
`generate` validates the graph, reads `skills_dir`, and writes the registry; it
does not generate stance or surface bodies.

## Hard invariants and semantic checks

The graph validator enforces items 1–3 and 6 below. The route CLI enforces the
`AXIS=REASON` shape in item 5. Item 4 is a review invariant: no validator can
tell whether an orchestrator hand-picked a set instead of using the route.

1. **Every stance names a payer and an opponent.**
2. **Every surface has an owner:** a contending stance reads it, or it names an
   unopposed stake.
3. **Every opposition has at least one decision.** Whether the recorded outcome
   reflects the real cost remains a semantic question.
4. **The route is the only selector.** A hand-picked stance set is an unrecorded
   route.
5. **Every skipped axis has a reason.** Silence is not a skip.
6. **Every decision has an owner document and a reopen condition.** Its kind and
   fields are defined in [graph-format.md](references/graph-format.md#decisions).

These checks require reading, not pattern matching:

- **A payer is real and the sacrifice is acceptable.** A non-empty field does
  not prove that anyone bears the cost.
- **A surface has not taken back a verdict.** If its prose decides the tradeoff,
  move the decision to the graph and the argument to a stance.
- **A stance is not seeded with its author's findings.** Current symbols in
  **Attacks**, an open violation in **Bad patterns**, or the defect restated in
  the Objective makes the pass confirm its author.
- **A missing interest stays visible.** Record `unrepresented`; do not invent an
  opponent or use the current stance count as a reason to omit it.

Everything else is advisory. Do not add a required field to avoid a
conversation.

## No fixed counts

No kind has a target number: stakes, stances, surfaces, axes, oppositions, and
decisions all follow the evidence:

- one stance per **side** of an axis, not one per axis;
- one stance may participate in several axes;
- a surface exists because a check needs a home and a route, not because a
  stance needs a partner;
- a surface may be read by several stances, and a stance may read several
  surfaces;
- an unopposed stake is a check, not a stance.

A graph where every payer is exactly the opposing stance, and every axis has
exactly two stances, is a quota signature. It is not an error, but check whether
each harmed side has an independent interest. A perfect one-to-one
surface/stance pairing is the same signature in the other layer: check that
each surface's checks predate the stance.

## Discover latent stakeholders

Start with "who pays, and who is missing?", not "what pairs can I form?"

1. **Read rejected alternatives and deliberate limits.** Every "unsupported" or
   "no formatter" records a lost task and a bearer.
2. **Trace the full user task for manual rescue.** Find hand edits, remembered
   context, retries, and history reads; record their frequency and cost.
3. **Attribute the cost of guards.** Ask who maintains each check, gate,
   ownership rule, or CI step, and what a false rejection costs.
4. **Read the losing side of a "no".** A prohibition is evidence of sacrifice,
   not a reason to silence the loser.
5. **Probe with two small designs.** If neither interest can name what the other
   loses, the candidate is a check or hypothesis, not an axis.
6. **Let misses change the set.** Record a real loss as `unrepresented` first;
   forge a stance only when the loss is real and recurring.

## Choose the mode

Read the project state before writing anything:

- **No graph, legacy review skills or a hand-written registry present.** Use the
  migration procedure below once. Existing material is evidence, not a parallel
  review layer.
- **No graph and no legacy layer.** Bootstrap from stakes and evidence below.
- **A v1 graph exists.** Follow [upgrade-v1.md](references/upgrade-v1.md).
- **A v2 graph exists.** Evolve it; do not rebuild or repeat migration.

## Build or repair the topology

Read [stance-design.md](references/stance-design.md) for stance anatomy and the
opposition test, [discovery-template.md](references/discovery-template.md) for
the evidence map, and [graph-format.md](references/graph-format.md) for every
graph field.

### 1. Recover stakes from evidence

Recover objectives from product and architecture documents, decision records,
validation and persistence boundaries, compatibility and performance limits,
authorization, tests, rejected alternatives, history, review comments, and the
user's explicit constraints.

Write each stake as *what this project would sacrifice other things to keep*.
Cite `path#section` evidence. Stakes without opponents remain checks or
unrepresented interests; do not manufacture contention.

If a decision model is configured, run the inventory first (see
[step 7](#7-audit-the-draft-against-the-owner-documents)) and give every
**Objective candidate** a disposition: cite it as stake evidence, merge it into
an existing stake, or reject it with a reason for the delivery report. A model
label is a candidate, not a stake.

### 2. Separate surfaces from stances

Classify each existing review paragraph semantically:

- checks, inspection paths, evidence requirements, and scope boundaries belong
  to a **surface**;
- verdicts and independent tradeoff adjudication belong to a **stance**;
- a scope boundary that actually chooses a winner is also a stance question.

A surface may keep its detailed checklist, but not a veto or escalation rule.
Write checks against the post-change state inside a named scope: "no X" means
"no X in this scoped path", not "the diff never mentions X".

A first build has no old skills to split. Derive surfaces from the checks the
project already runs—tests, CI gates, review questions, and requirements the
owner documents state—not from the stance list.

A prevention skill runs before writing rather than reviewing a change. Keep it
as an ordinary skill outside the graph. Record any otherwise unowned interest
it reveals as `unrepresented`; do not turn the prevention step into a surface.

### 3. Form oppositions only where a decision records contention

An opposition needs:

1. **A decision with evidence.** Cite a rejected alternative, deliberate limit,
   or owner-document decision where the objectives contended.
2. **Both sides.** Each stance names its opponent and the resource it gives up.
3. **A contended resource**, named as a quantity or surface, never a mood.
4. **A same-direction check.** If two stakes push the same way on every recorded
   decision, merge them.

Every opposition must be referenced by at least one decision's `axes`. A payer
without a stance may be latent: name the person, role, or interest in
`accepted_harm` without `payer_stance`. Keep a genuinely unowned interest in
`unrepresented`; do not force either into a stance to complete the graph.

### 4. Write the prose by hand

Create `.agents/skills/<project>-<stake>-stance/SKILL.md` from
[stance-template.md](references/stance-template.md). Its load-bearing sections
are **Objective**, **Accepts this harm**, **Attacks**, **Does not own**, and
**Escalates when**. Attacks are general failure shapes, not the author's current
findings.

Link surface checklists instead of copying them into stances. Mark each stance
`disable-model-invocation: true` as a best-effort hint and open its description
with "Use only when assigned by a stance-review orchestrator"; harness
enforcement varies.

### 5. Write the graph

Create `.agents/review-graph.toml` using
[graph-format.md](references/graph-format.md) as the sole field reference. Keep
it topology-only: stakes, surfaces, stances, oppositions, decisions, and
unrepresented interests. Use `contends` only for axes a surface actually
exercises, and keep prevention skills outside it.

### 6. Generate and lint

Set `HYDRA` to the installed skill directory, or to
`.agents/skills/hydra-crux` when vendored:

```sh
HYDRA="${HYDRA_CRUX_SKILL:-$HOME/.agents/skills/hydra-crux}"

python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml generate

python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml lint
```

Generate first, then lint. The command validates the schema, structured paths,
registry synchronization, and pass documents; it does not judge authored prose.
See [graph-format.md](references/graph-format.md#what-lint-checks) for its exact
scope. Whether a payer is real, a sacrifice is acceptable, or a surface contains
a hidden verdict remains a semantic review question.

### 7. Audit the draft against the owner documents

A first build has the same failure as a migration: the graph covers the stances
its author had in mind and misses a stake the project already wrote down. Run
the audit before step 1 without `--graph` (inventory only), and again once the
graph exists:

```sh
python3 "$HYDRA/scripts/concept_audit.py" run \
  --graph .agents/review-graph.toml \
  --source AGENTS.md --source README.md --source docs
```

The decision model is opt-in and not migration-only: once it is configured
([setup](references/concept-audit.md#setup)), every build, migration, and
evolution uses it, and without a config the audit still runs and says what it
skipped. It classifies sentences into roles as a second opinion. It does not
gate the build, decide a verdict, or change a route. Read the report with
[concept-audit.md](references/concept-audit.md#reading-the-report).

### 8. Add the entry point

Add a short section to the project's `AGENTS.md`, or its working-method owner,
covering only:

- where the graph and generated registry live;
- when to run a stance review;
- the route → one stance per reviewer → orchestrator adjudication shape;
- where decisions live, and that unresolved conflicts are not averaged;
- the independence rule: one stance and no other reviewer's output before the
  contest.

Link the protocol instead of copying it. Register `reviews_dir` in the
project's document routing and install the
[lint hook](references/graph-format.md#install-the-lint-hook). `jj commit` does
not trigger Git hooks, so run `lint` manually before committing.

### 9. Route a real change

```sh
python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml route \
  --changed src/example.py --format markdown
```

The review skill's step 1 owns selector and status semantics, including
`--diff-file`, `--include-axis`, per-axis `--skip`, and `--pass`. Use the route
as returned; never assemble a manual subset. If it misses or over-selects a
surface, repair the graph and reroute, or report the defect.

Run a **control** before declaring installation complete: take a real past
change that traded one objective against another and verify that the route
selects both sides. Run a **negative control** with a legitimate removal or
rename: a keyword match is only a candidate, and the surface check must read the
post-change state rather than reject the removal itself.

## Decisions that bind design

Decision kinds, required fields, status meaning, and reversible-choice rules
have one home: [graph-format.md](references/graph-format.md#decisions). Read it
before creating or changing a decision. A route surfaces applicable decisions;
the reviewer must determine whether the change follows, implements, verifies,
or reopens them rather than treating a recorded choice as proof of a changed
design.

## Migrate domain review skills

Use this section for the one-shot structural replacement. It is the only
migration procedure; do not rerun it after a v2 graph exists.

The old skills are raw material. Keep their checks and evidence, move their
verdicts into partisan stances, delete the old skills, and make hydra-crux the
only review entry point. Git history preserves the old source. Prevention skills
remain ordinary skills outside the graph.

### Migration rules

1. **No dual track.** Delete old review skill directories and remove their
   names from `AGENTS.md`, README, workflow documents, and discovery paths.
2. **Every old check has a home.** Preserve checks, evidence requirements, and
   scope boundaries in surface prose.
3. **Every old verdict has a home.** Move tradeoff decisions into stances and
   graph decisions; record an ownerless losing interest as `unrepresented`.
4. **Write stance arguments by hand.** Link checklists rather than copying them.
5. **Do not invent opponents.** Use latent payers or `unrepresented` where the
   losing interest has no stance.
6. **Record migration losses.** Name dropped checks, softened verdicts, and lost
   workflows rather than hiding them in a rename.

### 1. Inventory and classify

Read every old skill and produce this table before editing:

| Old skill | Checks and evidence | Verdicts and adjudication | Scope boundary | Destination |
| --------- | ------------------- | ------------------------- | -------------- | ----------- |

Classify each paragraph semantically. A verdict decides a tradeoff or forbids an
option regardless of another interest; a keyword alone cannot make that
classification. Inventory hand-written registries and entry points as well.

### 2. Build the replacement

Follow steps 1–5 above. Choose either per-surface skills for progressive
disclosure or one surface catalog with clear per-surface sections. Write every
stance from its evidence and opposition test, and keep prevention skills outside
the graph.

Before migration step 3 deletes anything, run the build step 7 audit with the old review skills
as `--source` and read its coverage rows: an old sentence no home covers is a
migration loss to fix or to report. Do not pass a prevention skill as a source.

### 3. Replace entry points and validate

Delete the old review skills, remove every old entry point, and point the
project only to the graph, generated registry, and hydra-crux route. Do not
hard-code a home-directory install path in project documentation. Run the
generate-then-lint commands in step 6.

### 4. Audit the prose

One reviewer reads every surface for verdicts, vetoes, and independent
escalation rules. Another reads every stance for copied checklists, missing
arguments, and preloaded open findings. These are semantic reviews; fix their
findings before the acceptance controls.

### 5. Run four acceptance controls

1. **Coverage:** route a real past change that exercised an old skill. Confirm
   the surface and both sides of the relevant axis are selected and the old
   check remains reachable.
2. **Locality:** route a local change and confirm it does not select the whole
   stance set.
3. **Veto audit:** temporarily add a surface sentence claiming final authority
   regardless of the opposing stance. Confirm an independent reviewer flags it,
   then remove the sentence. Lint is not expected to judge the prose.
4. **Entry point:** search project documentation and discovery paths for every
   deleted skill name; no active reference may remain.

### 6. Report the migration

Report:

- old skills and their destinations;
- axes, stances, decisions, and the evidence for each;
- checks moved, merged, or dropped, including orphans from the audit;
- unrepresented interests;
- commands and results;
- each acceptance control's outcome;
- migration costs and remaining unproven claims.

Success means old entry points are gone, checks remain reachable, a real change
routes to both sides, and the prose audit finds no hidden veto—not merely that
lint passes.

## Evolve an existing topology

Read the v2 graph, generated registry, applicable decisions, and recent pass
documents before editing.

1. Find evidence: an incident, rejected alternative, manual rescue, owner
   document, implemented decision, or reopen condition. No evidence, no stance.
2. Make the smallest change:
   - add a stake only with owner-document evidence;
   - add a stance only with a payer, opponent, and decision; update
     `accepted_harm` on both sides;
   - add an opposition only when both sides have evidence; otherwise record an
     `unrepresented` interest;
   - retire or merge a stance only with a reason and replacement route, keeping
     the losing cost visible;
   - add surfaces for checks, never for hidden verdicts;
   - update decisions without erasing their history.
3. Edit stance and surface prose by hand. Resolve pass map candidates and decide
   whether counterexample candidates belong in the general library, a stance's
   attacks, or the toolchain. Do not copy full patterns into project records.
4. Generate, lint, and route a real control change. Every omission is an
   explicit per-axis skip with a reason.
5. Repeat the semantic audits for surface verdicts, preloaded stances, real
   payers, and unrepresented interests. The build step 7 layer-bleed rows rank where
   to read first.
6. If an owner document changed, re-check every stake whose evidence cites it.
   A contract change that selects no relevant stance is a routing gap. Run the
   build step 7 audit on the changed documents to see what no home covers.

## Formalism is the failure mode

- **Filling the graph to make it valid:** green lint with invented payers is
  worse than an honest gap.
- **Inventing an opponent:** leave an uncontended stake unopposed or
  unrepresented.
- **Forcing every surface to have a stance:** a useful check may be unopposed.
- **Using a count as a reason:** name missing evidence instead.
- **Generating prose from topology:** an empty argument is a template, not a
  stance.
- **Treating green lint as a working review:** lint checks relationships, not
  whether the conflict or payer is real.
- **Treating no conflict as failure:** name the axes and evidence of
  satisfaction; silence is the failure.

## What this skill does not do

This skill does not run a pass, escalate a conflict, or harvest review
candidates. Those belong to
[hydra-crux-review](../hydra-crux-review/SKILL.md). It does not own decision
documents or replace domain expertise.

## Deliver the result

For a new topology, report:

- stakes and their evidence;
- **per axis**, both sides' stances, related decision ids, and what each stance
  accepts sacrificing;
- surfaces and owners;
- unrepresented interests;
- files written and commands run;
- control and negative-control results.

For maintenance, report the evidence and smallest change, then give the same
per-axis account for every affected axis plus route effects. Do not claim the
topology works because it exists; claim it when a route changes a design, a
decision is implemented or verified, or a real loss becomes visible.
