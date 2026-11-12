# Hydra Crux

Adversarial architecture review driven by **opposing stances**, for projects
that want their tradeoffs surfaced instead of averaged away.

## The idea in one paragraph

A single reviewer told to "find problems" converges on the same three issues
every time, weighted by whatever the prompt mentioned. Opposed stances remove
that degree of freedom: each subagent is given one objective it must maximize,
and the harm it causes another objective becomes visible as a conflict instead
of disappearing into a compromise nobody chose. The product is not a pile of
findings and not consensus. It is a ledger of where objectives genuinely
collide, a record of which collisions were merged by finding buffer space, and
a decision from the user for the collisions that cannot both be satisfied.

## Two layers

This repository holds the **meta** layer. The **stance** layer is generated per
project.

| Layer  | Lives in                                             | What it does                                                         |
| ------ | ---------------------------------------------------- | -------------------------------------------------------------------- |
| Meta   | this repo, `skills/hydra-crux*`                      | Builds a stance set for a project; runs one review pass over it      |
| Stance | target project, `.agents/skills/<project>-*-stance/` | One partisan objective each, written against that project's evidence |

```text
hydra-crux/
├── skills/
│   ├── hydra-crux/                # build + maintain the stance set
│   │   ├── SKILL.md
│   │   └── references/            # stance design, templates, escalation, counterexamples
│   └── hydra-crux-review/         # run one review pass
│       └── SKILL.md
├── examples/
│   ├── acme-sync/.agents/skills/  # a filled stance set + registry
│   └── escalation-example.md      # one merged conflict, one escalated
├── scripts/                       # vendored skill validator
├── prek.toml                      # pre-commit hooks for this repo
└── .evidence/                     # reviews of this skill, gitignored
```

The published skills sit in `skills/`, not `.agents/skills/`. `.agents/skills/`
is the *project-scope* discovery root, and this repository is not a consumer of
its own skills — it ships them. Keeping them under `skills/` means cloning the
repo does not silently inject two skills into every agent session that opens it.

## Install

These are meta skills: they operate on whatever project you are in, so install
them **globally**. `npx skills add` finds exactly the two product skills, because
the worked examples are marked `metadata.internal` and stay out of package
installs.

```bash
npx skills add specter119/hydra-crux -g
```

`-g` installs into `~/.agents/skills/` rather than the current project. Add
`--all` to skip the interactive prompts, or `--skill hydra-crux` to take one.
From a clone, pass the path instead: `npx skills add . -g`.

With `skm`, which keeps a config and lock file so `skm sync` reproduces the set
on another machine:

```bash
uvx --from skm-cli skm install https://github.com/specter119/hydra-crux hydra-crux
uvx --from skm-cli skm install https://github.com/specter119/hydra-crux hydra-crux-review
```

It asks which agents to install for and records the answer in
`~/.config/skm/skills.yaml`; pass `--agents-includes <agent>` to skip that
prompt in a script.

For one project only, drop `-g` and run inside it. Skills are discovered at
`<project root>/.agents/skills/<name>/SKILL.md`, where the project root is the
nearest ancestor containing `.git`; the `name` must be kebab-case and match the
directory.

## Use

Two skills, split by **when the work happens**, not by topic.

| Skill               | Runs           | Owns                                                                                                                   |
| ------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `hydra-crux`        | between passes | The set's shape: discovery, opposed pairs, stance files, the registry, and the rules a change to the set must satisfy. |
| `hydra-crux-review` | during a pass  | One end-to-end review: bind, brief, reconcile, contest, classify, escalate, record, harvest.                           |

The split is deliberate. Escalating and harvesting are acts of a running pass, so
they belong to the review skill; the generator never performs a review, and the
reviewer never redesigns the set mid-pass. The procedure is in each `SKILL.md` —
this README does not restate it.

## What "ablation" means here

Not deletion of a design, and not consensus:

- **Merge the overlap.** A finding both stances agree on is one finding, not two.
- **Find buffer space first.** Most conflicts are negotiable — scope split, time
  split, explicit opt-in, measurement instead of policy, asymmetric cost, layer
  reframe — and the agent must try them before calling a conflict essential. The
  ordered list and the four-part test are in
  [escalation.md](skills/hydra-crux/references/escalation.md).
- **Keep the real conflicts.** An essential conflict is not averaged. It goes to
  the user, and the decision is recorded with the losing objective named.
- **Never delete a losing stance.** It stays installed, with the sacrifice
  recorded, so the cost of the current design stays visible to the next reviewer.

A working set is measured by how many conflicts it merged without surrendering an
objective, and how few it had to escalate — not by how many findings it produced.

## Relationship to per-domain review skills

A project often already has per-domain review skills: one skill per surface, each
with an explicit "do not use for ..." clause. They are complementary. A domain
skill says how to check a surface well; a stance says what the project is
optimizing for and **who pays** when it wins. A domain skill that starts arguing
for a value rather than checking a surface is a sign the stance set is missing
that value. The full distinction is in [hydra-crux](skills/hydra-crux/SKILL.md).

## Counterexamples

[references/counterexamples.md](skills/hydra-crux/references/counterexamples.md)
is how the set compounds instead of resetting. It is written by the **pass**, not
the generator: the review skill harvests before it ends, and the generator applies
the resulting set changes against its rules. Bugs and missing tests are not
harvested — a library of obvious mistakes trains reviewers to check for things
nobody would do.

## Non-goals

- Not a linter or a static-analysis pass.
- Not a replacement for tests. A stance finding without evidence is a hypothesis.
- Not a consensus mechanism. A pass where every stance is happy has either found a
  real buffer or failed to argue hard enough.
- Not a verification of its own success. The set proves it can fire by stopping a
  known-bad control change, not by finding conflicts on a change nobody trusted it
  with.
- Not a registry linter. Table consistency is checked by reading eight rules in
  `hydra-crux`; the failure that matters is a stance with no opponent, and no
  script detects that.
- Not a single skill. Escalating and harvesting are acts of a running pass and
  live in `hydra-crux-review`.

## License

[MIT](LICENSE).
