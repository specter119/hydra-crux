#!/usr/bin/env python3
"""Mechanical rule: a generated stance registry must survive a fresh clone.

hydra-crux-review tells the orchestrator to check every path the registry cites
with the version-control ignore query. That was guidance; this is the rule. It
is the defect that made a real pass's adjudication a dead link for every reader
except the machine that ran it.

The object is a **generated registry artifact**, not authored skill prose. The
registry is rendered from the graph; this rule only checks that the paths it
cites are tracked. It does not judge whether the registry's text is true.

What it checks, per registry:

- **Every path the registry cites is tracked.** A path that git ignores, or that
  is not in the index, is a dead pointer after a clone.
- **The discovery map is tracked.** The registry cites the map it was derived
  from; a map in an ignored directory cannot be cited.

Run with `--self-test` to check the rule against fixtures. prek runs it on
every commit through `scripts/lint-skills.sh`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REGISTRY_GLOB = "*-stance-registry/SKILL.md"
# prek exports these for the hook. `git -C root` must discover `root`, not the
# hook's repository, or the self-test checks the wrong tree.
GIT_ENV_VARS = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
}
# A repo-relative path written in backticks: at least one slash, no scheme, no
# placeholder angle brackets, no glob.
PATH_TOKEN = re.compile(r"`([A-Za-z0-9_.][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]*)`")


def repo_root(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key not in GIT_ENV_VARS}
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def is_tracked(root: Path, rel: str) -> bool:
    """Whether a repo-relative path is in the index and not ignored."""
    if git(root, "check-ignore", "-q", rel).returncode == 0:
        return False
    return git(root, "ls-files", "--error-unmatch", rel).returncode == 0


def check(registry: Path) -> list[str]:
    problems: list[str] = []
    root = repo_root(registry)
    if root is None:
        return problems
    text = registry.read_text(encoding="utf-8")
    if "stance-registry" not in text:
        return problems
    # A path that does not exist is a different defect from a path that is
    # ignored, and a branch or a skill name is not a path at all.
    for token in PATH_TOKEN.findall(text):
        if token.startswith(("http://", "https://")) or "<" in token:
            continue
        if not (root / token).exists():
            continue
        if not is_tracked(root, token):
            problems.append(
                f"{registry}: cites `{token}`, which a fresh clone will not "
                "contain. Move it to a tracked path or drop the citation."
            )
    return problems


def self_test() -> int:
    """The rule must fire on an ignored path and stay quiet on a tracked one."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        git(root, "init", "-q")
        (root / ".gitignore").write_text(".evidence/\n", encoding="utf-8")
        (root / "docs").mkdir()
        (root / "docs" / "decision.md").write_text("decided\n", encoding="utf-8")
        (root / ".evidence").mkdir()
        (root / ".evidence" / "adjudication.md").write_text("filed\n", encoding="utf-8")
        git(root, "add", ".gitignore", "docs/decision.md")
        registry = root / "registry.md"
        registry.write_text(
            "---\nname: demo-stance-registry\n---\n"
            "See `docs/decision.md` and `.evidence/adjudication.md`.\n",
            encoding="utf-8",
        )
        problems = check(registry)
    if len(problems) != 1 or ".evidence/adjudication.md" not in problems[0]:
        print(f"self-test: expected one finding about the ignored path, got {problems}")
        return 1
    print("self-test: ok")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    # prek passes the changed files. The rule is about the project whose
    # registry changed, so walk from each file's own repository root rather
    # than from this skill's location: a stance set installed into another
    # checkout must be checked against that checkout.
    roots = {
        root
        for arg in argv
        if (root := repo_root(Path(arg).resolve())) is not None
    }
    if not roots:
        roots = {Path(__file__).resolve().parents[4]}
    problems = [
        problem
        for root in sorted(roots)
        for registry in sorted(root.glob(f"**/{REGISTRY_GLOB}"))
        for problem in check(registry)
    ]
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
