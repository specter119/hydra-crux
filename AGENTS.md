# Developing Hydra Crux

This file is the contributor and agent guide. It defines what each part of the
repository owns, how to change it without duplicating another part, and how to
verify the change. It is not user documentation; users start at `README.md`.

## Scope map

Every file has one audience and one job. If a fact does not fit a row, add a row
before adding the file.

| Path                       | Audience                          | Owns                                                       | Must not contain                                |
| -------------------------- | --------------------------------- | ---------------------------------------------------------- | ----------------------------------------------- |
| `README.md`                | users                             | what it is, install, use, how to read a review             | design rationale, contributor rules             |
| `docs/IDEA.md`             | users and contributors            | why the design exists, ablation, non-goals, open questions | install commands, runtime procedure             |
| `AGENTS.md`                | contributors and agents           | scope map, change rules, verification, anti-drift checks   | user-facing marketing, design essays            |
| `skills/*/SKILL.md`        | the agent at runtime              | the procedure the agent follows                            | project-specific topology, install instructions |
| `skills/*/references/*.md` | the agent at runtime              | deep procedure, templates, examples linked from `SKILL.md` | duplicated `SKILL.md` content                   |
| `skills/*/scripts/*.py`    | maintainers                       | graph engine, metadata and pass lint                       | prose judgment                                  |
| `.pre-commit-hooks.yaml`   | projects using pre-commit or prek | the installable lint hook id and command                   | prose, project topology                         |
| `tests/`                   | maintainers                       | verification; fixtures live in `tests/fixtures/`           | shipped examples, stance prose                  |
| `docs/assets/`             | users                             | images                                                     | text                                            |

The runtime skills ship from `skills/`, not `.agents/skills/`. `.agents/skills/`
is the project-scope discovery root; this repository is not a consumer of its
own skills.

## One fact, one home

1. **Link, do not restate.** If a fact already has a home, the second mention is
   a link. Duplicated prose is the copy nobody re-reads.
2. **README does not explain the design.** It says what the thing is and how to
   use it. The why belongs in `docs/IDEA.md`.
3. **IDEA does not give commands.** It explains the tradeoffs. Install and
   runtime steps belong in `README.md` or `SKILL.md`.
4. **`SKILL.md` does not restate its references.** It links to them and keeps
   the runtime decision small.
5. **Generated files are generated.** Do not hand-edit the registry; change the
   graph and regenerate.
6. **Fixtures are not documentation.** A graph kept only to exercise tests
   lives in `tests/fixtures/` and is not linked from user documentation.

## Checking skill prose

These rules apply to every change in this repository.

1. **Do not decide a semantic question about `SKILL.md` prose with pattern
   matching.** A substring check, a regex, a keyword list, or a heading match
   may segment a document or collect candidates, but it must not decide that a
   sentence is a verdict, a check, a scope boundary, an accepted harm, or a
   pass/fail result. Those decisions use a semantic method: role prototypes,
   embeddings, a model classification, or a human review. The failure this
   prevents is a regex that matches `must` inside a quoted old rule, or a
   heading named `Checks` that hides a verdict written under another heading.
2. **The restriction is scoped to Markdown prose in skills.** Graph metadata,
   TOML/JSON files, and script source are not prose. They may use structural or
   AST-like checks, including pattern matching, when the object is a schema, a
   reference, a path, or code structure. `hydra_graph.py lint` is the model:
   its object is structured review data, not the authored stance text.
3. **Prefer structured files for metadata.** An id, a link, a payer, a status,
   a path, or a decision record belongs in `.agents/review-graph.toml` (or
   another TOML/JSON file), not in Markdown prose. Markdown owns argument and
   narrative; structured files own facts a script must read. If a fact is
   duplicated into prose, the structured copy is the source of truth. Skill
   frontmatter is a structured block and may carry discovery fields such as
   `name`, `description`, `stance-axis`, and `opposes`; facts that a script must
   read for routing, coverage, or decisions still belong in the graph.

