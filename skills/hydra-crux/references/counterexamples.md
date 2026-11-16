# Counterexample library

Purpose: hold the concrete shapes a stance violation took, so a later review
recognizes the pattern instead of rediscovering it. A counterexample is not a
rule. It is evidence about how an objective gets violated, and the argument that
made the violation look reasonable.

## Two tiers, and why they must not mix

| Tier                | Holds                                      | Location                                                   |
| ------------------- | ------------------------------------------ | ---------------------------------------------------------- |
| **Pattern**         | The shape, project-neutral, no paths       | This file, `## Patterns`                                   |
| **Instance**        | Where it happened, with paths and evidence | The project's own registry, `## Counterexamples harvested` |
| **Process failure** | How a *review pass* failed                 | This file, `## Process failures`                           |

A pattern that carries one project's file paths cannot be reused by another,
and a reader cannot tell whether it was generalized or copied. Keep the shape
here and the instance there, linked by a short name.

## Promotion

When an instance reveals a general shape:

1. Add the pattern to `## Patterns` with the grounded defender argument.
2. Replace the project row's full prose with the short pattern name.
3. Keep the instance's `caught_by`, `status`, and evidence.
4. Delete the project row only when no instance-specific fact remains.

Do not copy the library prose into the project graph. A full pattern definition
has one home; the instance is a link. `caught_by` is a known surface or stance
id, or `all` / `all stances` for a pattern caught by the whole set. A
counterexample with no catcher is a bug report or a toolchain rule, not a
counterexample.

## Grounding rules

Every `## Patterns` entry needs:

- **Pattern** — the shape, stated so it is recognizable in a different module.
- **Why it looks reasonable** — the defender's argument, **grounded**. Cite where
  that argument actually appeared: a commit message, a PR comment, a document
  sentence, a test name, or the author's own words in the pass. If it cannot be
  cited, write `Reconstructed — no recorded origin` and treat the entry as a
  hypothesis rather than a pattern. An invented defender is a strawman, and a
  library of strawmen trains reviewers to fight arguments nobody makes.
- **How it was caught** — the stance, and the check that exposed it.
- **What it would have cost** — the consequence if it had shipped.
- **Instance** — `see <project> registry` or a decision record. Never a path from
  another project.

An entry that cannot supply a grounded "why it looks reasonable" is a bug
report, and belongs in the issue tracker. An entry a lint rule or a test could
catch is a rule or a test, and belongs in the project's toolchain.

## Patterns

### A document promises a compensating control the code does not implement

- **Pattern:** An owner document states a control exists — the plan shows the
  effective mode, the preview binds to the apply, the result names the reason —
  and the type has a field with that name, but the implementation fills it from
  a different source than the document claims.
- **Why it looks reasonable:** The field name matches the promise, so a reader
  who checks the schema is satisfied. The document and the code share a
  vocabulary and disagree only about provenance. **Grounded:** the claim appeared
  verbatim in the reference contract while the projection function returned the
  declared value, and the same contract defined the field as the declared value
  two sections earlier — a self-contradiction nobody re-read.
- **How it was caught:** Comparing the document's claim against the function that
  populates the field, then running the shipped test body with a probe.
- **What it would have cost:** A secret readable by every local account while the
  tool reported a narrow mode, with no reason for the operator to look.
- **Instance:** see the project registry that shipped this pass.

### A time window stands in for an evidence check

- **Pattern:** A freshness or validity decision compares a timestamp to a
  threshold instead of comparing the evidence. Written as an optimization, reads
  as one.
- **Why it looks reasonable:** Re-reading is expensive and the window is short,
  so the risk feels negligible; the code even names the constant, which makes it
  look considered. **Grounded:** the constant existed as a performance change
  with its own commit message.
- **How it was caught:** Asking what evidence the decision rests on, rather than
  what the decision is. The answer was "how long ago the plan was built".
- **What it would have cost:** A write authorized by a stale read, reported as
  fresh, with the window invisible in the output.
- **Instance:** see the project registry.

### A limit is stated as a fact rather than an argument

