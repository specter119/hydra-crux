from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "hydra-crux" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import concept_audit as ca
import hydra_graph as hg

FIXTURE = ROOT / "tests" / "fixtures" / "luwu-review-graph.toml"
TEST_KEY = "unit-test-key"

DOC = """# Notes

Nothing is written unless the exact bytes were re-read at the write boundary.
Compare the old and new behavior, then test each boundary.
Do not inline a near-copy of the guard.
The migration happened in three steps.
"""


def run_audit(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = ca.main(list(argv))
    return code, out.getvalue(), err.getvalue()


@contextmanager
def endpoint(answer):
    """Serve a decision-model endpoint. answer(text) returns (status, body)."""
    seen: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(
                {
                    "text": payload["state"]["text"],
                    "auth": self.headers.get("Authorization", ""),
                    "criteria": sorted(payload["questions"]["q"]["criteria"]),
                }
            )
            status, body = answer(payload["state"]["text"])
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1/systemone", seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def by_value(text: str) -> tuple[int, dict]:
    role = "objective" if "nothing is written" in text.lower() else "check"
    return 200, {
        "model": "jev-test",
        "answers": {"q": {"type": "choice", "choice": role, "confidence": 0.9}},
    }


class AuditCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        env = {k: v for k, v in os.environ.items() if not k.startswith("HYDRA_DECISION_")}
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        discover = mock.patch.object(ca.hydra_graph, "_default_graph", return_value=None)
        discover.start()
        self.addCleanup(discover.stop)
        self.config = self.root / "audit.toml"
        self.doc = self.root / "notes.md"
        self.doc.write_text(DOC, encoding="utf-8")

    def write_config(self, url: str, **extra: str) -> None:
        lines = ["[decision]", f'url = "{url}"', 'model = "test-model"']
        lines += [f'{key} = "{value}"' for key, value in extra.items()]
        self.config.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_json(self, *argv: str) -> tuple[int, dict, str]:
        out_json = self.root / "out.json"
        code, _, err = run_audit(
            "run", "--config", str(self.config), "--json", str(out_json),
            "--out", str(self.root / "report.md"), *argv,
        )
        data = json.loads(out_json.read_text(encoding="utf-8")) if out_json.exists() else {}
        return code, data, err

    def report(self) -> str:
        return (self.root / "report.md").read_text(encoding="utf-8")

    def make_graph_project(self) -> Path:
        project = self.root / "proj"
        graph = hg.load_graph(FIXTURE)
        (project / ".agents").mkdir(parents=True)
        (project / ".agents" / "review-graph.toml").write_text(
            FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
        )
        cited: list[str] = []
        for stake in graph["stake"]:
            cited.extend(stake["evidence"])
        for surface in graph["surface"]:
            cited.extend(surface["owner_documents"])
            cited.append(surface["skill"])
        for stance in graph["stance"]:
            cited.append(stance["skill"])
        for decision in graph["decision"]:
            cited.append(decision["owner_document"])
        for raw in cited:
            path = project / raw.split("#", 1)[0]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("stub\n", encoding="utf-8")
        return project


class RankingTests(AuditCase):
    def test_a_text_ranks_the_same_whatever_else_is_in_the_run(self) -> None:
        a = "Inspect the journal and the lock path before writing."
        b = "Sensitive values stay out of repositories and logs."
        alone = ca.assign_roles([a])[0]
        together = ca.assign_roles([b, a, b])[1]
        self.assertEqual(alone, together)

    def test_every_unit_becomes_an_atom_whatever_it_looks_like(self) -> None:
        atoms, read, empty = ca.collect_source_atoms([self.doc], self.root)
        texts = [atom.text for atom in atoms]
        self.assertEqual(len(texts), 4)
        self.assertTrue(any(t.startswith("Do not inline") for t in texts))
        self.assertTrue(any("migration happened" in t for t in texts))
        self.assertEqual((read, empty), (["notes.md"], []))

    def test_numbered_items_and_prose_beside_a_list_are_separate_atoms(self) -> None:
        text = (
            "# T\n\nA lead sentence stays in the run.\n\n"
            "1. First numbered item stands alone.\n"
            "2. Second numbered item stands alone.\n\n"
            "A closing sentence stays as well.\n"
        )
        found = [unit for _, _, unit in ca.units(text)]
        self.assertEqual(
            found,
            [
                "A lead sentence stays in the run.",
                "First numbered item stands alone.",
                "Second numbered item stands alone.",
                "A closing sentence stays as well.",
            ],
        )

    def test_sentences_in_one_paragraph_keep_their_own_line_numbers(self) -> None:
        atoms, _, _ = ca.collect_source_atoms([self.doc], self.root)
        self.assertEqual([a.line for a in atoms], [3, 4, 5, 6])

    def test_quoted_do_not_inside_a_sentence_is_kept(self) -> None:
        self.doc.write_text('Use the phrase "Do not write" in the example text.\n', encoding="utf-8")
        atoms, _, _ = ca.collect_source_atoms([self.doc], self.root)
        self.assertEqual(len(atoms), 1)

    def test_atoms_come_in_a_fixed_source_and_line_order(self) -> None:
        other = self.root / "a.md"
        other.write_text("Compare the before and after state at each boundary.\n", encoding="utf-8")
        forward, _, _ = ca.collect_source_atoms([self.doc, other], self.root)
        backward, _, _ = ca.collect_source_atoms([other, self.doc], self.root)
        self.assertEqual([a.where for a in forward], [a.where for a in backward])

    def test_document_without_english_prose_is_reported_empty(self) -> None:
        zh = self.root / "zh.md"
        zh.write_text("# \u8BF4\u660E\n\n\u8FD9\u4E2A\u9879\u76EE\u5B81\u53EF\u727A\u7272\u541E\u5410\u4E5F\u8981\u4FDD\u8BC1\u6BCF\u6B21\u5199\u5165\u524D\u91CD\u65B0\u8BFB\u53D6\u3002\n", encoding="utf-8")
        code, data, _ = self.run_json("--source", str(zh))
        self.assertEqual(code, 0)
        self.assertEqual([Path(p).name for p in data["empty_sources"]], ["zh.md"])
        report = self.report()
        self.assertIn("No atom was extracted from: ", report)
        self.assertIn("zh.md", report)
        self.assertIn("The inventory is empty.", report)


class OfflineTests(AuditCase):
    def test_no_config_makes_no_network_call(self) -> None:
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            code, data, _ = self.run_json("--source", str(self.doc))
        self.assertEqual(code, 0)
        self.assertEqual(data["mode"], "inventory-only")
        self.assertEqual(data["layers"], ["deterministic"])
        self.assertIn("skipped (no [decision])", self.report())

    def test_missing_graph_is_inventory_only_and_lists_every_atom_as_untriaged(self) -> None:
        code, data, _ = self.run_json("--source", str(self.doc))
        self.assertEqual(code, 0)
        self.assertEqual(len(data["untriaged"]), len(data["atoms"]))
        self.assertIn("--max-model-calls 4", self.report())

    def test_default_report_lists_every_untriaged_sentence(self) -> None:
        self.run_json("--source", str(self.doc))
        section = self.report().split("## Untriaged sentences")[1].split("## Needs human")[0]
        for sentence in ("Nothing is written", "Compare the old", "Do not inline", "The migration happened"):
            self.assertIn(sentence, section)

    def test_negative_call_limit_is_rejected(self) -> None:
        code, _, err = run_audit("run", "--config", str(self.config), "--source", str(self.doc),
                                 "--max-model-calls", "-1")
        self.assertEqual(code, 2)
        self.assertIn(">= 0", err)

    def test_malformed_toml_degrades_to_deterministic(self) -> None:
        self.config.write_text("[decision\n", encoding="utf-8")
        code, data, _ = self.run_json("--source", str(self.doc))
        self.assertEqual(code, 0)
        self.assertTrue(data["config_error"])
        self.assertIn("Config error:", self.report())


class ModelTests(AuditCase):
    def test_model_labels_objectives_and_the_report_names_the_endpoint(self) -> None:
        with endpoint(by_value) as (url, seen):
            self.write_config(url, key=TEST_KEY)
            code, data, _ = self.run_json("--source", str(self.doc), "--model-timeout", "5")
        self.assertEqual(code, 0)
        self.assertEqual(len(seen), 4)
        self.assertEqual({tuple(s["criteria"]) for s in seen}, {tuple(sorted(ca.ROLE_OPTIONS))})
        self.assertTrue(all(s["auth"] == f"Bearer {TEST_KEY}" for s in seen))
        report = self.report()
        self.assertIn("Sent 4 sentences", report)
        self.assertIn("model version jev-test", report)
        self.assertIn("Nothing is written unless", report.split("## Objective candidates")[1])
        self.assertEqual([r["line"] for r in data["triage"]], sorted(r["line"] for r in data["triage"]))
        self.assertNotIn(TEST_KEY, report)

    def test_call_limit_leaves_the_rest_untriaged_and_says_what_covers_all(self) -> None:
        with endpoint(by_value) as (url, seen):
            self.write_config(url)
            code, data, _ = self.run_json("--source", str(self.doc), "--max-model-calls", "1")
        self.assertEqual(code, 0)
        self.assertEqual(len(seen), 1)
        self.assertEqual(len(data["untriaged"]), 3)
        self.assertIn("--max-model-calls 4", self.report())

    def test_zero_calls_keeps_a_configured_run_local(self) -> None:
        with endpoint(by_value) as (url, seen):
            self.write_config(url)
            code, _, _ = self.run_json("--source", str(self.doc), "--max-model-calls", "0")
        self.assertEqual(code, 0)
        self.assertEqual(seen, [])
        self.assertIn("configured, not called (--max-model-calls 0)", self.report())

    def test_consecutive_transport_failures_stop_the_run(self) -> None:
        with endpoint(lambda text: (500, {"error": "down"})) as (url, seen):
            self.write_config(url)
            code, data, _ = self.run_json("--source", str(self.doc), "--model-timeout", "5")
        self.assertEqual(code, 0)
        self.assertEqual(len(seen), 2)
        self.assertEqual(len(data["untriaged"]), 2)
        self.assertIn("consecutive transport failures", data["stopped"])
        self.assertIn("HTTP Error 500", self.report())

    def test_malformed_answers_become_error_rows(self) -> None:
        answers = iter(
            [
                {"answers": {"q": {"choice": "banana", "confidence": 0.9}}},
                {"answers": {"q": {"choice": "check", "confidence": "high"}}},
                {"answers": []},
                {"answers": {"q": {"choice": "check", "confidence": True}}},
            ]
        )
        with endpoint(lambda text: (200, next(answers))) as (url, _):
            self.write_config(url)
            code, data, _ = self.run_json("--source", str(self.doc))
        self.assertEqual(code, 0)
        self.assertEqual([r["origin"] for r in data["triage"]], ["error"] * 4)
        self.assertIn("outside the seven labels", data["triage"][0]["error"])

    def test_a_non_object_response_is_an_error_row_not_a_failed_audit(self) -> None:
        bodies = iter([None, [], "text", 7])
        with endpoint(lambda text: (200, next(bodies))) as (url, _):
            self.write_config(url)
            code, data, _ = self.run_json("--source", str(self.doc))
        self.assertEqual(code, 0)
        self.assertEqual([r["origin"] for r in data["triage"]], ["error"] * 4)

    def test_a_model_that_echoes_the_key_does_not_leak_it(self) -> None:
        def echo(text: str) -> tuple[int, dict]:
            return 200, {"answers": {"q": {"choice": TEST_KEY, "confidence": TEST_KEY}}}

        with endpoint(echo) as (url, _):
            self.write_config(url, key=TEST_KEY)
            code, data, _ = self.run_json("--source", str(self.doc))
        self.assertEqual(code, 0)
        raw = json.dumps(data) + self.report()
        self.assertNotIn(TEST_KEY, raw)

    def test_a_success_resets_the_consecutive_failure_count(self) -> None:
        doc = self.root / "six.md"
        doc.write_text(
            "\n".join(f"Sentence number {name} stays in the inventory." for name in "ABCDEF") + "\n",
            encoding="utf-8",
        )
        statuses = iter([500, 200, 500, 500, 200, 200])

        def flaky(text: str) -> tuple[int, dict]:
            if next(statuses) == 500:
                return 500, {}
            return by_value(text)

        with endpoint(flaky) as (url, seen):
            self.write_config(url)
            code, data, _ = self.run_json("--source", str(doc))
        self.assertEqual(code, 0)
        self.assertEqual(len(seen), 4)
        self.assertEqual(len(data["untriaged"]), 2)
        self.assertIn("consecutive transport failures", data["stopped"])

    def test_cli_beats_environment_beats_config(self) -> None:
        with endpoint(by_value) as (cfg_url, cfg_seen), endpoint(by_value) as (env_url, env_seen), \
                endpoint(by_value) as (cli_url, cli_seen):
            self.write_config(cfg_url)
            with mock.patch.dict(os.environ, {"HYDRA_DECISION_URL": env_url}):
                self.run_json("--source", str(self.doc))
                self.assertEqual((len(cfg_seen), len(env_seen), len(cli_seen)), (0, 4, 0))
                self.run_json("--source", str(self.doc), "--decision-url", cli_url)
        self.assertEqual((len(cfg_seen), len(env_seen), len(cli_seen)), (0, 4, 4))

    def test_key_env_that_is_not_a_name_blocks_every_call_and_is_never_printed(self) -> None:
        secret = "sk-not-a-name-0000"
        with endpoint(by_value) as (url, seen):
            self.write_config(url, key_env=secret)
            code, data, _ = self.run_json("--source", str(self.doc))
            status_code, status_out, _ = run_audit("status", "--config", str(self.config))
        self.assertEqual(code, 0)
        self.assertEqual(seen, [])
        self.assertEqual(data["layers"], ["deterministic"])
        report = self.report()
        self.assertIn("key_env is not a valid environment variable name", report)
        self.assertNotIn(secret, report)
        self.assertEqual(status_code, 0)
        self.assertIn("incomplete", status_out)
        self.assertNotIn(secret, status_out)

    def test_environment_supplies_the_endpoint(self) -> None:
        with (
            endpoint(by_value) as (url, seen),
            mock.patch.dict(
                os.environ,
                {"HYDRA_DECISION_URL": url, "HYDRA_DECISION_MODEL": "m", "HYDRA_DECISION_KEY": TEST_KEY},
            ),
        ):
            code, _, _ = self.run_json("--source", str(self.doc))
        self.assertEqual(code, 0)
        self.assertEqual(len(seen), 4)

    def test_url_credentials_become_basic_auth_and_are_redacted(self) -> None:
        with endpoint(by_value) as (url, seen):
            self.write_config(url.replace("127.0.0.1", "user:pass@127.0.0.1"))
            code, _, _ = self.run_json("--source", str(self.doc))
        self.assertEqual(code, 0)
        self.assertTrue(seen and seen[0]["auth"].startswith("Basic "))
        self.assertNotIn("user:pass", self.report())


class UrlTests(unittest.TestCase):
    def test_ipv6_authority_keeps_its_brackets_when_credentials_are_split(self) -> None:
        clean, auth = ca.split_credentials("http://u:p@[::1]:3425/v1/systemone")
        self.assertEqual(clean, "http://[::1]:3425/v1/systemone")
        self.assertTrue(auth.startswith("Basic "))
        self.assertEqual(ca.redact_url("http://u:p@[::1]:3425/v1?token=abc"), "http://[::1]:3425/v1?token=****")

    def test_redact_text_removes_secrets_userinfo_and_query_values(self) -> None:
        text = "failed http://u:p@host/x?api_key=SECRET&b=2 with sk-1234"
        out = ca.redact_text(text, "sk-1234")
        for leaked in ("u:p", "SECRET", "sk-1234"):
            self.assertNotIn(leaked, out)


class SetupTests(AuditCase):
    def test_setup_writes_a_private_file_and_prefers_a_variable_name(self) -> None:
        code, _, _ = run_audit(
            "setup", "--config", str(self.config), "--decision-url", "http://x/v1",
            "--decision-model", "m", "--decision-key-env", "HYDRA_DECISION_KEY",
        )
        self.assertEqual(code, 0)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertIn('key_env = "HYDRA_DECISION_KEY"', self.config.read_text(encoding="utf-8"))

    def test_setup_refuses_a_key_passed_as_a_variable_name(self) -> None:
        code, out, err = run_audit(
            "setup", "--config", str(self.config), "--decision-url", "http://x/v1",
            "--decision-model", "m", "--decision-key-env", "sk-literal-key-value",
        )
        self.assertEqual(code, 2)
        self.assertFalse(self.config.exists())
        self.assertNotIn("sk-literal-key-value", out + err)

    def test_status_redacts_credentials_and_masks_the_key(self) -> None:
        self.write_config("http://user:pass@host/v1", key="abcdefghijklmnop")
        _, out, _ = run_audit("status", "--config", str(self.config))
        self.assertNotIn("pass", out.replace("passes", ""))
        self.assertIn("****mnop", out)
        self.assertIn("decision-model", out)


class GraphModeTests(AuditCase):
    def test_graph_mode_reads_v2_homes_and_the_graphs_own_skill_paths(self) -> None:
        project = self.make_graph_project()
        graph = hg.load_graph(FIXTURE)
        stance = graph["stance"][0]
        (project / stance["skill"]).write_text(
            "# Stance\n\nInspect the journal and the lock path before writing every file.\n",
            encoding="utf-8",
        )
        docs = project / "docs"
        (docs / "product.md").write_text(DOC, encoding="utf-8")
        code, data, _ = self.run_json(
            "--graph", str(project / ".agents" / "review-graph.toml"),
            "--source", str(docs), "--source", str(project / ".agents" / "skills"),
        )
        self.assertEqual(code, 0)
        self.assertEqual(data["mode"], "graph")
        sources = {atom["source"] for atom in data["atoms"]}
        self.assertEqual(sources, {"docs/product.md"})
        self.assertTrue(any(r["source"] == stance["skill"] for r in data["bleed"]))
        kinds = {top["kind"] for row in data["coverage"] for top in row["top"]}
        self.assertTrue(kinds <= {"stake", "surface", "stance", "unrepresented", "decision"})
        self.assertEqual(data["graph"]["stance_count"], len(graph["stance"]))
        self.assertEqual(data["graph"]["payer_total"], 12)

    def test_layer_bleed_keeps_every_sentence_of_a_stance(self) -> None:
        project = self.make_graph_project()
        graph = hg.load_graph(FIXTURE)
        stance = graph["stance"][0]
        (project / stance["skill"]).write_text(
            "# Stance\n\n"
            + "\n".join(f"Inspect boundary number {n} before every single write." for n in range(30))
            + "\n",
            encoding="utf-8",
        )
        code, data, _ = self.run_json(
            "--graph", str(project / ".agents" / "review-graph.toml"),
            "--source", str(project / "docs" / "missing.md"),
        )
        self.assertEqual(code, 0)
        rows = [r for r in data["bleed"] if r["source"] == stance["skill"]]
        self.assertEqual(len(rows), 30)

    def test_an_atom_nearest_an_unrepresented_row_is_a_known_gap(self) -> None:
        project = self.make_graph_project()
        graph = hg.load_graph(FIXTURE)
        row = graph["unrepresented"][0]
        doc = project / "docs" / "gap.md"
        doc.write_text(f"{row['stake']} {row['why']}.\n", encoding="utf-8")
        code, data, _ = self.run_json(
            "--graph", str(project / ".agents" / "review-graph.toml"), "--source", str(doc)
        )
        self.assertEqual(code, 0)
        self.assertEqual(data["coverage"][0]["top"][0]["home"], row["id"])
        self.assertTrue(data["coverage"][0]["known_gap"])
        self.assertFalse(data["coverage"][0]["orphan"])

    def test_candidates_are_spent_on_gaps_then_bleed_then_the_rest(self) -> None:
        project = self.make_graph_project()
        graph = hg.load_graph(FIXTURE)
        (project / graph["stance"][0]["skill"]).write_text(
            "# Stance\n\nInspect the journal and the lock path before writing every file.\n",
            encoding="utf-8",
        )
        doc = project / "docs" / "product.md"
        doc.write_text(DOC + "\nZebra quartz marmalade vortex unrelated.\n", encoding="utf-8")
        with endpoint(by_value) as (url, seen):
            self.write_config(url)
            code, data, _ = self.run_json(
                "--graph", str(project / ".agents" / "review-graph.toml"),
                "--source", str(doc), "--max-model-calls", "2",
            )
        self.assertEqual(code, 0)
        signals = [row["signal"] for row in data["triage"]]
        self.assertEqual(signals[0], "coverage-orphan")
        self.assertEqual(len(seen), 2)

    def test_v1_graph_is_rejected_with_the_upgrade_pointer(self) -> None:
        graph = self.root / "review-graph.toml"
        graph.write_text('version = 1\nproject = "old"\n', encoding="utf-8")
        code, _, err = run_audit(
            "run", "--config", str(self.config), "--graph", str(graph), "--source", str(self.doc)
        )
        self.assertEqual(code, 1)
        self.assertIn("upgrade-v1.md", err)

    def test_missing_explicit_graph_is_a_usage_error(self) -> None:
        code, _, err = run_audit(
            "run", "--config", str(self.config), "--graph", str(self.root / "nope.toml"),
            "--source", str(self.doc),
        )
        self.assertEqual(code, 2)
        self.assertIn("graph not found", err)


class ReferenceTests(unittest.TestCase):
    def test_every_script_a_skill_document_names_exists(self) -> None:
        # A path reference is structured metadata, not a judgment about prose.
        known = {path.name for path in (ROOT / "skills").glob("*/scripts/*.py")}
        missing = []
        for doc in sorted((ROOT / "skills").rglob("*.md")):
            for name in re.findall(r"scripts/([A-Za-z0-9_-]+\.py)", doc.read_text(encoding="utf-8")):
                if name not in known:
                    missing.append(f"{doc.relative_to(ROOT)} -> {name}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
