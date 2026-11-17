# Discovery template

Use this worksheet to collect evidence **before** writing
`.agents/review-graph.toml`. It is an authoring aid, not generated output. Keep
the cited evidence in durable owner documents so a later reader can distinguish
an argued pair from an assumed one.

## 1. Stakes

One row per objective the project would sacrifice other things to keep. Evidence
must be `path#section`, not a paraphrase.

| Id  | Objective (one line) | Evidence           | What it would demand                |
| --- | -------------------- | ------------------ | ----------------------------------- |
| S1  | <objective>          | `<path>#<section>` | <a concrete change to this project> |

Reject a row whose evidence is only a subsystem, module, or generic virtue with
no tradeoff. "The parser must be good" is not a stake.

## 2. Oppositions

One row per candidate pair; see the opposition test in
[stance-design.md](stance-design.md#the-opposition-test).

| Pair     | Contended resource    | A demands | B resists         | B demands | A resists         | Decision evidence  |
| -------- | --------------------- | --------- | ----------------- | --------- | ----------------- | ------------------ |
| S1 vs S2 | <quantity or surface> | <change>  | <what B protects> | <change>  | <what A protects> | `<path>#<section>` |

Every forged opposition needs at least one graph decision. If the choice is not
settled, record an open decision with an owner and next action rather than
calling a hypothetical joint outcome settled.

## 3. Surfaces and contention

A surface is a place to look, not a value. `Contends` names only the axes its
checks exercise. `Owner` is either a stance reader or an unopposed stake.

| Surface                      | Owner                           | Contends | Route hints                         |
| ---------------------------- | ------------------------------- | -------- | ----------------------------------- |
| `<project>-<surface>-review` | `<stance>` or `unopposed: S<n>` | `<axis>` | `<paths, exclusions, and keywords>` |

A surface may serve several stances, but each stake is either represented by a
stance or assigned as an unopposed stake, never both. A surface is not created
to give a stance a partner.

## 4. Unopposed stakes

Record stakes with no real opponent and the check that covers each. These
usually need a surface or test, not a stance.

| Id   | Why unpaired | Check that covers it |
| ---- | ------------ | -------------------- |
| S<n> | <reason>     | `<skill or test>`    |

## 5. Unrepresented interests

Record real interests with no stance, including candidate axes whose evidence is
incomplete. Do not omit them because the set already seems large.

| Interest   | Where it appears   | Why no stance holds it | Forge when                             |
| ---------- | ------------------ | ---------------------- | -------------------------------------- |
| <interest> | `<path>#<section>` | <reason>               | <evidence that would justify a stance> |

## 6. Latent payers

Record a payer named in accepted harm that has no stance yet. Do not invent one
to make the graph complete.

| Payer                        | What it pays for | Evidence           | Why no stance yet                            |
| ---------------------------- | ---------------- | ------------------ | -------------------------------------------- |
| \<person, role, or interest> | <cost>           | `<path>#<section>` | \<not recurring / no owner / not yet argued> |

## 7. Candidate stance set

Author one stance per side, each holding **one** objective in **one** direction.
A stance may belong to several pairs; a stance that owns both sides is a
balanced reviewer, not an opposition.

| Stance                     | Objective                        | In pairs |
| -------------------------- | -------------------------------- | -------- |
| `<project>-<stake>-stance` | <one direction of one objective> | S1 vs S2 |

There is no target count for any kind. Merge stances that push the same way on
every recorded decision; do not merge genuine contention to meet a quota.

## 8. Deviations

If authoring departs from this worksheet—a pair dropped, a stance split or
merged, an interest left unrepresented—record the reason. An unrecorded
deviation silently loses the opposition the set was built to test.
