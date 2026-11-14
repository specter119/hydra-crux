<p align="center">
  <img src="docs/assets/icon.svg" alt="Hydra" width="140">
</p>

# Hydra Crux

Adversarial architecture review driven by **opposing stances**, for projects
that want their tradeoffs surfaced instead of averaged away.

## The idea in one paragraph

A single reviewer told to "find problems" converges on the same three issues
every time, weighted by whatever the prompt mentioned. Opposed stances remove
that degree of freedom: each subagent is given one objective it must maximize,
and the harm it causes another objective becomes visible as a conflict instead
of disappearing into a compromise nobody chose. The product is not a pile of
findings and not consensus. It is a topology of where objectives genuinely
collide, a route that brings both sides to the changes that touch them, and a
decision record that names the losing objective and when the decision reopens.

## Three artifacts

The repository holds the **meta** layer. A target project has a topology, stance
prose, and surface prose. They are not the same source of truth.

| Artifact | Lives in                                                             | What it owns                                                        |
| -------- | -------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Meta     | this repo, `skills/hydra-crux*`                                      | Builds the topology; runs one review pass over it                   |
| Topology | target project, `.agents/review-graph.toml`                          | ids, links, payers, oppositions, decisions, unrepresented interests |
| Prose    | target project, `.agents/skills/<project>-*-stance/` and `*-review/` | objectives, attacks, checks, evidence, scope boundaries             |

The graph does not own the prose. `hydra_graph.py generate` writes the registry
and discovery map by default; it writes stance and surface bodies only with
`--views`, and only when the graph carries the prose.

```text
hydra-crux/
├── skills/
│   ├── hydra-crux/                # build + maintain the stance set
│   │   ├── SKILL.md
│   │   ├── scripts/               # graph engine + topology lint
│   │   └── references/            # graph format, stance design, migration prompt, escalation
│   └── hydra-crux-review/         # run one review pass
│       └── SKILL.md
├── examples/
│   ├── luwu-migration/            # 9-stance migration fixture + generated registry
│   ├── acme-sync/.agents/skills/  # an older hand-authored stance set
│   └── escalation-example.md      # one merged conflict, one escalated
├── tests/                         # graph, route, and migration tests
├── scripts/                       # vendored skill validator
├── prek.toml                      # pre-commit hooks for this repo
├── docs/assets/icon.svg           # the mark: three heads, one shared body
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

| Skill               | Runs           | Owns                                                                                                                          |
| ------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `hydra-crux`        | between passes | The topology: discovery, opposed pairs, stance/surface links, decisions, and the rules a change to the topology must satisfy. |
| `hydra-crux-review` | during a pass  | One end-to-end review: bind, brief, reconcile, contest, classify, escalate, record, harvest.                                  |

The split is deliberate. Escalating and harvesting are acts of a running pass, so
they belong to the review skill; the generator never performs a review, and the
reviewer never redesigns the set mid-pass. The procedure is in each `SKILL.md` —
this README does not restate it.

## Use the graph

```sh
# Validate the topology and its generated indexes.
python3 .agents/skills/hydra-crux/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml validate

# Regenerate the registry and discovery map.
python3 .agents/skills/hydra-crux/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml generate \
  --out .agents/skills --docs-out docs

# Route a change to the surfaces and axes it actually touches.
python3 .agents/skills/hydra-crux/scripts/hydra_graph.py \
  --graph .agents/review-graph.toml route \
  --changed src/example.py --format markdown
```

The route closes over the axes a surface declares in `contends`, not over every
axis a selected stance happens to touch. It lists prior decisions, open
conflicts, unclosed axes, and explicit skips. A local change stays local.

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
with an explicit "do not use for ..." clause. They are **surfaces**, not a second
review meta-system. A surface says how to check well; a stance says what the
project is optimizing for and **who pays** when it wins. A surface that starts
arguing for a value rather than checking a surface is a sign the topology is
missing that value. The migration path is in
[hydra-crux](skills/hydra-crux/SKILL.md).

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
- Not a consensus mechanism. A pass where every stance is happy must name the
  axes it checked and why the design already satisfies them; it must not invent a
  conflict to prove it ran.
- Not a verification of its own success. The set proves it can fire by stopping a
  known-bad control change, not by finding conflicts on a change nobody trusted it
  with.
- Not a proof that the review is good. The lint reads the graph metadata and
  generated indexes, never the authored `SKILL.md` prose; it cannot tell whether
  a payer is real, whether a sacrifice is acceptable, or whether a check is any
  good.
- Not a single skill. Escalating and harvesting are acts of a running pass and
  live in `hydra-crux-review`.

## License

[MIT](LICENSE).
