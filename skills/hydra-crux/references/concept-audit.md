# Concept audit

`scripts/concept_audit.py` is an optional pre-flight for a first build, a
migration, or an evolution. It reads owner documents (or old skills), and with a
v2 graph it compares them with the graph's homes. Its product is a candidate
list for a human.

It is **not a lint**. It reads authored prose, so it is not wired into
`.pre-commit-hooks.yaml`, never changes `route`, and must never fail a commit.

## Two layers

| Layer          | Requires                  | Gives                                                                         |
| -------------- | ------------------------- | ----------------------------------------------------------------------------- |
| deterministic  | nothing                   | atoms with `path:line`, a reading order, graph-only findings                  |
| decision-model | a decision-model endpoint | one role label per sentence, with the endpoint's confidence and model version |

The script ships no LLM client. The semantic step is the agent reading the
report. A configured decision model is an independent second opinion on one
question: *which of seven roles is this sentence?* It does not cluster, pair
oppositions, pick a route, or rule. Without a config nothing is called, and the
report says which layer was skipped.

## The seven labels and where they land

The model and the deterministic ranker share one label set. The ranker's label
is the "nearest prototype (unverified)": a reading order, never a filter. No
atom is dropped because of a label.

| Label          | Usual v2 home                                                  |
| -------------- | -------------------------------------------------------------- |
| `objective`    | a stake, or a stance **Objective**                             |
| `scope`        | a surface scope boundary, or a stance **Does not own**         |
| `check`        | a surface check                                                |
| `anti_pattern` | a surface bad pattern, or a stance **Attacks** entry           |
| `evidence`     | stake evidence, or a surface required-evidence line            |
| `history`      | stake evidence, or a decision candidate (rejected alternative) |
| `other`        | no home                                                        |

The table is a map for the reader. It is not a rule that a label decides a home.

## Where each mode uses it

| Mode      | Step                                  | Command shape                                 | What to read                                       |
| --------- | ------------------------------------- | --------------------------------------------- | -------------------------------------------------- |
| Build     | step 1, before the graph exists       | `run --source <owner docs>`                   | **Objective candidates** to cite, merge, or reject |
| Build     | step 7, after generate and lint       | `run --graph … --source <owner docs>`         | **Coverage**, **Layer bleed**, **Graph findings**  |
| Migration | end of step 2, before step 3 deletes  | `run --graph … --source <old skills>`         | orphans go into the step 6 report                  |
| Evolve    | step 5, and step 6 after a doc change | `run --graph … --source <changed owner docs>` | the same sections for the changed documents        |

Do not pass a prevention skill as a source: it is outside the graph by design.
The graph's own skill files and the generated registry are excluded from
`--source` automatically.

Every **Objective candidate** needs a disposition from the agent: cited as stake
evidence, merged into an existing stake, or rejected with a reason that goes in
the delivery report.

## Setup

Configuration is opt-in and lives outside the repository:

```bash
python3 "$HYDRA/scripts/concept_audit.py" setup \
  --decision-url http://127.0.0.1:3425/v1/systemone \
  --decision-model typesafe/jev-latest \
  --decision-key-env HYDRA_DECISION_KEY
python3 "$HYDRA/scripts/concept_audit.py" status
```

The URL and model above are an example of a JEV endpoint, not a requirement.

`setup` writes `~/.config/hydra-crux/audit.toml` with mode `0600`. Prefer
`--decision-key-env`, which stores the *name* of an environment variable; it
must be a valid variable name, or every call is blocked and the value is never
printed. `setup` refuses a literal key passed there. A literal `key` in the file
works, and `setup --decision-key` warns when it writes one.

Each field resolves as CLI flag, then environment
(`HYDRA_DECISION_URL`, `HYDRA_DECISION_MODEL`, `HYDRA_DECISION_KEY`), then the
config file. `status` prints the effective endpoint with credentials redacted
and the key masked. A section missing `url` or `model` is reported as
incomplete, and a CLI flag completes it. A config that is not valid TOML does
not abort `run`; the report records the error and the deterministic layer
stands alone.

## Endpoint contract

The configured URL is used as given, with one `POST`:

