from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "hydra-crux" / "scripts"))
LUWU_GRAPH = ROOT / "examples" / "luwu-migration" / ".agents" / "review-graph.toml"

from hydra_graph import (
    check_rendered,
    load_graph,
    render_all,
    route,
    validate_graph,
    validate_views,
    write_rendered,
)
from lint_review_graph import check_graph


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def ring_graph(count: int, with_prose: bool = False) -> str:
    """A graph with `count` stances in a ring, plus two many-to-many surfaces."""

    lines = [
        "version = 1",
        'project = "demo"',
        "",
    ]
    for index in range(count):
        lines.extend(
            [
                "[[stake]]",
                f'id = "s{index}"',
                f'objective = "Stake {index}"',
                'evidence = ["docs/reference.md#stake"]',
                'status = "represented"',
                "",
            ]
        )
    lines.extend(
        [
            "[[surface]]",
            'id = "demo-a-review"',
            'title = "Demo A"',
            'trigger = ["a change in A"]',
            'owner_documents = ["docs/reference.md#a"]',
            'skill = ".agents/skills/demo-a-review/SKILL.md"',
            'paths = ["src/a.py"]',
            'keywords = ["alpha"]',
            'contends = ["axis-0-1"]',
        ]
    )
    if with_prose:
        lines.extend(
            [
                'checks = ["Check A."]',
                'required_evidence = ["evidence A"]',
                'scope_boundary = "A only."',
            ]
        )
    lines.extend(
        [
            "",
            "[[surface]]",
            'id = "demo-b-review"',
            'title = "Demo B"',
            'trigger = ["a change in B"]',
            'owner_documents = ["docs/reference.md#b"]',
            'paths = ["src/b.py"]',
            'keywords = ["beta"]',
            'contends = ["axis-1-2"]',
        ]
    )
    if with_prose:
        lines.extend(
            [
                'checks = ["Check B."]',
                'required_evidence = ["evidence B"]',
                'scope_boundary = "B only."',
            ]
        )
    lines.extend(
        [
            "",
            "[[surface]]",
            'id = "demo-shared-review"',
            'title = "Demo shared"',
            'trigger = ["a change in shared code"]',
            'owner_documents = ["docs/reference.md#shared"]',
            'paths = ["src/shared.py"]',
            'keywords = ["shared"]',
        ]
    )
    if with_prose:
        lines.extend(
            [
                'checks = ["Check shared."]',
                'required_evidence = ["evidence shared"]',
                'scope_boundary = "Shared only."',
            ]
        )
    lines.append("")

    for index in range(count):
        next_index = (index + 1) % count
        previous_index = (index - 1) % count
        surfaces = ["demo-shared-review"]
        if index == 0:
            surfaces.append("demo-a-review")
        if index == 1:
            surfaces.append("demo-b-review")
        lines.extend(
            [
                "[[stance]]",
                f'id = "s{index}-stance"',
                f'title = "Stance {index}"',
                f'objective = "Objective {index}"',
                f"surfaces = [{', '.join(_toml_string(item) for item in surfaces)}]",
                f'stakes = ["s{index}"]',
            ]
        )
        if with_prose:
            lines.extend(
                [
                    f'stable_core = "Core {index}."',
                    f'changing_contract = "Contract {index}."',
                    f'attacks = ["Attack {index}."]',
                    f'evidence_to_demand = ["Evidence {index}."]',
                    f'does_not_own = ["Something else {index}."]',
                    f'escalates_when = ["Escalate {index}."]',
                ]
            )
        lines.append("")
        for opponent in (next_index, previous_index):
            if opponent == index:
                continue
            lines.extend(
                [
                    "[[stance.accepted_harm]]",
                    f'payer = "s{opponent}-stance"',
                    f'cost = "Cost {index} pays {opponent}"',
                    'resource = "shared resource"',
                    "",
                ]
            )
        lines.extend(
            [
                "[[opposition]]",
                f'id = "axis-{min(index, next_index)}-{max(index, next_index)}"',
                f'stances = ["s{index}-stance", "s{next_index}-stance"]',
                'contended_resource = "shared resource"',
                'recorded_sacrifice = "The project paid for this axis."',
                'state = "decided"',
                "",
            ]
        )
    return "\n".join(lines)


