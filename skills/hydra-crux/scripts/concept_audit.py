#!/usr/bin/env python3
"""Optional semantic audit for a hydra-crux build, migration, or evolution.

The audit has two layers. Only the first is required:

1. **deterministic**: parse source documents into atoms, rank them against the
   seven role labels, compare them with the graph's homes, and flag candidates.
   No network, no model, no third-party dependency.
2. **decision-model**: if an endpoint that answers typed questions about a
   state is configured (JEV is one implementation), it classifies one sentence
   at a time into the same seven labels. The answer is a probabilistic triage
   signal. It never becomes the verdict and never reaches route, lint, or a
   hook.

The script ships no LLM client. The semantic step is the agent reading the
report; the decision model is an independent second opinion, not a replacement
for that reading.

Configuration is opt-in. Without a ``[decision]`` section the audit still
runs, and the report says which layer was skipped and why.

This is not a lint. It reads authored prose, so it is not wired into any hook
and it must never fail a commit. Its product is a candidate list for a human.
"""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import math
import os
import re
import stat
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import hydra_graph

DEFAULT_CONFIG = Path("~/.config/hydra-crux/audit.toml").expanduser()
DEFAULT_MAX_CALLS = 40
DEFAULT_TIMEOUT = 60
MAX_CONSECUTIVE_TRANSPORT_FAILURES = 2
HUMAN_ONLY_BAND = (0.2, 0.6)
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

ROLE_OPTIONS = {
    "objective": "The value or interest the document protects, stated as a principle.",
    "scope": "What the document owns and what it explicitly does not own.",
    "check": "A concrete review question or good pattern to look for.",
    "anti_pattern": "A concrete bad pattern or failure to reject.",
    "evidence": "A pointer to a test, document, or command that proves a claim.",
    "history": "What was true in an earlier version or what a past delivery did.",
    "other": "None of the above.",
}

# These are cluster cores, not match keys. A sentence is ranked against the
# centroid of each label by TF-IDF cosine; the heading it sits under never
# decides its label, and the inverse document frequency comes from these
# sentences alone so one atom's ranking does not depend on the other inputs.
ROLE_PROTOTYPES = {
    "objective": [
        "A recoverable state survives every action.",
        "Who may change a value stays declared and answerable.",
        "A future actor can tell what happened and what to do next.",
        "Sensitive values stay out of repositories and logs.",
    ],
    "scope": [
        "This stance owns filesystem replacement and does not own authorization.",
        "Hand those findings to the authority stance instead.",
        "This surface owns meaning versus representation.",
    ],
    "check": [
        "Inspect the journal and the lock path before writing.",
        "Compare the old and new behavior, then test each boundary.",
        "Ask whether the reviewed action is the action that ran.",
        "Exercise the failure path and inspect the residue.",
        "Check whether a failure reveals less than a success.",
        "Compare the before and after state at each boundary.",
    ],
    "anti_pattern": [
        "Do not inline a near-copy.",
        "The surface must never decide the tradeoff.",
        "A convenient default must not adopt undeclared content.",
        "This rule wins over the opposing stance.",
        "Never let a default erase undeclared content.",
        "The guard must reject a silent overwrite.",
    ],
    "evidence": [
        "Evidence: tests/drift/test_ownership_classification.py.",
        "The command that reruns the test is the proof.",
        "Required evidence is a before-and-after count of walks.",
    ],
    "history": [
        "The migration happened in three steps.",
        "An earlier version wrote the manifest next to the profile.",
        "In the previous release this section described the old layout.",
    ],
    "other": [
        "The command writes a manifest next to the profile.",
        "This section describes the current layout.",
        "The operator pays an extra confirmation for each resource.",
        "This accepts slower applies in exchange for proof.",
    ],
}


@dataclass
class Endpoint:
    url: str
    model: str
    key: str = ""
    key_env: str = ""
    problem: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.url and self.model) and not self.problem

    @property
    def missing(self) -> list[str]:
        missing = [name for name in ("url", "model") if not getattr(self, name)]
        if self.problem:
            missing.append(self.problem)
        return missing


@dataclass
class Config:
    path: Path
    decision: Endpoint | None = None

    def layers(self) -> list[str]:
        layers = ["deterministic"]
        if self.decision and self.decision.configured:
            layers.append("decision-model")
        return layers


class ConfigError(Exception):
    """The config file exists but cannot be read as a config."""


@dataclass
class Atom:
    source: str
    section: str
    text: str
    line: int
    proto: str = "other"
    proto_score: float = 0.0

    @property
    def where(self) -> str:
        return f"{self.source}:{self.line}"


@dataclass
class Home:
    id: str
    kind: str
    title: str
    text: str
    skill: str = ""


# --------------------------------------------------------------------- config


def _endpoint_from_section(section: dict | None, env_prefix: str) -> Endpoint | None:
    if section is None:
        return None
    if not isinstance(section, dict):
        name = env_prefix.removeprefix("HYDRA_").lower()
        raise ConfigError(f"[{name}] must be a table, not {type(section).__name__}")
    url = str(section.get("url", "")).strip()
    model = str(section.get("model", "")).strip()
    key_env = str(section.get("key_env", "")).strip()
    key = str(section.get("key", "")).strip()
    problem = ""
    if key_env and not ENV_NAME.match(key_env):
        problem = "key_env is not a valid environment variable name"
        key_env = ""
    if not key and key_env:
        key = os.environ.get(key_env, "")
    if not key:
        key = os.environ.get(f"{env_prefix}_KEY", "")
    return Endpoint(url=url, model=model, key=key, key_env=key_env, problem=problem)


def load_config(path: Path) -> Config:
    if not path.exists():
        return Config(path=path)
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    return Config(
        path=path,
        decision=_endpoint_from_section(data.get("decision"), "HYDRA_DECISION"),
    )


