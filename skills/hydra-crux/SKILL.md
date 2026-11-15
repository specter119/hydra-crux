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

Most review systems collapse the two. A domain skill starts as a checklist,
then quietly acquires a verdict: "never do X", "always prefer Y". Once it has a
verdict, it is a stance wearing a checklist's name, and the project has lost the
ability to see who paid for that verdict.

Hydra-crux keeps them separate and records the **topology** that connects them.
The topology is not the argument. It is the index that makes the argument
findable, routable, and hard to forget.

## Topology, prose, and generated indexes

| Artifact                                        | Owns                                                                             | Written by                          |
| ----------------------------------------------- | -------------------------------------------------------------------------------- | ----------------------------------- |
| `.agents/review-graph.toml`                     | ids, links, payers, oppositions, route hints, decisions, unrepresented interests | this skill                          |
| `*-stance/SKILL.md`                             | objective, attacks, evidence, accepted harm, escalation                          | a person, from the graph's topology |
| `*-review/SKILL.md`                             | checks, required evidence, scope boundary                                        | a person, from the domain           |
| `*-stance-registry/SKILL.md`, `docs/stances.md` | navigation and generated indexes                                                 | `hydra_graph.py generate`           |

The graph does **not** own the prose. A graph that contains every sentence is a
second source of truth, and the copy nobody re-reads is the one that drifts.

`generate` writes only the registry and the discovery map by default. It writes
stance and surface bodies only with `--views`, and only when the graph carries
the prose fields. That is an explicit choice, not the normal path.

## Hard invariants and semantic checks

These are the hard invariants. The first group is machine-checkable; the second
group is a semantic review check that no string matcher can decide.

1. **Every stance names a payer and an opponent.** The graph checks the
   references. Whether the payer is real is a review question.
2. **Every surface names an owner.** Either a stance reads it, or it names an
   explicitly unopposed stake. A check with neither is an orphan.
3. **Every opposition names a recorded sacrifice.** The graph checks that the
   field is present. Whether the project actually paid that cost is a review
   question.
4. **A route closes over declared contention, not graph reachability.** A
   surface declares which axes it contends. The route adds both sides of those
   axes. It does not transitively add every axis a stance happens to touch.
5. **A skipped stance is named with a reason.** Silence is not a skip. Whether
   the reason is honest is a review question.
6. **A decision names its owner document, status, and reopen condition.** The
   graph checks the fields. Whether the decision was implemented and verified is
   a review question.

The semantic checks:

- **A deferred axis has an evidence-backed reason and a forge condition.** "The
  set is already full" is not a reason. A count is not evidence. The graph can
  record the reason; only a reviewer can judge it.
- **A payer is real and the sacrifice is acceptable.** A non-empty field is not
  evidence that anyone actually bears the cost.
- **A surface has not taken back a verdict.** A check surface owns checks, not
  the tradeoff. If its prose decides what to do when the check fails, the
  adjudication has moved back into the surface.
- **A stance is not seeded with its author's findings.** Current symbols in
  **Attacks**, an open violation in **Bad patterns**, or the defect restated in
  the Objective makes the stance a confirmation of its author.

`scripts/concept_audit.py` narrows these checks to a candidate list. It is
opt-in: with no config it makes no network call and reports deterministic
candidates; with `[decision]` it adds triage. It never decides a semantic check,
and it has no LLM client: the reading is yours. See
`references/concept-audit.md`.

Everything else is advisory. Do not add a required field to avoid a
conversation.

## No stance count

Three stances and nine stances pass the same checks. The count follows the
evidence:

- one stance per **side** of an axis, not one per axis;
- one stance may participate in several axes;
- a surface may be read by several stances, and a stance may read several
  surfaces;
- an unopposed stake is a check, not a stance.

A graph where every payer is exactly the opposing stance, and every axis has
exactly two stances, is a quota signature. It is not an error, but check whether
the harmed side has an independent interest. `concept_audit.py` reports the
ratio.

The `luwu` fixture graph under `tests/fixtures/` shows one evidence-driven
count: ten stances for thirteen stakes. It is not a target. If the evidence
supports three, write three.

## Discover latent stakeholders

The hardest failure is not a bad stance. It is a real interest nobody
represents. Do not start by asking "what pairs can I form?" Start by asking
"who pays, and who is missing?"

