# Luwu migration example

This directory is a migration fixture, not a copy of the Luwu repository. It
shows the split hydra-crux now expects:

- `.agents/review-graph.toml` owns the **topology**: stakes, stances, surfaces,
  oppositions, payers, decisions, and unrepresented interests.
- `.agents/skills/luwu-*-stance/SKILL.md` and
  `.agents/skills/luwu-*-review/SKILL.md` own the **prose**: objectives,
  attacks, checks, evidence, and scope boundaries.
- `.agents/skills/luwu-stance-registry/SKILL.md` and `docs/stances.md` are
  generated indexes. They are not the place to edit.

The paths inside the graph are relative to the Luwu repository. The fixture is
validated without path existence because it lives in the hydra-crux repository.

## Why nine stances

The old set had five stances for three axes. Two axes with recorded sacrifices
were deferred because the set was already at its working range:

- `authority-vs-completion` (`S5` vs `S6`)
- `equivalence-vs-noise` (`S8` vs `S9`)

The owner documents already record both sides of both axes. Forging them adds
four partisan stances. `S4` (continuable evidence) already participates in two
axes, so five axes produce nine stances, not ten. Nine is the result of the
evidence, not a new quota.

The graph does not require nine. A project with three stances passes the same
checks. A project with a stance that has no payer, a surface with no owner, or a
deferred axis justified by a count does not.

## What is generated

```sh
python3 ../../skills/hydra-crux/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml \
  generate \
  --out .agents/skills \
  --docs-out docs
```

This writes only the registry and the discovery map. It does not overwrite the
stance or surface prose. `generate --views` is available when a project wants
hydra-crux to own the skill bodies too, but that is an explicit choice, not the
default.

## How to route a change

```sh
python3 ../../skills/hydra-crux/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml \
  route --changed src/luwu/apply.py --format markdown
```

The route selects surfaces by path or keyword, then adds both sides of the axes
those surfaces declare in `contends`. It does not transitively add every axis a
stance happens to touch. Axes that a selected stance touches but no selected
surface declares appear under `Axes touched but not declared`, so the
orchestrator can decide whether to add them.

The route also lists the prior decisions the change must re-check, including
their status and reopening condition. A decision that is
`decided_not_implemented` is visible as such; it is not treated as done.

## Applying this to Luwu

1. Copy `.agents/review-graph.toml` into the Luwu repository.
2. Add the four new stance skills in `.agents/skills/`:
   `luwu-answerable-authority-stance`, `luwu-operational-completion-stance`,
   `luwu-proven-equivalence-stance`, and `luwu-quiet-signal-stance`.
3. Replace the hand-authored `luwu-stance-registry` body with the generated
   registry. Keep the registry as a generated view.
4. Add `contends` to each review surface's graph entry. A surface that does not
   declare an axis will show up as an unclosed axis instead of silently
   expanding the review.
5. Remove the sentence "A review that produces no conflict has not been run
   properly" from the old registry. Replace it with the rule that a no-conflict
   result must name the axes checked and why the design already satisfies them.
6. Keep `luwu-primitive-reuse` as a `before-write` surface. It is a prevention
   entry, not a review phase.
7. Keep the seven review skills as surface prose. Remove their independent
   stance declarations and adjudication procedure; they are checks, not a second
   review meta-system.

## What this fixture does not claim

- It does not claim the four new stances are complete. They are the minimum
  honest set supported by the owner documents.
- It does not claim the two open conflicts (C-1b and C-2) are resolved.
- It does not claim the five unrepresented interests should become stances.
  They are recorded so the gap stays visible.

Structural replacement and semantic replacement are different claims. This
fixture demonstrates the former: the old entry points are gone, the old checks
are reachable, and a change routes to both sides of the axes it declares. It
does not demonstrate the latter. Whether every old value survived, whether a
new axis is real, or whether a surface has taken back a verdict still requires
a prose audit and a real review pass; a valid graph cannot certify it.

## Repeated runs

This fixture is the result of a one-time migration. Do not run the migration
prompt again on the same project. Later changes are evolutions: read the graph,
add or retire the smallest entity with evidence, and log the change. See the
"Evolve an existing topology" section in `hydra-crux/SKILL.md`.