def _override(endpoint: Endpoint | None, args: argparse.Namespace, prefix: str) -> Endpoint | None:
    env = f"HYDRA_{prefix.upper()}"
    url = (
        getattr(args, f"{prefix}_url", None)
        or os.environ.get(f"{env}_URL", "")
        or (endpoint.url if endpoint else "")
    )
    model = (
        getattr(args, f"{prefix}_model", None)
        or os.environ.get(f"{env}_MODEL", "")
        or (endpoint.model if endpoint else "")
    )
    key = (
        getattr(args, f"{prefix}_key", None)
        or os.environ.get(f"{env}_KEY", "")
        or (endpoint.key if endpoint else "")
    )
    if not any((url, model, key)) and endpoint is None:
        return None
    return Endpoint(
        url=url,
        model=model,
        key=key,
        key_env=endpoint.key_env if endpoint else "",
        problem=endpoint.problem if endpoint else "",
    )


def resolve_config(args: argparse.Namespace) -> Config:
    config = load_config(Path(args.config).expanduser())
    config.decision = _override(config.decision, args, "decision")
    return config


def mask(value: str) -> str:
    if not value:
        return "(none)"
    if len(value) < 12:
        return "****"
    return "****" + value[-4:]


def _authority(parts: urllib.parse.SplitResult) -> str:
    """The host and port without userinfo, keeping IPv6 brackets."""
    return parts.netloc.rpartition("@")[2]


def redact_url(url: str) -> str:
    """Drop credentials and query values before a URL reaches a report."""
    if not url:
        return url
    try:
        parts = urllib.parse.urlsplit(url)
        parts.port  # noqa: B018  # raises ValueError on a malformed port
    except ValueError:
        return "(invalid URL)"
    host = _authority(parts)
    query = "&".join(f"{key}=****" for key in urllib.parse.parse_qs(parts.query))
    return urllib.parse.urlunsplit((parts.scheme, host, parts.path, query, ""))


def redact_text(text: str, *secrets: str) -> str:
    """Strip credentials from text that is about to reach a report.

    Removes the given secret values, URL userinfo, and URL query values, which
    an exception message may echo.
    """
    for secret in secrets:
        if secret:
            text = text.replace(secret, "****")
    text = re.sub(r"//[^\s/@]+@", "//****@", text)
    return re.sub(r"([?&][^=\s&#]+)=[^\s&#]*", r"\1=****", text)


def split_credentials(url: str) -> tuple[str, str]:
    """Return the URL without userinfo, plus a Basic auth header when present."""
    try:
        parts = urllib.parse.urlsplit(url)
        parts.port  # noqa: B018  # raises ValueError on a malformed port
    except ValueError as exc:
        raise ValueError("invalid endpoint URL") from exc
    if parts.username is None:
        return url, ""
    userinfo = urllib.parse.unquote(parts.username) + ":" + urllib.parse.unquote(
        parts.password or ""
    )
    host = _authority(parts)
    clean = urllib.parse.urlunsplit((parts.scheme, host, parts.path, parts.query, ""))
    return clean, "Basic " + base64.b64encode(userinfo.encode()).decode()


