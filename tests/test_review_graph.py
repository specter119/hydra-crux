from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "hydra-crux" / "scripts"
SCRIPT = SCRIPT_DIR / "hydra_graph.py"
sys.path.insert(0, str(SCRIPT_DIR))
import hydra_graph as hg

GIT_ENV_VARS = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
}


def demo_toml() -> str:
    return """
version = 2
project = "demo"

[[stake]]
id = "a"
objective = "A wins"
evidence = ["docs/a.md", "AGENTS.md"]

[[stake]]
id = "b"
objective = "B wins"
evidence = ["docs/b.md"]

[[stake]]
id = "c"
objective = "C wins"
evidence = ["docs/c.md", "AGENTS.md"]

[[stake]]
id = "d"
objective = "D wins"
evidence = ["docs/d.md"]

[[stake]]
id = "solo"
objective = "Run the direct check"
evidence = ["docs/check.md"]

[[surface]]
id = "a-review"
title = "A review"
trigger = ["A changes"]
owner_documents = ["docs/a.md#owner"]
skill = ".agents/skills/a-review/SKILL.md"
paths = ["src/a.py", "src/generated/**"]
exclude_paths = ["src/generated/**"]
keywords = ["alpha", "dry-run"]
contends = ["axis-a-b"]

[[surface]]
id = "b-review"
title = "B review"
trigger = ["B changes"]
owner_documents = ["docs/b.md"]
skill = ".agents/skills/b-review/SKILL.md"
paths = ["src/b.py"]
keywords = ["beta"]
contends = ["axis-c-d"]

[[surface]]
id = "shared-review"
title = "Shared review"
trigger = ["shared changes"]
owner_documents = ["docs/shared.md"]
skill = ".agents/skills/shared-review/SKILL.md"
paths = ["src/shared.py"]
contends = ["axis-a-b"]

[[surface]]
id = "check-review"
title = "Direct check"
trigger = ["check changes"]
owner_documents = ["docs/check.md"]
skill = ".agents/skills/check-review/SKILL.md"
paths = ["docs/check.md"]
unopposed_stake = "solo"

[[stance]]
id = "a-stance"
title = "A"
objective = "A wins"
skill = ".agents/skills/a-stance/SKILL.md"
surfaces = ["a-review", "shared-review"]
stakes = ["a"]

[[stance.accepted_harm]]
payer = "b-stance"
payer_stance = "b-stance"
cost = "A costs B"
resource = "shared"

[[stance]]
id = "b-stance"
title = "B"
objective = "B wins"
skill = ".agents/skills/b-stance/SKILL.md"
surfaces = ["a-review", "shared-review"]
stakes = ["b"]

[[stance.accepted_harm]]
payer = "a-stance"
payer_stance = "a-stance"
cost = "B costs A"
resource = "shared"

[[stance]]
id = "c-stance"
title = "C"
objective = "C wins"
skill = ".agents/skills/c-stance/SKILL.md"
surfaces = ["b-review", "shared-review"]
stakes = ["c"]

[[stance.accepted_harm]]
payer = "d-stance"
payer_stance = "d-stance"
cost = "C costs D"
resource = "other"

[[stance]]
id = "d-stance"
title = "D"
objective = "D wins"
skill = ".agents/skills/d-stance/SKILL.md"
surfaces = ["b-review", "shared-review"]
stakes = ["d"]

[[stance.accepted_harm]]
payer = "c-stance"
payer_stance = "c-stance"
cost = "D costs C"
resource = "other"

[[opposition]]
id = "axis-a-b"
stances = ["a-stance", "b-stance"]
contended_resource = "shared"

[[opposition]]
id = "axis-c-d"
stances = ["c-stance", "d-stance"]
contended_resource = "other"

[[decision]]
id = "D-ab"
kind = "joint"
summary = "Both sides are satisfied"
owner_document = "docs/a.md#decision"
reopen_when = "A or B changes"
axes = ["axis-a-b"]
stances = ["a-stance", "b-stance"]
surfaces = ["a-review"]

[[decision]]
id = "D-cd"
kind = "sacrifice"
summary = "C paid for D"
owner_document = "docs/c.md"
reopen_when = "C can be preserved"
status = "implemented"
given_up = "C"
decided_by = "user"
sacrificed = "c-stance"
axes = ["axis-c-d"]
stances = ["c-stance"]
surfaces = ["b-review"]

[[decision]]
id = "D-surface"
kind = "open"
summary = "A surface-only question"
owner_document = "docs/b.md"
reopen_when = "evidence arrives"
owner = "maintainers"
next_action = "Measure it"
surfaces = ["b-review"]
"""


def demo_graph() -> dict:
    return tomllib.loads(demo_toml())


def clean_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in GIT_ENV_VARS}
    env.update(
        {
            "GIT_AUTHOR_NAME": "Hydra Tests",
            "GIT_AUTHOR_EMAIL": "hydra@example.invalid",
            "GIT_COMMITTER_NAME": "Hydra Tests",
            "GIT_COMMITTER_EMAIL": "hydra@example.invalid",
        }
    )
    return env


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def commit_all(root: Path, message: str = "checkpoint") -> None:
    result = git(root, "add", "-A")
    assert result.returncode == 0, result.stderr
    result = git(root, "commit", "-m", message)
    assert result.returncode == 0, result.stderr


