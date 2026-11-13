#!/usr/bin/env python3
"""Mechanical rule: a stance set's shape must be a set, not a hub.

The rules a stance set has to satisfy about its own topology were prose in
registry-template.md: every pair appears in both stances, no stance opposes more
than two others, the axis name agrees between the two files, and a stance that
names a sibling in "Accepts this harm" also lists it in `opposes`. A real forge
run broke all four at once, and nothing caught it.

Run with `--self-test` to check the rule against fixtures. prek runs it on
every commit through `scripts/lint-skills.sh`.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

STANCE_GLOB = "*-stance/SKILL.md"
REGISTRY_GLOB = "*-stance-registry/SKILL.md"
MAX_OPPONENTS = 2

FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---", re.DOTALL)
NAME = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
# A stance in several pairs carries one axis per pair, written as a list.
# A stance in several pairs carries one axis per pair, written comma-separated:
# `stance-axis: a-vs-b, b-vs-c`. Repeating the key would be invalid YAML.
AXIS = re.compile(r"^[ \t]+stance-axis:[ \t]*(\S.*?)[ \t]*$", re.MULTILINE)
OPPOSES_BLOCK = re.compile(r"^[ \t]+opposes:[ \t]*\n((?:[ \t]+-[ \t]+\S+[ \t]*(?:\n|$))+)", re.MULTILINE)
# The template writes `opposes` as a comma-separated inline list; a stance may
# also write it as a block sequence. Both forms are read here.
OPPOSES_INLINE = re.compile(r"^\s+opposes:[ \t]*(\S.*?)[ \t]*$", re.MULTILINE)
PAIR_ROW = re.compile(r"^\|\s*`([^`]+)`\s+vs\s+`([^`]+)`\s*\|", re.MULTILINE)
ACCEPTS_HEADING = re.compile(r"^##\s+Accepts this harm\s*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^##\s+", re.MULTILINE)
# The payer is a stance name only when it looks like one: a bare identifier with
# a "-stance" suffix. A document path or a skill name in that position is a
# harm with no stance behind it, which is a different defect and not this rule.
PAYER = re.compile(r"^-\s+\*\*`([A-Za-z0-9_-]+-stance)`", re.MULTILINE)


def section(text: str, heading: re.Pattern[str]) -> str:
    match = heading.search(text)
    if match is None:
        return ""
    rest = text[match.end() :]
    end = NEXT_HEADING.search(rest)
    return rest[: end.start()] if end else rest


def parse_stance(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.search(text)
    front = match.group(1) if match else ""
    name = NAME.search(front)
    axes = [
        part.strip()
        for line in AXIS.findall(front)
        for part in line.split(",")
        if part.strip()
    ]
    block = OPPOSES_BLOCK.search(front)
    inline = OPPOSES_INLINE.search(front)
    if block is not None:
        opposes = re.findall(r"-\s+(\S+)", block.group(1))
    elif inline is not None:
        opposes = [part.strip() for part in inline.group(1).split(",") if part.strip()]
    else:
        opposes = []
    return {
        "path": path,
        "name": name.group(1) if name else path.parent.name,
        "axes": axes,
        "axis": axes[0] if axes else None,
        "opposes": opposes,
        "payers": PAYER.findall(section(text, ACCEPTS_HEADING)),
    }


def parse_registry(registry: Path) -> list:
    text = registry.read_text(encoding="utf-8")
    return [(a, b) for a, b in PAIR_ROW.findall(text)]


def same_axis(first: str, second: str) -> bool:
    """Whether two axis names describe the same pair, in either direction."""

    if first == second:
        return True
    head, _, tail = first.partition("-vs-")
    if not tail:
        return False
    return second == f"{tail}-vs-{head}"


def shares_axis(first: dict, second: dict) -> bool:
    """Whether two stances name at least one axis in common, either direction."""

    for one in first["axes"]:
        for other in second["axes"]:
            if same_axis(str(one), str(other)):
                return True
    return False


def check(registry: Path, stances: list) -> list:
    problems = []
    by_name = {str(s["name"]): s for s in stances}
    pairs = parse_registry(registry)

    for stance in stances:
        opposes = [str(o) for o in stance["opposes"]]
        if len(opposes) > MAX_OPPONENTS:
            problems.append(
                f"{stance['path']}: opposes {len(opposes)} stances "
                f"({chr(44).join(opposes)}). A stance with more than "
                f"{MAX_OPPONENTS} opponents is a hub: the others become its "
                "projections and a pass needs only the hub and one opponent. "
                "Split it or move a pair."
            )
        for payer in stance["payers"]:
            if payer not in opposes:
                problems.append(
                    f"{stance['path']}: names `{payer}` as paying in "
                    "Accepts this harm, but does not list it in "
                    "metadata.opposes. Nobody is assigned to contest that harm."
                )
        for opponent in opposes:
            if opponent not in stance["payers"]:
                problems.append(
                    f"{stance['path']}: opposes `{opponent}` but never says "
                    "what it costs it in Accepts this harm. A pair with no "
                    "stated cost on this side reads as a manufactured conflict."
                )

    for a, b in pairs:
        for side, other in ((a, b), (b, a)):
            stance = by_name.get(side)
            if stance is None:
                problems.append(
                    f"{registry}: pair `{a}` vs `{b}` names `{side}`, "
                    "which is not a stance in this set."
                )
                continue
            if other not in [str(o) for o in stance["opposes"]]:
                problems.append(
                    f"{stance['path']}: the registry pairs it with `{other}`, "
                    "but its metadata.opposes does not list it."
                )
        first, second = by_name.get(a), by_name.get(b)
        if first is None or second is None:
            continue
        axis_a, axis_b = first["axis"], second["axis"]
        if axis_a is None or axis_b is None:
            problems.append(
                f"{registry}: pair `{a}` vs `{b}` has a stance without "
                "metadata.stance-axis."
            )
        elif not shares_axis(first, second):
            problems.append(
                f"{registry}: pair `{a}` vs `{b}` names the axis "
                f"`{axis_a}` in one file and `{axis_b}` in the other. "
                "Write one name, in the direction of the row's first stance."
            )

    paired = {name for pair in pairs for name in pair}
    for stance in stances:
        if str(stance["name"]) not in paired:
            problems.append(
                f"{stance['path']}: is in no registry opposition row. An "
                "unopposed stance is removed or given its opposition."
            )
    return problems

def self_test() -> int:
    """The rule must fire on a hub with a reversed axis, and pass a clean set."""
    hub = """---