def write_config(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for section in ("decision",):
        values = data.get(section)
        if not values:
            continue
        lines.append(f"[{section}]")
        for key in ("url", "model", "key_env", "key"):
            if values.get(key):
                lines.append(f"{key} = {json.dumps(values[key])}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


# ------------------------------------------------------------------ extraction


def sections(text: str):
    """Yield (heading, first_line, body) blocks, splitting on Markdown headings."""
    heading = ""
    start = 1
    buf: list[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            if buf:
                yield heading, start, "\n".join(buf)
            heading = match.group(2).strip()
            start = number + 1
            buf = []
        else:
            buf.append(line)
    if buf:
        yield heading, start, "\n".join(buf)


ABBREVIATION = re.compile(r"\b(?:e\.g|i\.e|vs|etc|cf|approx|no)\.$", re.IGNORECASE)


def split_sentences(text: str) -> list[str]:
    return [sentence for _, sentence in sentence_spans(text)]


def sentence_spans(text: str) -> list[tuple[int, str]]:
    """Split prose into sentences; each comes with its start index in the text."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    merged: list[str] = []
    for part in re.split(r"(?<=[.!?])\s+(?=[A-Z`*\"(])", text):
        if merged and ABBREVIATION.search(merged[-1]):
            merged[-1] += " " + part
        else:
            merged.append(part)
    spans = []
    cursor = 0
    for part in merged:
        start = text.index(part, cursor)
        cursor = start + len(part)
        if len(part.split()) >= 3:
            spans.append((start, part))
    return spans


LIST_MARKER = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.+)$")


def blocks(body: str):
    """Yield (offset, unit) for every list item and every prose sentence.

    A list item is one unit. Hard-wrapped prose is joined into a paragraph and
    split into sentences. Prose next to a list is kept, not replaced by it.
    """
    paragraph: list[tuple[int, str]] = []
    item: list[str] = []
    item_start = 0

    def flush_paragraph():
        nonlocal paragraph
        text = " ".join(line for _, line in paragraph)
        starts = []
        cursor = 0
        for number, line in paragraph:
            starts.append((cursor, number))
            cursor += len(line) + 1
        paragraph = []
        found = []
        for start, sentence in sentence_spans(text):
            line_number = max(n for c, n in starts if c <= start)
            found.append((line_number, sentence))
        return found

    def flush_item():
        nonlocal item
        found = [(item_start, " ".join(item))] if item else []
        item = []
        return found

    for number, raw in enumerate(body.splitlines()):
        marker = LIST_MARKER.match(raw)
        if not raw.strip():
            yield from flush_paragraph()
            yield from flush_item()
        elif marker:
            yield from flush_paragraph()
            yield from flush_item()
            item_start = number
            item = [marker.group(1).strip()]
        elif item and raw.startswith(("  ", "\t")):
            item.append(raw.strip())
        else:
            yield from flush_item()
            paragraph.append((number, re.sub(r"\s+", " ", raw.strip())))
    yield from flush_paragraph()
    yield from flush_item()


def strip_frontmatter(text: str) -> tuple[str, int]:
    match = re.match(r"\A---\s*\n.*?\n---\s*\n", text, flags=re.DOTALL)
    if not match:
        return text, 0
    return text[match.end() :], text.count("\n", 0, match.end())


def display_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()


def units(text: str, min_words: int = 3):
    """Yield (heading, line, unit) for every bullet or sentence in a document.

    Headings and list markers only segment the text. Nothing is dropped here
    because of what a unit looks like; the ranking decides how to read it.
    """
    body, line_offset = strip_frontmatter(text)
    for heading, start, section in sections(body):
        start += line_offset
        for offset, unit in blocks(section):
            if len(unit.split()) >= min_words:
                yield heading, start + offset, unit


def parse_document(path: Path, root: Path) -> list[Atom]:
    rel = display_path(path, root)
    found = list(units(path.read_text(encoding="utf-8")))
    ranked = assign_roles([unit for _, _, unit in found])
    return [
        Atom(rel, heading, unit, line, proto=rank["role"], proto_score=rank["score"])
        for (heading, line, unit), rank in zip(found, ranked)
    ]


def collect_source_atoms(
    sources: list[Path], root: Path, exclude: frozenset[Path] = frozenset()
) -> tuple[list[Atom], list[str], list[str]]:
    """Inventory every source path once.

    A file is one document. A directory contributes its top-level ``*.md``
    documents and its ``*/SKILL.md`` skill views. Returns the atoms in a fixed
    (source, line) order, the documents read, and the documents that yielded no
    atom at all.
    """
    atoms: list[Atom] = []
    read: list[str] = []
    empty: list[str] = []
    seen: set[Path] = set()
    for source in sources:
        if source.is_dir():
            paths = sorted(source.glob("*.md")) + sorted(source.glob("*/SKILL.md"))
        elif source.is_file():
            paths = [source]
        else:
            print(f"warning: source not found: {source}", file=sys.stderr)
            continue
        for path in paths:
            resolved = path.resolve()
            if resolved in seen or resolved in exclude or not path.is_file():
                continue
            seen.add(resolved)
            parsed = parse_document(path, root)
            read.append(display_path(path, root))
            if not parsed:
                empty.append(display_path(path, root))
            atoms.extend(parsed)
    atoms.sort(key=lambda atom: (atom.source, atom.line, atom.text))
    return atoms, sorted(read), sorted(empty)


def _read_skill(root: Path, skill: str) -> str:
    path = root / skill if skill else None
    if path is not None and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def load_homes(graph: dict, root: Path) -> list[Home]:
    homes: list[Home] = []
    for stake in graph.get("stake", []):
        homes.append(
            Home(str(stake.get("id", "")), "stake", str(stake.get("id", "")),
                 str(stake.get("objective", "")))
        )
    for surface in graph.get("surface", []):
        skill = str(surface.get("skill", ""))
        homes.append(
            Home(
                id=str(surface.get("id", "")),
                kind="surface",
                title=str(surface.get("title", surface.get("id", ""))),
                text=" ".join(
                    [
                        str(surface.get("title", "")),
                        " ".join(str(x) for x in surface.get("trigger", [])),
                        " ".join(str(x) for x in surface.get("keywords", [])),
                        _read_skill(root, skill)[:3000],
                    ]
                ),
                skill=skill,
            )
        )
    for stance in graph.get("stance", []):
        skill = str(stance.get("skill", ""))
        homes.append(
            Home(
                id=str(stance.get("id", "")),
                kind="stance",
                title=str(stance.get("title", stance.get("id", ""))),
                text=" ".join(
                    [
                        str(stance.get("title", "")),
                        str(stance.get("objective", "")),
                        _read_skill(root, skill)[:3000],
                    ]
                ),
                skill=skill,
            )
        )
    for row in graph.get("unrepresented", []):
        homes.append(
            Home(
                str(row.get("id", "")),
                "unrepresented",
                str(row.get("stake", "")),
                " ".join(str(row.get(k, "")) for k in ("stake", "where", "why")),
            )
        )
    for row in graph.get("decision", []):
        homes.append(
            Home(
                str(row.get("id", "")),
                "decision",
                str(row.get("summary", "")),
                " ".join(
                    str(row.get(k, "")) for k in ("summary", "given_up", "reopen_when")
                ),
            )
        )
    return [home for home in homes if home.id]


def excluded_paths(graph: dict, root: Path) -> frozenset[Path]:
    """The graph's own prose and the generated registry are not owner documents."""
    paths = {
        (root / str(row["skill"])).resolve()
        for table in ("surface", "stance")
        for row in graph.get(table, [])
        if row.get("skill")
    }
    skills_dir = str(graph.get("skills_dir") or ".agents/skills")
    registry = root / skills_dir / f"{graph.get('project', '')}-stance-registry" / "SKILL.md"
    paths.add(registry.resolve())
    return frozenset(paths)


# -------------------------------------------------------------------- ranking

STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with",
    "without", "from", "by", "as", "at", "is", "are", "be", "been", "being",
    "it", "its", "this", "that", "these", "those", "not", "no", "do", "does",
    "did", "can", "may", "must", "should", "would", "could", "will", "shall",
    "who", "what", "which", "when", "where", "why", "how", "than", "then",
    "there", "their", "they", "them", "we", "our", "you", "your", "i", "he",
    "she", "his", "her", "own", "owns", "owned", "only", "also", "but", "if",
    "into", "over", "under", "between", "each", "any", "all", "some", "more",
    "most", "less", "least", "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten",
}


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z-]{2,}", text.lower()) if w not in STOP]


def role_tokens(text: str) -> list[str]:
    """Content words plus a sentence-mood feature.

    The mood feature is an input to the ranking, not a decision. It exists
    because a bag of content words cannot tell ``do not write`` from
    ``inspect before writing`` when both share the same domain vocabulary.
    """
    words = tokens(text)
    lowered = text.strip().lower()
    if re.match(r"^(do not|don't|never|must not|must never)\b", lowered):
        words.append("mood:prohibitive")
    elif re.match(
        r"^(inspect|check|compare|ask|collect|exercise|read|verify|confirm|test|run|"
        r"identify|classify|record|review|trace|count|measure)\b",
        lowered,
    ):
        words.append("mood:imperative-check")
    return words


def _weigh(doc: list[str], df: Counter, total: int) -> dict[str, float]:
    counts = Counter(doc)
    vec = {
        w: (1 + math.log(c)) * math.log((1 + total) / (1 + df.get(w, 0)))
        for w, c in counts.items()
    }
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {w: v / norm for w, v in vec.items()}


def tfidf(docs: list[list[str]]) -> list[dict[str, float]]:
    df: Counter = Counter()
    for doc in docs:
        df.update(set(doc))
    return [_weigh(doc, df, len(docs)) for doc in docs]


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(v * b.get(k, 0.0) for k, v in a.items())


@lru_cache(maxsize=1)
def _prototype_model() -> tuple[Counter, int, dict[str, dict[str, float]]]:
    flat = [(role, example) for role, examples in ROLE_PROTOTYPES.items() for example in examples]
    docs = [role_tokens(example) for _, example in flat]
    df: Counter = Counter()
    for doc in docs:
        df.update(set(doc))
    total = len(docs)
    centroids: dict[str, dict[str, float]] = {}
    for role, examples in ROLE_PROTOTYPES.items():
        acc: dict[str, float] = defaultdict(float)
        for (name, _), doc in zip(flat, docs):
            if name != role:
                continue
            for key, value in _weigh(doc, df, total).items():
                acc[key] += value / len(examples)
        norm = math.sqrt(sum(value * value for value in acc.values())) or 1.0
        centroids[role] = {key: value / norm for key, value in acc.items()}
    return df, total, centroids


def assign_roles(texts: list[str]) -> list[dict]:
    """Rank each text against the role prototypes by TF-IDF cosine.

    The result is the nearest prototype, unverified. The weights come from the
    prototype sentences only, so a text ranks the same whichever other texts
    are in the run. Headings are never consulted.
    """
    df, total, centroids = _prototype_model()
    results = []
    for text in texts:
        vector = _weigh(role_tokens(text), df, total)
        scored = sorted(
            ((cosine(vector, centroid), role) for role, centroid in centroids.items()),
            reverse=True,
        )
        best_score, best_role = scored[0]
        results.append(
            {
                "role": best_role,
                "score": round(best_score, 3),
                "margin": round(best_score - scored[1][0], 3),
                "scores": {role: round(score, 3) for score, role in scored},
            }
        )
    return results


def coverage(atoms: list[Atom], homes: list[Home], threshold: float) -> list[dict]:
    """Best lexical homes for each atom. The weights follow the corpus."""
    if not atoms or not homes:
        return []
    vectors = tfidf([tokens(a.text) for a in atoms] + [tokens(h.text) for h in homes])
    atom_vectors = vectors[: len(atoms)]
    home_vectors = vectors[len(atoms) :]
    rows = []
    for atom, vector in zip(atoms, atom_vectors):
        scored = sorted(
            (
                (home.id, home.kind, round(cosine(vector, hv), 3))
                for home, hv in zip(homes, home_vectors)
            ),
            key=lambda item: item[2],
            reverse=True,
        )
        top = [{"home": home, "kind": kind, "score": score} for home, kind, score in scored[:3]]
        _, best_kind, best_score = scored[0]
        rows.append(
            {
                "atom": atom,
                "top": top,
                "known_gap": best_kind == "unrepresented" and best_score >= threshold,
                "orphan": best_score < threshold,
            }
        )
    return rows


def bleed_candidates(homes: list[Home], root: Path) -> list[dict]:
    """Rank sentences that may sit in the wrong layer.

    A surface sentence ranks by its affinity to ``objective`` (the surface may be
    defending a value); a stance sentence ranks by its affinity to ``check``. The
    result is a reading order. The heading is never consulted.
    """
    items = []
    for home in homes:
        if home.kind not in ("surface", "stance") or not home.skill:
            continue
        text = _read_skill(root, home.skill)
        if not text:
            continue
        for heading, line, sentence in units(text, min_words=5):
            items.append(
                {
                    "home": home.id,
                    "kind": home.kind,
                    "source": home.skill,
                    "section": heading,
                    "line": line,
                    "text": sentence,
                }
            )
    rows = []
    for item, role in zip(items, assign_roles([item["text"] for item in items])):
        target = "objective" if item["kind"] == "surface" else "check"
        rows.append({**item, **role, "affinity": role["scores"][target]})

    ranked: list[dict] = []
    for kind, signal in (
        ("surface", "value-affinity-in-surface"),
        ("stance", "check-affinity-in-stance"),
    ):
        subset = sorted(
            (row for row in rows if row["kind"] == kind),
            key=lambda r: (-float(r["affinity"]), str(r["source"]), int(r["line"])),
        )
        ranked.extend({**row, "signal": signal} for row in subset)
    return ranked


# --------------------------------------------------------------- graph findings


def graph_findings(graph: dict) -> dict:
    stances = graph.get("stance", [])
    oppositions = graph.get("opposition", [])
    opponents: dict[str, set[str]] = defaultdict(set)
    for opposition in oppositions:
        members = [str(x) for x in opposition.get("stances", [])]
        for member in members:
            opponents[member].update(other for other in members if other != member)

    payer_rows = []
    for stance in stances:
        sid = str(stance.get("id", ""))
        for harm in stance.get("accepted_harm", []):
            payer_stance = str(harm.get("payer_stance") or "")
            payer_rows.append(
                {
                    "stance": sid,
                    "payer": str(harm.get("payer", "")),
                    "payer_stance": payer_stance,
                    "payer_is_opponent": bool(payer_stance) and payer_stance in opponents[sid],
                }
            )

    readers: dict[str, set[str]] = defaultdict(set)
    stance_surfaces: dict[str, list[str]] = {}
    stanced_stakes: set[str] = set()
    for stance in stances:
        sid = str(stance.get("id", ""))
        surfaces = [str(x) for x in stance.get("surfaces", [])]
        stance_surfaces[sid] = surfaces
        stanced_stakes.update(str(x) for x in stance.get("stakes", []))
        for surface in surfaces:
            readers[surface].add(sid)
    one_to_one = sorted(
        surface
        for surface, sids in readers.items()
        if len(sids) == 1 and len(stance_surfaces[next(iter(sids))]) == 1
    )
    unpaired = [
        str(surface.get("id", ""))
        for surface in graph.get("surface", [])
        if str(surface.get("id", "")) not in readers and not surface.get("unopposed_stake")
    ]
    unopposed_surfaces = [
        {"id": str(surface.get("id", "")), "stake": str(surface.get("unopposed_stake", ""))}
        for surface in graph.get("surface", [])
        if surface.get("unopposed_stake")
    ]
    return {
        "stance_count": len(stances),
        "axis_count": len(oppositions),
        "axis_sizes": dict(Counter(len(o.get("stances", [])) for o in oppositions)),
        "surface_count": len(graph.get("surface", [])),
        "one_to_one_surfaces": one_to_one,
        "payer_rows": payer_rows,
        "payer_symmetry": sum(1 for row in payer_rows if row["payer_is_opponent"]),
        "payer_total": len(payer_rows),
        "unpaired_surfaces": unpaired,
        "unopposed_surfaces": unopposed_surfaces,
        "unopposed_stakes": sum(
            1 for stake in graph.get("stake", []) if str(stake.get("id", "")) not in stanced_stakes
        ),
    }


# ------------------------------------------------------------------- model I/O


def post_json(url: str, payload: dict, key: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    url, basic = split_credentials(url)
    if basic:
        headers["Authorization"] = basic
    if key:
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


class DecisionModel:
    """Decision-model endpoint: a state plus one typed question."""

    def __init__(self, endpoint: Endpoint, timeout: int = DEFAULT_TIMEOUT):
        self.endpoint = endpoint
        self.timeout = timeout

    def choice(self, text: str, instructions: str, options: dict[str, str]) -> dict:
        result = post_json(
            self.endpoint.url,
            {
                "model": self.endpoint.model,
                "state": {"text": text},
                "questions": {
                    "q": {
                        "type": "choice",
                        "instructions": instructions,
                        "criteria": options,
                    }
                },
            },
            self.endpoint.key,
            self.timeout,
        )
        if not isinstance(result, dict):
            raise TypeError("decision-model response is not a JSON object")
        self.version = str(result.get("model", ""))
        return result["answers"]["q"]


def _confidence(value: object) -> float:
    """A model answer is usable only if its confidence is a finite 0..1 number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("confidence is not a number")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError("confidence is outside 0..1")
    return number


TRANSPORT_ERRORS = (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException)
ANSWER_ERRORS = (ValueError, KeyError, TypeError, IndexError)


def classify_role(model: DecisionModel, text: str) -> dict:
    answer = model.choice(
        text, "Which role does this statement play in a review skill?", ROLE_OPTIONS
    )
    if not isinstance(answer, dict):
        raise TypeError("decision-model answer is not an object")
    role = str(answer.get("choice", "")).strip()
    if role not in ROLE_OPTIONS:
        raise ValueError("decision model returned a role outside the seven labels")
    return {
        "role": role,
        "confidence": _confidence(answer.get("confidence")),
        "origin": "decision-model",
    }


def triage(
    candidates: list[dict], config: Config, max_calls: int, timeout: int
) -> tuple[list[dict], list[dict], str]:
    """Classify candidates in the order given, bounded by max_calls.

    Returns the classified rows, the untriaged candidates, and why triage
    stopped early (empty when it did not). Never raises on a model error, and
    stops after consecutive transport failures so a hung endpoint cannot stall
    the audit.
    """
    endpoint = config.decision
    if endpoint is None or not endpoint.configured or max_calls <= 0:
        return [], list(candidates), ""
    model = DecisionModel(endpoint, timeout)
    results: list[dict] = []
    stopped = ""
    transport_failures = 0
    for index, row in enumerate(candidates[:max_calls]):
        try:
            answer = classify_role(model, row["text"])
            transport_failures = 0
        except TRANSPORT_ERRORS as exc:
            transport_failures += 1
            answer = {
                "role": "error",
                "confidence": 0.0,
                "origin": "error",
                "error": redact_text(str(exc), endpoint.key),
            }
        except ANSWER_ERRORS as exc:
            transport_failures = 0
            answer = {
                "role": "error",
                "confidence": 0.0,
                "origin": "error",
                "error": redact_text(str(exc), endpoint.key),
            }
        results.append({**row, **answer, "model_version": getattr(model, "version", "")})
        if transport_failures >= MAX_CONSECUTIVE_TRANSPORT_FAILURES:
            stopped = (
                f"stopped after {transport_failures} consecutive transport failures; "
                "the rest is untriaged"
            )
            return results, list(candidates[index + 1 :]), stopped
    return results, list(candidates[max_calls:]), stopped


def skip_reason(config: Config, config_error: str, candidate_count: int, max_calls: int) -> str:
    """Why the triage section is empty. Each cause is a different fix."""
    if config_error:
        return "the config file is invalid; the deterministic findings stand alone"
    if not candidate_count:
        return "no candidate rows to triage"
    if max_calls <= 0:
        return "`--max-model-calls` is 0"
    endpoint = config.decision
    if endpoint is None:
        return (
            "no decision model configured. Read the candidates above yourself: "
            "the deterministic findings stand alone"
        )
    if not endpoint.configured:
        missing = ", ".join(endpoint.missing)
        return f"the [decision] section is incomplete ({missing}); nothing was called"
    return "no row was triaged"


def build_candidates(
    atoms: list[Atom], coverage_rows: list[dict], bleed_rows: list[dict]
) -> list[dict]:
    """Order the model's budget: coverage gaps, then layer bleed, then the rest."""
    candidates: list[dict] = []
    seen: set[tuple[str, int, str]] = set()

    def add(source: str, line: int, text: str, signal: str, section: str = "") -> None:
        key = (source, line, text)
        if key in seen:
            return
        seen.add(key)
        candidates.append(
            {"source": source, "line": line, "text": text, "signal": signal, "section": section}
        )

    for row in coverage_rows:
        if row["orphan"]:
            atom = row["atom"]
            add(atom.source, atom.line, atom.text, "coverage-orphan", atom.section)
    for row in bleed_rows:
        add(row["source"], row["line"], row["text"], row["signal"], row["section"])
    for atom in atoms:
        add(atom.source, atom.line, atom.text, "inventory", atom.section)
    return candidates


# ---------------------------------------------------------------------- report


def _cell(text: str, width: int = 160) -> str:
    return text.replace("|", "\\|").replace("\n", " ")[:width]


def render_report(
    project: str,
    mode: str,
    config: Config,
    inventory: dict,
    homes: list[Home],
    coverage_rows: list[dict],
    bleed_rows: list[dict],
    findings: dict | None,
    candidates: list[dict],
    triage_rows: list[dict],
    untriaged: list[dict],
    stopped: str,
    threshold: float,
    max_calls: int,
    config_error: str = "",
) -> str:
    atoms: list[Atom] = inventory["atoms"]
    lines = [f"# Concept audit: {project}", ""]
    lines.extend(
        [
            "This report is a candidate list for a human. Deterministic labels are the nearest",
            "prototype, unverified. Model labels are triage signals, not decisions. Nothing here",
            "selects a route, gates a commit, or decides a review.",
            "",
            f"Mode: {mode}.",
            "",
            "## Configuration",
            "",
            "| layer | status | endpoint |",
            "| --- | --- | --- |",
        ]
    )
    endpoint = config.decision

    def describe() -> str:
        if config_error:
            return "skipped (invalid config)"
        if endpoint is None:
            return "skipped (no [decision])"
        if not endpoint.configured:
            return f"skipped (incomplete [decision]: {', '.join(endpoint.missing)})"
        if triage_rows:
            failed = sum(1 for row in triage_rows if row.get("origin") == "error")
            suffix = f", {failed} failed" if failed else ""
            return f"active ({len(triage_rows)} calls{suffix})"
        if not candidates:
            return "configured, not called (no candidates)"
        if max_calls <= 0:
            return "configured, not called (--max-model-calls 0)"
        return "configured, not called"

    shown = f"{endpoint.model} @ {redact_url(endpoint.url)}" if endpoint else "-"
    lines.append("| deterministic | active | - |")
    lines.append(f"| decision-model | {describe()} | {shown} |")
    lines.extend(["", f"Config: `{config.path}`", ""])
    if config_error:
        lines.extend([f"Config error: {config_error}", ""])
    if triage_rows:
        versions = sorted({row["model_version"] for row in triage_rows if row.get("model_version")})
        lines.extend(
            [
                f"Sent {len(triage_rows)} sentences from the source documents to "
                f"{redact_url(endpoint.url) if endpoint else '-'}"
                + (f" (model version {', '.join(versions)})" if versions else "")
                + ". Use `--max-model-calls 0` to keep a run local.",
                "",
            ]
        )

    proto = Counter(atom.proto for atom in atoms)
    lines.extend(
        [
            "## Inventory",
            "",
            (
                f"{len(atoms)} atoms from {len(inventory['read'])} source documents; "
                f"{len(homes)} graph homes."
                if homes
                else f"{len(atoms)} atoms from {len(inventory['read'])} source documents; no graph."
            ),
            "",
            "| nearest prototype (unverified) | count |",
            "| --- | ---: |",
        ]
    )
    for role, count in proto.most_common():
        lines.append(f"| {role} | {count} |")
    if inventory["empty"]:
        lines.extend(
            [
                "",
                "No atom was extracted from: " + ", ".join(inventory["empty"]) + ". "
                "The splitter and the ranking read English prose; a document in another "
                "language or made of short fragments yields an empty inventory, which is "
                "not evidence that it holds no stake.",
            ]
        )
    if not atoms:
        lines.extend(["", "The inventory is empty."])

    needed = len(candidates)
    lines.extend(
        [
            "",
            "## Model budget",
            "",
            (
                f"{needed} candidate sentences; {len(triage_rows)} classified; "
                f"{len(untriaged)} untriaged. A run that classifies every one needs "
                f"`--max-model-calls {needed}` (limit now {max_calls})."
            ),
        ]
    )
    if stopped:
        lines.extend(["", f"Triage {stopped}."])

    lines.extend(["", "## Objective candidates", ""])
    objectives = [row for row in triage_rows if row.get("role") == "objective"]
    if triage_rows:
        lines.append(
            "Sentences the decision model labelled `objective`, in source order. Each is "
            "raw material for a stake or a stance Objective. Record a disposition for every "
            "one: cite it as stake evidence, merge it into an existing stake, or reject it "
            "with a reason in the delivery report. The confidence band "
            f"{HUMAN_ONLY_BAND[0]}-{HUMAN_ONLY_BAND[1]} is for a human only."
        )
        lines.append("")
        if objectives:
            lines.extend(["| where | confidence | band | sentence |", "| --- | ---: | --- | --- |"])
            for row in sorted(objectives, key=lambda r: (r["source"], r["line"])):
                human = HUMAN_ONLY_BAND[0] <= row["confidence"] <= HUMAN_ONLY_BAND[1]
                lines.append(
                    f"| {row['source']}:{row['line']} | {row['confidence']:.2f} | "
                    f"{'human only' if human else '-'} | {_cell(row['text'])} |"
                )
        else:
            lines.append("None among the classified sentences.")
        if untriaged:
            lines.extend(["", f"{len(untriaged)} sentences were not classified; read them yourself."])
    else:
        lines.append(
            "No decision model ran, so these are the atoms whose nearest prototype is "
            "`objective` (unverified reading order). Read every atom, not only these."
        )
        lines.append("")
        nearest = [atom for atom in atoms if atom.proto == "objective"]
        if nearest:
            lines.extend(["| where | score | sentence |", "| --- | ---: | --- |"])
            for atom in nearest:
                lines.append(f"| {atom.where} | {atom.proto_score:.3f} | {_cell(atom.text)} |")
        else:
            lines.append("None.")

    if mode == "graph":
        orphans = [row for row in coverage_rows if row["orphan"]]
        gaps = [row for row in coverage_rows if row["known_gap"]]
        scores = sorted(row["top"][0]["score"] for row in coverage_rows if row["top"])
        median = scores[len(scores) // 2] if scores else 0.0
        lines.extend(
            [
                "",
                "## Coverage candidates",
                "",
                (
                    f"Lexical threshold {threshold}. {len(orphans)} of {len(coverage_rows)} atoms "
                    f"have no home above it; {len(gaps)} land nearest an `unrepresented` row, "
                    f"a known gap rather than a miss. Best-home scores: min "
                    f"{scores[0] if scores else 0:.3f}, median {median:.3f}, "
                    f"max {scores[-1] if scores else 0:.3f}. The weights follow the corpus, so "
                    "the scores shift when the source set changes."
                ),
                "",
            ]
        )
        if orphans:
            lines.extend(
                ["| where | nearest prototype | atom | best home | score |",
                 "| --- | --- | --- | --- | ---: |"]
            )
            for row in orphans[:30]:
                atom = row["atom"]
                best = row["top"][0]
                lines.append(
                    f"| {atom.where} | {atom.proto} | {_cell(atom.text, 140)} | "
                    f"{best['home']} | {best['score']} |"
                )
            if len(orphans) > 30:
                lines.append(f"| ... | | {len(orphans) - 30} more | | |")
        else:
            lines.append("None.")

        distribution: dict[str, Counter] = defaultdict(Counter)
        for row in coverage_rows:
            if row["top"]:
                distribution[row["atom"].source][row["top"][0]["home"]] += 1
        if distribution:
            lines.extend(
                [
                    "",
                    "### Home distribution",
                    "",
                    (
                        "Top-1 home for each source document. A document that spreads "
                        "across several homes is evidence for a many-to-many cut, not a "
                        "1:1 rename."
                    ),
                    "",
                    "| source | top-1 homes |",
                    "| --- | --- |",
                ]
            )
            for source, counts in sorted(distribution.items()):
                cells = ", ".join(f"{home} ({count})" for home, count in counts.most_common(4))
                lines.append(f"| {source} | {cells} |")

        lines.extend(
            [
                "",
                "## Layer bleed candidates",
                "",
                (
                    f"{len(bleed_rows)} sentences ranked as a reading order, not a decision. "
                    "A surface sentence ranks by affinity to `objective` (it may be defending "
                    "a value); a stance sentence ranks by affinity to `check` (it may hide a "
                    "checklist). The seven-label model can rule a sentence out by calling it "
                    "a check, a scope, or evidence. It cannot confirm that a sentence is a "
                    "verdict."
                ),
                "",
            ]
        )
        if bleed_rows:
            lines.extend(
                [
                    "| home | signal | nearest prototype | affinity | line | sentence |",
                    "| --- | --- | --- | ---: | ---: | --- |",
                ]
            )
            for row in bleed_rows[:40]:
                lines.append(
                    f"| {row['home']} | {row['signal']} | {row['role']} | "
                    f"{row['affinity']:.3f} | {row['line']} | {_cell(row['text'])} |"
                )
            if len(bleed_rows) > 40:
                lines.append(f"| ... | | | | | {len(bleed_rows) - 40} more |")
        else:
            lines.append("None.")

        if findings is not None:
            lines.extend(["", "## Graph findings", ""])
            lines.append(
                f"- {findings['stance_count']} stances on {findings['axis_count']} axes; "
                f"axis sizes {findings['axis_sizes']}."
            )
            lines.append(
                f"- {findings['payer_symmetry']}/{findings['payer_total']} accepted harms name "
                "exactly the opposing stance as payer. A high ratio is a quota signature, not "
                "an error: check whether the harmed side has an independent interest."
            )
            lines.append(
                f"- {len(findings['one_to_one_surfaces'])}/{findings['surface_count']} surfaces "
                "pair one-to-one with a stance. A perfect matching is the same signature in "
                "the surface layer: check that each surface's checks predate the stance."
            )
            if findings["unpaired_surfaces"]:
                lines.append(
                    "- surfaces with no stance and no unopposed stake: "
                    + ", ".join(findings["unpaired_surfaces"])
                )
            else:
                lines.append("- every surface has a stance or an unopposed stake.")
            if findings["unopposed_surfaces"]:
                lines.append(
                    "- surfaces backed only by an unopposed stake: "
                    + ", ".join(f"{r['id']} ({r['stake']})" for r in findings["unopposed_surfaces"])
                    + ". An unopposed stake is a check, not a payer."
                )
            lines.append(f"- {findings['unopposed_stakes']} stakes no stance references.")

    lines.extend(["", "## Model triage", ""])
    if not triage_rows:
        lines.append(f"Skipped: {skip_reason(config, config_error, len(candidates), max_calls)}.")
    else:
        lines.extend(
            [
                "| where | signal | role | confidence | origin | error |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for row in triage_rows:
            lines.append(
                f"| {row['source']}:{row['line']} | {row.get('signal', '-')} | "
                f"{row.get('role', '-')} | {row.get('confidence', 0):.2f} | "
                f"{row.get('origin', '-')} | "
                f"{_cell(row.get('error', ''), 120)} |"
            )

    if untriaged:
        lines.extend(
            [
                "",
                "## Untriaged sentences",
                "",
                "No model label exists for these. Read each one yourself.",
                "",
                "| where | signal | sentence |",
                "| --- | --- | --- |",
            ]
        )
        for row in untriaged:
            lines.append(
                f"| {row['source']}:{row['line']} | {row.get('signal', '-')} | "
                f"{_cell(row['text'])} |"
            )

    lines.extend(
        [
            "",
            "## Needs human",
            "",
            "1. Every objective candidate: record a disposition.",
            (
                "2. Every classified row whose confidence is "
                f"{HUMAN_ONLY_BAND[0]}-{HUMAN_ONLY_BAND[1]}, and every error row."
            ),
            "3. Every untriaged sentence, and every document that yielded no atom.",
        ]
    )
    if mode == "graph":
        lines.append(
            "4. Every stance whose accepted harm names only its opponent as payer, and every "
            "surface that pairs one-to-one with a stance."
        )
    lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------------- CLI


def cmd_setup(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser()
    existing = {}
    if path.exists():
        try:
            with path.open("rb") as handle:
                existing = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            print(f"refusing to rewrite {path}: {exc}", file=sys.stderr)
            return 1
    data = {key: dict(value) for key, value in existing.items() if isinstance(value, dict)}
    url = args.decision_url
    model = args.decision_model
    key = args.decision_key
    key_env = args.decision_key_env
    if key_env and not ENV_NAME.match(key_env):
        print(
            "--decision-key-env takes the NAME of an environment variable, not a key; "
            "use --decision-key for a literal key. Nothing was written.",
            file=sys.stderr,
        )
        return 2
    if any((url, model, key, key_env)):
        values = data.setdefault("decision", {})
        if url:
            values["url"] = url
        if model:
            values["model"] = model
        if key:
            values["key"] = key
            values.pop("key_env", None)
            print(
                f"warning: storing a literal decision key in {path} (mode 0600); "
                "prefer --decision-key-env",
                file=sys.stderr,
            )
        if key_env:
            values["key_env"] = key_env
            values.pop("key", None)
    write_config(path, data)
    print(f"wrote {path} (mode 0600)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    try:
        config = resolve_config(args)
    except ConfigError as exc:
        print(f"config: {args.config} (invalid)")
        print(f"  {exc}")
        print("layers: deterministic")
        return 1
    print(f"config: {config.path} ({'present' if config.path.exists() else 'missing'})")
    endpoint = config.decision
    if endpoint and endpoint.configured:
        print(
            f"decision: {endpoint.model} @ {redact_url(endpoint.url)} key={mask(endpoint.key)}"
        )
        if endpoint.key_env and not os.environ.get(endpoint.key_env):
            print(f"  note: key_env {endpoint.key_env} is not set in this environment")
    elif endpoint:
        print(f"decision: incomplete [decision] ({', '.join(endpoint.missing)})")
    else:
        print("decision: not configured")
    print("layers: " + ", ".join(config.layers()))
    return 0


def _load_run_graph(args: argparse.Namespace) -> tuple[Path | None, dict | None, int]:
    graph_path = args.graph or hydra_graph._default_graph()
    if graph_path is None:
        return None, None, 0
    if not graph_path.exists():
        print(f"graph not found: {graph_path}", file=sys.stderr)
        return None, None, 2
    graph_path = graph_path.resolve()
    try:
        graph = hydra_graph.load_graph(graph_path)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"invalid graph: {exc}", file=sys.stderr)
        return None, None, 1
    errors = hydra_graph.validate_graph(graph)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return None, None, 1
    return graph_path, graph, 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.max_model_calls < 0:
        print("--max-model-calls must be >= 0", file=sys.stderr)
        return 2
    if args.model_timeout <= 0:
        print("--model-timeout must be > 0", file=sys.stderr)
        return 2
    config_error = ""
    try:
        config = resolve_config(args)
    except ConfigError as exc:
        config = Config(path=Path(args.config).expanduser())
        config_error = str(exc)

    graph_path, graph, status = _load_run_graph(args)
    if status:
        return status
    if args.project_root:
        root = args.project_root.resolve()
    elif graph_path:
        root = graph_path.parent.parent
    else:
        root = Path.cwd()

    exclude = excluded_paths(graph, root) if graph is not None else frozenset()
    atoms, read, empty = collect_source_atoms(
        [Path(p).resolve() for p in args.source], root, exclude
    )
    inventory = {"atoms": atoms, "read": read, "empty": empty}

    mode = "graph" if graph is not None else "inventory-only"
    homes: list[Home] = []
    coverage_rows: list[dict] = []
    bleed_rows: list[dict] = []
    findings = None
    if graph is not None:
        homes = load_homes(graph, root)
        coverage_rows = coverage(atoms, homes, args.threshold)
        bleed_rows = bleed_candidates(homes, root)
        findings = graph_findings(graph)

    candidates = build_candidates(atoms, coverage_rows, bleed_rows)
    triage_rows, untriaged, stopped = triage(
        candidates, config, args.max_model_calls, args.model_timeout
    )
    project = str(graph.get("project", root.name)) if graph is not None else root.name
    report = render_report(
        project,
        mode,
        config,
        inventory,
        homes,
        coverage_rows,
        bleed_rows,
        findings,
        candidates,
        triage_rows,
        untriaged,
        stopped,
        args.threshold,
        args.max_model_calls,
        config_error,
    )
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(report)
    if args.json:
        payload = {
            "project": project,
            "mode": mode,
            "layers": config.layers(),
            "config_error": config_error,
            "atoms": [atom.__dict__ for atom in atoms],
            "empty_sources": empty,
            "coverage": [
                {
                    "source": row["atom"].source,
                    "line": row["atom"].line,
                    "proto": row["atom"].proto,
                    "text": row["atom"].text,
                    "top": row["top"],
                    "orphan": row["orphan"],
                    "known_gap": row["known_gap"],
                }
                for row in coverage_rows
            ],
            "bleed": bleed_rows,
            "graph": findings,
            "triage": triage_rows,
            "untriaged": untriaged,
            "stopped": stopped,
        }
        Path(args.json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"wrote {args.json}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="audit config path")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="write an opt-in endpoint config")
    setup.add_argument("--config", default=argparse.SUPPRESS, help="audit config path")
    setup.add_argument("--decision-url")
    setup.add_argument("--decision-model")
    setup.add_argument("--decision-key")
    setup.add_argument("--decision-key-env", help="NAME of the environment variable")
    setup.set_defaults(func=cmd_setup)

    status = sub.add_parser("status", help="show which layers are configured")
    status.add_argument("--config", default=argparse.SUPPRESS, help="audit config path")
    status.set_defaults(func=cmd_status)

    run = sub.add_parser("run", help="run the audit")
    run.add_argument("--config", default=argparse.SUPPRESS, help="audit config path")
    run.add_argument(
        "--graph",
        type=Path,
        help="v2 review graph; default: discover .agents/review-graph.toml, else inventory only",
    )
    run.add_argument("--project-root", type=Path)
    run.add_argument(
        "--source",
        action="append",
        required=True,
        type=Path,
        help="file or directory to inventory; repeatable",
    )
    run.add_argument("--out", type=Path, help="write the report here instead of stdout")
    run.add_argument("--json", type=Path)
    run.add_argument("--threshold", type=float, default=0.08)
    run.add_argument("--max-model-calls", type=int, default=DEFAULT_MAX_CALLS)
    run.add_argument("--model-timeout", type=int, default=DEFAULT_TIMEOUT)
    run.add_argument("--decision-url")
    run.add_argument("--decision-model")
    run.add_argument("--decision-key")
    run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