- **Pattern:** An owner document records "X is not supported", "Y is scoped to
  Z" with no reason attached. The limit is correct and deliberate, and the reader
  cannot tell which.
- **Why it looks reasonable:** The limit was argued once, in discussion, and only
  the conclusion was written down. Writing conclusions in the imperative is the
  house style for limits and keeps documents short. **Grounded:** fifteen such
  limits in one pass, each with a stated conclusion and no stated reason.
- **How it was caught:** For each stated limit, asking which stance pays for it
  and what the payment buys.
- **What it would have cost:** A limit that no longer matches its reason survives
  forever, because nobody can tell when it expired.
- **Instance:** see the project registry.

### A stance's `Accepts this harm` names generic friction instead of an opponent

- **Pattern:** The harm section lists user annoyance without naming which sibling
  stance pays and in what resource. The stance reads as a value statement, so it
  cannot lose anything and never produces a conflict.
- **Why it looks reasonable:** The author writes the file in isolation and
  describes cost in the only vocabulary on hand, which is user experience. It
  sounds sincere and is the easiest section to satisfy superficially.
- **How it was caught:** A mechanical check — does every bullet name a sibling
  stance, a path, or a test? The thin file cited no files and no tests across its
  whole length, against seven and seven for its sibling.
- **What it would have cost:** The registry asserted an opposition one member did
  not hold, so a pass over that set would conclude "refuse" — the conclusion it
  would have reached without stances at all.
- **Instance:** recorded in the set validation report of the project that
  produced it.

### A stance absorbs a cost its opponent actually pays

- **Pattern:** A stance's harm list includes costs it does not pay, because a
  sibling already refuses that path. The set looks balanced while one orientation
  holds all the evidence and all the refusal authority.
- **Why it looks reasonable:** The author reasons "this stance demands rigor, so
  rigorous things are its costs". Cross-billing keeps every file looking
  symmetric and is invisible without reading the siblings together.
- **How it was caught:** Cross-reading harm sections against each other, and
  asking which stance's named refuse-path each cost actually came from.
- **What it would have cost:** Three of four stances voting the same way on every
  refuse-or-proceed question, manufacturing consensus and hiding the tradeoff.
- **Instance:** see the set validation report.

### A one-sided sacrifice is filed as a shared win

- **Pattern:** A conflict is recorded under "resolved without escalation, serves
  both" when one stance gave something up and the other gained. The ledger makes
  the loss invisible.
- **Why it looks reasonable:** The design genuinely serves one objective well and
  the sacrifice is subtle. It reads as a clever resolution rather than a
  concession.
- **How it was caught:** Comparing the ledger row against the stance files and the
  status document, and finding a stance that recorded the same facts as a
  one-sided cost.
- **What it would have cost:** The set's only documented sacrifice filed as a win,
  while the open-conflict table read "none recorded yet".
- **Instance:** see the project registry.

### An axis is named for a resource no stance contends

- **Pattern:** An axis named `A-vs-C` where no stance maximizes the second term,
  because the second term is A's cost rather than anyone's objective.
- **Why it looks reasonable:** The cost of an objective is obviously relevant to
  its axis, so naming the axis after the cost feels complete. The missing step is
  that a two-sided axis needs a defender for each side.
- **How it was caught:** Asking, for each axis name, which stance maximizes the
  second term. The answer was none.
- **What it would have cost:** A stated ambition of the project with no
  representative, so the set could not see the project's own goal.
- **Instance:** see the project registry's unrepresented-stakes table.

### The winning side of a recorded decision has no stance

- **Pattern:** `Decisions that sacrificed a stance` names the losing stance, but
  the objective that won has no stance file. The decision is attributed to a
  value the set does not contain.
- **Why it looks reasonable:** The decision was made by a domain review skill,
  and review skills and stances look interchangeable from a distance.
- **How it was caught:** For each sacrifice row, asking which stance represents
  the side that won.
- **What it would have cost:** A tradeoff recorded as settled by a party not
  present; a later reader cannot reconstruct why the winner won.
- **Instance:** see the project registry.

### An escalation trigger names today's vocabulary or today's number

