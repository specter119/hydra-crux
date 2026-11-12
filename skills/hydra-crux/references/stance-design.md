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

If step 2 has no answer, the stance is not opposed. Either find its opposition
or delete it — an unopposed stance adds review cost and produces agreement,
which is the most expensive kind of noise.

If step 1 has no answer, the stance is satisfied by the current design. Keep it
only if the design is fragile enough that a future change could break it; say
so explicitly in the registry.

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

Pick the two to four axes that this project actually feels. A project that has
never argued about latency does not need a latency stance, however defensible
it sounds.

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

## Sizing the set

- 3 to 6 stances is the working range. Below 3 there is rarely a real
  opposition. Above 6, reviewers duplicate and the orchestrator cannot hold the
  cross-product.
- 2 to 4 oppositions. Every stance should appear in at least one.
- One stance per axis. If two stances share an axis and a direction, merge
  them.

Prefer fewer, sharper stances. A stance set is a lens, and more lenses make the
image dimmer, not clearer.
