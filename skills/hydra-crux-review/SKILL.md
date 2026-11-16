---
name: hydra-crux-review
description: >-
  Runs one adversarial review pass over a project's review topology: routes a
  change to the surfaces and axes it actually touches, briefs one subagent per
  selected stance without telling it what to expect, reconciles findings by
  surface, contests each candidate conflict with the harmed stance, classifies
  each conflict as merged, incompatible under named constraints, or unresolved
  evidence, escalates only the incompatible ones to the user, and records the
  outcome plus the harvested counterexamples. Use when reviewing a change,
  branch, or proposed design against a project's `review-graph.toml` and
  `*-stance-registry`. Do not use to create or edit the topology (use
  hydra-crux), and do not use for a single-perspective code review.
license: MIT
---

# Hydra Crux review

One orchestrator, several partisan reviewers, one ledger of what they could not
agree on. The orchestrator's job is not to review the code. It is to keep the
reviewers honest, classify their conflicts, and make every unresolved tradeoff
legible to the user.

The stances are project skills linked from
[hydra-crux](../hydra-crux/SKILL.md)'s review graph. If the project has no
`review-graph.toml` and no `*-stance-registry`, stop and build the topology
first; a review without opposed stances is an ordinary review and should not use
this skill.

## 1. Bind the pass

Read the project's review graph and registry before anything else. They supply
the stances, the oppositions, the contract surfaces, and the conflicts already
resolved. Then route the target:

```sh
HYDRA="${HYDRA_CRUX_SKILL:-$HOME/.agents/skills/hydra-crux}"

python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml route \
  --changed <path> --format markdown
```

The route is the binding, not a suggestion. It selects surfaces by path or
keyword, adds both sides of the axes those surfaces declare in `contends`, and
lists the decisions the change must re-check. Do not manually assemble a
cross-product of every stance. The binding is about what the pass must inspect,
not what it must conclude: a path match is a direct hit, while a keyword match
only says the change mentions the surface's subject. Read the post-change state
before treating a keyword hit as a violation.

Do not hand-pick a subset either. If the route misses a surface or selects the
wrong one, fix the graph's `paths`, `keywords`, or `contends` and reroute.
Diagnosis is allowed: read the diff, compare the route's selection with the
touched code. But do not carry a hand-picked stance into the brief. If you
cannot change the graph, stop and report a route defect; a manual selection is
an unrecorded route.

Owner-document changes are the exception to path routing. If the target changes
`AGENTS.md`, `README.md`, `docs/product.md`, `docs/design.md`, or
`docs/reference.md`, the path route may select only an unopposed check or no
surface. Read the graph's `[[stake]]` evidence and the surfaces'
`owner_documents`; select every stance whose stake or surface cites the changed
document. This is a semantic binding, not a keyword match, and it is exactly
where a contract change can otherwise bypass the stances.

Then fix the pass's scope and record it:

- **Target** — the change under review: a diff, a branch, a proposed design, or
  a subsystem. Name the exact revision.
- **Oppositions in scope** — every axis the route selected. A pair where only
  one side is affected still gets both reviewers.
- **Axes touched but not declared** — the route's `unclosed_axes`. Decide
  explicitly whether to add them or record why the change does not contend
  them. If you keep a stance from an unclosed axis, add its opponent; otherwise
  drop the stance. Do not let a selected stance silently pull in every axis it
  touches.
- **Prior decisions** — the route's `prior_decisions` and `open_conflicts`. A
  reviewer that re-raises a settled conflict is producing noise; tell it so in
  the brief.
- **Skipped stances** — every `--skip STANCE=REASON`. `--skip` is the only way
  to drop a selected stance, and the reason is mandatory. If a skip removes one
  side of a selected opposition, skip the whole axis and record it as
  unreviewed, or keep both sides; a one-sided axis is a blocked route.
- **Reviewer list** — every selected stance is either briefed or explicitly
  skipped. A partial brief without a skip is a failed pass; do not collect
  findings from it.

