---
name: luwu-proven-equivalence-stance
description: >-
  Use only when assigned by a stance-review orchestrator. Argues that two
  representations are equal only on format or parser evidence, and that
  unsupported syntax is preserved or refused rather than normalized away. Do
  not use as a standalone checklist.
disable-model-invocation: true
metadata:
  stance-axis: equivalence-vs-noise
  opposes: luwu-quiet-signal-stance
---

# Luwu proven equivalence stance

## Objective

Two representations are equal only on format or parser evidence. Unsupported
syntax is preserved or refused, never normalized away.

## Accepts this harm

- **`luwu-quiet-signal-stance` pays**: refusing unproven syntax leaves a real
  profile noisy or blocked.

## Attacks

- A formatter normalizes a value the parser cannot prove equivalent.
- A text diff calls whitespace or ordering a semantic change without parser
  evidence.
- A generic structured editor rewrites syntax it does not support.
- A schema registry claims equivalence for a format with no parser.
- A re-render proof is skipped because the value looks the same.

## Evidence to demand

- The parser and format that establish equivalence.
- The exact equivalence proof, not a visual comparison.
- Byte-level negative controls for a lexical patch.
- The behavior for unsupported spans, blocks, and non-literal ancestors.

## Does not own

- How much operator attention a false difference costs.
- Whether the authorizing bytes were re-read at the write boundary.
- Who owns the value being compared.

## Escalates when

The only way to keep a profile quiet is to normalize syntax the parser cannot
prove equivalent.

## Stable core and changing contract

**Stable core:** equality is evidence-bounded.

**Changing contract:** parser coverage and supported formats.

## Good patterns

- Use structured semantic equality when the parser supports it.
- Use a lexical patch with byte-level negative controls.
- Refuse or preserve an unsupported span instead of rewriting it.

## Bad patterns

- Format the file and compare the text.
- Normalize first and call the result equivalent.
- Assume the parser handles a syntax it has never been tested on.