def run_cli(
    root: Path,
    *args: str,
    graph: bool = True,
    poison_git_env: bool = False,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT)]
    if graph:
        command.extend(["--graph", str(root / ".agents" / "review-graph.toml")])
    command.extend(args)
    env = clean_env()
    if poison_git_env:
        env.update(
            {
                "GIT_DIR": "/nonexistent/git-dir",
                "GIT_WORK_TREE": "/nonexistent/work-tree",
                "GIT_INDEX_FILE": "/nonexistent/index",
                "GIT_OBJECT_DIRECTORY": "/nonexistent/objects",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/nonexistent/alternates",
                "GIT_COMMON_DIR": "/nonexistent/common",
            }
        )
    return subprocess.run(
        command,
        cwd=cwd or root,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def write_graph(root: Path, text: str | None = None) -> Path:
    path = root / ".agents" / "review-graph.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or demo_toml(), encoding="utf-8")
    return path


def make_project(root: Path, *, in_git: bool = True, full: bool = False) -> Path:
    graph_path = write_graph(root)
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "a.py").write_text("value = 1\n", encoding="utf-8")
    (root / "src" / "b.py").write_text("value = 2\n", encoding="utf-8")
    if full:
        for name in ("a", "b", "c", "d", "shared", "check"):
            path = root / "docs" / f"{name}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {name}\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("owners\n", encoding="utf-8")
        for surface in demo_graph()["surface"]:
            path = root / surface["skill"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("surface\n", encoding="utf-8")
        for stance in demo_graph()["stance"]:
            path = root / stance["skill"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("stance\n", encoding="utf-8")
        generated = run_cli(root, "generate")
        assert generated.returncode == 0, generated.stderr
    if in_git:
        assert git(root, "init", "-q").returncode == 0
        commit_all(root, "initial")
    return graph_path


def read_pass(path: Path) -> tuple[dict, str]:
    return hg._parse_pass(path.read_text(encoding="utf-8"))


def write_pass(path: Path, metadata: dict, body: str) -> None:
    path.write_text(hg._serialize_pass(metadata, body), encoding="utf-8")


def only_pass(root: Path) -> Path:
    paths = list((root / ".agents" / "reviews").glob("*.md"))
    assert len(paths) == 1, paths
    return paths[0]


def bind(
    root: Path, slug: str = "demo", *extra: str
) -> subprocess.CompletedProcess[str]:
    return run_cli(
        root,
        "route",
        "--changed",
        "src/a.py",
        "--pass",
        slug,
        *extra,
    )


class GraphValidationTests(unittest.TestCase):
    def test_valid_graph_and_decision_kinds(self) -> None:
        graph = demo_graph()
        self.assertEqual(hg.validate_graph(graph), [])
        self.assertEqual(
            {row["kind"] for row in graph["decision"]},
            {"joint", "sacrifice", "open"},
        )

    def test_unknown_table_field_and_enum_are_rejected(self) -> None:
        graph = demo_graph()
        graph["surprise"] = []
        graph["stake"][0]["surprise"] = True
        graph["decision"][1]["status"] = "sometimes"
        graph["decision"][1]["decided_by"] = "robot"
        errors = hg.validate_graph(graph)
        self.assertTrue(
            any(error.startswith("graph: unknown field `surprise`") for error in errors)
        )
        self.assertTrue(
            any(
                error.startswith("stake `a`: unknown field `surprise`")
                for error in errors
            )
        )
        self.assertTrue(any("`status` must be" in error for error in errors))
        self.assertTrue(any("`decided_by` must be" in error for error in errors))

    def test_joint_must_cover_both_sides(self) -> None:
        graph = demo_graph()
        graph["decision"][0]["stances"] = ["a-stance"]
        errors = hg.validate_graph(graph)
        self.assertTrue(any("does not cover both sides" in error for error in errors))

    def test_joint_requires_axes_and_open_requires_action(self) -> None:
        graph = demo_graph()
        graph["decision"][0].pop("axes")
        graph["decision"][2].pop("next_action")
        errors = hg.validate_graph(graph)
        self.assertTrue(any("joint decision needs `axes`" in error for error in errors))
        self.assertTrue(
            any("missing or non-string `next_action`" in error for error in errors)
        )

    def test_unknown_sacrificed_id_is_rejected(self) -> None:
        graph = demo_graph()
        graph["decision"][1]["sacrificed"] = "nobody"
        errors = hg.validate_graph(graph)
        self.assertTrue(
            any("unknown sacrificed id `nobody`" in error for error in errors)
        )

    def test_unrepresented_can_be_sacrificed(self) -> None:
        graph = demo_graph()
        graph["unrepresented"] = [
            {"id": "users", "stake": "Users", "where": "docs/a.md", "why": "No stance"}
        ]
        graph["decision"][1]["sacrificed"] = "users"
        self.assertEqual(hg.validate_graph(graph), [])

    def test_opposition_needs_a_decision(self) -> None:
        graph = demo_graph()
        graph["decision"] = [graph["decision"][2]]
        errors = hg.validate_graph(graph)
        self.assertTrue(
            any("axis-a-b" in error and "not referenced" in error for error in errors)
        )
        self.assertTrue(
            any("axis-c-d" in error and "not referenced" in error for error in errors)
        )

    def test_stake_orphan_and_double_representation_are_rejected(self) -> None:
        orphan = demo_graph()
        orphan["stance"][0]["stakes"] = []
        errors = hg.validate_graph(orphan)
        self.assertTrue(any("stake `a`: is orphaned" in error for error in errors))

        dual = demo_graph()
        dual["surface"][0]["unopposed_stake"] = "a"
        errors = hg.validate_graph(dual)
        self.assertTrue(
            any("both stance-represented and unopposed" in error for error in errors)
        )

    def test_surface_read_by_stance_needs_contends(self) -> None:
        graph = demo_graph()
        graph["surface"][0]["contends"] = []
        errors = hg.validate_graph(graph)
        self.assertTrue(any("whose `contends` is empty" in error for error in errors))

    def test_global_id_uniqueness(self) -> None:
        graph = demo_graph()
        graph["surface"][0]["id"] = "a"
        errors = hg.validate_graph(graph)
        self.assertTrue(any("already used by stake" in error for error in errors))

    def test_v1_lists_retired_fields_and_upgrade_document(self) -> None:
        graph = demo_graph()
        graph["version"] = 1
        graph["resolved"] = []
        graph["surface"][0]["phase"] = "review"
        graph["opposition"][0]["recorded_sacrifice"] = "old"
        errors = hg.validate_graph(graph)
        self.assertEqual(len(errors), 1)
        self.assertIn("references/upgrade-v1.md", errors[0])
        self.assertIn("[[resolved]]", errors[0])
        self.assertIn("surface.phase", errors[0])
        self.assertIn("opposition.recorded_sacrifice", errors[0])


class GenerationTests(unittest.TestCase):
    def test_registry_links_follow_skill_field(self) -> None:
        graph = demo_graph()
        graph["stance"][0]["skill"] = "custom/a.md"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph_path = root / ".agents" / "review-graph.toml"
            rendered = hg.render_all(graph, graph_path, root)
            registry_path = next(iter(rendered))
            registry = rendered[registry_path]
            self.assertIn("[`a-stance`](../../../custom/a.md)", registry)
            self.assertIn("[`b-stance`](../b-stance/SKILL.md)", registry)

    def test_registry_renders_decision_ids_and_kinds_without_retired_sections(
        self,
    ) -> None:
        graph = demo_graph()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = next(
                iter(
                    hg.render_all(
                        graph, root / ".agents" / "review-graph.toml", root
                    ).values()
                )
            )
            self.assertIn("`D-ab` | joint", registry)
            self.assertIn("`D-cd` | sacrifice", registry)
            self.assertIn("`D-surface` | open", registry)
            for retired in (
                "Resolved without escalation",
                "Recorded sacrifice",
                "State",
                "Evidence",
                "Counterexamples",
                "Migration note",
            ):
                self.assertNotIn(retired, registry)

    def test_stale_detection_ignores_table_padding_only(self) -> None:
        graph = demo_graph()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rendered = hg.render_all(
                graph, root / ".agents" / "review-graph.toml", root
            )
            hg.write_rendered(rendered)
            self.assertEqual(hg.check_rendered(rendered), [])
            registry = next(iter(rendered))
            registry.write_text(
                registry.read_text(encoding="utf-8").replace(
                    "| --- | --- | --- | --- |", "| ----- | :--- | ---: | --- |", 1
                ),
                encoding="utf-8",
            )
            self.assertEqual(hg.check_rendered(rendered), [])
            registry.write_text(
                registry.read_text(encoding="utf-8") + "hand edit\n", encoding="utf-8"
            )
            self.assertTrue(
                any("stale" in error for error in hg.check_rendered(rendered))
            )

    def test_generate_validates_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = demo_toml().replace('kind = "joint"', 'kind = "unknown"')
            write_graph(root, text)
            result = run_cli(root, "generate")
            self.assertEqual(result.returncode, 1)
            self.assertFalse(
                (root / ".agents" / "skills" / "demo-stance-registry").exists()
            )

    def test_removed_generation_and_validation_flags_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_graph(root)
            for args in (
                ("generate", "--out", "x"),
                ("generate", "--docs-out", "docs"),
                ("generate", "--views"),
                ("generate", "--check"),
                ("validate",),
            ):
                with self.subTest(args=args):
                    self.assertEqual(run_cli(root, *args).returncode, 2)


class RouteTests(unittest.TestCase):
    def test_route_selects_whole_axis_and_unselected_readers(self) -> None:
        result = hg.route(demo_graph(), ["src/a.py"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["axes"], ["axis-a-b"])
        self.assertEqual(
            {row["id"] for row in result["stances"]}, {"a-stance", "b-stance"}
        )
        self.assertNotIn("closure_surfaces", result)
        self.assertNotIn("unclosed_axes", result)

        shared = hg.route(demo_graph(), ["src/shared.py"])
        self.assertEqual(
            {row["id"] for row in shared["unselected_readers"]},
            {"c-stance", "d-stance"},
        )

    def test_owner_document_and_stake_evidence_select_axes(self) -> None:
        owner = hg.route(demo_graph(), ["docs/a.md"])
        self.assertEqual(owner["axes"], ["axis-a-b"])
        self.assertTrue(
            any(
                "owner_document" in match
                for match in owner["surfaces"][0]["matched_by"]
            )
        )

        evidence = hg.route(demo_graph(), ["AGENTS.md"])
        self.assertEqual(evidence["axes"], ["axis-a-b", "axis-c-d"])

    def test_exclude_paths_suppresses_every_surface_match_for_file(self) -> None:
        result = hg.route(
            demo_graph(),
            ["src/generated/a.py"],
            added_lines={"src/generated/a.py": ["alpha"]},
            keywords_evaluated=True,
        )
        self.assertEqual(result["status"], "no_match")
        self.assertEqual(result["surfaces"], [])

    def test_keyword_uses_added_lines_word_boundaries_and_case_folding(self) -> None:
        graph = demo_graph()
        matched = hg.route(
            graph,
            ["src/unrelated.py"],
            added_lines={"src/unrelated.py": ["use ALPHA here"]},
            keywords_evaluated=True,
        )
        self.assertEqual(matched["axes"], ["axis-a-b"])
        for text in ("prealpha", "alpha2", "alphabet", "src/alpha-name.py"):
            with self.subTest(text=text):
                result = hg.route(
                    graph,
                    [text if text.endswith(".py") else "src/unrelated.py"],
                    added_lines={"src/unrelated.py": [text]}
                    if not text.endswith(".py")
                    else {},
                    keywords_evaluated=True,
                )
                self.assertEqual(result["status"], "no_match")

    def test_diff_rename_dev_null_no_prefix_and_per_file_added_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            diff = """diff --git old.py new.py
--- old.py
+++ new.py
@@ -1 +1 @@
-alpha
+ALPHA
diff --git a/src/gone.py b/src/gone.py
--- a/src/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-alpha
diff --git a/src/new.py b/src/new.py
--- /dev/null
+++ b/src/new.py
@@ -0,0 +1 @@
+beta
"""
            changed, added = hg.parse_diff(diff, root)
            self.assertEqual(changed, ["new.py", "old.py", "src/gone.py", "src/new.py"])
            self.assertEqual(added, {"new.py": ["ALPHA"], "src/new.py": ["beta"]})

    def test_cli_diff_only_and_changed_union(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_graph(root)
            diff_path = root / "change.diff"
            diff_path.write_text(
                "diff --git src/b.py src/b.py\n--- src/b.py\n+++ src/b.py\n@@ -1 +1 @@\n-old\n+beta\n",
                encoding="utf-8",
            )
            result = run_cli(
                root,
                "route",
                "--changed",
                "./src/../src/a.py",
                "--diff-file",
                str(diff_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["changed_files"], ["src/a.py", "src/b.py"])
            self.assertEqual(payload["axes"], ["axis-a-b", "axis-c-d"])
            self.assertTrue(payload["keywords_evaluated"])

    def test_diff_file_stdin_and_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_graph(root)
            missing = run_cli(root, "route", "--diff-file", "missing.diff")
            self.assertEqual(missing.returncode, 2)
            self.assertIn("cannot read --diff-file", missing.stderr)

            env = clean_env()
            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--graph",
                    str(root / ".agents" / "review-graph.toml"),
                    "route",
                    "--diff-file",
                    "-",
                ],
                input="diff --git src/a.py src/a.py\n--- src/a.py\n+++ src/a.py\n@@ -0,0 +1 @@\n+alpha\n",
                capture_output=True,
                text=True,
                check=False,
                cwd=root,
                env=env,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertTrue(json.loads(process.stdout)["keywords_evaluated"])

    def test_path_normalization_absolute_and_outside(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            tempfile.TemporaryDirectory() as outside,
        ):
            root = Path(tmp)
            write_graph(root)
            absolute = root / "src" / "a.py"
            result = run_cli(root, "route", "--changed", str(absolute))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["changed_files"], ["src/a.py"])
            rejected = run_cli(root, "route", "--changed", str(Path(outside) / "a.py"))
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("outside project root", rejected.stderr)
            rejected = run_cli(root, "route", "--changed", "../outside.py")
            self.assertEqual(rejected.returncode, 2)

    def test_explicit_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            graph_path = base / "graphs" / "nested" / "review-graph.toml"
            graph_path.parent.mkdir(parents=True)
            graph_path.write_text(demo_toml(), encoding="utf-8")
            project = base / "project"
            project.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--graph",
                    str(graph_path),
                    "route",
                    "--project-root",
                    str(project),
                    "--changed",
                    "src/a.py",
                ],
                capture_output=True,
                text=True,
                check=False,
                env=clean_env(),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["changed_files"], ["src/a.py"])

    def test_include_skip_no_reviewers_and_stance_hint(self) -> None:
        graph = demo_graph()
        included = hg.route(
            graph,
            ["docs/unrelated.md"],
            include_axes={"axis-c-d": "explicit concern"},
        )
        self.assertEqual(included["status"], "ok")
        self.assertEqual(included["axes"], ["axis-c-d"])
        self.assertEqual(included["included"][0]["reason"], "explicit concern")

        skipped = hg.route(
            graph,
            ["src/a.py"],
            skip_reasons={"axis-a-b": "out of scope"},
        )
        self.assertEqual(skipped["status"], "no_reviewers")
        self.assertEqual(skipped["stances"], [])
        self.assertEqual(skipped["prior_decisions"], [{"id": "D-ab", "kind": "joint"}])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_graph(root)
            result = run_cli(
                root,
                "route",
                "--changed",
                "src/a.py",
                "--skip",
                "a-stance=not relevant",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("axis-a-b", result.stderr)
            self.assertIn("not stance", result.stderr)

    def test_prior_decisions_use_axes_else_surfaces(self) -> None:
        graph = demo_graph()
        axis = hg.route(graph, ["src/a.py"])
        self.assertIn({"id": "D-ab", "kind": "joint"}, axis["prior_decisions"])
        self.assertNotIn({"id": "D-surface", "kind": "open"}, axis["prior_decisions"])
        surface = hg.route(graph, ["src/b.py"])
        self.assertIn({"id": "D-cd", "kind": "sacrifice"}, surface["prior_decisions"])
        self.assertIn({"id": "D-surface", "kind": "open"}, surface["prior_decisions"])

    def test_no_match_unopposed_only_and_keywords_flag(self) -> None:
        graph = demo_graph()
        no_match = hg.route(graph, ["docs/unrelated.md"])
        self.assertEqual(no_match["status"], "no_match")
        self.assertFalse(no_match["keywords_evaluated"])
        direct = hg.route(graph, ["docs/check.md"])
        self.assertEqual(direct["status"], "unopposed_only")
        self.assertEqual(direct["unopposed"][0]["surface"], "check-review")
        self.assertTrue(direct["unopposed"][0]["skill"])

    def test_no_graph_invalid_graph_and_removed_route_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = run_cli(root, "route", graph=False)
            self.assertEqual(missing.returncode, 2)
            self.assertEqual(json.loads(missing.stdout)["status"], "no_graph")
            missing_markdown = run_cli(
                root, "route", "--format", "markdown", graph=False
            )
            self.assertEqual(missing_markdown.returncode, 2)
            self.assertIn("no_graph", missing_markdown.stdout)
            self.assertNotIn("Traceback", missing_markdown.stderr)

            write_graph(root, "version = 2\nproject = 'demo'\nunknown = true\n")
            invalid = run_cli(root, "route")
            self.assertEqual(invalid.returncode, 1)
            self.assertEqual(json.loads(invalid.stdout)["status"], "invalid_graph")
            invalid_markdown = run_cli(root, "route", "--format", "markdown")
            self.assertEqual(invalid_markdown.returncode, 1)
            self.assertIn("invalid_graph", invalid_markdown.stdout)
            self.assertNotIn("Traceback", invalid_markdown.stderr)

            write_graph(root)
            for flag in (
                ("--accept-skip",),
                ("--budget", "2"),
                ("--phase", "review"),
                ("--diff", "alpha"),
            ):
                with self.subTest(flag=flag):
                    self.assertEqual(run_cli(root, "route", *flag).returncode, 2)

    def test_default_graph_search_stops_at_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            write_graph(base)
            repo = base / "repo"
            (repo / ".git").mkdir(parents=True)
            nested = repo / "nested"
            nested.mkdir()
            result = run_cli(nested, "route", graph=False, cwd=nested)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "no_graph")


class PassDocumentTests(unittest.TestCase):
    def test_new_pass_has_exact_fields_sections_and_python_blob_sha1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            result = bind(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            path = only_pass(root)
            metadata, body = read_pass(path)
            self.assertEqual(tuple(metadata), hg.PASS_FIELDS)
            self.assertEqual(metadata["status"], "draft")
            self.assertEqual(metadata["target"], "")
            self.assertEqual(metadata["changed"], ["src/a.py"])
            data = (root / "src" / "a.py").read_bytes()
            expected = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            self.assertEqual(metadata["baseline"], {"src/a.py": expected})
            self.assertEqual(metadata["decisions"], [])
            self.assertEqual(metadata["rebaselined"], [])
            for heading in (
                "Findings",
                "Ledger",
                "Map candidates",
                "Counterexample candidates",
            ):
                self.assertIn(f"## {heading}", body)

    def test_draft_rebind_preserves_body_and_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            metadata, body = read_pass(path)
            write_pass(
                path,
                metadata,
                body.replace("## Ledger\n", "## Ledger\n\nkept finding\n"),
            )
            baseline = dict(metadata["baseline"])
            result = bind(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            rebound, rebound_body = read_pass(path)
            self.assertEqual(rebound["baseline"], baseline)
            self.assertIn("kept finding", rebound_body)

    def test_rebind_can_add_clean_or_previously_dirty_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            result = run_cli(
                root,
                "route",
                "--changed",
                "src/a.py",
                "--changed",
                "src/b.py",
                "--pass",
                "demo",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rebound, _ = read_pass(path)
            self.assertEqual(rebound["changed"], ["src/a.py", "src/b.py"])
            self.assertIn("src/b.py", rebound["baseline"])

            (root / "src" / "b.py").write_text(
                "dirty before binding\n", encoding="utf-8"
            )
            self.assertEqual(bind(root, "other").returncode, 0)
            other = next((root / ".agents" / "reviews").glob("*-other.md"))
            other_metadata, _ = read_pass(other)
            self.assertIn("src/b.py", other_metadata["dirty_at_bind"])
            result = run_cli(
                root,
                "route",
                "--changed",
                "src/a.py",
                "--changed",
                "src/b.py",
                "--pass",
                "other",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            other_rebound, _ = read_pass(other)
            self.assertEqual(
                other_rebound["baseline"]["src/b.py"],
                other_metadata["dirty_at_bind"]["src/b.py"],
            )

    def test_changed_target_rebind_is_rejected_and_rebaseline_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            (root / "src" / "a.py").write_text("formatted = true\n", encoding="utf-8")
            rejected = bind(root)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("target changed", rejected.stderr)

            result = bind(root, "demo", "--rebaseline", "formatter rewrote target")
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata, _ = read_pass(path)
            self.assertEqual(
                metadata["rebaselined"][-1]["reason"], "formatter rewrote target"
            )
            changed, _ = hg.target_changes(root, metadata, ".agents/reviews")
            self.assertFalse(changed)

    def test_rebaseline_requires_existing_non_head_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            missing = bind(root, "missing", "--rebaseline", "no document")
            self.assertEqual(missing.returncode, 2)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            commit_all(root, "commit pass")
            rejected = bind(root, "demo", "--rebaseline", "must reject")
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("already in HEAD", rejected.stderr)
            self.assertIsNotNone(hg._head_version(root, path))

    def test_dirty_at_bind_does_not_false_positive_and_new_dirty_file_does(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            unrelated = root / "unrelated.txt"
            unrelated.write_text("committed\n", encoding="utf-8")
            commit_all(root, "add unrelated")
            unrelated.write_text("dirty at bind\n", encoding="utf-8")
            self.assertEqual(bind(root).returncode, 0)
            metadata, _ = read_pass(only_pass(root))
            self.assertIn("unrelated.txt", metadata["dirty_at_bind"])
            unrelated.write_text("stash restored or changed again\n", encoding="utf-8")
            changed, reasons = hg.target_changes(root, metadata, ".agents/reviews")
            self.assertFalse(changed, reasons)

            (root / "new-dirty.txt").write_text("new\n", encoding="utf-8")
            changed, reasons = hg.target_changes(root, metadata, ".agents/reviews")
            self.assertTrue(changed)
            self.assertTrue(any("new-dirty.txt" in reason for reason in reasons))

    def test_pass_rejects_bad_slug_all_and_non_ok_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            self.assertEqual(bind(root, "Bad_Slug").returncode, 2)
            self.assertEqual(
                run_cli(root, "route", "--all", "--pass", "demo").returncode, 2
            )
            self.assertEqual(
                run_cli(
                    root, "route", "--changed", "docs/none.md", "--pass", "demo"
                ).returncode,
                2,
            )


class LintTests(unittest.TestCase):
    def test_clean_draft_lints_with_scrubbed_git_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            result = run_cli(root, "lint", poison_git_env=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_survey_with_changed_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="survey", target="src/a.py")
            write_pass(
                path, metadata, body.replace("## Ledger\n", "## Ledger\n\nsurveyed\n")
            )
            (root / "src" / "a.py").write_text("changed\n", encoding="utf-8")
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 1)
            self.assertIn("status must be record or abandoned", result.stderr)
            self.assertIn("--rebaseline REASON", result.stderr)

    def test_empty_record_and_empty_ledger_are_rejected(self) -> None:
        for ledger_case in (False, True):
            with (
                self.subTest(ledger_case=ledger_case),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                make_project(root, full=True)
                self.assertEqual(bind(root).returncode, 0)
                path = only_pass(root)
                metadata, body = read_pass(path)
                metadata.update(status="record", target="src/a.py")
                if ledger_case:
                    metadata["decisions"] = ["D-ab"]
                else:
                    body = body.replace("## Ledger\n", "## Ledger\n\nentry\n")
                write_pass(path, metadata, body)
                result = run_cli(root, "lint")
                self.assertEqual(result.returncode, 1)
                expected = (
                    "requires a non-empty ## Ledger" if ledger_case else "empty record"
                )
                self.assertIn(expected, result.stderr)

    def test_committed_draft_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            commit_all(root, "accidentally commit draft")
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 1)
            self.assertIn("committed draft", result.stderr)
            self.assertNotIn("otherwise set status to record", result.stderr)

    def test_head_historical_document_only_gets_parse_and_status_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="record", target="src/a.py", decisions=["D-ab"])
            write_pass(
                path, metadata, body.replace("## Ledger\n", "## Ledger\n\nentry\n")
            )
            commit_all(root, "historical record")
            metadata["unknown_future_field"] = {"anything": True}
            write_pass(
                path, metadata, "+++ not valid body is irrelevant after front matter\n"
            )
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata["status"] = "draft"
            write_pass(path, metadata, "anything\n")
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 1)
            self.assertIn("historical pass cannot become a draft", result.stderr)

    def test_abandoned_reason_and_rebaseline_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata["status"] = "abandoned"
            write_pass(path, metadata, body)
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 1)
            self.assertIn("requires a reason", result.stderr)
            self.assertNotIn("otherwise set status to record", result.stderr)
            metadata["reason"] = "superseded"
            metadata["rebaselined"] = [{"reason": "format", "date": "2026-11-17"}]
            write_pass(path, metadata, body)
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("rebaselined 2026-11-17: format", result.stdout)

    def test_paths_registry_and_reviews_dir_ignore_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            (root / "docs" / "a.md").unlink()
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 1)
            self.assertIn("cited path does not exist", result.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            (root / ".gitignore").write_text(
                "docs/a.md\n.agents/reviews/\n", encoding="utf-8"
            )
            git(root, "rm", "-q", "--cached", "docs/a.md")
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 1)
            self.assertIn("cited path is git-ignored", result.stderr)
            self.assertIn("reviews_dir` is git-ignored", result.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            registry = root / ".agents" / "skills" / "demo-stance-registry" / "SKILL.md"
            registry.write_text(
                registry.read_text(encoding="utf-8") + "stale\n", encoding="utf-8"
            )
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 1)
            self.assertIn("generated registry is stale", result.stderr)

    def test_non_git_degraded_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, in_git=False, full=True)
            self.assertEqual(bind(root).returncode, 0)
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Not a git work tree", result.stdout)
            (root / "src" / "a.py").write_text("changed\n", encoding="utf-8")
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 1)
            self.assertIn("target blob changed", result.stderr)

            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="survey", target="")
            write_pass(path, metadata, body)
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 0, result.stderr)

    def assert_target_change_rejected(self, root: Path) -> None:
        result = run_cli(root, "lint", poison_git_env=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("target changed", result.stderr)
        self.assertIn("status must be record or abandoned", result.stderr)
        self.assertIn("otherwise set status to record", result.stderr)

    def test_rp1_code_changes_with_draft_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            (root / "src" / "a.py").write_text(
                "code changed with draft\n", encoding="utf-8"
            )
            self.assert_target_change_rejected(root)

    def test_rp1_code_changes_before_survey_is_written_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            (root / "src" / "a.py").write_text(
                "code changed before survey\n", encoding="utf-8"
            )
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="survey", target="src/a.py")
            write_pass(
                path, metadata, body.replace("## Ledger\n", "## Ledger\n\nentry\n")
            )
            self.assert_target_change_rejected(root)

    def test_rp2_survey_is_written_before_code_changes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="survey", target="src/a.py")
            write_pass(
                path, metadata, body.replace("## Ledger\n", "## Ledger\n\nentry\n")
            )
            (root / "src" / "a.py").write_text(
                "code changed after survey\n", encoding="utf-8"
            )
            self.assert_target_change_rejected(root)