A pass is bound when the target revision, the reviewer list, and the
constraining prior decisions are written down. Do not start reviewers before
this, or they will each invent their own scope.

Record the binding in a tracked path — the review doc draft or the project's
decision records — before the first reviewer starts. Do not add an
`[[evidence]]` row yet: evidence is a completion record, not a reservation. A
scope and an adjudication in a scratch or ignored directory are gone for the
next reader, who then re-litigates a decision whose reasoning nobody can find.

## 2. Brief each reviewer

Give each reviewer exactly one stance and nothing else. The brief contains:

- the stance file path, with the instruction to read it and treat it as its
  role for this pass, and to follow it as written;
- the target revision and scope;
- the prior decisions that constrain the target;
- the output format below, verbatim;
- an explicit statement that it is one of several opposed reviewers, that its
  job is to argue its objective fully, and that it must not balance, hedge, or
  anticipate the other reviewers.

Do not tell a reviewer what the other stances will say. Do not tell it which
conflicts you expect. A reviewer that knows the expected answer will find it.

Do not add finding categories, required counts, or a required finding of any
kind. A brief that asks for "at least one buffer" or labels each finding with a
kind has told the reviewer what to find, and the pass then measures the brief
rather than the design. If you want a taxonomy, apply it during reconciliation,
never in the brief.

Do not let a reviewer read another reviewer's output. Independence is the only
thing that makes the conflicts real; a reviewer that has read its opponent
anchors on it and the disagreement collapses. The single exception is the
bounded contest in step 3b, where an opponent sees a proposal and not the
argument behind it.

The same applies to the registry, which names the oppositions you expect. Keep
it, the discovery map, and the list of oppositions out of the brief.

Reviewer output format, one block per finding:

```text
Stance: <stance name>
Claim: <the violation, stated as a fact about the target>
Evidence: <path:line, command, test, or measurement that demonstrates it>
Maturity: implemented | partial | design-only | unstarted
Harm: <what this stance's objective loses if it stands>
Proposed change: <the smallest change that satisfies this stance>
Regression test: <the test that fails now, or the test the fix must add>
Cost to others: <which stance pays, and roughly how much>
Confidence: <high / medium / low, with the reason>
```

A finding without evidence is a hypothesis. Keep it, labeled, but do not let it
drive a resolution.

Maturity is not confidence. A design-only claim can be high-confidence, and an
implemented behavior can still be wrong. Do not collapse "described",
"implemented", and "verified".

A finding the project's own gates already prevent is not a finding. Run them
before reconciling and drop what they catch; a fix that a lint rule or a test
can hold is a rule or a test, not a review verdict.

Ask each reviewer to mark findings it took from its own stance's **Attacks**
as `seen before` and findings it discovered independently as `new`. A stance
whose reviewer reports only `seen before` findings was either accurate or was
pre-loaded with the answers; the orchestrator cannot tell which without this
label, and the difference decides whether the pass proved anything.

The label is only as good as the stance file. A stance written around its
author's open findings — current symbols in **Attacks**, an unfixed violation in
**Bad patterns**, the defect restated in the Objective — produces a report that
reads as a strong pass and proves nothing. Check for that before briefing; if
the stance fails, its `seen before` findings are not evidence the stance works.
This is a semantic audit: compare each stance's claims against the current code,
the decision records, and the pass that produced it. No lint rule can decide it
from a keyword or a path, and none should pretend to.

Read each selected surface the same way. A surface owns checks and required
evidence. If it says what to do when a check fails, or uses "always" or "never"
to settle a tradeoff, it has taken the verdict back from the stances. Remove
that sentence, or move the decision to a graph decision with an owner and a
reopen condition. This is also semantic: a keyword match cannot tell a check
from a verdict.

## 3. Reconcile

Collect all findings. Group them **by the surface they touch** — a path, a
symbol, a contract clause — across all stances, before classifying anything. The
registry's `## Oppositions` is a minimum to check, not the full map: the
conflicts that matter most are often between stances the registry never paired.

