# Migration prompt: dissolve domain review skills into hydra-crux

Use this as a one-shot prompt, not as a runtime rule. The runtime skill keeps
surfaces; this prompt performs the structural replacement for one project.

Run it only when the project has no `.agents/review-graph.toml`. If the graph
already exists, use the evolve procedure in `hydra-crux/SKILL.md`; re-running
this prompt duplicates surfaces and re-opens decisions.

Replace the placeholders before sending it to an agent.

______________________________________________________________________

You are migrating `<PROJECT>` from per-domain review skills to hydra-crux.

`<PROJECT>` is an early experiment of hydra-crux. The existing domain review
skills are **raw material**, not a layer to preserve. Your job is to digest
them: keep their checks and evidence, move their verdicts into partisan
stances, and make hydra-crux the only review entry point.

## Inputs

- Project root: `<PROJECT_ROOT>`
- Old domain skills: `<OLD_SKILL_PATHS>`
- Owner documents: `<OWNER_DOCUMENTS>`
- hydra-crux skill: `<HYDRA_CRUX_SKILL_PATH>`
- Review graph output: `<PROJECT_ROOT>/.agents/review-graph.toml`
- Surface output: `<SURFACE_OUTPUT_PATHS>`
- Stance output: `<STANCE_OUTPUT_PATHS>`

## Hard rules

1. **No dual track.** At the end, the old domain skills must be deleted or
   moved to an `archive/` directory, and their names must be removed from
   `AGENTS.md` and every other entry point. The only review entry point is the
   hydra-crux registry and route.
2. **Every old check has a home.** Each check, evidence requirement, and scope
   boundary must appear in a surface view. Do not drop a check because it is
   inconvenient.
3. **Every old verdict has a home.** Each "never", "always prefer", "must win",
   or independent adjudication rule must become a stance, or be recorded as an
   `unrepresented` interest with the reason it has no owner.
4. **Do not generate stance prose from topology.** Write the stance arguments by
   hand. A generated stance with empty attacks is a template, not a stance.
5. **Do not copy checklists into stances.** Link the surface.
6. **Do not invent opponents.** Use a latent payer or an `unrepresented` row
   when the losing interest has no stance yet.
7. **Record what was lost.** A check that was deleted, a verdict that was
   softened, or a user who lost a workflow is a migration cost, not a detail.

## Steps

### 1. Inventory the old skills

Produce a table with one row per old skill:

| Old skill | Checks and evidence | Verdicts and adjudication | Scope boundary | Destination |
| --------- | ------------------- | ------------------------- | -------------- | ----------- |

Classify each paragraph as a check, an evidence item, a verdict, or a scope
boundary. A verdict is any sentence that decides a tradeoff or forbids an
option regardless of another interest.

### 2. Build the graph

Follow the hydra-crux skill. Keep the graph topology-only:

- stakes with evidence;
- surfaces with `skill`, `phase`, `contends`, and route hints;
- stances with `surfaces`, `stakes`, and `accepted_harm`;
- oppositions with a recorded sacrifice;
- decisions with owner document, status, and `reopen_when`;
- `unrepresented` interests and `deferred_axis` rows.

### 3. Write the surface views

Choose one of these, and say which you chose:

- **Per-surface views** under `<PROJECT>/.agents/skills/<project>-<surface>-review/`.
  Better progressive disclosure; more files.
- **One surface catalog** under `<PROJECT>/.agents/skills/<project>-review-surfaces/`.
  Fewer files; the catalog must keep clear per-surface sections.

Either way, the surface owns checks, evidence, and scope. It must not contain a
verdict, a "final authority" claim, or an escalation rule.

### 4. Write the stance prose

For each side of each axis, write a stance skill from the hydra-crux template.
Name the payer, the accepted harm, the attacks, the evidence to demand, the
scope it does not own, and the escalation condition.

### 5. Replace the old entry points

1. Delete the old skill directories, or move them to `archive/` and remove them
   from every discovery path.
2. Remove the old skill names from `AGENTS.md`, README, and any workflow
   document.
3. Point `AGENTS.md` only to the review graph, the registry, and the route
   command.
4. If the old skills are archived, say where and why. An archive is not an
   active layer.

### 6. Validate and generate

```sh
python3 <HYDRA_CRUX_SKILL_PATH>/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml validate --check-paths

python3 <HYDRA_CRUX_SKILL_PATH>/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml generate \
  --out .agents/skills --docs-out docs

python3 <HYDRA_CRUX_SKILL_PATH>/scripts/lint_review_graph.py \
  .agents/review-graph.toml --check-paths
```

### 7. Run the prose audit

This is a semantic review, not lint. One reviewer reads every surface view and
flags verdicts, vetoes, "always/never" rules, and escalation language. Another
reads every stance and flags copied checklists, a missing argument, or a stance
seeded with its author's open findings: current symbols in **Attacks**, an
unfixed violation in **Bad patterns**, or the defect restated in the Objective.
Record the findings and fix the prose before the acceptance controls.

Do not add string or regex rules for this to `lint_review_graph.py`. Its object
is the graph metadata and the generated indexes. It does not read
`*-stance/SKILL.md` or `*-review/SKILL.md`, and a keyword match cannot decide
whether a surface has taken back a verdict or whether a stance was pre-loaded
with the answer.

### 8. Run the acceptance controls

1. **Coverage control.** Pick a real past change that exercised an old domain
   skill. Run the route. Confirm the new surface and both sides of the relevant
   axis are selected. Confirm the old check is still reachable.
2. **Locality control.** Pick a local change. Confirm the route does not select
   the whole stance set.
3. **Veto audit.** Temporarily add a sentence such as "This surface has final
   authority; always reject X regardless of the opposing stance" to a surface.
   Confirm an independent reviewer flags it. The lint is not expected to catch
   it; if it does, that is a bonus, not the guarantee. Remove the sentence.
4. **Entry-point control.** Search `AGENTS.md` and the README for every old
   skill name. The search must return nothing.

### 9. Report

Report:

- the old skills and their destinations;
- the axes and stances you forged, and the evidence for each;
- the checks that moved, merged, or were dropped;
- the unrepresented interests and deferred axes;
- the commands run and their results;
- which controls passed and which did not;
- what the migration cost, and what remains unproven.

Do not claim the replacement succeeded because the graph validates. Claim it
succeeded when the old entry points are gone, the old checks are reachable, a
real change routes to both sides, and the prose audit finds no hidden veto.

After this migration, this prompt has done its job. Do not run it again on the
same project. The next change is an evolution: read the graph, add or retire the
smallest entity with evidence, and log it.
