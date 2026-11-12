# Escalation

Purpose: separate an essential conflict, which needs a user decision, from a
negotiable one, which the agent must resolve itself by finding buffer space.

Getting this wrong in either direction destroys the instrument. Escalating
negotiable conflicts trains the user to rubber-stamp. Resolving essential
conflicts locally hides the tradeoff that the whole stance set exists to
surface.

## Three outcomes, not two

A conflict is not "negotiable" or "essential". It is in one of three states, and
collapsing the third into either of the others is the most common way this
protocol fails:

| State                                    | Meaning                                                                                           | Who decides                                             |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **Joint solution verified**              | A design serves both objectives, and both stances have confirmed it                               | The orchestrator records it                             |
| **Incompatible under named constraints** | No joint design exists within the budget, authorization, or contract the project can change       | The user                                                |
| **Unresolved evidence**                  | The joint design is plausible but unmeasured, or the failure is asserted rather than demonstrated | The orchestrator, with a named measurement and an owner |

"Unresolved evidence" is not a licence to pick the cheaper side. It is a
work item: state what would settle it, who runs it, and what happens if nobody
does. Until it is settled the conflict stays open, and the current design keeps
the status quo rather than being declared correct.

## The test

A conflict is **essential** — the second state — only when all four hold:

1. **Same resource.** Both stances need the same finite thing — the same
   latency budget, the same migration window, the same operator attention, the
   same review capacity. If they need different resources, the conflict is
   usually negotiable.
2. **No joint design, demonstrated.** At least two genuinely different designs
   were constructed that serve both objectives, and each failed for a concrete,
   named reason. Two failed attempts are the *minimum search record*; they do
   not prove no design exists. Say which constraint each attempt hit, and what
   a design would have to do to escape it.
3. **Cost is not the objection.** The joint design is not merely expensive. If
   it works and the only objection is effort, that is a scheduling decision,
   not an essential conflict; propose it and let the user choose on cost. Effort
   that exceeds what the project can afford *is* a named constraint, and belongs
   in condition 2 rather than here.
4. **Irreversible or contract-changing.** The choice changes a contract, a
   stored format, a public interface, or a commitment that is expensive to
   reverse. Reversible choices belong to the agent.

If any of the four fails, the conflict is in state 1 or 3. Find the buffer, or
name the measurement.

## Confirming a joint solution

A joint solution is verified when **both** stances say so, in their own words,
after seeing the same concrete design. Re-reading each stance's **Objective** and
finding a sentence that is satisfied is not confirmation: a sentence can always
be found, and text cannot verify behaviour.

Send the design to each affected reviewer with the question "what does your
objective still lose under this design, and what evidence would show it does
not?" A reviewer that names a residual loss has not confirmed the buffer. A
reviewer that says "nothing" must say what it checked.

"Not objected to", "already the current contract", and "fully satisfies the
objective" are three different claims. Only the third is a verified buffer.

## Finding buffer space

Before declaring a conflict essential, try these in order. Each is a way to
serve both objectives rather than split the difference.

- **Scope split.** Serve each stance on a different surface: strict at the
  boundary, lenient inside; explicit for the public API, inferred for internal
  callers.
- **Time split.** Serve one objective now and the other behind a scheduled
  change, with the schedule recorded. This is legitimate only when the second
  objective is genuinely not needed yet.
- **Explicit opt-in.** Give the losing objective a declared escape hatch that
  costs the winner nothing when unused. An escape hatch that silently becomes
  the default is not a buffer.
- **Measurement instead of policy.** Replace a contested fixed choice with a
  measured budget that both stances can live with, and record the measurement.
- **Asymmetric cost.** Check whether the costs are actually symmetric. A
  stance often gives up much more than it claims. Asymmetry produces a
  *recommendation*, not an authorization: report it, and still let the harmed
  stance confirm. Deciding unilaterally because one side looks cheaper is the
  silent tiebreak this protocol forbids.
- **Reframe.** Check whether the two stances are arguing about different
  layers. A correctness stance and a performance stance usually conflict at the
  wrong layer; move the decision one layer out and both hold.

A merged resolution is only valid when both stances accept it, in the way
[Confirming a joint solution](#confirming-a-joint-solution) requires: the design
goes back to each affected reviewer, and each says what it still loses or what it
checked. Reading the **Objective** yourself and finding a satisfied sentence is
not acceptance — that is the same text check this section just forbade. If one
stance's objective is only nominally satisfied, the conflict is still open.

## Escalation format

Present exactly this, in this order. The user is deciding under time pressure;
the format is what makes the decision possible.

```text
Conflict: <id> — <stance A> vs <stance B>
Resource: <the one thing both need and cannot share>

Stance A says: <objective, strongest form, one or two sentences>
Stance B says: <objective, strongest form, one or two sentences>

Buffer attempts:
  1. <design> — failed because <concrete reason>
  2. <design> — failed because <concrete reason>

Option A: <design>
  Serves: <stance A objective, and how>
  Costs: <what stance B loses, concretely — a number, a surface, a guarantee>
  Reversible: <yes/no, and at what cost>

Option B: <design>
  Serves: <stance B objective, and how>
  Costs: <what stance A loses, concretely>
  Reversible: <yes/no, and at what cost>

Option C (if a third is real): <design>

What becomes irreversible: <the contract, format, or commitment this locks>
Decision needed: <the specific question, answerable in one sentence>
```

Rules for the format:

- State each stance in its strongest form, even the one you expect to lose.
  A weakened opposing stance makes the escalation worthless.
- Every cost is concrete. "Some performance impact" is not a cost; "p99 from
  40ms to 120ms on the write path" is.
- Never present a recommended option as the only option. If you have a
  recommendation, say so separately and say why, after both options are stated
  fairly.
- Do not bundle several conflicts into one escalation. One decision per
  message.

## After the decision

1. Record the decision in the project's decision records, not in the stance
   files.
2. Add a row to the registry's `Decisions that sacrificed a stance`, naming the
   losing objective and what was given up. The losing stance stays installed.
3. Update the affected stance's **Accepts this harm** only if the decision
   revealed a cost the stance had not admitted. Do not weaken the stance to
   match the decision.
4. If the decision makes an opposition permanently moot, remove the pair from
   the registry's `## Oppositions` and say why in `## Evidence`. Removing a
   stance requires that its objective is no longer a project objective, not
   that it lost once.

## Anti-patterns

**The averaged resolution.** "Half strict, half lenient" satisfies neither
objective and is the most common way adversarial review silently fails. If you
cannot name which stance's objective the design fully serves, it is an average.

**The deferred conflict.** Recording a conflict as "open" without escalating it
and without a date. An open conflict that nobody is deciding is a decision to
let the current design win by default.

**The unilateral tiebreak.** Choosing a winner because one stance is easier to
satisfy, or because the agent has a preference. The agent's job is to make the
tradeoff legible, not to have taste.

**The manufactured conflict.** Reporting a conflict to appear rigorous when the
stances actually agree. Check each stance's **Accepts this harm** first: if
neither stance admits a cost here, there is no conflict.