class FollowUpSchemaTests(unittest.TestCase):
    def test_project_directories_are_relative_inside_project_without_dotdot(
        self,
    ) -> None:
        for field, value in (
            ("reviews_dir", "../reviews"),
            ("skills_dir", "/tmp/skills"),
            ("skills_dir", "nested/../skills"),
        ):
            with self.subTest(field=field, value=value):
                graph = demo_graph()
                graph[field] = value
                errors = hg.validate_graph(graph)
                self.assertTrue(
                    any(f"`{field}` must be relative" in error for error in errors)
                )


class FollowUpRouteTests(unittest.TestCase):
    def test_non_ok_pass_emits_normal_route_and_writes_nothing(self) -> None:
        for scenario in ("unopposed_only", "no_reviewers"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_project(root)
                args = ["route", "--pass", "demo"]
                if scenario == "unopposed_only":
                    args.extend(["--changed", "docs/check.md"])
                else:
                    args.extend(
                        ["--changed", "src/a.py", "--skip", "axis-a-b=not reviewed"]
                    )
                result = run_cli(root, *args)
                self.assertEqual(result.returncode, 2)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], scenario)
                if scenario == "unopposed_only":
                    self.assertEqual(payload["unopposed"][0]["surface"], "check-review")
                else:
                    self.assertEqual(payload["skipped"][0]["axis"], "axis-a-b")
                self.assertFalse((root / ".agents" / "reviews").exists())

    def test_pass_rejects_directory_and_include_axis_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            include_only = run_cli(
                root,
                "route",
                "--include-axis",
                "axis-a-b=explicit concern",
                "--pass",
                "axis-only",
            )
            self.assertEqual(include_only.returncode, 2)
            self.assertIn("at least one changed file", include_only.stderr)

            write_graph(
                root,
                demo_toml().replace(
                    'paths = ["src/a.py", "src/generated/**"]', 'paths = ["src"]'
                ),
            )
            directory = run_cli(root, "route", "--changed", "src", "--pass", "demo")
            self.assertEqual(directory.returncode, 2)
            self.assertIn("not directories", directory.stderr)
            self.assertFalse((root / ".agents" / "reviews").exists())

    def test_project_root_is_rejected_with_pass(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            tempfile.TemporaryDirectory() as other,
        ):
            root = Path(tmp)
            make_project(root)
            result = run_cli(
                root,
                "route",
                "--project-root",
                other,
                "--changed",
                "src/a.py",
                "--pass",
                "demo",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("cannot be combined with --pass", result.stderr)
            self.assertFalse((root / ".agents" / "reviews").exists())

    def test_unselected_axis_skip_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            result = run_cli(
                root,
                "route",
                "--changed",
                "src/a.py",
                "--skip",
                "axis-c-d=typo guard",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("unselected axis: axis-c-d", result.stderr)

    def test_path_normalization_is_lexical_not_symlink_resolution(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            tempfile.TemporaryDirectory() as outside,
        ):
            root = Path(tmp)
            make_project(root)
            (Path(outside) / "nested").mkdir()
            (root / "link").symlink_to(
                Path(outside) / "nested", target_is_directory=True
            )
            result = run_cli(root, "route", "--changed", "link/../src/a.py")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["changed_files"], ["src/a.py"])

    def test_hunk_internal_removed_header_is_not_a_file_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            changed, added = hg.parse_diff(
                "diff --git a/src/a.py b/src/a.py\n"
                "--- a/src/a.py\n"
                "+++ b/src/a.py\n"
                "@@ -1 +1 @@\n"
                "--- comment\n"
                "+alpha\n",
                Path(tmp),
            )
            self.assertEqual(changed, ["src/a.py"])
            self.assertEqual(added, {"src/a.py": ["alpha"]})

    def test_diff_paths_are_relative_to_git_root_not_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "nested"
            write_graph(project)
            self.assertEqual(git(base, "init", "-q").returncode, 0)
            diff_path = base / "change.diff"
            diff_path.write_text(
                "diff --git a/nested/src/a.py b/nested/src/a.py\n"
                "--- a/nested/src/a.py\n"
                "+++ b/nested/src/a.py\n"
                "@@ -0,0 +1 @@\n"
                "+alpha\n",
                encoding="utf-8",
            )
            result = run_cli(project, "route", "--diff-file", str(diff_path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["changed_files"], ["src/a.py"])

    def test_quoted_non_ascii_diff_headers_are_decoded(self) -> None:
        old = '"a/\\344\\270\\255\\346\\226\\207.py"'
        new = '"b/\\346\\226\\260.py"'
        with tempfile.TemporaryDirectory() as tmp:
            changed, added = hg.parse_diff(
                f"diff --git {old} {new}\n"
                f"--- {old}\n"
                f"+++ {new}\n"
                "@@ -0,0 +1 @@\n"
                "+alpha\n",
                Path(tmp),
            )
            self.assertEqual(changed, ["中文.py", "新.py"])
            self.assertEqual(added, {"新.py": ["alpha"]})


class FollowUpPassDocumentTests(unittest.TestCase):
    def test_pass_slug_requires_exact_dated_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suffix = root / "2026-11-01-route-review.md"
            exact = root / "2026-11-02-review.md"
            suffix.write_text("suffix\n", encoding="utf-8")
            exact.write_text("exact\n", encoding="utf-8")
            self.assertEqual(hg._find_pass(root, "review"), exact)
            exact.unlink()
            self.assertIsNone(hg._find_pass(root, "review"))
            self.assertEqual(hg._find_pass(root, "route-review"), suffix)

    def test_non_draft_rebind_requires_rebaseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="survey", target="src/a.py")
            write_pass(path, metadata, body)
            result = bind(root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("not draft", result.stderr)
            self.assertEqual(read_pass(path)[0]["status"], "survey")

    def test_rebaseline_preserves_survey_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="survey", target="src/a.py")
            write_pass(path, metadata, body)
            (root / "src" / "a.py").write_text("formatted\n", encoding="utf-8")
            result = bind(root, "demo", "--rebaseline", "formatter")
            self.assertEqual(result.returncode, 0, result.stderr)
            rebound, _ = read_pass(path)
            self.assertEqual(rebound["status"], "survey")
            self.assertEqual(rebound["rebaselined"][-1]["reason"], "formatter")

    def test_rebind_cannot_shrink_changed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            self.assertEqual(bind(root).returncode, 0)
            result = run_cli(root, "route", "--changed", "src/b.py", "--pass", "demo")
            self.assertEqual(result.returncode, 2)
            self.assertIn("cannot remove previously bound", result.stderr)
            self.assertEqual(read_pass(only_pass(root))[0]["changed"], ["src/a.py"])

    def test_non_ascii_dirty_path_is_recorded_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            path = root / "中文.txt"
            path.write_text("committed\n", encoding="utf-8")
            commit_all(root, "add non-ASCII file")
            path.write_text("dirty\n", encoding="utf-8")
            self.assertEqual(bind(root).returncode, 0)
            metadata, _ = read_pass(only_pass(root))
            self.assertIn("中文.txt", metadata["dirty_at_bind"])
            self.assertNotEqual(metadata["dirty_at_bind"]["中文.txt"], "absent")

    def test_markdown_contains_pass_oppositions_reader_axes_and_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root)
            bound = bind(root, "demo", "--format", "markdown")
            self.assertEqual(bound.returncode, 0, bound.stderr)
            self.assertIn(f"Pass file: {only_pass(root)}", bound.stdout)

            result = run_cli(
                root, "route", "--changed", "src/shared.py", "--format", "markdown"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("## Oppositions", result.stdout)
            self.assertIn("`axis-a-b` — shared", result.stdout)
            self.assertIn(
                "`c-stance` — surfaces: shared-review; axes: axis-c-d", result.stdout
            )
            self.assertIn("`D-ab` (joint)", result.stdout)


class FollowUpLintTests(unittest.TestCase):
    def test_valid_record_with_changed_target_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            (root / "src" / "a.py").write_text("implemented\n", encoding="utf-8")
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="record", target="src/a.py")
            write_pass(
                path, metadata, body.replace("## Ledger\n", "## Ledger\n\nentry\n")
            )
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_valid_survey_with_unchanged_target_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="survey", target="src/a.py")
            write_pass(
                path, metadata, body.replace("## Ledger\n", "## Ledger\n\nentry\n")
            )
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_survey_with_graph_decisions_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            self.assertEqual(bind(root).returncode, 0)
            path = only_pass(root)
            metadata, body = read_pass(path)
            metadata.update(status="survey", target="src/a.py", decisions=["D-ab"])
            write_pass(
                path, metadata, body.replace("## Ledger\n", "## Ledger\n\nentry\n")
            )
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 1)
            self.assertIn("survey cannot contain graph decisions", result.stderr)
            self.assertNotIn("otherwise set status to record", result.stderr)

    def test_real_git_stash_does_not_invalidate_bound_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_project(root, full=True)
            unrelated = root / "unrelated.txt"
            unrelated.write_text("committed\n", encoding="utf-8")
            commit_all(root, "add unrelated")
            unrelated.write_text("dirty at bind\n", encoding="utf-8")
            self.assertEqual(bind(root).returncode, 0)
            stashed = git(
                root, "stash", "push", "-m", "test stash", "--", "unrelated.txt"
            )
            self.assertEqual(stashed.returncode, 0, stashed.stderr)
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 0, result.stderr)
            restored = git(root, "stash", "pop")
            self.assertEqual(restored.returncode, 0, restored.stderr)
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 0, result.stderr)


