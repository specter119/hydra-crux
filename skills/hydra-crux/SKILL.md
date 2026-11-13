---
name: hydra-crux
description: >-
  Builds and maintains a project's stance set: discovers the objectives a
  project would sacrifice for, forms opposed pairs each backed by a recorded
  decision, writes one partisan stance skill per side, and writes the crux
  ledger that holds their unresolved conflicts. Use when a project has no
  stance set, when installing one into `.agents/skills`, or when a completed
  review showed the set itself is wrong — a false conflict, a stance that
  never fires, a conflict the set should have found, a decision whose winner
  has no stance. Changes the set only on evidence from a pass. Do not use to
  run a pass (use hydra-crux-review) or for ordinary code review without a
  stance question.
license: MIT
---

# Hydra Crux

A hydra grows heads that disagree. Each head is a **stance**: a first-principles
objective that would, if fully pursued, harm what another stance protects. The
disagreement is the instrument. Architecture is what survives it.

Two rules carry the whole design:

1. **A stance is an objective, not a checklist.** It is written as a commitment
   the project would defend to a hostile reviewer, plus the harm it accepts. If
   two stances never conflict, one of them is dead weight.
2. **Conflicts are the product.** The goal is not consensus and not a pile of
   findings. It is to find where objectives genuinely collide, separate
   essential collisions from negotiable ones, and let the surviving design
   record which stances it serves and which it sacrifices.

This skill generates a stance set for one project and the **crux ledger** that
holds its conflicts: the oppositions still open, the buffers that served both
sides, and the decisions that sacrificed a stance. It does not perform the
review; that is [hydra-crux-review](../hydra-crux-review/SKILL.md).

## Why stances must be opposed

A single reviewer with a general "find problems" instruction converges. It
reports the same three issues every time, weighted by whatever the prompt
happened to mention, and it silently optimizes for the objective it inferred.
Opposed stances remove that degree of freedom: each reviewer is given an
objective it must maximize, and the harm it causes another objective becomes
visible as a conflict instead of disappearing into a compromise nobody chose.

A stance that cannot lose anything is not a stance. A stance whose loss is
acceptable to everyone is a preference, and belongs in a style guide.

## Build the stance set

Read [stance-design.md](references/stance-design.md) before writing any stance.
It defines the anatomy, the opposition test, and the failure modes that make a
stance useless.

### 1. Establish the project's real objectives

Do not invent objectives. Recover them from evidence:

- the product brief, architecture notes, and decision records;
- what the code actually protects: validation, boundaries, persistence,
  compatibility, performance budgets, authorization;
- what the tests refuse to let change;
- what maintainers argue about in history and review comments;
- what the user says must not break.

Write each objective as a stake: _what this project would sacrifice other things
to keep_. Objectives that nothing competes with are background, not stances.

### 2. Commit a stake map, then pair it

Write the stake map to a file the project commits, before writing any stance.
Use [discovery-template.md](references/discovery-template.md). The map is the
gate: a pair that cannot be entered in it is not an opposition yet.

For every stake, find the objective it trades against. A useful set is usually
3 to 6 stances arranged in 2 to 4 oppositions, not one stance per subsystem.
Subsystem-shaped stances ("the parser stance", "the CLI stance") produce
locality, not conflict; see the anti-patterns in
[stance-design.md](references/stance-design.md).

Each opposition row needs four things, and the row is rejected if any is
missing:

1. **A recorded decision.** Cite the place where one stake already lost to the
   other — a rejected alternative, a deliberate limit, a changelog entry, a
   decision record — with `path#section`. This is the decidable test that
   replaces "name a resource". A pair with no recorded decision is
   **hypothetical**: keep it, mark it, and do not count it toward the set's
   oppositions until a real change exercises it.
2. **Both directions.** What each side would demand, and what each side resists.
3. **The contended resource**, named as a quantity or a surface, never as a mood.
   "Friction" and "complexity" are not resources; "operator attention before a
   write" is.
4. **A same-direction check.** If two stakes push the same way on every decision
   found, they are one stake. Merge them and say so.

Run the opposition test in [stance-design.md](references/stance-design.md) here,
on the stakes, **before** any stance file exists. Once a stance is written, its
author has a reason to defend it, and the counterexamples show the mismatch gets
patched by cross-billing harms instead of being fixed.

List separately, in the same map: stakes with no opponent, and decision themes
the documents show but no stake represents. An unopposed stake usually needs a
check, not a stance.

### 3. Write each stance as a project skill

Create `.agents/skills/<project>-<stake>-stance/SKILL.md`. The
`<project>` prefix keeps stances from colliding with global skills and makes the
set greppable. Frontmatter must satisfy the harness grammar: kebab-case `name`
matching the directory, and a `description` that says when to use the stance
and what it must not be used for.

Stances are handed to a reviewer **by path**, never loaded through skill
invocation. The orchestrator reads the neutral registry; each reviewer reads one
stance file with a file-read tool and treats it as its role for that pass. Do not
design the set around automatic skill activation.