- **Pattern:** A gate fires on an identifier blacklist or on a specific ceiling in
  a specific test file. The trigger is a fact about the current code, not about
  the value the stance protects.
- **Why it looks reasonable:** The list encodes real past incidents, and a
  concrete gate feels more actionable than an abstract one — and greps easily.
- **How it was caught:** Asking whether the trigger survives a rename of the
  mechanism it protects.
- **What it would have cost:** A benign rename blocked, and a genuine violation
  in different words passed — the failure stances exist to prevent.
- **Instance:** see the set validation report.

### A stance file is seeded with its author's open findings

- **Pattern:** The stance's `## Attacks` or `## Bad patterns` contains defects
  the author found while reading the code, written as specifics tied to current
  functions. The reviewer then finds exactly those, reports a productive pass, and
  the pass measured the author rather than the design.
- **Why it looks reasonable:** A stance is supposed to be grounded in this
  project, so real examples feel like good evidence. The author is being helpful.
  **Grounded:** in one pass, every non-buffer finding a reviewer reported already
  appeared, almost verbatim, in that reviewer's own stance file.
- **How it was caught:** Comparing reviewer findings against the stance file they
  came from, and noticing that the "new" findings were the file's attack list.
- **What it would have cost:** Verification theatre — a set that appears to
  produce findings which were decided before the review began.
- **Instance:** see the project registry's evidence table.

## Process failures

The shapes above are failures of a *design*. These are failures of a *pass*, and
they are harder to notice because a failed pass still produces a report.

### The pass found conflicts it was told to expect

- **Shape:** Every reported conflict matches the registry's predicted pairs, and
  every finding maps onto a stance's attack list.
- **Why it looks reasonable:** A consistent result looks like a good set.
- **Check:** Count findings that surprised the orchestrator. Zero is a warning,
  not a success. Send one candidate conflict to a stance that had no finding on
  that surface and see whether it objects; a pass where nobody ever objects is
  not adversarial.
- **Cost:** Confirming a prediction instead of testing a design.

### The pass found nothing and that was accepted

- **Shape:** No conflicts, no buffers, few findings, closed as "the design is
  fine".
- **Why it looks reasonable:** The clean result is plausible and everyone wants
  to move on.
- **Check:** A clean pass is legitimate only with evidence that the stances could
  have fired: at least one finding per reviewed stance, or a recorded statement
  that the target was too small for that stance's attacks. A stance that was
  reviewed twice on a surface it claims and produced no `new` findings is either
  satisfied or badly written, and the two need different responses — see *the
  silent stance* in [stance-design.md](stance-design.md).
- **Cost:** Silent stances accumulate and the set stops being an instrument.

### The contest was skipped because the conflict "looked obvious"

- **Shape:** A conflict is escalated or resolved with only the first reviewer's
  account of what the opponent loses.
- **Why it looks reasonable:** The opponent's cost seems clear enough to state on
  its behalf, and asking again feels like process for its own sake.
- **Check:** Does the escalation quote the *opposing stance's* own words? If the
  only source is the first reviewer's `Cost to others` line, the conflict was not
  contested and must not be called essential.
- **Cost:** A strawman escalation, presenting a decided question as a live one.

### The measurement outcome was recorded as a resolution

- **Shape:** A conflict becomes "under measurement", the measurement never runs,
  and the current design quietly persists.
- **Why it looks reasonable:** Recording a follow-up looks responsible, and the
  conflict table is no longer showing "open".
- **Check:** Every "under measurement" row names an owner, the measurement, and
  the date or condition at which it stops being pending.
- **Cost:** The status quo wins by default, which is the tiebreak this protocol
  exists to prevent.

### The five-stance quota deferred a real axis

- **Shape:** A candidate axis has evidence on both sides, but the set is already
  at its working range, so the axis is deferred with "the set already carries
  five stances". The deferral looks like scope discipline and is a count gate.
- **Why it looks reasonable:** A smaller set is easier to review, and the
  deferred axis has not yet caused a visible failure. The cost is invisible
  because the losing interest has no reviewer.
- **Check:** For every deferred axis, replace the reason with the missing
  evidence. If the evidence exists, the axis is not deferred; it is suppressed.