name: a-hub-stance
metadata:
  stance-axis: a-vs-b
  opposes:
    - b-stance
    - c-stance
    - d-stance
---

## Accepts this harm

- **`b-stance` pays**: latency.
- **`e-stance` pays**: coverage.

## Attacks

- a shape
"""
    clean = """---
name: a-hub-stance
metadata:
  stance-axis: a-vs-b
  opposes:
    - b-stance
---

## Accepts this harm

- **`b-stance` pays**: latency.

## Attacks

- a shape
"""
    other = """---
name: b-stance
metadata:
  stance-axis: b-vs-a
  opposes:
    - a-hub-stance
---

## Accepts this harm

- **`a-hub-stance` pays**: throughput.

## Attacks

- a shape
"""
    registry = """# demo stance registry

## Oppositions

| Pair | Contended resource | Where these compete |
| --- | --- | --- |
| `a-hub-stance` vs `b-stance` | latency | write path |
"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        registry_path = root / "demo-stance-registry" / "SKILL.md"
        registry_path.parent.mkdir()
        registry_path.write_text(registry, encoding="utf-8")
        hub_path = root / "a-hub-stance" / "SKILL.md"
        hub_path.parent.mkdir()
        hub_path.write_text(hub, encoding="utf-8")
        other_path = root / "b-stance" / "SKILL.md"
        other_path.parent.mkdir()
        other_path.write_text(other, encoding="utf-8")
        broken = check(
            registry_path, [parse_stance(hub_path), parse_stance(other_path)]
        )
        # The reversed axis is the same pair named from the other side, so it is
        # legal; the fixed set only has to drop the hub and the unlisted payer.
        hub_path.write_text(clean, encoding="utf-8")
        fixed = check(
            registry_path, [parse_stance(hub_path), parse_stance(other_path)]
        )
    if len(broken) != 4:
        print(f"self-test: expected 4 findings on the broken set, got {len(broken)}")
        for problem in broken:
            print("  " + problem)
        return 1
    if fixed:
        print(f"self-test: expected none on the fixed set, got {fixed}")
        return 1
    print("self-test: ok")
    return 0


def main(argv: list) -> int:
    if "--self-test" in argv:
        return self_test()

    # prek passes the changed files. The set is the whole directory around
    # the registry, so walk from the repository of the file that changed.
    roots = set()
    for arg in argv:
        path = Path(arg).resolve()
        for parent in [path, *path.parents]:
            if (parent / ".git").exists():
                roots.add(parent)
                break
    if not roots:
        roots = {Path(__file__).resolve().parents[4]}

    problems = []
    for root in sorted(roots):
        for registry in sorted(root.glob(f"**/{REGISTRY_GLOB}")):
            # The worked example is checked too: an example that violates the
            # rule teaches the violation.
            skill_root = registry.parent.parent
            stances = [
                parse_stance(p) for p in sorted(skill_root.glob(STANCE_GLOB))
            ]
            if len(stances) < 2:
                continue
            problems.extend(check(registry, stances))
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
