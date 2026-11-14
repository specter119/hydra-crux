---
name: luwu-operational-completion-stance
description: >-
  Use only when assigned by a stance-review orchestrator. Argues that the
  routine loop finishes on a real profile without hand-edited files or deleted
  baselines, and that the previous manager becomes genuinely removable. Do not
  use as a standalone checklist.
disable-model-invocation: true
metadata:
  stance-axis: authority-vs-completion
  opposes: luwu-answerable-authority-stance
---

# Luwu operational completion stance

## Objective

The routine loop finishes on a real profile without hand-edited files or
deleted baselines, and the previous manager becomes genuinely removable.

## Accepts this harm

- **`luwu-answerable-authority-stance` pays**: batch adoption and partial apply
  give up per-resource answerability.

## Attacks

- A per-resource stop leaves the operator with a half-migrated profile and no
  safe next step.
- A conflict rule that requires a person for every field makes the daily loop
  unusable.
- A preview that cannot be applied without editing files by hand is not a
  completion path.
- A migration that depends on the old manager staying installed has not
  completed.
- A baseline that must be deleted to make progress destroys the evidence the
  next run needs.

## Evidence to demand

- A run on a real profile, not a fixture.
- Counts of manual edits, completed resources, and skipped resources.
- A removal test showing the old manager is no longer required.
- The operator's next safe action after a partial run.

## Does not own

- Who may change a value.
- Whether the authorizing bytes were re-read at the write boundary.
- Whether the result exposes sensitive values.

## Escalates when

Completion requires adopting undeclared content or keeping the old manager as a
permanent fallback.

## Stable core and changing contract

**Stable core:** the routine loop completes on a real profile.

**Changing contract:** batch size, interface, and migration sequence.

## Good patterns

- Apply the resources that need no decision and report the ones that do.
- Advance the baseline after a successful apply.
- Show an adoption preview before a batch adopt.

## Bad patterns

- Delete the baseline and re-adopt to make the loop finish.
- Hand-edit the manifest and call the migration complete.
- Keep the old manager installed forever as an undocumented fallback.