Then classify each group:

- **Agreement** — every finding in the group points the same way. Merge and drop
  the duplication. Agreement is not a conflict; do not manufacture one.
- **Independent** — findings touch different surfaces. Keep both.
- **Conflict** — satisfying one stance's proposed change harms another's
  objective. These are the only findings that matter for the next step.
- **Factual disagreement** — two stances assert opposite things about the same
  code. This is not a value conflict and must not be adjudicated as one. Resolve
  it first by reading the code or running the smallest reproduction, and record
  which claim held. A stance that asserted the losing claim has a defect to fix.

A conflict found between a stance pair the registry does not list is a **map
miss**. It is still a conflict; record it in the graph's `[[opposition]]` table
and regenerate the registry. Do not edit the generated registry by hand.

## 3b. Contest

A conflict is not established until the harmed side has said so in its own
words. A reviewer's `Cost to others` line is a guess by a partisan about what
its opponent loses, and partisans systematically understate their own costs.
Treating that guess as the opponent's position is the strawman failure produced
by the procedure itself.

For each candidate conflict, send the opposing stance's reviewer only:

- the proposed change and its evidence;
- the surface it touches.

Do not send the finding's reasoning, the first reviewer's framing, or the
orchestrator's view. Ask that stance for its objection, with evidence.

Then classify. A conflict may be called **essential** only when both stances
have a written position on it. A conflict the opponent does not contest becomes
an **agreement** or an **independent** finding, not an escalation.

Only candidate conflicts need both sides. An agreement or an independent finding
does not need a contest. A one-sided contest is a finding, not a classification:
it cannot become `merged`, `incompatible`, or `unresolved`.

This is the one place reviewers see each other's material, and it is bounded on
purpose: the opponent sees the proposal, never the argument. Discovery stays
independent; only the contest is shared.

Reconciliation is complete when every finding is grouped by surface and
classified, every conflict has both sides' written positions, every factual
disagreement is resolved against the code, and every map miss is recorded.

## 4. Classify each conflict

Place every conflict in one of the **three** states defined in
[escalation.md](../hydra-crux/references/escalation.md), using the four-part test
for the second. Do not collapse them into negotiable-or-essential: the third state
is where this protocol usually fails, and it is not a licence to pick the cheaper
side. Do not skip to a resolution because one option is easier.

- **Joint solution verified** — find buffer space first. Attempt the buffer
  strategies in order, and record each attempt with the reason it succeeded or
  failed. A buffer counts only when **both** stances confirm it against the same
  concrete design; a design that serves one nominally is an average, not a buffer.
- **Incompatible under named constraints** — stop. No joint design exists within
  the budget, authorization, or contract the project can change. Do not pick a
  winner, do not average, do not quietly drop the harder stance. Escalate in the
  format below, one conflict per message, with both stances in their strongest
  form.
- **Unresolved evidence** — the joint design is plausible but unmeasured, or the
  failure is asserted rather than demonstrated. Name the measurement, name who
  runs it, say what happens if nobody does. The conflict stays open and the
  current design keeps the status quo rather than being declared correct.

`Merged` needs both stances' confirmations. `Incompatible` needs both stances'
written positions. `Unresolved` needs both stances' positions on the evidence.
If one side is missing, the conflict is not classified yet.

An escalation is complete only when it presents:

- the two objectives, each stated in its own strongest form;
- the specific resource they both need and cannot share;
- every buffer attempt already tried, and why each failed;
- the concrete designs on each side, with their costs;
- the decision the user is being asked to make, and what becomes irreversible.

See [escalation.md](../hydra-crux/references/escalation.md) for the finding
format and the questions that separate a real essential conflict from a lazy one.

The classification is complete when every conflict is in one of the three
states; every joint solution names **both** stances' confirmations; every
unresolved-evidence conflict names a measurement, an owner, and an end condition;
and every incompatible one is escalated or waiting on a user answer.