Use these discovery moves:

1. **Read rejected alternatives and deliberate limits.** Every "no journal",
   "Linux-first", "no formatter", "unsupported" is a decision where someone
   lost something. Name the lost task and its user.
2. **Trace the full user task for manual rescue.** From a new machine, a daily
   edit, a failed apply, to the next run: where must a person hand-edit a file,
   remember context, retry, or read history? Record the bearer, frequency, and
   measurable cost.
3. **Attribute the cost of guards.** For every new check, test gate, ownership
   rule, or CI step, ask who maintains it, how many places must change together,
   and what a false rejection costs.
4. **Read the losing side of a "no".** A prohibition is evidence of a sacrifice,
   not a reason to silence the loser.
5. **Probe with two small designs.** Write one design that favors each interest.
   If you cannot name what the other loses, it is a check or a hypothesis, not
   an axis.
6. **Let misses change the set.** A real loss found outside the review is
   stronger evidence than a neatly filled payer field. Add it as an
   `unrepresented` row first; forge a stance only when the loss is real and
   recurring.

An interest with no stance is not a failure of the graph. It is a recorded gap.
`unrepresented` is a first-class outcome. Do not invent an opponent to make the
graph look complete.

## Choose the mode

Read the project state before writing anything:

- **No graph, legacy domain review skills present.** Use
  [migration-prompt.md](references/migration-prompt.md) once. It dissolves the
  old layer, archives it, and makes hydra-crux the only entry point.
- **No graph, no legacy layer.** Bootstrap from stakes and evidence with the
  procedure below.
- **Graph exists.** Evolve it. Do not rebuild from scratch, and do not run the
  migration prompt again: the old skills are already archived, and
  re-inventorying them duplicates surfaces.

## Build or repair the topology

Read [stance-design.md](references/stance-design.md) for the anatomy and the
opposition test. Read [discovery-template.md](references/discovery-template.md)
for the stake map. Read [graph-format.md](references/graph-format.md) for the
field reference.

### 1. Recover stakes from evidence

Do not invent objectives. Recover them from:

- the product brief, architecture notes, and decision records;
- what the code protects: validation, boundaries, persistence, compatibility,
  performance budgets, authorization;
- what the tests refuse to let change;
- rejected alternatives and stated limits;
- what maintainers argue about in history and review comments;
- what the user says must not break.

Write each stake as *what this project would sacrifice other things to keep*.
Stakes with no opponent are still stakes; they become checks or `unopposed`
rows.

### 2. Separate surfaces from stances

For every existing `*-review` skill, classify each paragraph:

- a check, a path to inspect, or a required evidence item belongs to the
  **surface**;
- a verdict, a "never", an "always prefer", or a "this must win" belongs to a
  **stance**;
- a scope boundary belongs to the surface, unless it is really a value
  judgment.

A surface may keep its detailed checklist. It must not keep an independent
adjudication procedure or a claim to decide the tradeoff. That role moves to
the orchestrator and the stance set.

### 3. Form oppositions only where a sacrifice is recorded

An opposition row needs:

1. **A recorded sacrifice.** Cite the place where one stake already lost to the
   other: a rejected alternative, a deliberate limit, a changelog entry, a
   decision record, with `path#section`.
2. **Both sides.** Each stance names the other as a payer, with the resource it
   gives up.
3. **A contended resource**, named as a quantity or a surface, never a mood.
4. **A same-direction check.** If two stakes push the same way on every recorded
   decision, they are one stake. Merge them and say so.

A payer may be a **latent payer**: a named person, role, or interest with no
stance yet. Record it in `accepted_harm` without `payer_stance`. It will not be
routed, but it will be visible. Do not force it into a stance in the same pass.

### 4. Write the prose by hand

Create `.agents/skills/<project>-<stake>-stance/SKILL.md` from
[stance-template.md](references/stance-template.md). The load-bearing sections
are:

- **Objective** — the one thing this stance maximizes.
- **Accepts this harm** — the cost it knowingly imposes, with a named payer.
- **Attacks** — concrete failure shapes, not current symbols or open findings.
- **Does not own** — findings to route to a sibling stance or a surface.
- **Escalates when** — the conditions under which it refuses a local
  compromise.

Do not copy a surface checklist into a stance. Link the surface. A stance that
restates the checklist has no independent value, and a checklist that argues for
a value has become a stance by accident.

