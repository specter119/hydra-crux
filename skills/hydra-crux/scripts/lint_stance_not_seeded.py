#!/usr/bin/env python3
"""Mechanical rule: a stance must not be seeded with its author's open findings.

The rule that a stance file may not name a current symbol, or carry an unfixed
violation as an example, was guidance in stance-template.md. Guidance is read
once; this runs on every commit. It is the rule that turned the Luwu pass into
a confirmation of its author instead of a test of the design.

What it checks, per stance file:

- **Attacks name current symbols.** A backticked identifier that exists in the
  target project's source is a finding the author already made.
- **Bad patterns cite an open violation.** An entry whose evidence points at a
  path the project still ships is an example of the defect, not of the fix.

It cannot check whether an attack *describes* a live defect in prose. That is
the reviewer's job, and the `seen before` / `new` label is what makes it
visible. This rule only removes the cheapest way to seed a stance.

Run with `--self-test` to check the rule against fixtures. prek runs it on
every commit through `scripts/lint-skills.sh`.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

STANCE_GLOB = "*-stance/SKILL.md"
BACKTICK = re.compile(r"`([^`]+)`")
# A backticked token that looks like an identifier rather than a path, a
# command, or prose. Paths are checked separately and are not symbols.
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{2,}$")
# Sections whose content is an example of the defect rather than an attack on it.
BAD_PATTERN_HEADING = re.compile(r"^##\s+Bad patterns\s*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^##\s+", re.MULTILINE)


def frontmatter(text: str) -> str:
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    return match.group(1) if match else ""


def section(text: str, heading: re.Pattern[str]) -> str:
    match = heading.search(text)
    if match is None:
        return ""
    rest = text[match.end() :]
    end = NEXT_HEADING.search(rest)
    return rest[: end.start()] if end else rest


def repo_root(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def source_tokens(root: Path) -> set[str]:
    """Identifiers the target project's source contains, as a set of words."""
    tokens: set[str] = set()
    if not root.is_dir():
        return tokens
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".ts", ".js", ".go", ".rs"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        tokens.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text))
    return tokens


def check(stance: Path, source_root: Path | None) -> list[str]:
    problems: list[str] = []
    text = stance.read_text(encoding="utf-8")
    if "stance-axis" not in frontmatter(text):
        return problems

    if source_root is not None:
        known = source_tokens(source_root)
        attacks = section(text, re.compile(r"^##\s+Attacks\s*$", re.MULTILINE))
        for token in BACKTICK.findall(attacks):
            if IDENTIFIER.match(token) and token in known:
                problems.append(
                    f"{stance}: Attacks name the current symbol `{token}`. "
                    "Describe the shape, or move the finding to the pass record."
                )

    for entry in re.split(r"^- ", section(text, BAD_PATTERN_HEADING), flags=re.MULTILINE):
        if "fixed" in entry or "decided" in entry:
            continue
        for token in BACKTICK.findall(entry):
            if "/" in token and source_root is not None:
                if (source_root / token).exists():
                    problems.append(
                        f"{stance}: Bad patterns cite `{token}`, which still "
                        "exists. An open violation is a finding, not an example."
                    )
    return problems


def self_test() -> int:
    """The rule must fire on a seeded stance and stay quiet on a clean one."""
    seeded = """---
name: demo-seeded-stance
metadata:
  stance-axis: a-vs-b
---

# Demo

## Attacks

- A window decides whether evidence is re-read, see `_entry_window`.
- A default silently adopts an undeclared value.

## Bad patterns

- A prediction stands in for a read (`src/demo/engine.py`).
"""
    clean = seeded.replace("`_entry_window`", "the entry window").replace(
        "(`src/demo/engine.py`)", "(recorded in 1.2)"
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "src"
        root.mkdir()
        (root / "engine.py").write_text("_entry_window = 0.25\n", encoding="utf-8")
        (root / "demo").mkdir()
        (root / "demo" / "engine.py").write_text("x = 1\n", encoding="utf-8")
        seeded_file = Path(tmp) / "seeded.md"
        clean_file = Path(tmp) / "clean.md"
        seeded_file.write_text(seeded, encoding="utf-8")
        clean_file.write_text(clean, encoding="utf-8")
        fired = check(seeded_file, Path(tmp))
        quiet = check(clean_file, Path(tmp))
    if len(fired) != 2:
        print(f"self-test: expected 2 findings on the seeded stance, got {len(fired)}")
        return 1
    if quiet:
        print(f"self-test: expected none on the clean stance, got {quiet}")
        return 1
    print("self-test: ok")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    # prek passes the changed files. Each stance file is checked against the
    # source of the project it is installed into, which is not this skill's
    # repository: a stance set lives in its target project.
    stances = [Path(arg).resolve() for arg in argv if Path(arg).name == "SKILL.md"]
    if not stances:
        stances = sorted(
            Path(__file__).resolve().parents[4].glob(f"**/{STANCE_GLOB}")
        )
    problems: list[str] = []
    for stance in stances:
        root = repo_root(stance)
        source = root / "src" if root is not None else None
        source_root = source if source is not None and source.is_dir() else None
        problems.extend(check(stance, source_root))
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