Mark each stance `disable-model-invocation: true` as a best-effort hint that an
unrelated task should not pull in a partisan objective by itself. Do not rely on
it. Its enforcement varies by harness: some hide the skill from the model
catalog and refuse a model-initiated load, others ignore it entirely. Because
enforcement varies, the `description` must also be written to discourage
accidental use — open it with "Load only when assigned by a stance-review
orchestrator" rather than with a list of surfaces that looks like an ordinary
trigger.

Do not put the flag on the registry. The registry is neutral, and on a harness
that hides flagged skills an orchestrator that checks its skill list would
wrongly conclude the project has no registry. Detect the registry by path glob
(`.agents/skills/*-stance-registry/SKILL.md`), not by its presence in a skill
list.

Copy the section order from [stance-template.md](references/stance-template.md).
The load-bearing sections are:

- **Objective** — the one thing this stance maximizes, stated so a reviewer
  can tell when it is being violated.
- **Accepts this harm** — the cost this stance knowingly imposes on others.
  This is what makes it a stance rather than an aspiration, and it is the
  first thing to check when a conflict seems false.
- **Attacks** — concrete failure modes, phrased as things to look for.
- **Does not own** — the findings to route to a sibling stance instead. Without
  this, every stance drifts toward reviewing everything.
- **Escalates when** — the conditions under which this stance refuses to
  compromise locally and requires a user decision.

### 4. Register the set

Write `.agents/skills/<project>-stance-registry/SKILL.md` from
[registry-template.md](references/registry-template.md). The registry is the
only place that lists the full set, the oppositions, and who owns which
question. Stances link to it; they never restate each other's scope.

The registry also declares the project's **contract surfaces**: the files that
hold decisions a stance conflict may change. A review that cannot name which
contract a resolution edits has not finished.

### 5. Prove the set is alive

A stance set that has never produced a conflict is decoration. Before declaring
the set installed, run the opposition test in
[stance-design.md](references/stance-design.md) against a real recent change,
and record the result in the registry's `## Evidence` section.

Then run a **control**: take a change that you know trades one objective against
another — a real past incident, or a small synthetic diff that does — and check
that the stance set stops it. A set that passes its control has shown it can
fire; a set that has never failed anything has not been tested. Record the
control and its outcome next to the evidence. Without a control, "the review
found conflicts" and "the review would find conflicts" are indistinguishable,
and only one of them is worth the review cost.

### 6. Add the entry point to the project's AGENTS.md

A stance set that no agent knows to use is dead weight. The project's
`AGENTS.md` is the only file every agent in that project reads without being
told, so the entry point goes there — **as a pointer, not a procedure.**

Add a short section (roughly 8 to 15 lines) covering only:

- that the project has opposed stances, and where the registry is;
- when to run a stance review (which changes warrant one) and when not to;
- the three-step shape: assign one stance per reviewer, keep reviewers
  independent, adjudicate in the orchestrator and record the result;
- where the ledger lives, and that conflicts unresolved by the user are not
  averaged;
- the one rule reviewers must not break: a reviewer reads one stance and does
  not read another reviewer's output.

Do not copy the protocol, the stance file structure, the escalation format, or
the buffer strategies into `AGENTS.md`. Those belong to the fixed operation
skill that already exists. A second copy of a procedure drifts from the first,
and the copy in `AGENTS.md` is the one nobody re-reads.

Respect the target file's existing ownership. If `AGENTS.md` declares which
document owns the working method, put the pointer in that document and link it
from `AGENTS.md`, rather than creating a competing owner.

Then verify the entry point actually works from the target project:

- the registry path in `AGENTS.md` resolves from the project root;
- the procedure skills the pointer names are installed **in that project**, or
  available to whoever runs the review — check, do not assume;
- a stance can be read by path with a plain file read, with no skill invocation
  required;
- any path cited in the registry survives a fresh clone (see the record step in
  the review skill for what commonly does not).

An entry point naming a skill that is not installed is worse than no entry point:
it reads as a working procedure and fails at the first step.

A rule that can be checked mechanically belongs in `scripts/lint_*.py` inside
the skill, not in prose. This skill ships two: `lint_stance_not_seeded.py` (a
stance may not name a current symbol or carry an unfixed violation) and
`lint_registry_paths_tracked.py` (a cited path must survive a fresh clone).
Both run through `scripts/lint-skills.sh` on every commit, and each must pass
its own `--self-test`, so a rule that silently stops firing fails the same gate
that runs it.

## Run and maintain the loop

The set is not static. Each review pass feeds back into it:

- A conflict that turned out to be negotiable, and was merged, teaches what the
  buffer space looks like. Add the merged resolution to the registry's
  `## Resolved without escalation` list so the next pass does not relitigate it.
- A stance that produced no `new` findings in two consecutive passes is either
  satisfied or badly written — but only if those passes touched a surface it
  claims, because silence is evidence only when the stance had something to
  review. Decide which it is, record the satisfaction with its evidence, or
  sharpen the stack of attacks. Do not keep an undecided silent stance. The full
  rule is in [stance-design.md](references/stance-design.md), under _the silent
  stance_; this bullet is the trigger, not a second definition.
