#!/usr/bin/env python3
"""Semantic concept audit for a hydra-crux build, migration, or evolution.

The audit has two layers. Only the first is required:

1. **deterministic** — parse source documents into role-tagged atoms, compare them
   with the graph's homes, and flag candidates. No network, no model, no
   third-party dependency.
2. **decision-model** — if an endpoint that answers typed questions about a
   state is configured (JEV is one implementation), use its Noul and Choice
   answers as a probabilistic triage signal. It never becomes the verdict;
   every answer carries a confidence band and a human-review flag.

The script ships no LLM client. The semantic step is the agent reading the
candidate list; the decision model is an optional second opinion, not a
replacement for that reading.

Configuration is opt-in. Without a ``[decision]`` section the audit still runs,
and the report says which layers were skipped and why.

This is not a lint. It reads authored ``SKILL.md`` prose, so it is not wired
into ``scripts/lint-skills.sh`` and it must never fail a commit. Its product is
a diff list for a human, not a pass/fail gate.
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
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG = Path("~/.config/hydra-crux/audit.toml").expanduser()
DEFAULT_MAX_CALLS = 40

ROLE_OPTIONS = {
    "objective": "The value or interest the document protects, stated as a principle.",
    "scope": "What the document owns and what it explicitly does not own.",
    "check": "A concrete review question or good pattern to look for.",
    "anti_pattern": "A concrete bad pattern or failure to reject.",
    "evidence": "A pointer to a test, document, or command that proves a claim.",
    "history": "What was true in an earlier version or what a past delivery did.",
    "other": "None of the above.",
}

# These are cluster cores, not match keys. A sentence is assigned to the nearest
# centroid by TF-IDF cosine; the heading it sits under never decides its role.
ROLE_PROTOTYPES = {
    "verdict": [
        "Do not inline a near-copy.",
        "The surface must never decide the tradeoff.",
        "A convenient default must not adopt undeclared content.",
        "This rule wins over the opposing stance.",
        "Never let a default erase undeclared content.",
        "The guard must reject a silent overwrite.",
    ],
    "check": [
        "Inspect the journal and the lock path before writing.",
        "Compare the old and new behavior, then test each boundary.",
        "Ask whether the reviewed action is the action that ran.",
        "Exercise the failure path and inspect the residue.",
        "Check whether a failure reveals less than a success.",
        "Compare the before and after state at each boundary.",
    ],
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
    "cost": [
        "The operator pays an extra confirmation for each resource.",
        "This accepts slower applies in exchange for proof.",
        "The cost is borne by the user who must repeat the work.",
    ],
    "evidence": [
        "Evidence: tests/drift/test_ownership_classification.py.",
        "The command that reruns the test is the proof.",
        "Required evidence is a before-and-after count of walks.",
    ],
    "statement": [
        "The command writes a manifest next to the profile.",
        "This section describes the current layout.",
        "The migration happened in three steps.",
    ],
}

# The archived domain skills share one template. This table records the
# template's own labels for inventory; it is not a semantic classifier and it
# must not be reused for a new skill set. Unknown headings fall through to
# ``assign_roles``.
ARCHIVE_TEMPLATE = {
    "stable core and changing contract": "objective",
    "scope boundary": "scope",
    "good patterns": "check",
    "bad patterns": "anti_pattern",
    "when a duplicate gets written": "check",
    "do this before you write": "check",
    "review a diff for a copy": "check",
    "limits of the guard": "check",
}


@dataclass
class Endpoint:
    url: str
    model: str
    key: str = ""
    key_env: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.url and self.model)

    @property
    def missing(self) -> list[str]:
        return [name for name in ("url", "model") if not getattr(self, name)]


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
    role: str
    text: str
    line: int = 0


@dataclass
class Home:
    id: str
    kind: str
    title: str
    text: str
    objective: str = ""
    keywords: list[str] = field(default_factory=list)


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
    if not key and key_env:
        key = os.environ.get(key_env, "")
    if not key:
        key = os.environ.get(f"{env_prefix}_KEY", "")
    return Endpoint(url=url, model=model, key=key, key_env=key_env)


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


def redact_url(url: str) -> str:
    """Drop credentials and query values before a URL reaches a report."""
    if not url:
        return url
    try:
        parts = urllib.parse.urlsplit(url)
        port = parts.port
    except ValueError:
        return "(invalid URL)"
    host = parts.hostname or ""
    if port:
        host = f"{host}:{port}"
    query = "&".join(f"{key}=****" for key in urllib.parse.parse_qs(parts.query))
    return urllib.parse.urlunsplit(
        (parts.scheme, host, parts.path, query, "")
    )


def redact_text(text: str) -> str:
    """Strip userinfo from any URL that an exception message may echo."""
    return re.sub(r"//[^\s/@]+@", "//****@", text)


def split_credentials(url: str) -> tuple[str, str]:
    """Return the URL without userinfo, plus a Basic auth header when present."""
    try:
        parts = urllib.parse.urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise ValueError("invalid endpoint URL") from exc
    if parts.username is None:
        return url, ""
    userinfo = urllib.parse.unquote(parts.username) + ":" + urllib.parse.unquote(
        parts.password or ""
    )
    host = parts.hostname or ""
    if port:
        host = f"{host}:{port}"
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
                lines.append(f'{key} = {json.dumps(values[key])}')
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
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z`*\"(])", text)
    merged: list[str] = []
    for part in parts:
        if merged and ABBREVIATION.search(merged[-1]):
            merged[-1] += " " + part
        else:
            merged.append(part)
    return [part for part in merged if len(part.split()) >= 3]


def sentences(body: str):
    """Yield (paragraph_start_line, sentence), joining hard-wrapped lines."""
    paragraph: list[str] = []
    para_start = 0
    for number, raw in enumerate(body.splitlines()):
        if raw.strip():
            if not paragraph:
                para_start = number
            paragraph.append(raw.strip())
            continue
        if paragraph:
            for sentence in split_sentences(" ".join(paragraph)):
                yield para_start, sentence
            paragraph = []
    if paragraph:
        for sentence in split_sentences(" ".join(paragraph)):
            yield para_start, sentence


def bullets(body: str):
    lines = body.splitlines()
    index = 0
    while index < len(lines):
        match = re.match(r"^\s*[-*]\s+(.+)$", lines[index])
        if not match:
            index += 1
            continue
        start = index
        parts = [match.group(1).strip()]
        index += 1
        while index < len(lines):
            line = lines[index]
            if not line.strip() or re.match(r"^\s*[-*]\s+", line):
                break
            if not line.startswith(("  ", "\t")):
                break
            parts.append(line.strip())
            index += 1
        yield start, " ".join(parts)


def strip_frontmatter(text: str) -> tuple[str, int]:
    match = re.match(r"\A---\s*\n.*?\n---\s*\n", text, flags=re.DOTALL)
    if not match:
        return text, 0
    return text[match.end() :], text.count("\n", 0, match.end())


def parse_skill(path: Path, root: Path) -> list[Atom]:
    """Inventory a source document by its declared template, then semantically.

    Headings and list markers segment the document. A heading that the archived
    skill template declares gets the template's own label; every unknown heading
    is assigned by the nearest role prototype. The template table is inventory,
    not a semantic check of a new skill set.
    """
    text, line_offset = strip_frontmatter(path.read_text(encoding="utf-8"))
    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
    templated: list[tuple[str, str, int, str]] = []
    generic: list[tuple[str, int, str]] = []
    for heading, start, body in sections(text):
        start += line_offset
        declared = ARCHIVE_TEMPLATE.get(heading.strip().lower())
        if declared == "objective":
            flat = re.sub(r"\s+", " ", body).strip()
            plain = re.sub(r"\*\*|__", "", flat)
            match = re.search(r"stable value is:\s*(.+?)(?:\.\s|$)", plain, re.IGNORECASE)
            if match:
                templated.append((declared, heading, start, match.group(1).strip()))
                continue
        bullet_items = list(bullets(body))
        stream = (
            (offset, item) for offset, item in bullet_items
        ) if bullet_items else sentences(body)
        for offset, unit in stream:
            if len(unit.split()) < 3:
                continue
            if declared:
                templated.append((declared, heading, start + offset, unit))
            else:
                generic.append((heading, start + offset, unit))

    atoms = [Atom(rel, heading, role, unit, line) for role, heading, line, unit in templated]
    for (heading, line, unit), role in zip(generic, assign_roles([unit for _, _, unit in generic])):
        if role["role"] != "statement":
            atoms.append(Atom(rel, heading, role["role"], unit, line))
    return atoms


def collect_source_atoms(sources: list[Path], root: Path) -> list[Atom]:
    """Inventory every source path once.

    A file is one document. A directory contributes its top-level ``*.md``
    documents and its ``*/SKILL.md`` skill views, so a first build can audit
    the owner documents that already state requirements instead of waiting for
    an archived skill layer to exist.
    """
    atoms: list[Atom] = []
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
            if resolved in seen or not path.is_file():
                continue
            seen.add(resolved)
            atoms.extend(parse_skill(path, root))
    return atoms


def load_homes(graph: dict, root: Path) -> list[Home]:
    homes: list[Home] = []
    for surface in graph.get("surface", []):
        skill = surface.get("skill", "")
        path = root / skill if skill else None
        text = path.read_text(encoding="utf-8") if path and path.exists() else ""
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
                        text[:3000],
                    ]
                ),
                keywords=[str(x) for x in surface.get("keywords", [])],
            )
        )
    for stance in graph.get("stance", []):
        skill = stance.get("skill", "")
        path = root / skill if skill else None
        text = path.read_text(encoding="utf-8") if path and path.exists() else ""
        objective = str(stance.get("objective", ""))
        homes.append(
            Home(
                id=str(stance.get("id", "")),
                kind="stance",
                title=str(stance.get("title", stance.get("id", ""))),
                text=" ".join([str(stance.get("title", "")), objective, text[:3000]]),
                objective=objective,
            )
        )
    return homes


# -------------------------------------------------------------------- coverage

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

    The mood feature is an input to the centroid classifier, not a decision. It
    exists because a bag of content words cannot tell ``do not write`` from
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


def tfidf(docs: list[list[str]]) -> list[dict[str, float]]:
    df = Counter()
    for doc in docs:
        df.update(set(doc))
    total = len(docs)
    vectors = []
    for doc in docs:
        counts = Counter(doc)
        vec = {w: (1 + math.log(c)) * math.log((1 + total) / (1 + df[w])) for w, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({w: v / norm for w, v in vec.items()})
    return vectors


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def assign_roles(texts: list[str]) -> list[dict]:
    """Assign each text to the nearest role prototype by TF-IDF cosine.

    The prototype sentences are cluster cores. Section headings are metadata for
    the report; they are never consulted here.
    """
    if not texts:
        return []
    flat = [(role, example) for role, examples in ROLE_PROTOTYPES.items() for example in examples]
    vectors = tfidf([role_tokens(example) for _, example in flat] + [role_tokens(text) for text in texts])
    centroids: dict[str, dict[str, float]] = {}
    index = 0
    for role, examples in ROLE_PROTOTYPES.items():
        role_vectors = vectors[index : index + len(examples)]
        index += len(examples)
        acc: dict[str, float] = defaultdict(float)
        for vector in role_vectors:
            for key, value in vector.items():
                acc[key] += value / len(role_vectors)
        norm = math.sqrt(sum(value * value for value in acc.values())) or 1.0
        centroids[role] = {key: value / norm for key, value in acc.items()}

    results = []
    for vector in vectors[len(flat) :]:
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
        rows.append(
            {
                "atom": atom,
                "top": [
                    {"home": home, "kind": kind, "score": score}
                    for home, kind, score in scored[:3]
                ],
                "orphan": scored[0][2] < threshold,
            }
        )
    return rows


# ------------------------------------------------------------------ layer bleed


def bleed_candidates(homes: list[Home], root: Path, limit: int = 15) -> list[dict]:
    """Rank sentences by semantic affinity to the other layer's role.

    This returns a reading order, not a verdict. Collection is structural and
    the ranking is nearest-prototype cosine; the heading is never consulted.
    A model layer decides which ranked candidates are real.
    """
    items = []
    for home in homes:
        if not home.id:
            continue
        path = None
        for candidate in root.glob(f".agents/skills/{home.id}/SKILL.md"):
            path = candidate
        if path is None:
            continue
        text, line_offset = strip_frontmatter(path.read_text(encoding="utf-8"))
        for heading, start, body in sections(text):
            start += line_offset
            bullet_items = list(bullets(body))
            stream = (
                (offset, sentence)
                for offset, item in bullet_items
                for sentence in split_sentences(item)
            ) if bullet_items else sentences(body)
            for offset, sentence in stream:
                if len(sentence.split()) < 5:
                    continue
                items.append(
                    {
                        "home": home.id,
                        "kind": home.kind,
                        "section": heading,
                        "line": start + offset,
                        "text": sentence,
                    }
                )

    rows = []
    for item, role in zip(items, assign_roles([item["text"] for item in items])):
        target = "verdict" if item["kind"] == "surface" else "check"
        rows.append({**item, **role, "affinity": role["scores"][target]})

    ranked: list[dict] = []
    for kind, signal in (
        ("surface", "verdict-affinity-in-surface"),
        ("stance", "check-affinity-in-stance"),
    ):
        subset = sorted((row for row in rows if row["kind"] == kind), key=lambda r: r["affinity"], reverse=True)
        ranked.extend({**row, "signal": signal} for row in subset[:limit])
    return ranked


# --------------------------------------------------------------- graph findings


def graph_findings(graph: dict) -> dict:
    stances = graph.get("stance", [])
    oppositions = graph.get("opposition", [])
    opponent: dict[str, str] = {}
    for opposition in oppositions:
        pair = [str(x) for x in opposition.get("stances", [])]
        if len(pair) == 2:
            opponent[pair[0]] = pair[1]
            opponent[pair[1]] = pair[0]

    payer_rows = []
    for stance in stances:
        sid = str(stance.get("id", ""))
        for harm in stance.get("accepted_harm", []):
            payer = str(harm.get("payer_stance") or harm.get("payer") or "")
            payer_rows.append(
                {
                    "stance": sid,
                    "payer": payer,
                    "opponent": opponent.get(sid, ""),
                    "payer_is_opponent": bool(payer) and payer == opponent.get(sid),
                }
            )

    referenced = set()
    readers: dict[str, set[str]] = defaultdict(set)
    stance_surfaces: dict[str, list[str]] = {}
    for stance in stances:
        sid = str(stance.get("id", ""))
        surfaces = [str(x) for x in stance.get("surfaces", [])]
        stance_surfaces[sid] = surfaces
        referenced.update(surfaces)
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
        if str(surface.get("id", "")) not in referenced and not surface.get("unopposed_stake")
    ]
    unopposed_surfaces = [
        {"id": str(surface.get("id", "")), "stake": str(surface.get("unopposed_stake", ""))}
        for surface in graph.get("surface", [])
        if surface.get("unopposed_stake")
    ]

    axis_sizes = Counter(len(o.get("stances", [])) for o in oppositions)
    return {
        "stance_count": len(stances),
        "axis_count": len(oppositions),
        "axis_sizes": dict(axis_sizes),
        "surface_count": len(graph.get("surface", [])),
        "one_to_one_surfaces": one_to_one,
        "payer_rows": payer_rows,
        "payer_symmetry": sum(1 for row in payer_rows if row["payer_is_opponent"]),
        "payer_total": len(payer_rows),
        "unpaired_surfaces": unpaired,
        "unopposed_surfaces": unopposed_surfaces,
        "unopposed_stakes": sum(
            1 for stake in graph.get("stake", []) if str(stake.get("status", "")) == "unopposed"
        ),
    }


# ------------------------------------------------------------------- model I/O


def post_json(url: str, payload: dict, key: str, timeout: int = 120) -> dict:
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
    """Decision-model endpoint: a state plus typed questions."""

    def __init__(self, endpoint: Endpoint):
        self.endpoint = endpoint

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
        )
        return result["answers"]["q"]


def _confidence(value: object) -> float:
    """A model answer is usable only if its confidence is a finite 0..1 number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"confidence is not a number: {value!r}")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"confidence outside 0..1: {value!r}")
    return number