Mark each stance `disable-model-invocation: true` as a best-effort hint. Its
enforcement varies by harness, so the description must also open with "Use only
when assigned by a stance-review orchestrator".

### 5. Write the graph

Create `.agents/review-graph.toml`. Keep it topology-only:

- `[[stake]]` — id, objective, evidence, status
  (`represented`, `unopposed`, `unrepresented`, `missing`);
- `[[surface]]` — id, title, trigger, owner documents, `skill`, `phase`,
  `contends`, route `paths`/`keywords`, and either a stance link or
  `unopposed_stake`;
- `[[stance]]` — id, objective, `skill`, `surfaces`, `stakes`, and
  `[[stance.accepted_harm]]` rows;
- `[[opposition]]` — id, stances, contended resource, recorded sacrifice, state;
- `[[resolved]]`, `[[open_conflict]]`, `[[sacrifice]]` — decisions with owner
  document, status, reopen condition, and the surfaces/stances they constrain;
- `[[unrepresented]]` — a real interest with no stance, and why;
- `[[deferred_axis]]` — only with a semantic reason and a forge condition.

Use `contends` on a surface to name the axes it actually exercises. This is what
keeps a local change local. A surface that does not declare an axis will show
up as an unclosed axis instead of silently expanding the review.

### 6. Validate and generate indexes

```sh
python3 .agents/skills/hydra-crux/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml validate

python3 .agents/skills/hydra-crux/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml generate \
  --out .agents/skills --docs-out docs
```

Run `lint_review_graph.py` on every commit. Its object is the graph metadata in
`.agents/review-graph.toml` and the generated indexes, not the authored
`SKILL.md` prose. It checks the graph structure, the path references, and
whether the generated indexes are in sync. It does not read stance or surface
prose. Whether a payer is real, whether a sacrifice is acceptable, whether a
check is any good, or whether a surface has quietly taken back a verdict are
semantic review questions, not lint rules.

### 7. Add the entry point

Add a short section to the project's `AGENTS.md` (or the document that owns the
working method) covering only:

- where the review graph and registry are;
- when to run a stance review and when not to;
- the three-step shape: route, assign one stance per reviewer, adjudicate in the
  orchestrator;
- where decisions live, and that unresolved conflicts are not averaged;
- the one rule reviewers must not break: one stance, no other reviewer's output.

Do not copy the protocol into `AGENTS.md`. A second copy drifts.

### 8. Route a real change

```sh
python3 .agents/skills/hydra-crux/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml route \
  --changed src/example.py --format markdown
```

The route returns:

- surfaces selected by path or keyword;
- both sides of the axes those surfaces declare in `contends`;
- closure surfaces that contend the same axes;
- axes touched by a selected stance but not declared by any selected surface;
- prior decisions and open conflicts the change must re-check;
- unopposed checks and explicit skips.

For a prevention step such as primitive reuse, run
`route --phase before-write`; it is not part of the normal review route.

If the route is too broad, do not silently drop stances. Use `--budget` to get
disjoint batches, and `--skip STANCE=REASON` for anything that will not run.
`needs_grouping` means the pass has not been bound yet.

Run a **control** before declaring the topology installed: take a real past
change that traded one objective against another and check that the route
selects both sides. A topology that has never fired is a hypothesis.

## Decisions that bind design

A decision is not a registry row that says "resolved". It has:

- the scope it constrains (surfaces and stances);
- the axes it belongs to, when a shared stance would otherwise pull unrelated
  history into a local route;
- the choice and the sacrifice;
- the owner document that holds the contract;
- a status: `decided`, `decided_not_implemented`, `implemented`, `verified`,
  `reopened`;
- the implementation or test that makes it real;
- a `reopen_when` condition.

The route surfaces prior decisions that touch the change. The reviewer must say
which of these happened:

- the change follows the decision;
- the change implements a missing part;
- the change triggers the reopen condition.

Do not collapse "decided", "implemented", and "verified". Most passes end at
"findings recorded" or "decided"; say so. A decision that stays
`decided_not_implemented` is visible debt, not success.

## Migrate domain review skills

A domain review skill is usually a surface with a hidden stance. Migrate it in
this order:

1. Keep its checks, evidence, scope boundary, and "do not use for" clauses.
2. Remove its independent verdict, adjudication procedure, and claim to decide
   the tradeoff.