class GraphValidationTests(unittest.TestCase):
    def test_counts_are_not_gated(self) -> None:
        for count in (3, 5, 7, 9):
            with self.subTest(count=count):
                graph = __import__("tomllib").loads(ring_graph(count))
                self.assertEqual(validate_graph(graph), [])
                self.assertEqual(len(graph["stance"]), count)
                self.assertEqual(len(graph["opposition"]), count)

    def test_orphan_surface_fails(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        graph["surface"].append(
            {
                "id": "orphan-review",
                "title": "Orphan",
                "trigger": ["anything"],
                "owner_documents": ["docs/reference.md#orphan"],
            }
        )
        errors = validate_graph(graph)
        self.assertTrue(
            any("no stance and no `unopposed_stake`" in error for error in errors)
        )

    def test_missing_payer_fails(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        graph["stance"][0]["accepted_harm"] = graph["stance"][0]["accepted_harm"][:1]
        errors = validate_graph(graph)
        self.assertTrue(any("does not name it as a payer" in error for error in errors))

    def test_semantic_deferral_passes(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        graph["deferred_axis"] = [
            {
                "axis": "authority-vs-completion",
                "reason": "No owner document records a sacrifice on this axis yet.",
                "forge_when": "a decision record names what completion gave up",
            }
        ]
        self.assertEqual(validate_graph(graph), [])

    def test_views_require_prose(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        self.assertTrue(validate_views(graph))
        full = __import__("tomllib").loads(ring_graph(3, with_prose=True))
        self.assertEqual(validate_views(full), [])

    def test_latent_payer_is_allowed(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        graph["stance"][0]["accepted_harm"].append(
            {
                "payer": "future maintainers",
                "cost": "a guard nobody maintains",
                "resource": "maintenance cost",
            }
        )
        self.assertEqual(validate_graph(graph), [])

    def test_surface_can_serve_a_stance_and_an_unopposed_stake(self) -> None:
        graph = load_graph(LUWU_GRAPH)
        self.assertEqual(validate_graph(graph), [])
        verifiability = next(
            surface
            for surface in graph["surface"]
            if surface["id"] == "luwu-verifiability-review"
        )
        self.assertEqual(verifiability["unopposed_stake"], "S12")
        self.assertTrue(
            any(
                "luwu-verifiability-review" in stance["surfaces"]
                for stance in graph["stance"]
            )
        )

    def test_lint_does_not_read_skill_prose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph_path = root / ".agents" / "review-graph.toml"
            skill = root / ".agents" / "skills" / "demo-a-review" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "This surface has final authority. Always reject a performance "
                "improvement that weakens freshness, regardless of the opposing "
                "stance.\n",
                encoding="utf-8",
            )
            graph_path.parent.mkdir(parents=True, exist_ok=True)
            graph_path.write_text(ring_graph(3), encoding="utf-8")
            self.assertEqual(
                check_graph(graph_path, check_paths=False, check_generated=False),
                [],
            )

    def test_lint_pipeline_does_not_target_authored_skill_prose(self) -> None:
        scripts = ROOT / "skills" / "hydra-crux" / "scripts"
        authored_globs = ("*-stance/SKILL.md", "*-review/SKILL.md")
        offenders = [
            path.name
            for path in sorted(scripts.glob("lint_*.py"))
            if any(glob in path.read_text(encoding="utf-8") for glob in authored_globs)
        ]
        self.assertEqual(offenders, [])


class GenerationTests(unittest.TestCase):
    def test_registry_is_deterministic_and_stale_detection_works(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(5))
        graph_path = Path("/tmp/demo/.agents/review-graph.toml")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rendered = render_all(graph, graph_path, out)
            write_rendered(rendered)
            self.assertEqual(check_rendered(rendered), [])
            registry = out / "demo-stance-registry" / "SKILL.md"
            registry.write_text(
                registry.read_text() + "\nhand edit\n", encoding="utf-8"
            )
            self.assertTrue(any("stale" in error for error in check_rendered(rendered)))

    def test_views_are_generated_only_when_asked(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3, with_prose=True))
        graph_path = Path("/tmp/demo/.agents/review-graph.toml")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            topology = render_all(graph, graph_path, out)
            self.assertFalse(any("s0-stance" in str(path) for path in topology))
            views = render_all(graph, graph_path, out, views=True)
            self.assertTrue(any("s0-stance" in str(path) for path in views))

    def test_table_padding_is_not_drift(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        graph_path = Path("/tmp/demo/.agents/review-graph.toml")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rendered = render_all(graph, graph_path, out)
            write_rendered(rendered)
            registry = out / "demo-stance-registry" / "SKILL.md"
            registry.write_text(
                registry.read_text(encoding="utf-8").replace(
                    "| --- | --- | --- | --- |", "| ----- | :--- | ---: | --- |", 1
                ),
                encoding="utf-8",
            )
            self.assertEqual(check_rendered(rendered), [])


class RouteTests(unittest.TestCase):
    def test_closure_adds_the_opponent_and_its_surface(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        result = route(graph, ["src/a.py"])
        self.assertEqual(result["status"], "ok")
        self.assertIn("s0-stance", [stance["id"] for stance in result["stances"]])
        self.assertIn("s1-stance", [stance["id"] for stance in result["stances"]])
        self.assertTrue(result["closure_added"])

    def test_budget_makes_skips_explicit(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(5))
        result = route(graph, ["src/shared.py"], budget=2)
        self.assertEqual(result["status"], "needs_grouping")
        self.assertTrue(result["skipped"])
        accepted = route(
            graph,
            ["src/shared.py"],
            budget=2,
            accept_skip=True,
            skip_reasons={f"s{index}-stance": "second batch" for index in range(5)},
        )
        self.assertEqual(accepted["status"], "accepted_with_skips")
        self.assertTrue(all(item["reason"] for item in accepted["skipped"]))
        executed = {
            stance for group in accepted["groups"] for stance in group["stances"]
        }
        skipped = {item["stance"] for item in accepted["skipped"]}
        self.assertFalse(executed & skipped)

    def test_prior_decision_is_routed(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        graph["sacrifice"] = [
            {
                "decision": "D1",
                "sacrificed": "s0-stance",
                "given_up": "whole-profile proof",
                "why": "the budget gate",
                "stances": ["s0-stance"],
            }
        ]
        result = route(graph, ["src/a.py"])
        self.assertTrue(
            any(item["decision"] == "D1" for item in result["prior_decisions"])
        )

    def test_prior_decision_is_filtered_by_axis(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        graph["sacrifice"] = [
            {
                "decision": "D1",
                "sacrificed": "s0-stance",
                "given_up": "whole-profile proof",
                "why": "the budget gate",
                "axes": ["axis-0-1"],
                "stances": ["s0-stance"],
            }
        ]
        result = route(graph, ["src/b.py"])
        self.assertFalse(
            any(item["decision"] == "D1" for item in result["prior_decisions"])
        )

    def test_no_match_is_not_silent(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        result = route(graph, ["docs/unrelated.md"])
        self.assertEqual(result["status"], "no_match")
        self.assertEqual(result["surfaces"], [])

    def test_undeclared_axes_are_reported(self) -> None:
        graph = __import__("tomllib").loads(ring_graph(3))
        result = route(graph, ["src/shared.py"])
        self.assertTrue(result["unclosed_axes"])
        self.assertTrue(all(axis["reason"] for axis in result["unclosed_axes"]))


class LuwuMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = load_graph(LUWU_GRAPH)

    def test_nine_stances_and_five_axes(self) -> None:
        self.assertEqual(len(self.graph["stance"]), 9)
        self.assertEqual(len(self.graph["opposition"]), 5)
        axes = {
            axis
            for stance in self.graph["stance"]
            for axis in [
                opposition["id"]
                for opposition in self.graph["opposition"]
                if stance["id"] in opposition["stances"]
            ]
        }
        self.assertEqual(
            axes,
            {
                "proof-vs-cost",
                "exposure-vs-continuity",
                "authority-vs-completion",
                "footprint-vs-recovery",
                "equivalence-vs-noise",
            },
        )

    def test_equivalence_route_does_not_expand_to_all(self) -> None:
        result = route(self.graph, ["src/luwu/semantic.py"])
        ids = {stance["id"] for stance in result["stances"]}
        self.assertEqual(
            ids,
            {"luwu-proven-equivalence-stance", "luwu-quiet-signal-stance"},
        )
        self.assertEqual(
            [opposition["id"] for opposition in result["oppositions"]],
            ["equivalence-vs-noise"],
        )

    def test_apply_route_selects_authority_axis_without_equivalence(self) -> None:
        result = route(self.graph, ["src/luwu/apply.py"])
        ids = {stance["id"] for stance in result["stances"]}
        self.assertIn("luwu-answerable-authority-stance", ids)
        self.assertIn("luwu-operational-completion-stance", ids)
        self.assertNotIn("luwu-proven-equivalence-stance", ids)
        self.assertNotIn("luwu-quiet-signal-stance", ids)
        self.assertLess(len(ids), len(self.graph["stance"]))

    def test_decision_status_is_visible(self) -> None:
        result = route(self.graph, ["src/luwu/apply.py"])
        c1a = next(
            decision
            for decision in result["prior_decisions"]
            if decision["conflict"].startswith("C-1a")
        )
        self.assertEqual(c1a["status"], "decided_not_implemented")
        self.assertTrue(c1a["reopen_when"])
        self.assertTrue(c1a["owner_document"])

    def test_unrepresented_stakes_are_preserved(self) -> None:
        themes = {row["stake"] for row in self.graph["unrepresented"]}
        self.assertIn("platform reach", themes)
        self.assertIn("the cost of the guard apparatus itself", themes)

    def test_primitive_reuse_is_a_before_write_surface(self) -> None:
        review = route(self.graph, ["src/luwu/apply.py"])
        self.assertNotIn(
            "luwu-primitive-reuse",
            {surface["id"] for surface in review["surfaces"]},
        )
        before_write = route(self.graph, ["src/luwu/apply.py"], phase="before-write")
        self.assertIn(
            "luwu-primitive-reuse",
            {surface["id"] for surface in before_write["surfaces"]},
        )


if __name__ == "__main__":
    unittest.main()
