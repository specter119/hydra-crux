# Discovery template

The canonical discovery map is generated from `.agents/review-graph.toml` into
`docs/stances.md`. Use this template to collect the evidence **before** writing
the graph. The generated map is the readable view; the graph is the topology.

A map that lives only in a scratch or ignored directory cannot be cited by the
registry later, and a later reader cannot tell whether a pair was argued or
assumed.

## 1. Stakes

One row per objective the project would sacrifice other things to keep. Evidence
must be `path#section`, not a paraphrase.

| Id  | Objective (one line) | Evidence           | What it would demand                |
| --- | -------------------- | ------------------ | ----------------------------------- |
| S1  | <objective>          | `<path>#<section>` | <a concrete change to this project> |

A row is rejected if the evidence is a subsystem name, a module, or a generic
virtue with no tradeoff attached. "The parser must be good" is not a stake.

## 2. Oppositions

One row per pair. Every column is required; see the four-part rule in the forge
skill's step 2.

| Pair     | Contended resource    | A demands | B resists         | B demands | A resists         | Recorded decision                     |
| -------- | --------------------- | --------- | ----------------- | --------- | ----------------- | ------------------------------------- |
| S1 vs S2 | <quantity or surface> | <change>  | <what B protects> | <change>  | <what A protects> | `<path>#<section>`, or `hypothetical` |

A pair whose `Recorded decision` is `hypothetical` is kept and marked, and does
not count as settled until a change exercises it.

## 3. Surfaces and contention

One row per surface. A surface is a place to look, not a value. `Contends` names
the axes the surface actually exercises; this is what keeps a local change
local. `Owner` is either the stances that read it or an unopposed stake.

| Surface                      | Owner (stances or unopposed stake) | Contends | Route hints            |
| ---------------------------- | ---------------------------------- | -------- | ---------------------- |
| `<project>-<surface>-review` | `<stance>` or `unopposed: S<n>`    | `<axis>` | `<paths and keywords>` |

A surface may serve several stances and an unopposed stake at the same time. That
is not a contradiction; it means the check protects more than one interest.

## 4. Unopposed stakes

Stakes found with no real opponent. Say why each is unpaired, and what check
covers it instead. An unopposed stake usually needs a domain review skill, not a
stance.

| Id   | Why unpaired | Check that covers it |
| ---- | ------------ | -------------------- |
| S<n> | <reason>     | `<skill or test>`    |

## 5. Missing stakes

Decision themes the documents show, that no stake represents. These are the
places where the set will fail to see a tradeoff, and they are worth recording
even when nothing is done about them.

| Theme   | Where it appears   | Why no stake holds it |
| ------- | ------------------ | --------------------- |
| <theme> | `<path>#<section>` | <reason>              |

## 6. Latent payers

A payer named in a stance's accepted harm that has no stance yet. Record it; do
not invent a stance to make the graph complete.

| Payer                        | What it pays for | Evidence           | Why no stance yet                            |
| ---------------------------- | ---------------- | ------------------ | -------------------------------------------- |
| \<person, role, or interest> | <cost>           | `<path>#<section>` | \<not recurring / no owner / not yet argued> |

## 7. Candidate stance set

The stances to author, one per side, each naming the pairs it belongs to. A
stance holds **one** objective in **one** direction; it may belong to more than
one pair. A stance that owns both sides of a pair is a balanced reviewer, and a
balanced reviewer finds nothing.

| Stance                     | Objective                        | In pairs |
| -------------------------- | -------------------------------- | -------- |
| `<project>-<stake>-stance` | <one direction of one objective> | S1 vs S2 |

There is no target count. A stance may appear in several pairs; a pair may have
two or more sides. The count follows the evidence.

## 8. Deferred axes

Axes considered and not forged. The reason must be semantic; "the set is
already full" is not a reason.

| Axis   | Stakes   | Reason                      | Forge when                         |
| ------ | -------- | --------------------------- | ---------------------------------- |
| <axis> | <stakes> | <missing evidence or owner> | <the evidence that would forge it> |

## 9. Deviations

If authoring departs from this map — a pair dropped, an axis deferred, a stance
split or merged — record it here with the reason. An unrecorded deviation is how
a set silently loses the opposition it was built for.
