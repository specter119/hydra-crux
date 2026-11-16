from __future__ import annotations

import argparse
import http.client
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "hydra-crux" / "scripts"))

from concept_audit import (
    Config,
    Endpoint,
    bleed_candidates,
    cmd_run,
    cmd_setup,
    cmd_status,
    coverage,
    graph_findings,
    load_config,
    load_homes,
    parse_skill,
    resolve_config,
    triage,
)

GRAPH = """\
version = 1
project = "demo"

[[stake]]
id = "S1"
title = "A recoverable state survives every action"
status = "represented"

[[surface]]
id = "demo-surface"
title = "Demo surface"
skill = ".agents/skills/demo-surface/SKILL.md"
keywords = ["boundary", "recovery"]

[[stance]]
id = "demo-stance"
title = "Demo stance"
objective = "A recoverable state survives every action."
skill = ".agents/skills/demo-stance/SKILL.md"
surfaces = ["demo-surface"]

[[stance.accepted_harm]]
payer = "demo-other-stance"
cost = "extra work"

[[opposition]]
id = "demo-axis"
stances = ["demo-stance", "demo-other-stance"]
state = "decided"
"""

OLD_SKILL = """\
---
name: demo-review
description: Demo review.
---

# Demo review

## Stable core and changing contract

The stable value is: **A recoverable state survives every action.** It does not
own unrelated questions.

## Scope boundary

This stance owns filesystem replacement and recovery. It does not own who may
authorize a change. Hand those findings to the authority stance.

## Good patterns

- Re-observe the staged identity before replacing the file.

## Bad patterns

- Trust a cached digest after the tree changed.
- Quantify the orbital angular momentum of the deployment.
"""

SURFACE = """\
---
name: demo-surface
description: Demo surface.
---

# Demo surface

## Checks

- Inspect the journal and the lock path before writing.
- Do not delete the journal before the write commits.
"""

STANCE = """\
---
name: demo-stance
description: Demo stance.
---

# Demo stance

## Objective

A recoverable state survives every action.

## Stable core and changing contract

When the contract changes, compare the old and new recovery paths, preserve the
safe-next-action link, and test each boundary.
"""


class ConceptAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / ".agents" / "skills" / "demo-surface").mkdir(parents=True)
        (self.root / ".agents" / "skills" / "demo-stance").mkdir(parents=True)
        (self.root / "archive" / "domain-review" / "demo-review").mkdir(parents=True)
        (self.root / ".agents" / "review-graph.toml").write_text(GRAPH, encoding="utf-8")
        (self.root / ".agents" / "skills" / "demo-surface" / "SKILL.md").write_text(
            SURFACE, encoding="utf-8"
        )
        (self.root / ".agents" / "skills" / "demo-stance" / "SKILL.md").write_text(
            STANCE, encoding="utf-8"
        )
        (self.root / "archive" / "domain-review" / "demo-review" / "SKILL.md").write_text(
            OLD_SKILL, encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_parse_skill_splits_roles(self) -> None:
        atoms = parse_skill(
            self.root / "archive" / "domain-review" / "demo-review" / "SKILL.md", self.root
        )
        roles = {atom.role for atom in atoms}
        self.assertIn("objective", roles)
        self.assertIn("scope", roles)
        self.assertIn("check", roles)
        self.assertIn("anti_pattern", roles)
        objective = next(atom for atom in atoms if atom.role == "objective")
        self.assertIn("recoverable state", objective.text)
        self.assertNotIn("**", objective.text)

    def test_coverage_flags_orphan(self) -> None:
        import tomllib

        graph = tomllib.loads(GRAPH)
        homes = load_homes(graph, self.root)
        atoms = parse_skill(
            self.root / "archive" / "domain-review" / "demo-review" / "SKILL.md", self.root
        )
        rows = coverage(atoms, homes, threshold=0.08)
        orphan_texts = [row["atom"].text for row in rows if row["orphan"]]
        self.assertTrue(any("orbital angular momentum" in text for text in orphan_texts))
        self.assertFalse(any("Re-observe the staged identity" in text for text in orphan_texts))

    def test_bleed_ranks_candidates_without_heading_gate(self) -> None:
        import tomllib

        graph = tomllib.loads(GRAPH)
        homes = load_homes(graph, self.root)
        rows = bleed_candidates(homes, self.root)
        surface = [row for row in rows if row["home"] == "demo-surface"]
        stance = [row for row in rows if row["home"] == "demo-stance"]
        self.assertTrue(any("journal" in row["text"] for row in surface))
        self.assertTrue(any("compare" in row["text"] for row in stance))
        self.assertTrue(all(row["signal"] == "verdict-affinity-in-surface" for row in surface))
        self.assertTrue(all(row["signal"] == "check-affinity-in-stance" for row in stance))

    def test_graph_findings_reports_payer_symmetry(self) -> None:
        import tomllib

        findings = graph_findings(tomllib.loads(GRAPH))
        self.assertEqual(findings["payer_symmetry"], 1)
        self.assertEqual(findings["payer_total"], 1)
        self.assertEqual(findings["axis_sizes"], {2: 1})

    def test_graph_findings_reports_one_to_one_surfaces(self) -> None:
        import tomllib

        graph = tomllib.loads(GRAPH)
        graph["surface"].append(
            {"id": "extra-surface", "title": "Extra", "skill": ".agents/skills/extra/SKILL.md"}
        )
        graph["stance"].append(
            {
                "id": "extra-stance",
                "title": "Extra",
                "skill": ".agents/skills/extra-stance/SKILL.md",
                "surfaces": ["extra-surface"],
            }
        )
        findings = graph_findings(graph)
        self.assertEqual(findings["surface_count"], 2)
        self.assertEqual(findings["one_to_one_surfaces"], ["demo-surface", "extra-surface"])

        graph["stance"].append(
            {
                "id": "shared-stance",
                "title": "Shared",
                "skill": ".agents/skills/shared/SKILL.md",
                "surfaces": ["demo-surface", "extra-surface"],
            }
        )
        self.assertEqual(graph_findings(graph)["one_to_one_surfaces"], [])

    def test_document_sources_are_inventoried(self) -> None:
        doc = self.root / "AGENTS.md"
        doc.write_text(
            "# Working method\n\n"
            "## Boundaries\n\n"
            "- Inspect the journal and the lock path before writing.\n",
            encoding="utf-8",
        )
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "NOTES.md").write_text(
            "# Notes\n\n## Recovery\n\n"
            "- Inspect the journal and the lock path before writing.\n",
            encoding="utf-8",
        )
        report = self.run_report(source=[str(doc), str(docs)], source_dir=[])
        self.assertIn("atoms from 2 source documents", report)
        self.assertIn("| AGENTS.md |", report)
        self.assertIn("| docs/NOTES.md |", report)
        self.assertIn("1/1 surfaces pair one-to-one", report)

    def test_missing_config_is_deterministic_only(self) -> None:
        config = load_config(self.root / "missing.toml")
        self.assertEqual(config.layers(), ["deterministic"])

    def test_setup_writes_0600_and_prefers_key_env(self) -> None:
        path = self.root / "audit.toml"
        args = argparse.Namespace(
            config=str(path),
            decision_url="http://127.0.0.1:3425/v1/systemone",
            decision_model="typesafe/jev-latest",
            decision_key=None,
            decision_key_env="DEMO_DECISION_KEY",
            llm_url=None,
            llm_model=None,
            llm_key=None,
            llm_key_env=None,
        )
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cmd_setup(args), 0)
        text = path.read_text(encoding="utf-8")
        self.assertIn("key_env", text)
        self.assertNotIn("key =", text)
        self.assertEqual(oct(path.stat().st_mode)[-3:], "600")

    def run_args(self, **overrides: object) -> argparse.Namespace:
        values = {
            "config": str(self.root / "missing.toml"),
            "graph": self.root / ".agents" / "review-graph.toml",
            "project_root": self.root,
            "source": [],
            "source_dir": [str(self.root / "archive" / "domain-review")],
            "out": self.root / "audit.md",
            "json": None,
            "threshold": 0.08,
            "max_model_calls": 2,
            "decision_url": None,
            "decision_model": None,
            "decision_key": None,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def run_report(self, **overrides: object) -> str:
        args = self.run_args(**overrides)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cmd_run(args), 0)
        return Path(args.out).read_text(encoding="utf-8")

    def test_missing_config_reports_absent_sections(self) -> None:
        report = self.run_report()
        self.assertIn("skipped (no [decision])", report)
        self.assertIn("Skipped: no decision model configured", report)
        self.assertIn("Read the candidates above yourself", report)

    def test_partial_decision_section_is_incomplete_not_absent(self) -> None:
        config = self.root / "partial.toml"
        config.write_text('[decision]\nurl = "http://127.0.0.1:1/v1"\n', encoding="utf-8")
        args = self.run_args(config=str(config), max_model_calls=0)
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cmd_status(args), 0)
        self.assertIn("incomplete [decision] (missing model)", out.getvalue())
        self.assertIn(
            "skipped (incomplete [decision]: missing model)",
            self.run_report(config=str(config), max_model_calls=0),
        )

    def test_cli_flags_complete_a_partial_section(self) -> None:
        config = self.root / "partial.toml"
        config.write_text('[decision]\nurl = "http://127.0.0.1:1/v1"\n', encoding="utf-8")
        resolved = resolve_config(self.run_args(config=str(config), decision_model="cli-model"))
        decision = resolved.decision
        if decision is None:
            self.fail("the partial section was dropped instead of completed")
        self.assertTrue(decision.configured)
        self.assertEqual(decision.model, "cli-model")
        self.assertEqual(decision.url, "http://127.0.0.1:1/v1")

    def test_cli_only_endpoint_reads_the_env_key(self) -> None:
        args = self.run_args(decision_url="http://127.0.0.1:1/v1", decision_model="cli-model")
        with mock.patch.dict(os.environ, {"HYDRA_DECISION_KEY": "env-secret"}):
            resolved = resolve_config(args)
        decision = resolved.decision
        if decision is None:
            self.fail("the CLI endpoint was dropped")
        self.assertEqual(decision.key, "env-secret")

    def test_configured_but_uncalled_says_why(self) -> None:
        config = self.root / "full.toml"
        config.write_text(
            '[decision]\nurl = "http://127.0.0.1:1/v1"\nmodel = "m"\n', encoding="utf-8"
        )
        report = self.run_report(config=str(config), max_model_calls=0)
        self.assertIn("configured, not called (--max-model-calls 0)", report)
        self.assertIn("Skipped: `--max-model-calls` is 0", report)

    def test_invalid_toml_degrades_to_deterministic(self) -> None:
        config = self.root / "broken.toml"
        config.write_text("[decision\n", encoding="utf-8")
        report = self.run_report(config=str(config), max_model_calls=0)
        self.assertIn("Config error:", report)
        self.assertIn("orbital angular momentum", report)

    def test_malformed_model_answers_become_error_rows(self) -> None:
        rows = [{"text": "t", "home": "h", "signal": "s"}]
        decision = Config(
            path=self.root / "x.toml", decision=Endpoint("http://127.0.0.1:1/v1", "m")
        )
        for payload in (
            {"answers": []},
            {"answers": {"q": {"choice": "banana", "confidence": 0.9}}},
            {"answers": {"q": {"choice": "check", "confidence": "high"}}},
            {"answers": {"q": {"choice": "check", "confidence": None}}},
        ):
            with self.subTest(payload=payload):
                with mock.patch("concept_audit.post_json", return_value=payload):
                    result = triage(rows, decision, 1)
                self.assertEqual(result[0]["role"], "error")
                self.assertEqual(result[0]["layer"], "decision-model")

    def test_status_redacts_url_credentials(self) -> None:
        config = self.root / "creds.toml"
        config.write_text(
            '[decision]\nurl = "http://user:pass@127.0.0.1:1/v1?token=abc"\nmodel = "m"\n',  # pragma: allowlist secret
            encoding="utf-8",
        )
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cmd_status(self.run_args(config=str(config))), 0)
        self.assertNotIn("pass@", out.getvalue())
        self.assertNotIn("token=abc", out.getvalue())

    def test_decision_model_end_to_end(self) -> None:
        seen: list[dict] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers["Content-Length"])
                seen.append(json.loads(self.rfile.read(length)))
                body = json.dumps(
                    {"answers": {"q": {"choice": "check", "confidence": 0.9}}}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            config = self.root / "full.toml"
            config.write_text(
                f'[decision]\nurl = "http://127.0.0.1:{server.server_port}/v1"\n'
                'model = "m"\n',
                encoding="utf-8",
            )
            report = self.run_report(config=str(config), max_model_calls=1)
        finally:
            server.shutdown()
            server.server_close()
        self.assertIn("active (1 calls)", report)
        self.assertIn("| check | 0.90 | decision-model |", report)
        self.assertEqual(seen[0]["model"], "m")
        self.assertEqual(seen[0]["questions"]["q"]["type"], "choice")
        self.assertIn("state", seen[0])

    def test_http_exceptions_become_error_rows(self) -> None:
        rows = [{"text": "t", "home": "h", "signal": "s"}]
        decision = Config(
            path=self.root / "x.toml", decision=Endpoint("http://127.0.0.1:1/v1", "m")
        )
        for error in (
            http.client.IncompleteRead(b"x", 100),
            http.client.BadStatusLine("NOT HTTP"),
            http.client.InvalidURL("nonnumeric port: 'secret@'"),
        ):
            with self.subTest(error=type(error).__name__):
                with mock.patch("concept_audit.post_json", side_effect=error):
                    result = triage(rows, decision, 1)
                self.assertEqual(result[0]["role"], "error")

    def test_error_text_redacts_userinfo(self) -> None:
        rows = [{"text": "t", "home": "h", "signal": "s"}]
        decision = Config(
            path=self.root / "x.toml", decision=Endpoint("http://127.0.0.1:1/v1", "m")
        )
        error = ValueError("failed for http://user:secret@127.0.0.1:1/v1")
        with mock.patch("concept_audit.post_json", side_effect=error):
            result = triage(rows, decision, 1)
        self.assertNotIn("secret", result[0]["error"])

    def test_numeric_string_and_bool_confidence_are_rejected(self) -> None:
        rows = [{"text": "t", "home": "h", "signal": "s"}]
        decision = Config(
            path=self.root / "x.toml", decision=Endpoint("http://127.0.0.1:1/v1", "m")
        )
        for confidence in ("0.9", True):
            payload = {"answers": {"q": {"choice": "check", "confidence": confidence}}}
            with self.subTest(confidence=confidence):
                with mock.patch("concept_audit.post_json", return_value=payload):
                    result = triage(rows, decision, 1)
                self.assertEqual(result[0]["role"], "error")

    def test_error_column_shows_the_reason(self) -> None:
        config = self.root / "full.toml"
        config.write_text(
            '[decision]\nurl = "http://127.0.0.1:1/v1"\nmodel = "m"\n', encoding="utf-8"
        )
        report = self.run_report(config=str(config), max_model_calls=1)
        self.assertIn("| error |", report)
        self.assertIn("1 failed", report)

    def test_incomplete_section_explains_the_skip(self) -> None:
        config = self.root / "partial.toml"
        config.write_text('[decision]\nurl = "http://127.0.0.1:1/v1"\n', encoding="utf-8")
        report = self.run_report(config=str(config), max_model_calls=1)
        self.assertIn("the [decision] section is incomplete (missing model)", report)

    def test_invalid_config_marks_status_and_skip(self) -> None:
        config = self.root / "broken.toml"
        config.write_text("[decision\n", encoding="utf-8")
        report = self.run_report(config=str(config), max_model_calls=1)
        self.assertIn("skipped (invalid config)", report)
        self.assertIn("the config file is invalid", report)

    def test_wrong_shape_section_is_a_config_error(self) -> None:
        config = self.root / "shape.toml"
        config.write_text('decision = "not a table"\n', encoding="utf-8")
        report = self.run_report(config=str(config), max_model_calls=1)
        self.assertIn("must be a table", report)

    def test_url_credentials_become_basic_auth(self) -> None:
        seen: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                seen.append(self.headers.get("Authorization", ""))
                length = int(self.headers["Content-Length"])
                self.rfile.read(length)
                body = json.dumps(
                    {"answers": {"q": {"choice": "check", "confidence": 0.9}}}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            config = self.root / "creds.toml"
            config.write_text(
                f'[decision]\nurl = "http://user:pw@127.0.0.1:{server.server_port}/v1"\n'  # pragma: allowlist secret
                'model = "m"\n',
                encoding="utf-8",
            )
            report = self.run_report(config=str(config), max_model_calls=1)
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(seen, ["Basic dXNlcjpwdw=="])
        self.assertIn("active (1 calls)", report)
        self.assertNotIn("pw@", report)

    def test_env_supplies_url_and_model(self) -> None:
        args = self.run_args()
        with mock.patch.dict(
            os.environ,
            {
                "HYDRA_DECISION_URL": "http://127.0.0.1:1/v1",
                "HYDRA_DECISION_MODEL": "env-model",
            },
        ):
            resolved = resolve_config(args)
        decision = resolved.decision
        if decision is None:
            self.fail("the environment did not configure an endpoint")
        self.assertTrue(decision.configured)
        self.assertEqual(decision.model, "env-model")

    def test_negative_max_calls_is_rejected(self) -> None:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cmd_run(self.run_args(max_model_calls=-1)), 2)

    def test_json_reports_config_error(self) -> None:
        config = self.root / "broken.toml"
        config.write_text("[decision\n", encoding="utf-8")
        payload = self.root / "audit.json"
        self.run_report(config=str(config), max_model_calls=1, json=payload)
        data = json.loads(payload.read_text(encoding="utf-8"))
        self.assertIn("config_error", data)
        self.assertTrue(data["config_error"])


if __name__ == "__main__":
    unittest.main()
