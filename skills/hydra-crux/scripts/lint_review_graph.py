#!/usr/bin/env python3
"""Mechanical rules for a hydra-crux review graph.

This is a lint: its object is the graph metadata in
``.agents/review-graph.toml``, the paths it cites, and the generated indexes.
It does **not** read or judge authored stance/surface ``SKILL.md`` prose.
Whether a surface has quietly taken back a verdict, whether a stance's argument
is good, and whether a deferred axis is justified are semantic questions for a
review pass, not for a string matcher.

The structural rules are:

- ids are unique and references exist;
- a stance has a payer, and every payer is an opponent;
- a surface has a stance or an explicitly unopposed stake;
- an opposition has a recorded sacrifice;
- a decision has an owner, status, reopen condition, and route scope;
- generated registry and discovery map match the graph.

Run with ``--self-test`` to check the rules against fixtures. prek runs it on
every commit through ``scripts/lint-skills.sh``.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from hydra_graph import check_rendered, load_graph, render_all, validate_graph


def _project_root(graph_path: Path) -> Path:
    # The graph lives at <project>/.agents/review-graph.toml.
    return graph_path.parent.parent


def _default_out(graph_path: Path) -> Path:
    return _project_root(graph_path) / ".agents" / "skills"


def _default_docs(graph_path: Path) -> Path:
    return _project_root(graph_path) / "docs"


def _find_graphs(args: list[str]) -> list[Path]:
    explicit = [Path(arg) for arg in args if Path(arg).name == "review-graph.toml"]
    if explicit:
        return sorted({path.resolve() for path in explicit})
    root = Path(__file__).resolve().parents[3]
    found = sorted(root.glob("**/.agents/review-graph.toml"))
    return [path.resolve() for path in found]


def check_graph(
    graph_path: Path,
    check_paths: bool = False,
    check_generated: bool = True,
) -> list[str]:
    graph = load_graph(graph_path)
    root = _project_root(graph_path)
    errors = validate_graph(graph, project_root=root, check_paths=check_paths)
    if check_generated:
        out = _default_out(graph_path)
        docs = _default_docs(graph_path)
        rendered = render_all(graph, graph_path, out, docs)
        errors.extend(check_rendered(rendered))
    return errors


SELF_TEST_GRAPH = """\
version = 1
project = "demo"

[[stake]]
id = "s1"
objective = "A written value is re-read at the boundary."
evidence = ["docs/reference.md#write"]
status = "represented"

[[stake]]
id = "s2"
objective = "A whole run stays inside its measured budget."
evidence = ["docs/maintenance.md#budget"]
status = "represented"

[[surface]]
id = "demo-boundary-review"
title = "Demo boundary review"
trigger = ["a write boundary"]
owner_documents = ["docs/reference.md#write"]
checks = ["Re-read the exact bytes and identities that authorize the write before replacing the target."]
required_evidence = ["path and line", "a focused regression test"]
scope_boundary = "Filesystem boundaries only."
paths = ["src/demo/filesystem.py"]
keywords = ["symlink", "atomic"]

[[stance]]
id = "demo-proof-stance"
title = "Demo proof stance"
objective = "Nothing is written without a fresh boundary read."
stable_core = "The authorizing bytes are re-read."
changing_contract = "The mechanism may change."
surfaces = ["demo-boundary-review"]
stakes = ["s1"]
attacks = ["A cached plan stands in for a fresh read."]
evidence_to_demand = ["the read and the write in one trace"]
does_not_own = ["the profile budget"]
escalates_when = ["a proof needs a durable cache"]
good_patterns = ["re-read then replace"]
bad_patterns = ["trust the plan"]

[[stance.accepted_harm]]
payer = "demo-cost-stance"
cost = "whole-profile proof costs latency"
resource = "latency"

[[stance]]
id = "demo-cost-stance"
title = "Demo cost stance"
objective = "A whole run stays inside its measured budget."
stable_core = "The budget is measured."
changing_contract = "The budget number may change."
surfaces = ["demo-boundary-review"]
stakes = ["s2"]
attacks = ["A per-action recheck hides a whole-profile computation."]
evidence_to_demand = ["a measured run inside the gate"]
does_not_own = ["the write boundary"]
escalates_when = ["a proof does not fit the gate"]
good_patterns = ["scope the recheck"]
bad_patterns = ["drop the proof silently"]

[[stance.accepted_harm]]
payer = "demo-proof-stance"
cost = "scoping the recheck weakens whole-profile proof"
resource = "proof coverage"

[[opposition]]
id = "proof-vs-cost"
stances = ["demo-proof-stance", "demo-cost-stance"]
contended_resource = "latency"
recorded_sacrifice = "The project scoped the recheck and recorded the lost coverage."
state = "decided"
"""


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".agents").mkdir()
        (root / "docs").mkdir()
        (root / "docs" / "reference.md").write_text("# write\n", encoding="utf-8")
        (root / "docs" / "maintenance.md").write_text("# budget\n", encoding="utf-8")
        graph_path = root / ".agents" / "review-graph.toml"
        graph_path.write_text(SELF_TEST_GRAPH, encoding="utf-8")

        clean = check_graph(graph_path, check_paths=True, check_generated=False)
        if clean:
            print("self-test: expected the clean graph to pass, got:")
            for problem in clean:
                print("  " + problem)
            return 1

        orphan = (
            SELF_TEST_GRAPH
            + """
[[surface]]
id = "demo-orphan-review"
title = "Demo orphan review"
trigger = ["an orphan check"]
owner_documents = ["docs/reference.md#write"]
paths = ["src/demo/orphan.py"]
"""
        )
        graph_path.write_text(orphan, encoding="utf-8")
        fired = check_graph(graph_path, check_paths=True, check_generated=False)
        if not any(
            "no stance and no `unopposed_stake`" in problem for problem in fired
        ):
            print("self-test: orphan surface did not fire")
            return 1

        missing_payer = SELF_TEST_GRAPH.replace(
            'payer = "demo-proof-stance"\ncost = "scoping',
            'payer = "demo-proof-stance"\npayer_stance = "demo-missing-stance"\ncost = "scoping',
        )
        graph_path.write_text(missing_payer, encoding="utf-8")
        fired = check_graph(graph_path, check_paths=True, check_generated=False)
        if not any("unknown stance" in problem for problem in fired):
            print("self-test: missing payer did not fire")
            return 1

    print("self-test: ok")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-paths", action="store_true")
    parser.add_argument("--no-generated", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    graph_paths = _find_graphs(args.paths)
    if not graph_paths:
        print("No review graph found.")
        return 0

    errors: list[str] = []
    for graph_path in graph_paths:
        errors.extend(
            check_graph(
                graph_path,
                check_paths=args.check_paths,
                check_generated=not args.no_generated,
            )
        )
    for error in errors:
        print(f"error: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