class PrekConfigTests(unittest.TestCase):
    def test_validate_skills_runs_for_code_tests_and_scripts(self) -> None:
        text = (ROOT / "prek.toml").read_text(encoding="utf-8")
        hook = text.split('id = "validate-skills"', 1)[1]
        self.assertIn("files = '^(skills|tests|scripts)/'", hook)


class LuwuFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = ROOT
        self.graph_path = ROOT / "tests" / "fixtures" / "luwu-review-graph.toml"
        self.graph = hg.load_graph(self.graph_path)

    def test_fixture_v2_counts_and_unrepresented_ids(self) -> None:
        self.assertEqual(hg.validate_graph(self.graph), [])
        self.assertEqual(len(self.graph["stake"]), 11)
        self.assertEqual(len(self.graph["surface"]), 7)
        self.assertEqual(len(self.graph["stance"]), 9)
        self.assertEqual(len(self.graph["opposition"]), 6)
        self.assertTrue(all(row.get("id") for row in self.graph["unrepresented"]))
        self.assertIn(
            "primitive-reuse", {row["id"] for row in self.graph["unrepresented"]}
        )
        self.assertNotIn(
            "luwu-primitive-reuse", {row["id"] for row in self.graph["surface"]}
        )

    def test_fixture_lints_in_a_stub_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_graph(root, self.graph_path.read_text(encoding="utf-8"))
            cited = []
            for stake in self.graph["stake"]:
                cited.extend(stake["evidence"])
            for surface in self.graph["surface"]:
                cited.extend(surface["owner_documents"])
                cited.append(surface["skill"])
            for stance in self.graph["stance"]:
                cited.append(stance["skill"])
            for decision in self.graph["decision"]:
                cited.append(decision["owner_document"])
            for raw in cited:
                path = root / raw.split("#", 1)[0]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("stub\n", encoding="utf-8")
            generated = run_cli(root, "generate")
            self.assertEqual(generated.returncode, 0, generated.stderr)
            result = run_cli(root, "lint")
            self.assertEqual(result.returncode, 0, result.stderr)

    def route(self, changed: str) -> dict:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--graph",
                str(self.graph_path),
                "route",
                "--changed",
                changed,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            env=clean_env(),
        )
        return {"code": result.returncode, **json.loads(result.stdout)}

    def test_manifest_contains_opponents_and_unselected_reader(self) -> None:
        result = self.route("./src/luwu/manifest.py")
        self.assertEqual(result["code"], 0, result)
        self.assertEqual(result["status"], "ok")
        stances = {row["id"] for row in result["stances"]}
        for axis in result["oppositions"]:
            self.assertTrue(set(axis["stances"]) <= stances)
        self.assertTrue(result["unselected_readers"])

    def test_agents_selects_stake_evidence_axes(self) -> None:
        result = self.route("AGENTS.md")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            set(result["axes"]),
            {
                "proof-vs-cost",
                "exposure-vs-continuity",
                "exposure-vs-proof",
                "authority-vs-completion",
                "footprint-vs-recovery",
            },
        )

    def test_catalog_does_not_select_confidentiality(self) -> None:
        result = self.route("src/luwu/catalog.py")
        self.assertNotIn(
            "luwu-confidentiality-review", {row["id"] for row in result["surfaces"]}
        )
        self.assertNotIn("exposure-vs-continuity", result["axes"])

    def test_accept_skip_is_rejected(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--graph",
                str(self.graph_path),
                "route",
                "--changed",
                "src/luwu/manifest.py",
                "--accept-skip",
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            env=clean_env(),
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