```json
{
  "model": "<model-id>",
  "state": { "text": "<one sentence>" },
  "questions": {
    "q": {
      "type": "choice",
      "instructions": "...",
      "criteria": { "<label>": "<description>" }
    }
  }
}
```

The answer is `{"answers": {"q": {"choice": "<label>", "confidence": 0.0}}}`.
`choice` must be one of the labels in `criteria`. `confidence` must be a JSON
number in `0..1`; anything else is an error row. Credentials in the URL are sent
as Basic auth; a configured key is sent as Bearer and wins. JEV is one
implementation of this shape.

## Run

```bash
python3 "$HYDRA/scripts/concept_audit.py" run \
  --graph .agents/review-graph.toml \
  --source AGENTS.md --source README.md --source docs \
  --out concept-audit.md
```

- `--source` is required and repeatable. A file is one document; a directory
  contributes its top-level `*.md` and its `*/SKILL.md`.
- `--graph` is optional. Without it the audit looks for
  `.agents/review-graph.toml`, and with none it is inventory-only. A v1 graph
  is rejected with a pointer to [upgrade-v1.md](upgrade-v1.md); an explicit path
  that does not exist exits 2.
- `--out` defaults to stdout. Do not write it into `reviews_dir`: a report is
  not a pass document.
- `--max-model-calls` bounds cost (default 40); `0` skips the model for one
  run. The report prints the candidate count and the value that covers all of
  them, and lists what stayed untriaged.
- `--model-timeout` defaults to 60 seconds. Two consecutive transport failures
  stop further calls. A malformed answer is an error row, not a failed audit.
- `--threshold` is the lexical coverage floor (default 0.08).

Calls go in a fixed order: coverage orphans, then layer-bleed candidates (every
sentence of every graph skill, best-ranked first), then the remaining atoms.
Orphans and atoms are sorted by path and line. Only the layer-bleed display is
shortened; the queue is not.

## Reading the report

- **Objective candidates**: sentences the model labeled `objective`, with
  confidence. Confidence between 0.2 and 0.6 is *human only*. Without a model,
  the section is the atoms nearest the objective prototype, in reading order.
- **Coverage**: atoms whose nearest graph home scores below the floor. A low
  score means the vocabulary does not overlap, which is where to look. When the
  nearest home is an `unrepresented` row, the atom is a known gap.
- **Layer bleed**: surface sentences ranked by affinity to `objective` (a
  surface defending a value) and stance sentences ranked by affinity to
  `check`. The model can rule out a false alarm. It cannot confirm that a
  sentence is a verdict.
- **Graph findings**: metadata only. Payer symmetry (via `payer_stance`),
  one-to-one surface/stance pairs, unpaired surfaces, unopposed stakes, and
  stakes no stance references. A perfect pairing is a quota signature, not
  proof.
- **Model triage**: one row per call with `where`, `signal`, `role`,
  `confidence`, `origin`, and `error`. A failed call never looks like a
  successful one.
- **Untriaged sentences**: every candidate the model did not label, with
  `path:line` and text. Without a model this is the whole inventory.
- **Needs human**: a fixed checklist, not a filtered list: every objective
  candidate, every 0.2–0.6 or error row, every untriaged sentence, every
  empty document, and the graph findings that need a person.

A document with no English prose, such as a Chinese-only file, yields no atoms.
The report says "No atom was extracted from …" instead of an empty success.

## Limits

The experiment numbers and the reasons behind these limits live in
[docs/EXPERIMENTS.md](../../../docs/EXPERIMENTS.md).

- Lexical coverage cannot see a paraphrase, and its IDF depends on the corpus
  it is run on. It is a reading-order tool.
- Model labels on borderline sentences can change between identical runs. The
  report records the endpoint and model version so a rerun is comparable,
  nothing more.
- Raw confidence is overconfident; do not threshold it into a verdict.
- Pairwise clustering and opposition pairing are not supported.
- The audit does not judge whether a stance is good, whether a payer is real, or
  whether a deferred axis is justified.

## Relationship to the repository rules

`AGENTS.md` forbids pattern matching as the decision procedure for skill prose.
This script uses Markdown structure only to segment documents and locate lines.
Role ranking is nearest-prototype cosine; the model call is the semantic method;
the graph is checked structurally because it is TOML. Prose never gets a verdict
from a heading or a keyword.