- A defect that reached production, or a design change nobody opposed, means a
  stake is missing. Add the stance that would have caught it.
- An essential conflict resolved by the user becomes a decision record. The
  losing stance is not deleted: it stays, with the decision cited, so the
  sacrifice is visible to the next reviewer.
- Every recorded decision states what would **reopen** it: the measurement that
  came in under target, the platform that gained the primitive, the dependency
  that disappeared. A decision with no reopen condition is permanent by accident,
  and a stance that lost one is asked to stay quiet forever with no way back.

This section lists what a pass may change in the set. **The acts of escalating a
conflict and harvesting a counterexample belong to the pass, not to this skill**:
they happen while a review is running, and
[hydra-crux-review](../hydra-crux-review/SKILL.md) owns them. This skill owns the
set's shape and the rules a change to it must satisfy. When a pass reports a set
change, apply it here against those rules; do not restate the pass procedure.

## Coexist with domain review skills

A project often already has per-domain review skills — one skill per surface,
each with an explicit "do not use for ..." clause. They are complementary, and
confusing the two roles wastes both.

|          | Domain review skill                 | Stance                                                         |
| -------- | ----------------------------------- | -------------------------------------------------------------- |
| Answers  | How do I check this surface well?   | What is this project optimizing for, and who pays when it wins |
| Verdict  | This surface is clean, or it is not | This change serves or harms my objective; someone pays         |
| Output   | Findings about a surface            | Findings plus a named payer, and escalation conditions         |
| Fails by | Missing a check                     | Having no opponent                                             |

The difference is not that a stance cannot be satisfied. A stance can report
"harm: none on this surface" and that is a real result. The difference is that a
stance always names **who pays** when it wins, and a domain review skill never
does. That is the line to draw.

A stance **may reuse a domain review skill's surface map wholesale**. The
exposure stance was the confidentiality review's surface list plus a named payer
and an escalation rule, and it produced the sharpest finding of the pass. Do not
tell an author to avoid that overlap.

Before forging a set, check for existing `*-review` skills and read their
`## Does not own` or "do not use for" clauses. Those clauses are the project's
own map of its surfaces, and they save most of the objective-discovery work.

Wire them together rather than duplicating them:

- A stance's **Attacks** may point at the domain skill that holds the detailed
  checklist, instead of restating the checklist.
- A domain skill should not be added to the stance registry. It is not a stance.
  If a domain skill is doing the work of a stance — that is, it argues for a
  value rather than checking a surface — the stance set is missing that value.
  See the counterexample _"The winning side of a recorded decision has no
  stance"_.
- Do not forge a stance that adds no named payer and no escalation condition. A
  stance that only restates a domain skill's surface list, without saying who
  pays when it wins, adds no opposition and no review value.

## Check the set mechanically

Table consistency does not need an executable checker. The rules are few enough
to verify by reading, and a script would add a dependency to a documentation
artifact that must stay readable by hand.

Before declaring a set valid, confirm by reading the registry:

1. Every stance in `## Stances` appears in at least one `## Oppositions` row.
2. Every stance named in `## Oppositions` exists in `## Stances`.
3. `metadata.opposes` is an **index, not a second source of truth**. Every entry
   must name a stance that names it back, and the registry's `## Oppositions`
   must agree with it. Where they disagree, the registry wins and the metadata is
   corrected; a stance whose `opposes` and registry row disagree is not installed.
4. Every `## Accepts this harm` bullet names a sibling stance, a path, or a
   test. A bullet naming only generic user friction is the defect in the
   counterexample library's first entry.
5. Every row in `## Decisions that sacrificed a stance` names the losing
   stance, and the objective that won also has a stance. If it does not, list the
   winning objective under `## Unrepresented stakes` instead of implying the set
   decided it.
6. Every axis name has a stance defending each of its two terms.
7. No Objective contains two clauses joined by "and" that can be satisfied
   separately. Either split the stance or mark one clause as a constraint the
   other may not trade against.
8. Every stance names a sibling stance as the payer of its accepted harm. A
   stance whose only cost is "user friction" has no payer and no opponent.

If a check fails, fix the registry or the stance. Do not add a script that
enforces the table while leaving the substance wrong; the failure that matters
is a stance with no opponent, and no script can detect that.

## What this skill does not do

A stance set is static between passes. This skill never runs a review, never
escalates a conflict, and never harvests a counterexample — those are the
running pass, and they live in [hydra-crux-review](../hydra-crux-review/SKILL.md).

The split is deliberate. A procedure written in two places drifts, and the copy
in the generator is the one nobody re-reads when a review is actually happening.
If you find yourself describing how to conduct a pass inside this file, that text
belongs in the review skill.

## Deliver the result

For a new set, report the stakes found, the oppositions formed, the files
written, the opposition-test evidence, and any stake that could not be opposed
and was therefore left out.

For a maintenance pass, report which stance changed, the pass evidence that
justified it, and the effect on the registry's opposition map.

Do not claim a stance set is working because it exists. Claim it is working when
it has produced at least one conflict that changed a design or reached the user.
