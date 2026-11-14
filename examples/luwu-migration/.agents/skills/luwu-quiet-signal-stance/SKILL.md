---
name: luwu-quiet-signal-stance
description: >-
  Use only when assigned by a stance-review orchestrator. Argues that only
  consequential differences reach the operator, and that incidental text,
  formatting, and converged state do not present themselves as drift. Do not
  use as a standalone checklist.
disable-model-invocation: true
metadata:
  stance-axis: equivalence-vs-noise
  opposes: luwu-proven-equivalence-stance
---

# Luwu quiet signal stance

## Objective

Only consequential differences reach the operator. Incidental text, formatting,
and converged state do not present themselves as drift.

## Accepts this harm

- **`luwu-proven-equivalence-stance` pays**: normalizing incidental differences
  gives up proof that the bytes are equivalent.

## Attacks

- A plan reports every whitespace, ordering, or comment difference as drift.
- A converged template with a stale baseline produces a visible drift.
- A formatter is rejected even when it reduces false drift without changing
  ownership.
- A parser limitation makes the whole profile noisy instead of scoping the
  unsupported span.
- A status output makes the operator read machine detail to find the one
  consequential change.

## Evidence to demand

- A plan on a real profile, with the false differences counted.
- The consequential difference that remains visible after suppression.
- The handling of an unsupported span: scoped, preserved, or refused.
- The operator's next action, stated without reading the raw diff.

## Does not own

- Whether the parser can prove equivalence.
- Whether the authorizing bytes were re-read at the write boundary.
- Who owns the value being compared.

## Escalates when

Quietness requires hiding a difference the parser cannot prove incidental.

## Stable core and changing contract

**Stable core:** only consequential differences are surfaced.

**Changing contract:** formatter coverage and normalization rules.

## Good patterns

- Write the baseline only when a template has converged.
- Use structured equality instead of text equality.
- Report an unsupported span as a scoped question, not a whole-file drift.

## Bad patterns

- Show everything to be safe.
- Normalize silently and hope the difference was incidental.
- Suppress the whole file because one span is unsupported.
