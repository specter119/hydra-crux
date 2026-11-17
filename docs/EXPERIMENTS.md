# Experiments

Dated measurements that bear on a design choice. Each entry states the question,
the method, the numbers, and what the numbers do not show. The reasons for the
design are in [`IDEA.md`](IDEA.md); this file is the evidence, and it can go
stale. Add an entry when you measure something; do not rewrite an old one.

## Context: the decision model removed and restored

The concept audit and its decision-model layer were added in `14e6f64`
(2026-11-15) and removed in `f116115` (2026-11-17), the change that made `route`
the only selector. The audit was restored the same day as opt-in triage after
the maintainer tested without it and could not get a stable set of stance cores
from the deterministic ranker alone. That is a product call, not a measurement.
The entries below are the measurements that informed it.

## 2026-11-14: role labels, clustering, and confidence on a Luwu set

**Question.** Can a decision model classify sentences of a real project's
review documents, and what else can it do?

**Method.** One experiment on a 50-sentence set from the Luwu project, labeled by
hand, run with a JEV endpoint. The labeled set and the session are not
preserved in this repository, so these numbers cannot be rerun.

**Results.**

- Role classification was 78% accurate. `objective` and `scope` were 7 of 7
  each.
- TF-IDF role prototypes over-judged dense paragraphs.
- Pairwise clustering failed: 49 of 50 sentences merged into one cluster at 0.5.
- Pairs scored above 0.9 were only 66% reliable, so raw confidence is
  overconfident.
- Sense disambiguation reached precision 0.93 and recall 0.66.

**Does not show.** Accuracy on any other project or label set. The seven-label
accuracy has not been remeasured since the label set was lost.

## 2026-11-17: label stability under input changes

**Question.** Does a sentence get the same role when the surrounding input
changes, and how does the deterministic ranker compare with the model?

**Method.** `concept_audit.py run --max-model-calls 400` in inventory-only mode
against a local JEV endpoint (`typesafe/jev-latest`, reported version
`jev-1.14.0`). Sources: `AGENTS.md`, `README.md`, and `docs/IDEA.md` as they
were that day (182 sentences). One baseline, then four variants:

| Variant         | Change                                                                       |
| --------------- | ---------------------------------------------------------------------------- |
| identical rerun | none                                                                         |
| reordered       | `--source` order reversed                                                    |
| plus unrelated  | `skills/hydra-crux-review/SKILL.md` added (290 sentences)                    |
| rewrapped       | paragraphs rewrapped at 70 columns (234 sentences, 131 shared with baseline) |

Labels were compared per sentence on the sentences both runs contain. The
deterministic ranker ran the same variants with the model off.

**Results.**

| Variant         | Ranker label flips | Model label flips | Model `objective` Jaccard vs baseline |
| --------------- | -----------------: | ----------------: | ------------------------------------: |
| identical rerun |                  0 |   9 of 182 (4.9%) |                                 0.857 |
| reordered       |                  0 |  10 of 182 (5.5%) |                                 0.810 |
| plus unrelated  |                  0 |  14 of 182 (7.7%) |                                 0.727 |
| rewrapped       |                  0 |  11 of 131 (8.4%) |                                 0.778 |

- The ranker's `objective` set (17 sentences) and the model's (20) shared one
  sentence.
- The labels that flipped between the identical runs had low confidence: mean
  0.31, maximum 0.43. The stable labels averaged 0.62.
- The four `objective` sentences at confidence 0.6 or higher were the same in all
  five runs.
- Mean absolute change in confidence for an unchanged sentence was 0.026 to 0.028
  (maximum 0.11 to 0.19).
- Read by hand, the model's `objective` sentences looked like stance cores ("No
  stance without a decision", "A stance with no payer is a preference"). Two
  of its misses were a link line and an installation sentence.

**Does not show.**

- Why identical input gives different labels. The cause was not investigated.
- Whether any other model, or a generative LLM, would flip more or fewer
  labels. No other model was run.
- Accuracy. There are no human labels for this corpus, so "looked like stance
  cores" is the author's reading.
- Anything about a second corpus. This is one repository and one model.
