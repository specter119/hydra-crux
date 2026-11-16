<p align="center">
  <img src="docs/assets/icon.svg" alt="Hydra" width="140">
</p>

# Hydra Crux

Adversarial architecture review driven by **opposing stances**, for projects
that want their tradeoffs surfaced instead of averaged away.

Hydra Crux does not ask one reviewer to "find problems". It gives each stance
one objective to maximize, records the harm that objective does to another, and
routes a change to the conflicts it actually touches. The result is a decision
record, not a pile of findings.

## What you get

| Artifact    | Where it lives                                    | What it is                                                                 |
| ----------- | ------------------------------------------------- | -------------------------------------------------------------------------- |
| Topology    | `.agents/review-graph.toml`                       | stakes, surfaces, stances, oppositions, decisions, unrepresented interests |
| Prose       | `.agents/skills/<project>-*-stance/`, `*-review/` | the argument each stance makes and the checks each surface performs        |
| Review pass | `hydra-crux-review`                               | bind, brief, reconcile, contest, classify, escalate, record, harvest       |

The graph owns the relationships. The prose owns the argument. The review pass
is the only thing that runs a review; the generator never reviews, and the
reviewer never redesigns the set mid-pass.

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
There is no `requirements.txt`, no lock file, and no model to download.

## Use

Two skills, split by **when the work happens**, not by topic.

| Skill               | Runs           | Owns                                                                                                    |
| ------------------- | -------------- | ------------------------------------------------------------------------------------------------------- |
| `hydra-crux`        | between passes | discovery, opposed pairs, stance/surface links, decisions, and the rules a topology change must satisfy |
| `hydra-crux-review` | during a pass  | one end-to-end review: bind, brief, reconcile, contest, classify, escalate, record, harvest             |

Start with the generator when the project has no topology. Start with the
reviewer when it has one and a change is ready.

### Build or update the topology

Ask the agent to use `hydra-crux`. It will inventory the existing review
skills, find the objectives the project would sacrifice for, form opposed
pairs, and write `.agents/review-graph.toml` plus the generated registry.

### Run a review pass

Ask the agent to use `hydra-crux-review` on the change, branch, or design. It
will brief one subagent per stance without telling it what to expect, reconcile
the findings by surface, contest each candidate conflict with the harmed
stance, and escalate only the conflicts that survive a buffer search.

### Use the graph directly

Set `HYDRA` to the directory containing the installed skill. The examples use
the global install path; if you installed the skill inside the project, use
`.agents/skills/hydra-crux` instead.

```sh
HYDRA="${HYDRA_CRUX_SKILL:-$HOME/.agents/skills/hydra-crux}"

# Validate the topology and its generated indexes.
python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml validate

# Regenerate the registry and discovery map.
python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml generate \
  --out .agents/skills --docs-out docs

# Route a change to the surfaces and axes it actually touches.
python3 "$HYDRA/scripts/hydra_graph.py" \
  --graph .agents/review-graph.toml route \
  --changed src/example.py --format markdown
```

The route closes over the axes a surface declares in `contends`, not over every
axis a selected stance happens to touch. It lists prior decisions, open
conflicts, unclosed axes, and explicit skips. A local change stays local.

The route is the only selector. If it misses a surface or selects the wrong
one, fix the graph's `paths`, `keywords`, or `contends` and reroute; do not
hand-pick a subset. `--skip STANCE=REASON` is the only omission mechanism, and
a skip that leaves one side of an axis active is blocked.

## Reading a review

A review result has three parts. Read them in this order:

1. **Route.** Which surfaces and axes the change touches, and which prior
   decisions apply. If the route is empty, the change did not reach a recorded
   contention.
2. **Conflicts.** Each candidate is classified as merged, incompatible under
   named constraints, or unresolved evidence. Only the incompatible ones are
   escalated.
3. **Decision.** The winner, the losing objective, the payer, the owner
   document, and the condition that reopens the decision.

A pass where every stance is happy must name the axes it checked and why the
design already satisfies them. It must not invent a conflict to prove it ran.

## Worked example

[`tests/fixtures/luwu-review-graph.toml`](tests/fixtures/luwu-review-graph.toml)
is a real stance set for a real project: twelve stakes, nine stances, five
axes. It is metadata only, and the mechanical rules check it on every commit.
[`escalation-worked-example.md`](skills/hydra-crux/references/escalation-worked-example.md)
takes two conflicts from one pass and shows the difference between a negotiable
conflict and an essential one.

## Concept audit (optional)

