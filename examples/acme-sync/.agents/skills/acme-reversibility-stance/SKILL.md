---
name: acme-reversibility-stance
description: >-
  Use when reviewing Acme Sync migrations, schema version bumps, destructive
  operations, feature flags, or anything that decides how much state a change
  can leave behind. Test whether a change can be undone without operator
  intervention. Do not use for validation correctness or sync throughput.
disable-model-invocation: true
metadata:
  internal: true
  stance-axis: reversibility-vs-integrity, reversibility-vs-throughput
  opposes: acme-integrity-stance, acme-throughput-stance
---

# Acme reversibility stance

Acme Sync runs on operator machines that are not always reachable, and a bad
release has to be recoverable without a support call. Every change that commits
irreversibly converts a recoverable incident into a data-loss incident. This
stance exists because the project's 1.2.0 migration was not reversible and cost
a weekend of manual repair.

## Objective

**Every change leaves the system in a state from which the previous release can
resume without operator intervention, and any operation that cannot meet that
bar is gated behind an explicit flag that is off by default.** A change that
consumes state the old code cannot read violates this stance.

## Accepts this harm

This stance knowingly costs code paths, throughput, and delivery speed.

- **`acme-integrity-stance` pays**: keeping a migration reversible means
  keeping the old reader alive, and that reader is a second write path the
  integrity stance cannot delete because it still has to admit records.
- **`acme-throughput-stance` pays**: a reversible write may need to write both
  shapes, or defer a compaction that would otherwise run inline, so the
  batch's remote calls are paid twice or postponed.

It also slows delivery, and that cost is paid to nobody: no stance in this set
maximizes shipping speed. The registry records delivery momentum under
`## Unrepresented stakes`. Naming a cost with no owner is honest; inventing an
opponent for it would not be.

## Attacks

- A schema change that rewrites records in place with no dual-read window.
- A migration that deletes its source data before the new shape is verified.
- A feature flag whose default is on, so the escape hatch is unused by the time
  it is needed.
- A compaction or cleanup that runs before the release is known good.
- A destructive operation that has no dry-run mode.
- A rollback path that exists in documentation but has no test.

## Evidence to demand

A finding must include the path and line of the irreversible operation, the
state it consumes, and either a test that proves rollback or a statement of why
no test is possible. "This might be hard to undo" is a hypothesis.

## Does not own

- Whether the migrated records were validated → `acme-integrity-stance`
- Whether the migration is fast enough → `acme-throughput-stance`
- Release process, which is owned by `docs/maintenance.md`

## Escalates when

- A required migration cannot be made reversible without keeping a reader the
  integrity stance needs deleted.
- A throughput target can only be met by compacting inline, which removes the
  rollback window.
- Two releases must ship together, and only one of them can be rolled back.

## Stable core and changing contract

The stable value is: **a release can be undone without operator intervention.**
The current contract expressions are the dual-read window in
`src/acme/migrate.py`, the `--dry-run` flag, and the flag-default rule in
`docs/maintenance.md`. These may change when evidence warrants it. What may not
change is that every destructive operation has a tested undo.

When the contract changes, require a rollback test per destructive operation and
a named flag for anything that cannot have one. Do not defend the current
migration shape merely because it is current; do reject any change that makes
reversibility implicit or untested.

## Good patterns

- Schema v3 migration dual-reads v2 and v3 for one release before writing v3
  only. Evidence: `src/acme/migrate.py`.
- Compaction is behind `--compact`, off by default. Evidence: `src/acme/cli.py`.

## Bad patterns

- The 1.2.0 in-place rewrite had no dual-read window. Evidence:
  `docs/changelog.md`, repaired manually.
- A rollback path documented in `docs/maintenance.md` with no test. Evidence:
  `tests/` has no `test_rollback.py`.

Patterns are evidence about how the objective is violated here. The release
contract stays owned by `docs/maintenance.md`.
