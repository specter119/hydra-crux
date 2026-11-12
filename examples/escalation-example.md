# Worked example: one negotiable conflict, one essential conflict

Two conflicts from the same Acme Sync pass (see
[the example stance set](acme-sync/.agents/skills/acme-stance-registry/SKILL.md)).
The first is resolved by the agent. The second is escalated. The contrast is
the point: most conflicts are the first kind, and treating them like the second
is what makes the user stop reading.

## Negotiable: batch writes

**Reported conflict.** `acme-integrity-stance` requires every record to pass the
validation gate. `acme-throughput-stance` requires remote calls to be amortized
across a batch. The proposed fix from each reviewer made the other's objective
worse: per-record validation inside the batch loop looked like it forced a
remote call per record, and batching looked like it skipped the gate.

**Check the four-part test.**

1. Same resource? No. Integrity needs a *local* validation pass; throughput
   needs *remote* call amortization. The two reviewers both said "round trip"
   but meant different things.
2. No joint design? A joint design exists trivially.
3. Cost is the objection? No.
4. Irreversible? No.

Fails at step 1, so the conflict is negotiable. It did not need escalation.

**Buffer found.** Validate per record inside the batch, send per batch.
Verification is local and stays per record; amortization is remote and stays
per batch. Both objectives are fully served, not averaged.

**Recorded.** Registry row under `Resolved without escalation`, with
`tests/test_batch.py` asserting the remote call count so the buffer cannot
silently erode.

## Essential: schema v4 field removal

**Reported conflict.** The remote is removing field `legacy_id` in schema v4.
`acme-integrity-stance` requires that no record is persisted without full
validation against the declared schema, so v4 records must be written without
`legacy_id`. `acme-reversibility-stance` requires that the previous release can
resume, and the previous release reads `legacy_id` and treats its absence as
corruption.

**Check the four-part test.**

1. Same resource? Yes — the same records, in the same window, in one shape.
2. No joint design, demonstrated? Three were tried, including the opt-in
   exception the reversibility stance grants in its own objective:
   - *Dual-write both shapes for one release.* Fails: v4 validation rejects
     `legacy_id` as an undeclared field, so writing it is itself a violation.
   - *Keep a v3 reader behind a flag.* Fails: the flag does not help, because
     the rollback target is a release that predates the flag.
   - *Gate the v4 migration behind an off-by-default opt-in flag*, which is the
     exception the stance allows. Fails because the stance's bar is
     release-scoped, not tenant-scoped: after a rollback the previous release
     must serve every record, and opted-in tenants have already written
     v4-only records it cannot read.
3. Cost is the objection? No — no design works at any cost.
4. Irreversible? Yes — once v4 records exist, the previous release cannot read
   them, and the migration cannot be undone.

All four hold. The conflict is essential.

**Escalation, in the required format:**

```text
Conflict: C-1 — acme-reversibility-stance vs acme-integrity-stance
Resource: the shape of records written during the v4 migration window

Stance A says: Every release leaves the system in a state from which the
previous release can resume without operator intervention. A change that
consumes state the old code cannot read violates this.
Stance B says: No record is persisted unless every field was validated against
the remote's declared schema. A write path that cannot name its validation gate
violates this.

Buffer attempts:
  1. Dual-write both shapes for one release — failed because v4 validation
     rejects legacy_id as an undeclared field, so writing it is a violation.
  2. Keep a v3 reader behind a flag — failed because the rollback target
     predates the flag, so the flag is not present in the release we would
     roll back to.
  3. Gate the v4 migration behind an off-by-default opt-in flag, which is the
     exception the reversibility stance itself grants for operations that
     cannot meet the bar — failed because the stance's bar is release-scoped,
     not tenant-scoped: after a rollback the previous release must serve every
     record, and opted-in tenants have already written v4-only records that it
     cannot read. The flag moves the breakage, it does not remove it.

Option A: Write v4-only records during the migration; rollback requires a
  re-sync from the remote.
  Serves: integrity — every record validated against the declared schema.
  Costs: reversibility — rollback to 1.3.x is impossible; recovery is a full
    re-sync, estimated 6h for the largest tenant.
  Reversible: no, once v4 records exist.

Option B: Pin the remote to schema v3 for this release; defer v4.
  Serves: reversibility — the previous release can still read every record.
  Costs: integrity — records written during the window are validated against a
    schema the remote has already deprecated, so new remote fields are dropped
    silently until v4 ships.
  Reversible: yes, by dropping the pin.

What becomes irreversible: if Option A ships, the v3 read path can never be
restored for records written in the window.
Decision needed: Accept one-way rollback (A), or accept silent field loss for
one release (B)?
```

**Recorded.** C-1 in `Open essential conflicts`; after the answer, a row in
`Decisions that sacrificed a stance` naming whichever objective lost.

Note what the escalation does *not* do: it does not recommend, does not pick,
and does not soften the losing stance. It also does not bundle the batch-write
conflict into the same message.