- **Cost:** A real tradeoff stays unrepresented until a user or a production
  incident forces it, and the set reports itself complete in the meantime.

### The generated stance with no argument

- **Shape:** A stance skill is generated from a topology row. It has an
  objective and a payer, but its attacks, evidence, and escalation sections are
  empty or generic. The file passes the schema and cannot test a design.
- **Why it looks reasonable:** Generation guarantees consistency and removes
  hand-editing drift. The output looks like the other stance files.
- **Check:** Open the generated file and ask whether a reviewer could point at a
  diff and say "this violates it". If not, the file is a template.
- **Cost:** A complete-looking set that produces agreement, which is the most
  expensive kind of noise.

### The orphan check

- **Shape:** A surface has checks and an owner document, but no stance reads it
  and no unopposed stake is named. It survives because it is useful.
- **Why it looks reasonable:** The checks are good, and deleting them feels like
  losing knowledge. The missing owner is invisible in a checklist.
- **Check:** For every surface, name the stance or the unopposed stake. If
  neither exists, the check is a finding without a value.
- **Cost:** A check that cannot lose anything, so it can never tell the project
  what it is sacrificing.

### The invented payer

- **Shape:** A stance needs a payer to satisfy the topology rule, so the author
  names a plausible sibling or a generic "users" without evidence that the cost
  is real. The graph is green and the conflict is manufactured.
- **Why it looks reasonable:** The sibling does lose something in some scenario,
  and the rule says every stance needs a payer. The author is being thorough.
- **Check:** Ask for the recorded decision or observation where the payer
  actually bore the cost. If there is none, mark it as a latent payer or an
  unrepresented interest.
- **Cost:** A fake conflict that makes the set look adversarial while the real
  tradeoff remains unseen.

### The whole-component route

- **Shape:** The router starts from one changed surface, follows every stance to
  every opposition, and selects the entire connected component. A local change
  triggers a full review, so the orchestrator either runs everything or silently
  trims the list.
- **Why it looks reasonable:** Closure sounds rigorous, and a connected graph
  feels like a complete review. The cost is hidden in reviewer time.
- **Check:** Does the route select an axis because the changed surface declares
  it contends, or only because a selected stance happens to touch it? The latter
  belongs under "axes touched but not declared", not in the automatic set.
- **Cost:** Review fatigue, then silent skipping, then a set nobody trusts.

### The resolved decision that was never implemented

- **Shape:** A decision is recorded as resolved, the registry stops showing it as
  open, and the code still does the old thing. The next reader treats the
  decision as settled and does not re-check it.
- **Why it looks reasonable:** The design question really was answered, and the
  implementation feels like a separate task. "Resolved" is the only status the
  ledger has.
- **Check:** Every decision names a status (`decided`, `decided_not_implemented`,
  `implemented`, `verified`) and an implementation or test. A route that touches
  the decision surfaces it.
- **Cost:** A decision that dominates the document but not the design, which is
  the exact drift the stance set exists to prevent.

### The no-conflict pass was treated as a failed pass

- **Shape:** A reviewer finds no conflict, and the orchestrator pushes it to
  produce one because "a review that produces no conflict has not been run
  properly". The resulting conflict is manufactured.
- **Why it looks reasonable:** The set exists to find tradeoffs, and a clean
  result feels like the reviewer did not try.
- **Check:** A no-conflict result must name the axes checked and why the design
  already satisfies them. That is a result. Silence is the failure.
- **Cost:** Reviewers learn to reward conflict production, and the set becomes a
  generator of noise.

## How to add an entry

Add a `## Patterns` entry when a pass found a **design or contract deviation from
the project's stated intent** — not a bug, not a style complaint, not a missing
test. The test is: could a defender argue for it in good faith? Ground the
defender's argument in something that was actually written or said.

Add a `## Process failures` entry when a pass itself went wrong in a way a later
orchestrator could repeat. These are the most valuable entries and the least
likely to be written, because the orchestrator is judging itself.

Bugs and missing tests are not harvested. A library full of obvious mistakes
trains reviewers to check for things nobody would ever do.
