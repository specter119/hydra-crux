# Concept audit

`scripts/concept_audit.py` is an optional pre-flight for a first build, a
migration, or an evolution. It reads the owner documents or old skills, the
graph, and the generated prose, and produces a diff list for a human.

It is **not a lint**. It reads authored documents and `SKILL.md` prose, so it is
not wired into `scripts/lint-skills.sh` and it must never fail a commit. Its
product is a candidate list, not a pass/fail gate.

## Two layers, and the agent

| Layer          | Requires                  | What it gives                                                                                   |
| -------------- | ------------------------- | ----------------------------------------------------------------------------------------------- |
| deterministic  | nothing                   | role-tagged atoms, lexical coverage candidates, layer-bleed candidates, graph metadata findings |
| decision-model | a decision-model endpoint | probabilistic Noul/Choice answers, with confidence                                              |

The script ships no LLM client. The semantic step is the agent reading the
report: the deterministic layer produces a reading order, and the agent decides
what each candidate is. The decision model is an optional second opinion, not a
replacement for that reading. Without a config nothing is called, and the
report says so.

## Endpoint contract

The `decision-model` layer is not tied to one vendor. It sends one `POST` to the
configured URL with this body:

```json
{
  "model": "<model-id>",
  "state": { "text": "<the sentence or section under audit>" },
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
`confidence` must be a JSON number in `0..1`; a string, a boolean, `null`, or a
value outside the range is an error row. `choice` must be one of the labels in
`criteria`. JEV is one implementation of this shape; any endpoint that speaks it
works. The configured URL is used as given, with no path appended. Credentials
in the URL are sent as Basic auth; a configured key is sent as Bearer and wins.

## Setup

Configuration is opt-in and lives outside the repository:

```bash
python3 scripts/concept_audit.py setup \
  --decision-url http://127.0.0.1:3425/v1/systemone \
  --decision-model typesafe/jev-latest \
  --decision-key-env HYDRA_DECISION_KEY
```

That URL and model are an example of a JEV endpoint, not a requirement.

The file is written to `~/.config/hydra-crux/audit.toml` with mode `0600`.
Prefer `--decision-key-env` over `--decision-key`; a literal key in the file is
supported but warned about.

Resolution order is CLI flag, then environment, then config file. `status`
prints what is configured without revealing the key.

A section that exists but lacks `url` or `model` is reported as incomplete, not
absent, and a CLI flag completes it. A config file that is not valid TOML does
not abort `run`: the report records the error and the deterministic layer stands
alone.

## Run

```bash
python3 scripts/concept_audit.py run \
  --graph .agents/review-graph.toml \
  --source-dir archive/domain-review \
  --out concept-audit.md --json concept-audit.json
```

`--source` takes a file or a directory and may be repeated. A file is one
document; a directory contributes its top-level `*.md` documents and its
`*/SKILL.md` views. A first build has no archived skill layer, so point it at
the documents that already state requirements:

```bash
python3 scripts/concept_audit.py run \
  --graph .agents/review-graph.toml \
  --source AGENTS.md --source README.md --source docs \
  --out concept-audit.md
```

`--source-dir` is kept as an alias for a directory source.

`--max-model-calls` bounds cost (default 40). `--threshold` controls the
lexical coverage floor (default 0.08); the report prints the score distribution
so the threshold is interpretable rather than magic.

## How to read the report

- **Coverage candidates** are atoms whose best lexical home is below the floor.
  A low score is not proof of an orphan. It means the atom's vocabulary does
  not overlap the homes, which is exactly where a human should look.
- **Layer bleed candidates** are sentences ranked by TF-IDF cosine to role
  prototypes. The prototype sentences are cluster cores; the section heading is
  never consulted. The ranking is a reading order, not a decision. With a model
  layer, the model's role is the classification; without one, treat the
  prototype role as a candidate only.
- **Graph findings** are metadata only: payer symmetry, axis sizes, one-to-one
  surface/stance pairs, unpaired surfaces, unopposed stakes. A high
  payer-symmetry ratio and a perfect surface/stance matching are quota
  signatures, not errors.
- **Model triage** is a ranking signal. A `decision-model` answer carries a
  probability from the endpoint. It is not a verdict. Treat the 0.2-0.6 band as
  human-only. The `error` column carries the reason a row failed, so a failed
  call never looks like a successful one.

## Limits

- Lexical coverage cannot see a paraphrase. It is a reading-order tool.
- A decision model does not know project-specific senses such as `accept` as a
  command; it is high precision and low recall on those.
- Pairwise semantic clustering is not supported. In the Luwu pilot, the
  decision model merged 49 of 50 atoms into one cluster at 0.5; use topic
  clustering only to group reading, never to decide opposition.
- The audit does not judge whether a stance is good, whether a payer is real,
  or whether a deferred axis is justified. Those remain review questions.
- The deterministic role ranking uses content words plus a sentence-mood
  feature. It is a weak semantic method: it can rank a prohibition above a
  check, but it cannot prove the prohibition is a verdict. That is why the
  model layer exists and why the report says "reading order, not a decision".

## Relationship to the repository rules

`AGENTS.md` forbids pattern matching as the decision procedure for skill prose.
This script follows that rule:

- Markdown headings are used only to segment a document and to locate a line.
- Role assignment is nearest-prototype cosine over content words and a
  sentence-mood feature. The prototype sentences are examples, not match keys.
- Archived skills are inventoried through a declared `ARCHIVE_TEMPLATE` table.
  That is template inventory, not a semantic check of a new skill set; unknown
  headings fall through to the prototype classifier.
- Graph metadata is checked structurally, which is allowed because the object
  is TOML, not prose.
- The model layer, when configured, makes the semantic call; the deterministic
  layer only ranks.
- A model row whose `source` is `error` carries the reason in `error`. A
  malformed answer is an error row, not a failed audit.