3. If it argues for a value, extract that value into a stance. If the value has
   no opponent, keep it as an unopposed check.
4. Link the surface from the stance's `surfaces` list. Do not copy the checklist.
5. If the skill is a prevention step rather than a review step, give it
   `phase = "before-write"` and keep it out of the review route.

Do not keep a dual track. If a domain skill cannot be dissolved, name the
semantic boundary it still owns: a surface, an evidence source, an owner
document, an opposition, or a genuinely new stance. "It has useful checks" is
not a boundary; those checks belong to a surface.

For a one-shot structural replacement — delete or archive the old domain skills,
make hydra-crux the only entry point, and prove the old checks are still
reachable — use
[migration-prompt.md](references/migration-prompt.md). That prompt is a
migration act, not a runtime rule; the default skill does not delete anything.

## Evolve an existing topology

Run this when `.agents/review-graph.toml` already exists. The graph is the
current topology, not a draft. Read it, the registry, the review log, and the
open decisions before editing.

1. Find the evidence for the change: a new incident, a rejected alternative, a
   manual rescue, a new owner document, or a decision that was implemented or
   reopened. No evidence, no new stance.
2. Make the smallest topology change:
   - add a stake only when a new objective has owner-document evidence;
   - add a stance only when it has a payer and an opponent with a recorded
     sacrifice; update `accepted_harm` on both sides;
   - add an axis only when both sides have evidence; otherwise record a
     `deferred_axis`;
   - retire or merge a stance only with a recorded reason and a replacement
     route; keep the losing cost visible;
   - add a surface for a new check; do not move a verdict into it;
   - if a new legacy domain skill appears, dissolve it with the per-skill
     procedure above; do not re-run the whole migration prompt;
   - update a decision's status, owner, or `reopen_when`; do not overwrite its
     history.
3. Edit the stance and surface prose by hand. Do not regenerate bodies.
4. Validate, regenerate the indexes, and route a real change. The route must
   select both sides of the axes it touches; an unselected stance is a skip with
   a reason, not silence.
5. Run the semantic audit: a surface has not taken back a verdict, a stance is
   not seeded with its author's findings, and a deferred axis has evidence, not
   a count.
6. If an owner document changed, re-check every stake whose `evidence` cites the
   changed document. A contract change that selects no stance is a routing gap,
   not a clean review.
7. Record the change in the registry's review log: date, scope, pair or crux,
   outcome, and what was retired or re-opened.

## Formalism is the failure mode

The graph is a tool, not a success metric. These are the ways it goes wrong:

- **Filling the graph to make it valid.** A green lint with invented payers is
  worse than a red lint with an honest gap.
- **Inventing an opponent.** If a stake has no real opponent, leave it
  unopposed. Do not manufacture a pair to satisfy the payer rule.
- **Forcing every surface to have a stance.** A check can be unopposed. Record
  the stake and move on.
- **Deferring an axis because the set is full.** A count is not a reason. Name
  the missing evidence and the condition that would forge the axis.
- **Generating prose from topology.** A generated stance with empty attacks is a
  template, not a stance. Keep the prose hand-authored unless the project
  explicitly chooses generated views.
- **Treating a green lint as a working review.** The lint checks relationships.
  It does not check whether the conflict is real, whether the payer cares, or
  whether the design changed.
- **Treating "no conflict" as failure.** A review that finds no conflict must
  name the axes it checked and why the design already satisfies them. Silence
  is not evidence; a named satisfaction is.

## What this skill does not do

This skill does not run a pass, escalate a conflict, or harvest a
counterexample. Those belong to [hydra-crux-review](../hydra-crux-review/SKILL.md).
It does not own decision documents; the graph references them. It does not
replace domain expertise; it routes to it.

## Deliver the result

For a new topology, report:

- the stakes found and their evidence;
- the axes with recorded sacrifices, and the stances on each side;
- the surfaces and their owners;
- the unrepresented interests and deferred axes;
- the files written and the commands run;
- the control change and whether the route selected both sides.

For a maintenance pass, report what changed, the evidence that justified it, and
the effect on the axes and routes.

Do not claim a topology is working because it exists. Claim it is working when a
route changed a design, a decision was implemented, or a real loss was recorded
that the old set would have missed.