`concept_audit.py` (in the skill's `scripts/` directory) is a pre-flight for a
first build, a migration, or an evolution. It reads the owner documents or old
skills, the graph, and the generated prose, and produces a diff list for a
human. It is not a gate: it never runs in `prek` and never fails a commit.

The commands below use the `HYDRA` variable defined in
[Use the graph directly](#use-the-graph-directly).

The script has no LLM client. The semantic step is you, the agent, reading the
report. The script gives you two things:

| Layer            | Needs                                    | Gives                                                        |
| ---------------- | ---------------------------------------- | ------------------------------------------------------------ |
| `deterministic`  | nothing                                  | role extraction, lexical coverage, layer bleed, graph checks |
| `decision-model` | an endpoint that answers typed questions | role labels with the endpoint's own confidence               |

The deterministic layer is always on and makes no network call. The decision
model is opt-in: with no config, nothing is called and the report says so.
Configuring one buys independence, not intelligence: it has not read this
conversation and did not help write the stance set, so its labels are a second
opinion rather than a restatement.

### Configure a decision model

```bash
python3 "$HYDRA/scripts/concept_audit.py" setup \
  --decision-url https://your-decision-model.example/v1/systemone \
  --decision-model <model-id> \
  --decision-key-env HYDRA_DECISION_KEY
```

`setup` writes `~/.config/hydra-crux/audit.toml` with mode `0600`. That file is
the default: it survives a new shell and behaves the same on any OS. The other
two sources exist to override it, not to replace it.

| Source                                                             | Use it for                                         |
| ------------------------------------------------------------------ | -------------------------------------------------- |
| `audit.toml`                                                       | the endpoint you normally use                      |
| `HYDRA_DECISION_URL`, `HYDRA_DECISION_MODEL`, `HYDRA_DECISION_KEY` | overriding a field for one run, a container, or CI |
| CLI flags                                                          | a one-off experiment                               |

Each field resolves as CLI flag, then environment, then config file, so a stale
environment variable wins over a corrected file. `status` prints the effective
endpoint and whether the section is complete. Prefer `--decision-key-env` over
`--decision-key`: it stores the *name* of an environment variable, not the key.
The decision URL is used exactly as written; credentials in it are sent as
Basic auth.

The endpoint receives one `POST` with `{"model", "state": {"text"}, "questions": {"q": {"type": "choice", "instructions", "criteria"}}}` and
answers `{"answers": {"q": {"choice", "confidence"}}}`, where `confidence` is a
number in `0..1`. Any endpoint that speaks this shape works; JEV is one
implementation. The full contract is in
[`references/concept-audit.md`](skills/hydra-crux/references/concept-audit.md#endpoint-contract).

```bash
# What is configured, and what is incomplete.
python3 "$HYDRA/scripts/concept_audit.py" status

# Run it: the report is a reading order, not a verdict list.
python3 "$HYDRA/scripts/concept_audit.py" run --graph .agents/review-graph.toml
```

### With and without a decision model

|             | No decision model                      | Decision model configured                   |
| ----------- | -------------------------------------- | ------------------------------------------- |
| Role source | `deterministic`; you classify the rest | `decision-model`; never silently downgraded |
| Endpoint    | none                                   | `<decision.url>` verbatim                   |
| Confidence  | the ranker's score, a lexical signal   | the endpoint's answer, validated to `0..1`  |
| Bad answer  | n/a                                    | error row; the audit still completes        |

Every model row carries its `source` and `confidence`, and `--max-model-calls`
bounds the total. An answer that is missing a field, names an unknown role, or
carries a non-numeric confidence becomes an error row, not a crash.

## Learn more

- [docs/IDEA.md](docs/IDEA.md) — why opposing stances, what ablation means, and
  what the project deliberately does not do.
- [skills/hydra-crux/SKILL.md](skills/hydra-crux/SKILL.md) — how to build and
  maintain the topology.
- [skills/hydra-crux-review/SKILL.md](skills/hydra-crux-review/SKILL.md) — how to
  run one review pass.
- [skills/hydra-crux/references/](skills/hydra-crux/references/) — graph format,
  stance design, escalation, migration, counterexamples.
- [AGENTS.md](AGENTS.md) — how to develop this repository without duplicating
  or drifting its scopes.

## Non-goals

Hydra Crux is not a linter, a consensus mechanism, or a proof that a review is
good. The full list, including why a stance finding without evidence is only a
hypothesis, is in [docs/IDEA.md](docs/IDEA.md#non-goals).

## License

[MIT](LICENSE).
