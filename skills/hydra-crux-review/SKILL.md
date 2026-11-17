---
name: hydra-crux-review
description: >-
  Runs one adversarial review pass over a project's review topology: routes a
  change to its surfaces and axes, binds a pass document, briefs one independent
  reviewer per selected stance, contests candidate conflicts, records decisions,
  and harvests counterexample candidates. Use when reviewing a change, branch,
  or proposed design against a project's `review-graph.toml`. Do not use to
  create or edit the topology (use hydra-crux), or for single-perspective review.
license: MIT
---

# Hydra Crux review

One orchestrator, several partisan reviewers, one ledger of what they could not
agree on. The orchestrator keeps the reviewers independent, tests their
conflicts, and makes every unresolved tradeoff legible; it is not another
partisan reviewer.

The stances are project skills linked from
[hydra-crux](../hydra-crux/SKILL.md)'s review graph. Decision and pass-document
semantics live in [graph-format.md](../hydra-crux/references/graph-format.md).

## 1. Bind the pass

Run the project's formatter on the target first. Then bind the exact revision
with `route --pass`; do not use `--all` for a pass:

```sh
HYDRA="${HYDRA_CRUX_SKILL:-$HOME/.agents/skills/hydra-crux}"

python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml route \
  --changed <path> --pass <slug> --format markdown
```

Use `--diff-file PATH|-` for added-line keyword evidence, `--include-axis AXIS=REASON` to add an axis, and `--skip AXIS=REASON` to omit an entire axis. A
skip names an axis, never a stance, and its reason is mandatory. Do not start
reviewers until the route returns `ok` and writes the draft.

Branch on the printed `status`, not the exit code:

| Status           | Action                                                                                                                                            |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ok`             | Read the bound draft, selected axes and stances, prior decisions, and checks.                                                                     |
| `no_graph`       | Stop. Ask the user to build a topology with hydra-crux or migrate the existing review layer; a hand-written registry alone still needs migration. |
| `invalid_graph`  | Stop and repair the reported graph error before routing again.                                                                                    |
| `no_match`       | Report that the change reached no recorded surface; do not invent a reviewer set.                                                                 |
| `no_reviewers`   | Report the skipped axes and their reasons; the pass has no reviewers.                                                                             |
| `unopposed_only` | Run the listed checks directly. Do not open a pass or brief stances.                                                                              |

The route is the only selector. Per file, it honors each surface's
`exclude_paths`, then matches `paths`, an owner document, or a keyword in added
diff lines. Deleted lines and filenames are not keyword evidence; without a
diff, keyword matching is not evaluated. A keyword hit is only a reason to read
the post-change state, never a finding by itself.

Selected axes come from matching surfaces, stakes whose evidence cites a changed
file, and explicit includes, minus explicit skips. Every selected axis supplies
all its stances. Never hand-pick a subset or add a stance manually. If routing is
wrong, fix the graph through hydra-crux and reroute; if that is not possible,
stop and report the route defect.

A stance that read a matching surface but belongs to an unselected axis appears
in `unselected_readers`. If it represents real contention in this change, rerun
`route` with `--include-axis AXIS=REASON` and the same `--pass` slug to rebind
the same draft. Otherwise record the reader and reason in `## Map candidates`.
Do not silently brief or drop it.