An escalation is a message to the user, sent during the pass. A conflict filed
under an "escalated" heading in a document has not been escalated.

## 5. Record

A pass ends in one of three states. Do not collapse them:

- **draft** — bound, not finished. The binding lives in the review doc draft or
  a decision record. No `[[evidence]]` row and no conclusion.
- **survey** — finished, changed nothing. The review doc says `survey` and names
  the axes it checked. No `[[evidence]]` row.
- **record** — finished and changed something. Add an `[[evidence]]` row; the
  review doc links to it by `date` + `pass`.

Write the pass into the graph and the project's decision records, then
regenerate the registry. The registry is generated; do not edit it by hand.

- Merged buffers go to the graph's `[[resolved]]` table, with the evidence that
  **both** stances accept the design — a buffer the contest did not confirm is
  not resolved. Regenerate the registry.
- Escalated conflicts go to the graph's `[[open_conflict]]` table until the user
  decides, with the status the contest established: awaiting decision, or under
  a named measurement with an owner and a condition that ends it.
- Decisions go to the graph's `[[sacrifice]]` table, naming the losing
  objective, what was given up, the owner document, the status
  (`decided`, `decided_not_implemented`, `implemented`, `verified`), and the
  `reopen_when` condition.
- A `record` pass goes to the graph's `[[evidence]]` table: date, pass, the
  conflict or crux, what changed, and optional `doc` and `skipped` fields. A
  `survey` or `draft` does not get a row. Do not add an evidence row to make a
  draft look finished.
- The review doc is narrative, not a second record. It links to the evidence row
  by `date` + `pass`; a doc without a row is a survey or a draft, not
  automatically incomplete.
- Project-specific counterexample instances go to the graph's
  `[[counterexample]]` table, with the surface or stance that caught them and
  their status. The full pattern prose lives in the library; see step 6.

Do not use `--no-generated` to hide a discovery map you edited by hand. The
flag is for a project that has not adopted generated indexes; a stale map is a
generator or output-path problem, not a lint exception.

Everything the graph and registry cite must survive a fresh clone. Check the project's
version-control ignore rules before writing a path into the ledger: run output
and scratch evidence are commonly ignored, and a ledger that points at an
ignored file is a dead pointer for every later reader. A decision record belongs
where the project's own ownership rules put decision records — read them and
follow them, rather than inventing a location.

Check the exact path, not the directory's name, with the version-control tool's
own query (`git check-ignore -v <path>`). A project that ignores `.evidence/`
also ignores the discovery map and the adjudication, and the maintainer sees no
breakage because the file is still on their disk.

Do not record a resolution before it exists. A registry row that says a buffer
was adopted, while the code still does the old thing, is a false success and it
becomes permanent the moment the next reader trusts it. Distinguish three states
in the ledger and never collapse them: **findings recorded**, **fix implemented**,
and **fix verified**. Most passes end at the first.

An open conflict's row names its owner and next action. Without them it is the
deferred conflict: the current design wins by default.

Then apply the change to the code, if the pass was authorized to change code.
A review pass that ends at findings is a survey; say so rather than implying the
design changed. If it was a survey, mark the registry rows as survey results and
do not mark any conflict resolved.

A survey may run read-only. When the pass is not authorized to change code, say
so in the brief so reviewers do not write fixes, and treat every proposed change
as a proposal for a later pass.

## 6. Feed back into the set

After the pass, check the topology itself:

- Did any stance produce no `new` findings on a surface it claims? Note it. Two
  such passes in a row means the stance is either satisfied or badly written —
  silence is evidence only when the stance had something to review. Decide which;
  the rule is [stance-design.md](../hydra-crux/references/stance-design.md), under
  *the silent stance*.
- Did any conflict turn out to be a misreading, or a manufactured one? The
  stance's **Attacks** or **Accepts this harm** is imprecise. Fix the stance.
- Did the user's decision reveal a stake the set did not represent? Add an
  `unrepresented` row first. Forge a stance only when the loss is real and
  recurring, and do it through [hydra-crux](../hydra-crux/SKILL.md).
