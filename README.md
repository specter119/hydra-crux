<p align="center">
  <img src="docs/assets/icon.svg" alt="Hydra" width="140">
</p>

# Hydra Crux

Adversarial architecture review driven by **opposing stances**, for projects
that want their tradeoffs surfaced instead of averaged away.

Hydra Crux gives each stance one objective to maximize, records the harm that
objective does to another, and routes a change to the conflicts it actually
touches. The result is a decision record, not a pile of findings.

## What you get

| Artifact    | Where it lives                                    | What it is                                                                 |
| ----------- | ------------------------------------------------- | -------------------------------------------------------------------------- |
| Topology    | `.agents/review-graph.toml`                       | stakes, surfaces, stances, oppositions, decisions, unrepresented interests |
| Prose       | `.agents/skills/<project>-*-stance/`, `*-review/` | each stance's argument and each surface's checks                           |
| Review pass | `.agents/reviews/`, driven by `hydra-crux-review` | binding, findings, Ledger, map and counterexample candidates               |

The graph owns relationships, the prose owns arguments, and the generated
registry owns navigation. The reviewer never redesigns the set mid-pass.

## Install

These are meta skills: they operate on whatever project you are in, so install
them **globally**.

```bash
npx skills add specter119/hydra-crux -g
```

`-g` installs into `~/.agents/skills/`. Add `--all` to skip the prompts, or
`--skill hydra-crux` to take one. From a clone, pass the path: `npx skills add . -g`.

With `skm`, which keeps a config and lock file so `skm sync` reproduces the set
on another machine:

```bash
uvx --from skm-cli skm install https://github.com/specter119/hydra-crux hydra-crux
uvx --from skm-cli skm install https://github.com/specter119/hydra-crux hydra-crux-review
```

For one project only, drop `-g` and run inside it. Skills are discovered at
`<project root>/.agents/skills/<name>/SKILL.md`, where the project root is the
nearest ancestor containing `.git`; the `name` must be kebab-case and match the
directory.

The bundled scripts need Python 3.11 or newer and nothing else: every import is
from the standard library, and `tomllib` is the only reason for the 3.11 floor.

## Use

Two skills, split by **when the work happens**, not by topic.

| Skill               | Runs           | Owns                                                                        |
| ------------------- | -------------- | --------------------------------------------------------------------------- |
| `hydra-crux`        | between passes | discovery, opposed pairs, stance/surface links, decisions, topology changes |
| `hydra-crux-review` | during a pass  | bind, brief, reconcile, contest, classify, escalate, record, harvest        |

Start with `hydra-crux` when the project has no topology. Start with
`hydra-crux-review` when it has one and a change is ready.

### Build or update the topology

Ask the agent to use `hydra-crux`. It inventories existing review skills, finds
objectives the project would sacrifice for, forms opposed pairs, and writes the
graph plus generated registry.

### Upgrading an existing graph

Follow [the v1-to-v2 upgrade procedure](skills/hydra-crux/references/upgrade-v1.md)
to migrate an existing v1 graph.

### Run a review pass

Ask the agent to use `hydra-crux-review` on the change, branch, or design. It
binds a pass document, briefs one independent subagent per stance, reconciles
findings by surface, contests candidate conflicts with the harmed stance, and
escalates only conflicts that survive a buffer search.

### Use the graph directly

Set `HYDRA` to the installed skill directory, or to
`.agents/skills/hydra-crux` when vendored:

```sh
HYDRA="${HYDRA_CRUX_SKILL:-$HOME/.agents/skills/hydra-crux}"

# Regenerate the registry, then validate the graph, paths, registry, and passes.
python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml generate
python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml lint

# Route and bind a review pass.
python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml route \
  --changed src/example.py --pass example-review --format markdown
```

The route is the only selector. Its selection, status, per-axis skip, and pass
binding rules are documented in
[the review skill](skills/hydra-crux-review/SKILL.md#1-bind-the-pass). Fix the
graph and reroute rather than hand-picking stances.

## Reading a review

A review result has three parts:

1. **Route:** the surfaces and axes touched, applicable decisions, explicit
   skips, and unselected readers that need a map decision.
2. **Ledger:** joint designs, incompatible constraints, unresolved evidence, and
   one-sided findings. Only genuine tradeoffs become graph decisions.
3. **Decision:** its kind, owner document, reopen condition, and—when one side
   loses—the losing objective, payer, and decision-maker.

A pass with no conflict must name the axes checked and why the design satisfies
them. It must not invent conflict to prove it ran. A pass is complete only after
the agent runs `lint` successfully.

## Worked example

[`tests/fixtures/luwu-review-graph.toml`](tests/fixtures/luwu-review-graph.toml)
is a metadata-only stance set for a real project, checked by the mechanical
rules. [`escalation-worked-example.md`](skills/hydra-crux/references/escalation-worked-example.md)
contrasts a negotiable conflict with an essential one.

## Learn more

- [docs/IDEA.md](docs/IDEA.md) — why opposing stances, what ablation means, and
  the project's non-goals.
- [skills/hydra-crux/SKILL.md](skills/hydra-crux/SKILL.md) — build, migrate, and
  maintain the topology.
- [skills/hydra-crux-review/SKILL.md](skills/hydra-crux-review/SKILL.md) — run one
  review pass.
- [skills/hydra-crux/references/](skills/hydra-crux/references/) — graph format,
  stance design, escalation, upgrades, and counterexamples.
- [AGENTS.md](AGENTS.md) — develop this repository without duplicating scopes.

## Non-goals

Hydra Crux is not a linter, a consensus mechanism, or a proof that a review is
good. The full list, including why a stance finding without evidence is only a
hypothesis, is in [docs/IDEA.md](docs/IDEA.md#non-goals).

## License

[MIT](LICENSE).
