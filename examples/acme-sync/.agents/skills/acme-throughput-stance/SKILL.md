---
name: acme-throughput-stance
description: >-
  Use when reviewing Acme Sync batching, concurrency, caching, streaming, or
  anything that decides how many records move per unit time. Test whether a
  change adds a per-record round trip or serialization point. Do not use for
  validation correctness or rollback-scope review.
disable-model-invocation: true
metadata:
  internal: true
  stance-axis: correctness-vs-throughput, reversibility-vs-throughput
  opposes: acme-integrity-stance, acme-reversibility-stance
---

# Acme throughput stance

Acme Sync is used against remotes that charge per request and rate-limit
aggressively. A sync that is correct but takes eleven hours is a sync users
abandon, and an abandoned sync leaves the local store stale, which is a
correctness problem the integrity stance cannot see. This stance exists because
the project's users measure it in records per second.

## Objective

**Amortize every remote interaction across as many records as the remote's
contract allows, and never add a per-record round trip or serialization point
to a path that already batches.** A change that makes a batched path
per-record violates this stance, even if it makes that path more verifiable.

## Accepts this harm

This stance knowingly costs verification granularity, blast radius, and
rollback scope.

- **`acme-integrity-stance` pays**: batching means a partial failure affects a
  whole batch, and a batch-level retry can re-send records that already
  landed, so the system has to tolerate idempotent replay rather than assume
  exactly-once. A record that needed per-record verification waits for the
  batch it was bundled into.
- **`acme-reversibility-stance` pays**: a batch is the smallest unit that can
  be undone cheaply, so undoing one bad record means replaying or repairing
  the batch it belonged to.

## Attacks

- A validation or transformation inserted inside the per-record loop of a
  batched path, turning O(1) remote calls into O(n).
- A round trip added to confirm a write that the remote's response already
  confirms.
- A lock or mutex held across a batch that serializes otherwise independent
  batches.
- A cache read that misses on every record because the key includes a
  per-record nonce.
- Retry logic that sleeps the whole batch for a single record's transient
  error.
- A "safe" default that reduces batch size to 1 when the remote errors once.

## Evidence to demand

A finding must include the path and line, the number of remote calls the
change adds per record or per batch, and either a benchmark or a counted call
trace. "This will be slow" is a hypothesis.

## Does not own

- Whether the records written were verified → `acme-integrity-stance`
- Whether a batch can be undone → `acme-reversibility-stance`
- Remote rate-limit policy, which is owned by `docs/reference.md`

## Escalates when

- The remote's contract cannot express a batch operation that the required
  validation needs, so throughput and verification genuinely need different
  round trips.
- Meeting a stated latency target requires tolerating unchecked records.
- A batch size that is safe for the remote's rate limit is smaller than the
  batch size that is correct for partial-failure recovery.

## Stable core and changing contract

The stable value is: **remote interaction cost is amortized, not paid per
record.** The current contract expressions are the 500-record batch cap in
`src/acme/batch.py`, the connection pool size, and the `--concurrency` flag.
These may change when evidence warrants it. What may not change is that a
batched path stays batched.

When the contract changes, measure remote calls per record before and after and
require the measurement in the change. Do not defend the current batch size
merely because it is current; do reject any change that makes the amortization
implicit or unmeasured.

## Good patterns

- Batch construction is separated from batch sending, so validation runs per
  record while the remote call stays per batch. Evidence:
  `src/acme/batch.py`.
- Transient errors are retried per record inside a batch without re-sending the
  whole batch. Evidence: `src/acme/retry.py`.

## Bad patterns

- A change that called the remote once per record to "confirm" each write,
  which tripled sync time. Evidence: `docs/changelog.md`, reverted in 1.3.0.
- A cache keyed on a per-record nonce, which never hit. Evidence:
  `tests/test_cache.py::test_nonce_key`.

Patterns are evidence about how the objective is violated here. The remote
contract stays owned by `docs/reference.md`.