- Did a reviewer name a payer with no stance? Record it as a latent payer in
  `accepted_harm` without `payer_stance`. Do not invent a stance to make the
  graph complete.

### Harvest counterexamples

This is the step most passes skip, and the one that makes the set worth keeping.
It is the pass's job: the knowledge is produced here, and it is lost if the pass
does not write it down before it ends.

For every finding that is a **design or contract deviation from the project's
stated intent** — a deviation a defender could plausibly argue for, not a bug
and not a style issue — add an entry to
[counterexamples.md](../hydra-crux/references/counterexamples.md).

A counterexample entry needs the shape, the defender's argument, the stance and
check that caught it, the path, and the consequence that was avoided. The
"why it looks reasonable" field is mandatory and must be **grounded** in
something actually written or said — a commit message, a comment, a document
sentence, a test name. A pattern that only looks wrong in hindsight teaches a
later reviewer nothing, and an invented defender is a strawman.

Then **edit the stance file**, not only the library. A pattern added to the
library but not to the catching stance's **Attacks** is a note nobody reads at
the moment it would help. Change the attack list to describe the generalized
shape, and record in the stance's own history that the pass added it. If the
pattern is project-specific, it belongs in the graph's `[[counterexample]]`
table, which regenerates into the registry's counterexamples table;
if it is project-neutral, in the library's `## Patterns` section — never a
project's paths in the general file. A pattern a lint rule or a test could
catch goes to the project's toolchain instead.

The two tiers are **Pattern** (the full, project-neutral shape) and **Instance**
(the project's paths, evidence, and caught-by). They are not two copies of the
same fact. A full pattern definition has one home; a project instance links to
it by a short name. To promote an instance, add the pattern to the library,
replace the project row's full prose with the short name, and keep the
instance's `caught_by`, `status`, and evidence. Delete the project row only when
it has no instance-specific facts left.

Do not harvest bugs, missing tests, or anything that only looks wrong in
hindsight. A counterexample library full of obvious mistakes is worse than
none: it trains reviewers to check for things nobody would ever do.

Route set changes through
[hydra-crux](../hydra-crux/SKILL.md), which owns the rules a change to the set
must satisfy. Do not edit a stance mid-pass to make the current review come out
differently.

## Orchestrator discipline

These are the failure modes that make adversarial review theater:

- **Briefing toward the answer.** Telling reviewers which conflicts to find, or
  what the user wants. The result is a set of findings that justify a decision
  already made.
- **Weak opposing stances.** Writing the losing stance's brief lazily, or
  trimming its scope, so the favored stance wins by default. Every brief is
  written as if that stance were the project's only objective.
- **Sharing outputs before reconciliation.** Reviewers must not see each
  other's findings. Reconcile after collection, never during.
- **Averaging.** A resolution that splits the difference satisfies no
  objective. If both objectives are not fully served, the conflict is not
  resolved.
- **Silent tiebreaks.** Choosing a winner because it is cheaper to implement,
  or because the orchestrator prefers it. That decision is the user's.
- **Escalation fatigue.** Escalating negotiable conflicts trains the user to
  approve without reading. The four-part test exists to prevent this.
- **The filled-in map.** Reporting the conflicts the registry predicts. The
  pass then confirms the map and says nothing about the design.

## When to use fewer reviewers

A small, local change does not need the full cross-product. Use the route's
`contends` selection, not a manual list. If the route is still too broad, use
`--budget` to get disjoint batches and `--skip STANCE=REASON` for anything that
will not run. Say which stances were skipped and what tradeoff is therefore
unreviewed.

Never run a single stance on a change that a selected opposition covers — that
is the case where the conflict is most likely and least likely to be noticed.
The route already adds both sides; do not trim one side to fit a budget.

A pass that finds no conflict is a valid result. It must name the axes it
checked and why the design already satisfies them. Do not manufacture a conflict
to prove the review ran.
