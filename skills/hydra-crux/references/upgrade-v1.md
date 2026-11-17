# Upgrade a v1 review graph

Use this procedure once for an existing `version = 1` graph. Work row by row,
preserve the evidence in owner documents, and write the v2 fields defined in
[graph-format.md](graph-format.md). The mappings that distinguish a joint design
from a sacrifice are semantic judgments; do not make them with keyword matching.

01. **Map each `[[resolved]]` row.** Use `kind = "joint"` only when the recorded
    outcome satisfies both sides of every axis. Otherwise use
    `kind = "sacrifice", decided_by = "user"` and name what lost. Read the row
    and its owner document before choosing.
02. **Map each `[[sacrifice]]` row.** Use
    `kind = "sacrifice", decided_by = "user"`, merging the old `decision` and
    `why` into `summary`. Change `decided_not_implemented` to `decided`. Change
    `reopened` to `kind = "open"` and supply `owner` and `next_action`: copy them
    from the owner document when present; otherwise ask the user.
03. **Map each `[[open_conflict]]` row.** Use `kind = "open"`. Split the old
    `owner` text into `owner` and `next_action`, folding any old status prose into
    whichever field preserves its meaning.
04. **Replace opposition `recorded_sacrifice` text with decisions.** If an axis
    has no decision, create at least one: `sacrifice` for an already decided
    tradeoff, or `open` for an undecided one. Remove the old opposition fields.
05. **Deduplicate decisions.** Merge rows that record the same actual decision,
    retaining their evidence and route scope. Delete meta-decisions about the
    migration itself.
06. **Preserve decisions without an axis.** Keep only their `surfaces`; do not
    invent `axes`. When the losing interest is unrepresented, put its id in
    `sacrificed`. Create the missing `[[unrepresented]]` row when necessary,
    using the decision's `owner_document` for `where` and its old rationale for
    `why`.
07. **Repair cross-axis decisions.** If a decision's stances do not belong to one
    existing opposition, add the missing opposition with its contended resource
    and add `accepted_harm` on both sides. This is a map repair, not permission to
    attach a decision to an unrelated axis.
08. **Fold `[[deferred_axis]]` into `[[unrepresented]]`.** Preserve the reason
    and forge condition, and write the old stakes into `where` with enough
    context to recover their evidence.
09. **Remove phase metadata.** Move each `before-write` surface out of the graph
    and keep it as an ordinary prevention skill. Convert its unopposed stake to
    `[[unrepresented]]`. Delete `phase` from every other surface. Also remove
    retired surface prose fields and stake status metadata.
10. **Delete retired records and generated output.** Remove `[[evidence]]`,
    `[[counterexample]]`, and `[migration]`; their old contents remain in git
    history. Delete the generated discovery map, including `docs/stances.md`
    when that is its location, and point its former links to the generated
    registry instead. Delete old review skills rather than moving them to
    `archive/` when the migration includes the legacy skill layer.
11. **Assign and verify ids.** Give every decision and every unrepresented row
    an id, retaining existing `C-n` numbering where possible. Check global
    uniqueness and every reference, then run `generate` followed by `lint` and
    repair any reported mapping omissions.

Do not carry forward removed flags or tables to preserve a green command. The
upgrade is complete when the owner documents still support every decision, each
opposition has a decision, old checks remain reachable, and v2 lint passes.
