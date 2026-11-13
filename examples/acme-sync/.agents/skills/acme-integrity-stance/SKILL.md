---
name: acme-integrity-stance
description: >-
  Use when reviewing Acme Sync write paths, validation, conflict resolution,
  retry semantics, or anything that decides whether a record is persisted.
  Test whether a change can persist a value the system could not fully verify.
  Do not use for throughput, batching, or rollback-scope review.
disable-model-invocation: true
metadata:
  internal: true
  stance-axis: correctness-vs-throughput, reversibility-vs-integrity
  opposes: acme-throughput-stance, acme-reversibility-stance
---

# Acme integrity stance

Acme Sync's entire value is that a record in the local store is the same record
the remote had. Every feature that trades verification for speed trades away
the only thing users cannot get elsewhere. This stance exists because the
project has already shipped one silent-corruption bug by batching past
validation.

## Objective

**No record is persisted unless every field was validated against the remote's
declared schema, and any record that could not be validated is reported rather
than written.** A write path that cannot state which validation gate admitted a
record violates this stance.

## Accepts this harm

This stance knowingly costs throughput, availability, and the ability to
delete legacy paths.

- **`acme-throughput-stance` pays**: per-record validation means no bulk fast
  path, and a batch of 10,000 records with one malformed entry stops at that
  entry rather than streaming past it. When the remote's schema is
  unavailable, this stance prefers refusing writes, so the batch waits on a
  schema read.
- **`acme-reversibility-stance` pays**: a write path that refuses unverified
  records cannot dual-write a legacy shape to keep an old reader alive, so
  the rollback window this stance depends on is narrower on every write.

## Attacks

- A batch or bulk path that constructs records without passing each one through
  the same validation gate as the single-record path.
- A default that adopts an undeclared value when the remote omits a field.
- Retry logic that re-sends a record after a partial write without re-reading
  what landed.
- Conflict resolution that picks a winner by timestamp when the two versions
  differ in a field the schema marks as non-mergeable.
- A cache that serves a value that was never validated because it was written
  by an older version of the code.
- Error handling that swallows a validation failure and continues the batch.

## Evidence to demand

A finding must include the path and line of the write, the validation gate it
bypasses (or the gate it uses), and either a failing test or a command that
reproduces the unchecked write. "This looks racy" is a hypothesis.

## Does not own

- Whether the write path is fast enough → `acme-throughput-stance`
- Whether a change can be rolled back → `acme-reversibility-stance`
- Schema design itself, which is owned by `docs/reference.md`

## Escalates when

- A remote schema change makes a currently-validated field unvalidatable, and
  the only options are to stop syncing or to accept unchecked values.
- A user-facing feature requires writing records faster than per-record
  validation allows, and no batching design preserves the gate.
- Two sources of truth disagree about a record and neither is authoritative.

## Stable core and changing contract

The stable value is: **a persisted record is a verified record, or it is
reported.** The current contract expressions are the `validate_record` gate in
`src/acme/validate.py`, the `--strict` default on the CLI, and the schema
version pin in `src/acme/schema.py`. These may change when evidence warrants
it. What may not change is that every write path passes through one named gate.

When the contract changes, compare every write path against the gate and
require a test per path that proves the gate is reached. Do not defend the
current gate's shape merely because it is current; do reject any change that
makes validation implicit or unverifiable.

## Good patterns

- Single-record and batch paths both call `validate_record`; the batch path
  calls it per record before appending. Evidence: `tests/test_batch.py`.
- Unvalidatable records are collected into a `rejected` list surfaced to the
  caller rather than logged and dropped. Evidence: `src/acme/sync.py`.

## Bad patterns

- The pre-1.2 bulk importer built records directly from CSV rows and skipped
  the gate. Evidence: `docs/changelog.md`, fixed in 1.2.1.
- A cache layer that returned values written before schema v3 without
  revalidating them. Evidence: `tests/test_cache.py::test_legacy_entry`.

Patterns are evidence about how the objective is violated here. The write
contract stays owned by `docs/reference.md`.