def classify_role(text: str, config: Config) -> dict:
    if config.decision and config.decision.configured:
        answer = DecisionModel(config.decision).choice(
            text, "Which role does this statement play in a review skill?", ROLE_OPTIONS
        )
        if not isinstance(answer, dict):
            raise ValueError(f"decision-model answer is not an object: {answer!r}")
        role = str(answer.get("choice", "")).strip()
        if role not in ROLE_OPTIONS:
            raise ValueError(f"unknown role from decision model: {role!r}")
        return {
            "role": role,
            "confidence": _confidence(answer.get("confidence")),
            "source": "decision-model",
        }
    role = assign_roles([text])[0]
    return {"role": role["role"], "confidence": role["score"], "source": "deterministic"}


def triage(rows: list[dict], config: Config, max_calls: int) -> list[dict]:
    """Classify flagged rows, bounded by max_calls. Never raises on model error."""
    if not config.layers()[1:]:
        return []
    if max_calls <= 0:
        return []
    layer = "decision-model"
    results = []
    for row in rows[:max_calls]:
        try:
            answer = classify_role(row["text"], config)
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            http.client.HTTPException,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
        ) as exc:
            answer = {
                "role": "error",
                "confidence": 0.0,
                "source": "error",
                "layer": layer,
                "error": redact_text(str(exc)),
            }
        results.append({**row, **answer, "layer": answer.get("layer", answer["source"])})
    return results