The draft records the target's baseline and the initial binding. Lint need not
pass yet. To bind an unchanged draft again, rerun the same route. If the target
changed, use `--rebaseline REASON` only when deliberately establishing a new
baseline; the reason remains in the pass history. The precise binding rules are
in [graph-format.md](../hydra-crux/references/graph-format.md#pass-documents).

## 2. Brief each reviewer

Give each selected stance exactly one reviewer. The brief contains only:

- the stance file path, with instructions to read and argue it as written;
- the target revision and scope;
- the output format below;
- the independence rule.

State the objective and scope neutrally. Do not include expected findings,
desired conclusions, other stances' arguments, or another reviewer's output.
Independence means a reviewer does not read any other reviewer's output before
the bounded contest in step 3b. Do not prescribe finding categories, counts, or
a required finding.

Reviewer output, one block per finding:

```text
Stance: <stance name>
Claim: <the violation, stated as a fact about the target>
Evidence: <path:line, command, test, or measurement>
Harm: <what this stance's objective loses if it stands>
Proposed change: <smallest change, including the regression test it needs>
Cost to others: <which stance pays, and roughly how much>
Seen before | new: <whether the stance's Attacks already described this shape>
```

A finding without evidence is a hypothesis: retain the label, but do not resolve
a conflict from it. Run the project's existing gates before reconciliation and
drop findings they already prevent.

`Seen before | new` exposes preloaded answers. If a stance's **Attacks**, **Bad
patterns**, or Objective already describes its author's open findings, its
report proves only that the reviewer followed the file. Audit this semantically
against the target and decision records; no keyword rule can decide it. Apply
the same semantic audit to surfaces: they own checks and evidence, not verdicts
or tradeoff adjudication.

## 3. Reconcile

Collect findings and group them by the surface they touch—a path, symbol, or
contract clause—across stances. Then classify each group:

- **Agreement:** findings point the same way; merge duplicates.
- **Independent:** findings concern different surfaces; keep both.
- **Conflict:** one proposed change harms another stance's objective; contest it.
- **Factual disagreement:** assertions about the target differ. Read the code or
  run the smallest reproduction before treating the group as a value conflict.

A conflict between stances not paired in the graph is a map miss. Record the
pair, evidence, and contended resource in `## Map candidates`; add or repair an
opposition later through hydra-crux's evolve procedure. Do not rewrite the graph
mid-pass to fit the current findings.

### 3b. Contest

A candidate conflict requires the harmed side's own position. Send its reviewer
only the proposed change, its evidence, and the surface—not the first
reviewer's reasoning or the orchestrator's framing. Ask what its objective loses
and for evidence.

Both sides must have written positions before a conflict can be classified. An
uncontested proposal becomes agreement or an independent finding. This bounded
exchange is the first time reviewers may see one another's material.

## 4. Classify each conflict

Use [escalation.md](../hydra-crux/references/escalation.md) to search for a joint
design, test claimed incompatibility, and escalate one decision at a time. Buffer
strategies are options, not a required order. Both affected stances must confirm
the same concrete joint design; nominal satisfaction is not confirmation.

Write every classification in the draft's `## Ledger`. For an outcome that
belongs in the graph, create the appropriate `[[decision]]` and add its id to
the pass front matter's `decisions`. Use the semantics in
[graph-format.md](../hydra-crux/references/graph-format.md#decisions), not a
second local interpretation.

| Situation                           | Ledger and graph action                                                                                         |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Both stances confirm a joint design | Record `joint`.                                                                                                 |
| The objectives are irreconcilable   | Escalate to the user; record `sacrifice, decided_by=user` after an answer, or `open, owner=user` while waiting. |
| Evidence is insufficient            | Record `open` with the measurement owner, `next_action`, and `reopen_when`.                                     |
| A reversible choice remains         | The orchestrator may decide, but must record `decided_by=orchestrator` and disclose it at delivery.             |
| The only difference is cost         | Record `open, owner=user`; do not choose the cheaper side silently.                                             |
| Only one stance has a finding       | Keep it in the Ledger; do not manufacture a graph decision.                                                     |

Do not modify target files before this step is complete, apart from the
formatting run in step 1. An escalation is a message to the user, not a heading
in a document.

## 5. Finish and record

Keep one status set in the pass front matter:

- `draft`: bound but unfinished;
- `survey`: finished without target changes or graph decisions;
- `record`: finished after target changes or with graph decisions;
- `abandoned`: stopped, with `reason` explaining why.

For `survey` and `record`, fill `target` and the Ledger. Apply authorized target
changes only after classification. If the pass was read-only, leave proposed
changes as proposals and mark it `survey` when no decision was recorded. Update
the graph through hydra-crux, generate the registry after graph changes, and run:

```sh
python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml lint
```

Every evidence path cited by the Ledger must survive a fresh clone and must not
be git-ignored—this repository's `.evidence/` is one example—because lint does
not check those citations.

The agent must run lint itself; exit 0 is required before calling the pass
complete. A hook is only a backstop. Follow its remediation when formatting has
changed the bound target, and never use rebaselining or `abandoned` to hide work.
Report every `rebaselined` entry and lint's warning when an abandoned pass has a
changed target. See
[graph-format.md](../hydra-crux/references/graph-format.md#what-lint-checks) for
the completion rules.

## 6. Feed back into the set

After the pass, use [hydra-crux](../hydra-crux/SKILL.md) for topology changes:

- investigate a stance that repeatedly reports no `new` findings on a surface it
  claims, using *the silent stance* in
  [stance-design.md](../hydra-crux/references/stance-design.md);
- sharpen imprecise attacks or accepted harms after the pass, never to steer the
  current result;
- record a newly discovered payer as `unrepresented` before considering a new
  stance;
- resolve each `## Map candidates` entry as a graph repair or a documented
  non-contention.

### Harvest counterexample candidates

For every design or contract deviation from stated intent that a defender could
argue for in good faith, write the shape, grounded defender argument, catcher,
and avoided cost in `## Counterexample candidates`. Do not harvest ordinary bugs,
missing tests, style complaints, or shapes a rule or test can enforce.

Hydra-crux's evolve flow decides whether to promote a candidate into the general
[pattern library](../hydra-crux/references/counterexamples.md) and whether to
update a stance. Do not create a second project-specific copy of the full
pattern, and do not edit a stance mid-pass.

## Orchestrator discipline

- **Briefing toward the answer:** expected conclusions measure the brief, not
  the design.
- **Weak opposing stances:** argue every stance in its strongest form.
- **Sharing outputs early:** discovery is independent; only contests are shared.
- **Averaging:** splitting the difference is not a joint solution unless both
  stances confirm that their objectives are fully served.
- **Silent tiebreaks:** cost-only and irreversible choices belong to the user;
  an orchestrator's reversible choice must be recorded and reported.
- **Escalation fatigue:** search for joint designs and measurements before
  asking the user to decide.
- **The filled-in map:** do not report only the conflicts the registry predicts.

## When to use fewer reviewers

Use the route, never a manual subset. Omit an entire axis only with
`--skip AXIS=REASON`, and report the reason and the unreviewed tradeoff. Never
run only one side of a selected axis. A pass with no conflict is valid when its
Ledger names the axes checked and the evidence that the design satisfies them;
do not manufacture conflict to prove the review ran.