Structural parsing is not semantic judgment. Using Markdown headings and list
markers to split a document into sections is parsing. Using the same heading
text to conclude that everything under it is a check, a verdict, or a scope
boundary is a semantic judgment and falls under rule 1. When a template's
structure is known, a structural inventory may record its own labels; it must
not become the semantic classifier for a new skill set.

## Keeping the skill set honest

The product is a stance set, not a file count. These rules keep it from turning
into a schema or a quota.

- **No fixed skill count.** Stakes, stances, surfaces, axes, oppositions, and
  decisions follow the evidence; none has a target number. Report a symmetric
  payer graph or a perfect surface/stance matching as a quota signature; do not
  treat either as proof. The reasoning is in `docs/IDEA.md#no-fixed-count`.
- **No stance without a decision.** A stance needs a recorded decision it would
  sacrifice for. No decision, no stance.
- **No invented payer.** For a real payer without a stance, use `accepted_harm`
  without `payer_stance`; for an unowned interest, add an `[[unrepresented]]`
  row. Do not invent a stance.
- **No surface verdict.** A surface says how to check. If it starts deciding a
  tradeoff, the topology is missing a stance or the surface has absorbed one.
- **No prose in the graph.** The graph records relationships. The argument
  stays in `SKILL.md`.

## Change workflow

Before editing, find the scope row. Then follow the matching path.

### Add or change a stance

1. Name the decision it would sacrifice for and the payer of the harm.
2. Add the stance, its `accepted_harm`, and its `surfaces` to the graph.
3. Write the prose in `.agents/skills/<project>-<name>-stance/SKILL.md`.
4. Regenerate the registry.
5. Add or update a test that proves the stance fires on a control change.

### Add or change a surface

1. Name the check and the stance it serves, or the unopposed stake it records.
2. Add the surface, its `contends`, route paths, exclusions, and keywords to the
   graph.
3. Write the checks in `.agents/skills/<project>-<name>-surface/SKILL.md`.
4. Regenerate the registry.
5. Add a route test for the path it owns.

### Add a reference

1. Put the detail in `skills/hydra-crux/references/<name>.md`.
2. Link it from the `SKILL.md` step that needs it.
3. Do not paste the reference into `SKILL.md` or `README.md`.

### Change a decision

1. Record the new winner, the losing objective, and the payer.
2. Set the reopen condition, not a date.
3. Update the owner document the decision cites.
4. If the change reverses an earlier decision, say so in the graph, not only in
   a commit message.

### Remove an old skill

1. Extract its stable checks, evidence, and verdicts before deleting the prose;
   a renamed file is not a migration.
2. Delete the old skill and remove its name from `AGENTS.md`, `README.md`, every
   entry point, and every discovery path. Git history retains the old source.
3. Add each extracted fact's new home to the graph and regenerate the registry.

## Verification

Run all four before calling a change done:

```bash
python3 -m unittest discover -s tests
ruff check skills tests
bash scripts/validate-skills.sh
ty check
```

## Anti-drift checklist

- Does this sentence already exist elsewhere? Link instead of repeating it.
- Is this a fact a script reads? Move it to TOML.
- Is this a semantic judgment? Use a semantic method, not a regex.
- Is this a new stance? Name the decision and the payer.
- Is this a new surface? Name the check and the stance it serves.
- Does a project doc hardcode the skill's install path? Use a `HYDRA` variable
  or the command name; a home-directory path breaks on the next machine.
- Is the route the only selector? A hand-picked subset is an unrecorded route.
- Is a counterexample's full pattern in one home, with the pass record holding
  only its project-specific candidate and evidence?
- Is this a fixture? Put it under `tests/fixtures/`.
- Is this a stance set? Only `tests/fixtures/` holds one. A worked example is
  prose in `skills/*/references/`, never a stance set.
- Is this a new top-level document? Add its scope row first.