def skip_reason(
    config: Config, config_error: str, candidate_count: int, max_calls: int
) -> str:
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
        return f"the [decision] section is incomplete (missing {missing}); nothing was called"
    return "no row was triaged"


# ---------------------------------------------------------------------- report


def render_report(
    project: str,
    config: Config,
    atoms: list[Atom],
    homes: list[Home],
    coverage_rows: list[dict],
    bleed_rows: list[dict],
    findings: dict,
    triage_rows: list[dict],
    threshold: float,
    candidate_count: int = 0,
    max_calls: int = 0,
    config_error: str = "",
) -> str:
    lines = [f"# Concept audit: {project}", ""]
    lines.extend(
        [
            "This report is a diff list for a human. Deterministic findings are candidates,",
            "not verdicts. Model findings are triage signals, not decisions.",
            "",
            "## Configuration",
            "",
            "| layer | status | endpoint |",
            "| --- | --- | --- |",
        ]
    )
    calls = Counter(str(row.get("layer", "")) for row in triage_rows)

    def describe(layer: str, section: str, endpoint: Endpoint | None) -> str:
        if config_error:
            return "skipped (invalid config)"
        if endpoint is None:
            return f"skipped (no [{section}])"
        if not endpoint.configured:
            return f"skipped (incomplete [{section}]: missing {', '.join(endpoint.missing)})"
        if calls[layer]:
            failed = sum(
                1
                for row in triage_rows
                if row.get("layer") == layer and row.get("source") == "error"
            )
            suffix = f", {failed} failed" if failed else ""
            return f"active ({calls[layer]} calls{suffix})"
        if not candidate_count:
            return "configured, not called (no candidates)"
        if max_calls <= 0:
            return "configured, not called (--max-model-calls 0)"
        return "configured, not called"

    status = {
        "deterministic": "active",
        "decision-model": describe("decision-model", "decision", config.decision),
    }
    for layer in ("deterministic", "decision-model"):
        endpoint = ""
        if layer == "decision-model" and config.decision:
            endpoint = f"{config.decision.model} @ {redact_url(config.decision.url)}"
        lines.append(f"| {layer} | {status[layer]} | {endpoint or '-'} |")
    lines.extend(["", f"Config: `{config.path}`", ""])
    if config_error:
        lines.extend([f"Config error: {config_error}", ""])

    role_counts = Counter(atom.role for atom in atoms)
    lines.extend(
        [
            "## Inventory",
            "",
            (
                f"{len(atoms)} atoms from {len({a.source for a in atoms})} source documents; "
                f"{len(homes)} homes ({sum(1 for h in homes if h.kind == 'surface')} surfaces, "
                f"{sum(1 for h in homes if h.kind == 'stance')} stances)."
            ),
            "",
            "| role | count |",
            "| --- | ---: |",
        ]
    )
    for role, count in role_counts.most_common():
        lines.append(f"| {role} | {count} |")

    orphans = [row for row in coverage_rows if row["orphan"]]
    scores = sorted(row["top"][0]["score"] for row in coverage_rows if row["top"])
    median = scores[len(scores) // 2] if scores else 0.0
    lines.extend(
        [
            "",
            "## Coverage candidates",
            "",
            (
                f"Lexical threshold {threshold}. {len(orphans)} of {len(coverage_rows)} atoms "
                f"have no home above it. Best-home scores: min {scores[0] if scores else 0:.3f}, "
                f"median {median:.3f}, max {scores[-1] if scores else 0:.3f}."
            ),
            "",
        ]
    )
    if orphans:
        lines.extend(["| source | role | atom | best home | score |", "| --- | --- | --- | --- | ---: |"])
        for row in orphans[:30]:
            atom = row["atom"]
            best = row["top"][0] if row["top"] else {"home": "-", "score": 0}
            text = atom.text.replace("|", "\\|")[:140]
            lines.append(f"| {atom.source} | {atom.role} | {text} | {best['home']} | {best['score']} |")
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
                    "Top-1 home for each source document. A document that spreads across several "
                    "homes is evidence for a many-to-many cut, not a 1:1 rename."
                ),
                "",
                "| source | top-1 homes |",
                "| --- | --- |",
            ]
        )
        for source, counts in sorted(distribution.items()):
            cells = ", ".join(f"{home} ({count})" for home, count in counts.most_common(4))
            lines.append(f"| {source} | {cells} |")
        concentrated = []
        for source, counts in distribution.items():
            home, count = counts.most_common(1)[0]
            if count / sum(counts.values()) >= 0.8:
                concentrated.append(f"{source} -> {home}")
        if concentrated:
            lines.extend(
                [
                    "",
                    "Concentrated sources (at least 80% of atoms in one home): "
                    + "; ".join(concentrated)
                    + ". These are the 1:1 candidates; check whether the home has a stance "
                    "or only an unopposed stake.",
                ]
            )

    lines.extend(
        [
            "",
            "## Layer bleed candidates",
            "",
            (
                f"{len(bleed_rows)} sentences ranked by semantic affinity to the other layer's "
                "role. This is a reading order, not a decision. The section heading is metadata, "
                "not a gate."
            ),
            "",
        ]
    )
    if bleed_rows:
        lines.extend(
            [
                "| home | signal | prototype role | affinity | margin | line | sentence |",
                "| --- | --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for row in bleed_rows[:40]:
            text = row["text"].replace("|", "\\|")[:160]
            lines.append(
                f"| {row['home']} | {row['signal']} | {row['role']} | {row['affinity']:.3f} | "
                f"{row['margin']:.3f} | {row['line']} | {text} |"
            )
        if len(bleed_rows) > 40:
            lines.append(f"| ... | | | | | | {len(bleed_rows) - 40} more |")
    else:
        lines.append("None.")

    lines.extend(["", "## Graph findings", ""])
    lines.append(
        f"- {findings['stance_count']} stances on {findings['axis_count']} axes; "
        f"axis sizes {findings['axis_sizes']}."
    )
    lines.append(
        f"- {findings['payer_symmetry']}/{findings['payer_total']} payers are exactly the "
        "opposing stance. A high ratio is a quota signature, not an error: check whether "
        "the harmed side has an independent interest."
    )
    lines.append(
        f"- {len(findings['one_to_one_surfaces'])}/{findings['surface_count']} surfaces pair "
        "one-to-one with a stance. A perfect matching is the same quota signature in the "
        "surface layer: check whether each surface exists because a check has a home, not "
        "because a stance needed a partner."
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
            + ", ".join(f"{row['id']} ({row['stake']})" for row in findings["unopposed_surfaces"])
            + ". An unopposed stake is a check, not a payer; treat verdict language there as "
            "uncontested."
        )
    lines.append(f"- {findings['unopposed_stakes']} unopposed stakes.")

    lines.extend(["", "## Model triage", ""])
    if not triage_rows:
        lines.append(f"Skipped: {skip_reason(config, config_error, candidate_count, max_calls)}.")
    else:
        lines.extend(
            [
                "| home/source | signal | role | confidence | source | error |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for row in triage_rows:
            lines.append(
                f"| {row.get('home', '-')} | {row.get('signal', '-')} | {row.get('role', '-')} | "
                f"{row.get('confidence', 0):.2f} | {row.get('source', '-')} | "
                f"{row.get('error', '')} |"
            )

    lines.extend(
        [
            "",
            "## Needs human",
            "",
            "1. Every coverage candidate whose role is `check` or `verdict`.",
            (
                "2. Every `verdict-affinity-in-surface` candidate that the model rates as "
                "`verdict` or `anti_pattern` above 0.6."
            ),
            (
                "3. Every stance whose payer is only its opponent and whose accepted harm "
                "describes a cost the stance itself bears."
            ),
            "",
        ]
    )
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
    for section, prefix in (("decision", "decision"),):
        url = getattr(args, f"{prefix}_url", None)
        model = getattr(args, f"{prefix}_model", None)
        key = getattr(args, f"{prefix}_key", None)
        key_env = getattr(args, f"{prefix}_key_env", None)
        if not any((url, model, key, key_env)):
            continue
        values = data.setdefault(section, {})
        if url:
            values["url"] = url
        if model:
            values["model"] = model
        if key:
            values["key"] = key
            values.pop("key_env", None)
            print(
                f"warning: storing a literal {section} key in {path} (mode 0600); "
                f"prefer --{prefix}-key-env",
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
    for name, section, endpoint in (("decision", "decision", config.decision),):
        if endpoint and endpoint.configured:
            print(
                f"{name}: {endpoint.model} @ {redact_url(endpoint.url)} "
                f"key={mask(endpoint.key)}"
            )
        elif endpoint:
            print(f"{name}: incomplete [{section}] (missing {', '.join(endpoint.missing)})")
        else:
            print(f"{name}: not configured")
    print("layers: " + ", ".join(config.layers()))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.max_model_calls < 0:
        print("--max-model-calls must be >= 0", file=sys.stderr)
        return 2
    config_error = ""
    try:
        config = resolve_config(args)
    except ConfigError as exc:
        config = Config(path=Path(args.config).expanduser())
        config_error = str(exc)
    graph_path = Path(args.graph).resolve()
    root = Path(args.project_root).resolve() if args.project_root else graph_path.parent.parent
    with graph_path.open("rb") as handle:
        graph = tomllib.load(handle)

    sources = [Path(p).resolve() for p in getattr(args, "source", [])]
    sources += [Path(p).resolve() for p in getattr(args, "source_dir", [])]
    if not sources:
        default = root / "archive" / "domain-review"
        if default.exists():
            sources = [default]
    atoms = collect_source_atoms(sources, root)

    homes = load_homes(graph, root)
    coverage_rows = coverage(atoms, homes, args.threshold)
    bleed_rows = bleed_candidates(homes, root)
    findings = graph_findings(graph)

    candidates = [
        {"text": row["atom"].text, "home": row["atom"].source, "signal": "coverage-orphan"}
        for row in coverage_rows
        if row["orphan"]
    ]
    candidates += [
        {"text": row["text"], "home": row["home"], "signal": row["signal"]}
        for row in bleed_rows
    ]
    triage_rows = triage(candidates, config, args.max_model_calls)

    report = render_report(
        str(graph.get("project", root.name)),
        config,
        atoms,
        homes,
        coverage_rows,
        bleed_rows,
        findings,
        triage_rows,
        args.threshold,
        candidate_count=len(candidates),
        max_calls=args.max_model_calls,
        config_error=config_error,
    )
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(report)
    if args.json:
        payload = {
            "project": graph.get("project", root.name),
            "layers": config.layers(),
            "config_error": config_error,
            "atoms": [atom.__dict__ for atom in atoms],
            "coverage": [
                {
                    "source": row["atom"].source,
                    "role": row["atom"].role,
                    "text": row["atom"].text,
                    "top": row["top"],
                    "orphan": row["orphan"],
                }
                for row in coverage_rows
            ],
            "bleed": bleed_rows,
            "graph": findings,
            "triage": triage_rows,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
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
    setup.add_argument("--decision-key-env")
    setup.set_defaults(func=cmd_setup)

    status = sub.add_parser("status", help="show which layers are configured")
    status.add_argument("--config", default=argparse.SUPPRESS, help="audit config path")
    status.set_defaults(func=cmd_status)

    run = sub.add_parser("run", help="run the audit")
    run.add_argument("--config", default=argparse.SUPPRESS, help="audit config path")
    run.add_argument("--graph", required=True, type=Path)
    run.add_argument("--project-root", type=Path)
    run.add_argument(
        "--source",
        action="append",
        default=[],
        type=Path,
        help="file or directory to inventory; repeatable (default: archive/domain-review)",
    )
    run.add_argument("--source-dir", action="append", default=[], type=Path, help=argparse.SUPPRESS)
    run.add_argument("--out", type=Path)
    run.add_argument("--json", type=Path)
    run.add_argument("--threshold", type=float, default=0.08)
    run.add_argument("--max-model-calls", type=int, default=DEFAULT_MAX_CALLS)
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
