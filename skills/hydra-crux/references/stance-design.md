# Stance design

Purpose: turn a project's objectives into opposed stances that produce real
conflicts instead of parallel checklists.

## What a stance is

A stance is a commitment of the form:

> **I will sacrifice X to protect Y, and I accept that this costs Z.**

All three parts are required. A statement with only Y is a value. A statement
with only X is a complaint. A statement with no Z is a wish.

Example of a real stance:

> **Data-integrity stance.** I will reject a write rather than persist a value I
> could not fully validate, and I accept that this makes the system refuse some
> operations a lenient implementation would have completed.

Example of a non-stance:

> **Quality stance.** I care about correctness and maintainability.

The second cannot lose anything, so it can never conflict, so it produces no
information.

## Surface and stance are different objects

A surface is a place to look: a file boundary, a contract, a parser, a CLI. It
owns checks, required evidence, and a scope boundary. A stance is a value that
would sacrifice something else. It owns an objective, a payer, and an escalation
condition.

The same surface can be read by several stances. The same stance can read
several surfaces. This is many-to-many, not a hierarchy. A surface that starts
arguing for a value has become a stance by accident; a stance that starts
listing checks has become a surface by accident. Move the text to the right
object.

## Anatomy of a stance file

Each section exists to prevent one specific failure:

| Section                         | Prevents                                                  |
| ------------------------------- | --------------------------------------------------------- |
| Objective                       | A reviewer optimizing for whatever the prompt implied     |
| Why this project needs it       | A generic stance copied from a blog post                  |
| Accepts this harm               | A stance that quietly claims to have no cost              |
| Attacks                         | Findings that restate the objective instead of testing it |
| Evidence to demand              | Findings asserted without a path, line, or command        |
| Does not own                    | Every stance reviewing everything, then duplicating       |
| Escalates when                  | Local compromise that silently sacrifices the objective   |
| Stable core / changing contract | Freezing one implementation as the objective itself       |

The **Stable core and changing contract** section is borrowed from the
per-domain review skills in this repository: a stance owns a value, not a
current shape. When the contract changes, the stance survives; when the value
changes, that is a new stance and a user decision.

## The opposition test

A set of stances is valid when, for every stance, there exists a plausible
design that maximizes it and measurably harms at least one other stance in the
set. Test each stance by answering:

1. Name a concrete change to this project that this stance would demand.
2. Name the stance that change makes worse, and the resource it costs.
3. Name a change that the other stance would demand which this one resists.

If step 2 has no answer, the stake is unopposed. Do not manufacture an opponent
to keep it. Record it as an unopposed check or an `unrepresented` interest. An
unopposed check is useful; an unopposed stance is a value with no cost, and it
adds review noise.

If step 1 has no answer, the stance is satisfied by the current design. Keep it
only if the design is fragile enough that a future change could break it; say so
explicitly in the registry. A named satisfaction is a result; silence is not.

Run the opposition test on a real recent change, not on a hypothetical. A set
that passes only in the abstract will fail in the first review.

## Choosing the axis of opposition

Oppose stances along a contended resource, not along subsystem boundaries.
Subsystem-shaped stances ("the parser stance", "the CLI stance") partition the
review and then never meet. Resource-shaped stances meet constantly.

Resources that reliably produce essential conflicts:

- **Correctness vs availability** — reject the bad write, or serve the request.
- **Strictness vs compatibility** — validate everything, or accept what exists.
- **Latency vs memory** — recompute, or cache and invalidate.
- **Local simplicity vs system coherence** — one obvious module, or one shared
  primitive every module uses.
- **Feature breadth vs blast radius** — ship the capability, or keep every
  change reversible.
- **Explicitness vs ergonomics** — require the user to say it, or infer it.
- **Isolation vs reuse** — let components evolve independently, or give them
  one implementation.
- **Reversibility vs momentum** — keep the door open, or commit and move.

Pick the axes this project actually feels. A project that has never argued about
latency does not need a latency stance, however defensible it sounds. The number
of axes is evidence, not a target.

## Failure modes

**The checklist stance.** Sections of "consider X, consider Y" with no
objective. It produces the same findings as a general review and cannot
conflict. Fix: force an **Accepts this harm** line.

**The universal stance.** Objective so broad ("the system must be good") that
every stance agrees with it. Fix: narrow to a resource.

**The mirror stance.** Two stances that are the same objective phrased
positively and negatively. They conflict trivially and teach nothing. Fix:
oppose different resources, not the same one twice.

**The strawman stance.** A stance written so its demands are obviously wrong,
so the favored stance always wins. This is the most dangerous failure because
it looks like adversarial review while guaranteeing the conclusion. Fix: write
each stance in its strongest form, and have the orchestrator check that each
stance's demands were taken seriously — see
[escalation.md](escalation.md).

**The frozen implementation.** A stance that names a current module, flag, or
schema as its objective. When the implementation changes, the stance fights the
change instead of protecting the value. Fix: separate the stable core from the
changing contract in every stance.

**The silent stance.** A stance that produced no `new` findings in two
consecutive passes, on a surface the stance claims. The qualifier is the whole
rule: silence is only evidence when the stance had something to review, so a
pass that never touched its surface proves nothing either way. Where it did have
something to review, one of two things is true — the project already satisfies it
(record that, with the evidence), or its **Attacks** section is too vague to fire
(sharpen the attacks). Decide which; do not keep it undecided.

**The self-opposed stance.** An Objective with two clauses that can be satisfied
separately — "no durable state, and no removal without identity proof" — lets one
reviewer settle a conflict between the clauses privately, with nobody watching.
That is the averaging this instrument exists to prevent, performed by a single
agent instead of a committee. Fix: split the halves into two stances, or mark one
clause as a standing constraint the other may not trade against and say so in the
Objective. Two objectives joined by "and" is a defect, not thoroughness.

**The stance that should have been a rule.** An attack or bad pattern a lint
rule, a type, or a test could catch on every change. It costs a reviewer and a
briefing to enforce what the toolchain enforces for free. Fix: write the rule
and delete the entry; only a tradeoff no rule can decide belongs in a stance.
A skill may ship the rule itself as `scripts/lint_*.py`, which the repository
runs on every commit.

## Sizing the set

There is no target count for any kind. The count follows the evidence:

- one stance per **side** of an axis, not one per axis;
- one stance may participate in several axes;
- one surface may be read by several stances;
- an unopposed stake is a check, not a stance.

Two stances that push the same direction on every recorded decision are one
stance. Merge them and say so. Two stances that genuinely contend are not merged
because the set "already has enough"; that is a count gate, not a design
decision.

The `luwu` fixture graph under `tests/fixtures/` shows an evidence-driven count.
It is not a target. A project with three stances is not incomplete.

Prefer sharper stances, not fewer stances. A stance set is a lens; a vague lens
is worse than several sharp ones.
