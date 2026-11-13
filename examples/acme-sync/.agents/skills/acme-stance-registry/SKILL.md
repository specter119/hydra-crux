---
name: acme-stance-registry
description: >-
  Use to find which stance owns a question in Acme Sync, which stances oppose
  each other, and which conflicts are still open. Read before assigning a
  stance review or recording a resolution. Do not use as a review stance
  itself.
disable-model-invocation: true
metadata:
  internal: true
---

# Acme Sync stance registry

The stances below are first-principles objectives, not checklists. They are
deliberately opposed: each one demands something another one pays for. A review
that produces no conflict has not been run properly.

This is a worked example of a generated registry. The project, the stances, and
the history are illustrative; the structure is what a real registry should
look like.

## Stances

| Stance                      | Axes                                                    | Objective (one line)                             | Accepts                                                                     |
| --------------------------- | ------------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------- |
| `acme-integrity-stance`     | correctness-vs-throughput, reversibility-vs-integrity   | Persist only verified records; report the rest   | Slower writes, no bulk fast path, refuses writes when schema is unavailable |
| `acme-throughput-stance`    | correctness-vs-throughput, reversibility-vs-throughput  | Amortize every remote interaction across records | Batch-level blast radius, idempotent-replay assumptions                     |
| `acme-reversibility-stance` | reversibility-vs-integrity, reversibility-vs-throughput | Every release can be undone without an operator  | Keeps old readers alive, costs code paths and inline compaction             |

## Oppositions

Each row is a pair that must be reviewed together. A pass that reviews only one
side of a row is not a stance review.

| Pair                                                    | Contended resource             | Typical essential conflict                                       |
| ------------------------------------------------------- | ------------------------------ | ---------------------------------------------------------------- |
| `acme-integrity-stance` vs `acme-throughput-stance`     | Remote round trips per record  | Verification needs a round trip the batch was meant to amortize  |
| `acme-reversibility-stance` vs `acme-integrity-stance`  | Code paths that can be deleted | Dual-read keeps a legacy path the integrity stance wants removed |
| `acme-reversibility-stance` vs `acme-throughput-stance` | Inline work in the write path  | Reversible writes cannot compact inline                          |

## Unrepresented stakes

Decision themes that move a real resource but have no stance on one side.
Recorded so a pass does not mistake silence for agreement.

| Stake             | Where it appears                    | Why no stance holds it                                                                                                            |
| ----------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Delivery momentum | `docs/changelog.md` release cadence | The reversibility stance names momentum as a cost it pays, but no stance maximizes shipping speed, so the axis reads as one-sided |

## Contract surfaces

Decisions from a stance conflict land in these places. A resolution that
cannot name its file here is incomplete.

- `docs/reference.md` — write contract, remote schema, rate-limit policy
- `docs/maintenance.md` — release process, flag defaults, rollback procedure
- `src/acme/validate.py` — the single validation gate
- `src/acme/batch.py` — batch size and construction
- `src/acme/migrate.py` — dual-read window

## Resolved without escalation

Buffer-space merges that both stances accepted. Recorded so the next pass does
not relitigate them. A resolution here is not a compromise of the objectives;
it is a design that serves both.

| Conflict                                  | Resolution                                                                                           | Serves | Evidence                                   |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------ |
| Integrity vs throughput on batch writes   | Validate per record inside the batch, send per batch. Verification is local, amortization is remote. | both   | `tests/test_batch.py`, call count asserted |
| Reversibility vs throughput on compaction | Compaction deferred to a post-sync step behind `--compact`, off by default                           | both   | `src/acme/cli.py`, `tests/test_cli.py`     |

## Open essential conflicts

Conflicts waiting on a user decision. Each must follow the format in
[escalation.md](../../../../../skills/hydra-crux/references/escalation.md).

| Conflict                    | Pair                       | Status | Decision record |
| --------------------------- | -------------------------- | ------ | --------------- |
| C-1 schema v4 field removal | reversibility vs integrity | open   | pending         |

## Decisions that sacrificed a stance

When the user resolves an essential conflict, the losing stance is not deleted.
Record the sacrifice so the next reviewer sees the cost.

| Decision                                    | Sacrificed stance           | What was given up                                              | Why                                                                    |
| ------------------------------------------- | --------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `docs/decisions/0003-drop-legacy-reader.md` | `acme-reversibility-stance` | Rollback to 1.3.x is no longer possible after the v3 migration | Remote deprecated the v2 endpoint; keeping the reader was not possible |

## Evidence

Proof that the set is alive. Not a log of every review — only passes that
changed something.

| Date       | Pass                     | Conflict found                                                     | Effect on design or set                                   |
| ---------- | ------------------------ | ------------------------------------------------------------------ | --------------------------------------------------------- |
| 2026-10-02 | v1.2.1 bulk importer fix | integrity vs throughput: importer bypassed the gate to stay fast   | merged (per-record gate inside batch); registry row added |
| 2026-10-19 | v1.3.0 revert            | throughput vs integrity: per-record confirmation tripled sync time | merged (confirmation dropped, remote response trusted)    |
| 2026-11-04 | schema v4 proposal       | reversibility vs integrity: field removal cannot dual-read         | escalated as C-1; awaiting user decision                  |
