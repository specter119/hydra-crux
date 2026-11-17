# The idea

## The failure this exists to prevent

A single reviewer told to "find problems" converges. It reports the three
issues the prompt made salient, weighted by the reviewer's taste, and it
resolves every tradeoff into a compromise. The compromise is not chosen by
anyone; it is the average of objectives nobody named. The next reviewer repeats
the exercise, and the project drifts because no one can say which objective
lost.

## The move: partisan stances

Hydra Crux replaces the generalist reviewer with a small set of **stances**. A
stance is not a checklist and not a persona. It is a partisan argument:

- one objective it maximizes;
- the harm it knowingly accepts;
- who pays that harm;
- the evidence that would make it lose;
- the decisions it would sacrifice for.

Two stances are opposed when maximizing one costs the other on the same
resource. The opposition is recorded, not resolved by the set. A review pass
briefs each stance independently, reconciles their findings by surface, and
escalates only the conflicts that survive a buffer search.

## What the product is

Not a pile of findings. Not consensus. Three things:

1. **A topology** — stakes, surfaces, stances, oppositions, decisions, and
   unrepresented interests.
2. **A route** — the surfaces and axes a change actually touches, with prior
   decisions and open conflicts attached.
3. **A decision record** — the winner, the losing objective, the payer, the
   owner document, and the condition that reopens the decision.

## Three artifacts, three owners

| Artifact | Lives in                                                             | Owns                                                                |
| -------- | -------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Meta     | this repository, `skills/hydra-crux*`                                | Builds the topology; runs one review pass over it                   |
| Topology | target project, `.agents/review-graph.toml`                          | ids, links, payers, oppositions, decisions, unrepresented interests |
| Prose    | target project, `.agents/skills/<project>-*-stance/` and `*-review/` | objectives, attacks, checks, evidence, scope boundaries             |

The separation is deliberate. The meta layer is reusable across projects; the
topology is project-specific; the prose is authored. If the generator also
owned the prose, it would become a second source of truth, and the copy nobody
re-reads is the one that drifts. `hydra_graph.py generate` writes only the
registry; stance and surface bodies remain hand-authored.

## What ablation means

Ablation here is not deletion of a design, and not consensus:

- **Merge the overlap.** A finding both stances agree on is one finding, not
  two.
- **Find buffer space first.** Most conflicts are negotiable — scope split,
  time split, explicit opt-in, measurement instead of policy, asymmetric cost,
  layer reframe. The agent must try them before calling a conflict essential.
- **Keep the real conflicts.** An essential conflict is not averaged. It goes
  to the user, and the decision is recorded with the losing objective named.
- **Never delete a losing stance.** It stays installed, with the sacrifice
  recorded, so the cost of the current design stays visible to the next
  reviewer.

## Surface versus stance

A surface says **how to check**. A stance says **what the project is optimizing
for and who pays when it wins**. A surface that starts arguing for a value is a
sign the topology is missing that value. A stance that starts listing checks is
a surface that has not been separated. The two layers are allowed to reference
each other; they are not allowed to absorb each other.

## No fixed count

No kind has a target number: stakes, stances, surfaces, axes, oppositions, and
decisions all follow the evidence.

The number of stances follows the axes where both sides have a real payer. A
graph where every payer is exactly the opposing stance, and every axis has
exactly two stances, is a quota signature. It is not an error, but it is not
evidence either. The question is not "do we have five?" but "who pays, and who
is missing?"

The same holds for every other kind. A surface exists because a check needs a
home and a route, not because a stance needs a partner. A perfect
surface/stance matching is the quota signature in the other layer; the audit
reports it, and the question is whether each surface has a check that predates
the stance.

## Evidence, not symmetry

Every stance needs a recorded decision it would sacrifice for. No decision, no
stance. A stance with no payer is a preference. A payer that is only the
opposing stance may be a real cost, or it may be the set talking to itself; the
prose has to show which.

## How the set stays honest

- Lint checks metadata, structured paths, the registry, and pass records. It
  does not judge prose.
- Prose needs semantic review. A pattern match can segment a document or
  collect candidates; it cannot decide that a sentence is a verdict. A decision
  model may triage candidates, and a human decides. The audit never becomes the
  authority.
- The set proves it can fire by stopping a known-bad control change, not by
  finding conflicts on a change nobody trusted it with.
- Counterexamples compound when a pass records candidates and evolution
  promotes the reusable shapes. Bugs and missing tests are not harvested; a
  library of obvious mistakes trains reviewers to look for things nobody would
  do. See `skills/hydra-crux/references/counterexamples.md`.

## What good looks like

- Merged conflicts without surrendering an objective.
- Few escalations, each with a named loser.
- Decisions that reopen on evidence, not on taste.
- A migration that removes the old skill's verdicts, not just renames its
  files.

## The migration lesson

The first migration showed the trap: eight domain skills became eight surfaces,
one per old file. The file count looked preserved, but the old skills' implicit
stances were not extracted. The surface layer is a check catalogue; the stance
layer is the new value. A migration is complete when every old stable value is
claimed by a stance, every old check has a surface home, and every surface
verdict has a payer or is explicitly uncontested.

## The decision model is triage

A stake lives in sentences that a keyword list or a prototype ranker cannot tell
apart: "No stance without a decision" and "Run the test before merging" share
vocabulary and differ in role. A decision model, an external endpoint that
answers a typed question about one sentence, can propose which role a sentence
plays. It is opt-in, and once configured it applies to every mode.

It proposes and never decides. Its answer is a probability, so a label is a
candidate, a person records the disposition, and nothing enters the graph
because a model said so. A probability near its boundary is not a decision, so
low-confidence labels are for a person, not for a rule. It
labels one sentence at a time. It does not cluster sentences or pair opposing
stances, because agreement between two sentences is not opposition.

The deterministic ranker has the opposite profile: a repeatable order that does
not depend on the other inputs, and a weak reading of what a sentence means.
The two are used together, each for what it is good at. The measurements behind
this are in [`EXPERIMENTS.md`](EXPERIMENTS.md).

## Open questions

- How much of the migration can be semantic automation without turning into a
  new schema?
- How do we keep the graph from becoming a second prose layer?
- How do we measure prose drift without turning a heuristic into a verdict?
- Can a decision model triage prose without becoming the authority? A cache of
  accepted and rejected candidates may make triage repeatable, but then the
  cache is the authority.
- Can a model check whether the graph's own anchors have already drifted from
  the owner documents? Any classification of an anchor presupposes the anchor is
  right, so this stays open until the check can be verified independently.

## Non-goals

- Not a linter or a static-analysis pass.
- Not a replacement for tests. A stance finding without evidence is a
  hypothesis.
- Not a consensus mechanism. A pass where every stance is happy must name the
  axes it checked and why the design already satisfies them; it must not invent
  a conflict to prove it ran.
- Not a verification of its own success. The set proves it can fire by stopping
  a known-bad control change, not by finding conflicts on a change nobody
  trusted it with.
- Not a proof that the review is good. The lint reads structured graph data,
  the registry, and pass records, never the authored `SKILL.md` prose; it cannot
  tell whether a payer is real, whether a sacrifice is acceptable, or whether a
  check is any good.
- Not a single skill. Escalating and harvesting are acts of a running pass and
  live in `hydra-crux-review`.
