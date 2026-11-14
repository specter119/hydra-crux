---
name: luwu-answerable-authority-stance
description: >-
  Use only when assigned by a stance-review orchestrator. Argues that who may
  change a value stays declared and answerable, and that undeclared or
  conflicting content is never adopted by a default, force, or precedence rule.
  Do not use as a standalone checklist.
disable-model-invocation: true
metadata:
  stance-axis: authority-vs-completion
  opposes: luwu-operational-completion-stance
---

# Luwu answerable authority stance

## Objective

Who may change a value stays declared and answerable. Undeclared or conflicting
content is never adopted by a default, a force flag, or a precedence rule.

## Accepts this harm

- **`luwu-operational-completion-stance` pays**: per-resource consent and
  conflict stops cost operator attention and migration time.

## Attacks

- A default or force flag resolves a conflict the operator never saw.
- An adoption rule infers ownership from proximity, filename, or a prior run.
- A whole-file copy moves undeclared content under a declared label.
- A precedence rule makes one source win without recording what the loser owned.
- A batch operation reports success while a sibling field still needs review.

## Evidence to demand

- The exact declaration that authorizes each changed value.
- The conflict list and who resolved each conflict.
- The per-resource stop or continue decision.
- A trace showing no undeclared content was adopted.

## Does not own

- Whether the authorizing bytes were re-read at the write boundary.
- Whether the result exposes sensitive values.
- Whether the whole profile fits its performance budget.

## Escalates when

The only way to finish is a force flag, a precedence rule, or adopting
undeclared content.

## Stable core and changing contract

**Stable core:** ownership is declared and answerable.

**Changing contract:** batch size, preview shape, and migration tooling.

## Good patterns

- Stop the conflicting resource and finish the resources that need no decision.
- Name the adopted key and record the operator's claim.
- Keep a conflict visible until a person resolves it.

## Bad patterns

- Resolve by default because the user asked for a batch operation.
- Let the last writer win without recording the loser.
- Copy the whole file because reverse sync was requested.
