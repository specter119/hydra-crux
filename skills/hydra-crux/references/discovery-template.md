# Discovery template

Copy to a path the project commits — commonly `docs/stances.md` or
`docs/decisions/stance-map.md`, following the project's own ownership rules. The
map is written **before** any stance file and is the gate the authoring step
must pass.

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
not count toward the set's opposition count until a change exercises it.

## 3. Unopposed stakes

Stakes found with no real opponent. Say why each is unpaired, and what check
covers it instead. An unopposed stake usually needs a domain review skill, not a
stance.

| Id   | Why unpaired | Check that covers it |
| ---- | ------------ | -------------------- |
| S<n> | <reason>     | `<skill or test>`    |

## 4. Missing stakes

Decision themes the documents show, that no stake represents. These are the
places where the set will fail to see a tradeoff, and they are worth recording
even when nothing is done about them.

| Theme   | Where it appears   | Why no stake holds it |
| ------- | ------------------ | --------------------- |
| <theme> | `<path>#<section>` | <reason>              |

## 5. Candidate stance set

The stances to author, one per side, each naming the pairs it belongs to. A
stance holds **one** objective in **one** direction; it may belong to more than
one pair. A stance that owns both sides of a pair is a balanced reviewer, and a
balanced reviewer finds nothing.

| Stance                     | Objective                        | In pairs |
| -------------------------- | -------------------------------- | -------- |
| `<project>-<stake>-stance` | <one direction of one objective> | S1 vs S2 |

## 6. Deviations

If authoring departs from this map — a pair dropped, an axis deferred, a stance
split or merged — record it here with the reason. An unrecorded deviation is how
a set silently loses the opposition it was built for.
