"""Shared by run_bench.py and score.py: the task definition and dataset paths.

A dataset lives in datasets/<name>/data/ and holds:

  task.json            the question every model is asked (see Task below)
  items.<split>.jsonl  one item per line: {"id", "gold", "text" or "state", ...slice fields}
  published/*.jsonl    optional: predictions other people published for the
                       same items, in the runner's record format (test split only)

`text` is a single string sent under task.state_key. `state` is a JSON object
with named fields, for tasks that judge several pieces of text together.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BENCH_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BENCH_DIR / "datasets"

SYSTEM_PROMPT = (
    "You are a classifier. Choose the single best option from the list. "
    "Reply only in the requested JSON format."
)
# Bump when llm_prompt() changes shape, so old results never mix with new ones.
PROMPT_VERSION = 2


@dataclass(frozen=True)
class Task:
    name: str
    source: str
    type: str  # "choice": one of many labels. "noul": yes/no, Jev returns P(positive).
    instructions: str | dict  # Jev accepts a JSON object here (question, focus, ...)
    labels: dict[str, Any]  # label -> description: a string, or an object (what, types, ...)
    state_key: str = "text"
    positive: str | None = None  # noul only: the label that means "yes"
    # Optional, Jev only: several Nouls asked in one request instead of the single question,
    # and how their P(yes) values combine into P(positive). See combine_nouls().
    jev_questions: dict[str, dict] | None = None
    jev_combine: Any = "mean"
    slice_fields: tuple[str, ...] = ()
    slice_cross: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict, compare=False)

    @classmethod
    def load(cls, path: Path) -> Task:
        raw = json.loads(path.read_text())
        kind = raw.get("type", "choice")
        labels = raw["labels"]
        positive = raw.get("positive")
        if kind not in ("choice", "noul"):
            raise SystemExit(f"{path}: type must be 'choice' or 'noul', not {kind!r}")
        if kind == "noul" and (len(labels) != 2 or positive not in labels):
            raise SystemExit(f"{path}: a noul task needs exactly 2 labels and 'positive' naming one")
        return cls(
            name=raw.get("name", path.parent.parent.name),
            source=raw.get("source", ""),
            type=kind,
            instructions=raw["instructions"],
            labels=labels,
            state_key=raw.get("state_key", "text"),
            positive=positive,
            jev_questions=raw.get("jev_questions"),
            jev_combine=raw.get("jev_combine", "mean"),
            slice_fields=tuple(raw.get("slice_fields", ())),
            slice_cross=tuple(raw.get("slice_cross", ())),
            raw=raw,
        )

    @property
    def negative(self) -> str | None:
        if self.positive is None:
            return None
        return next(label for label in self.labels if label != self.positive)

    @property
    def is_binary(self) -> bool:
        return self.positive is not None and len(self.labels) == 2

    @property
    def fingerprint(self) -> str:
        """Identifies everything that shapes a model's input. Thresholds are not part of it."""
        parts = [self.type, self.instructions, self.state_key, self.labels, self.positive,
                 SYSTEM_PROMPT, PROMPT_VERSION]
        if self.jev_questions:  # appended only when used, so older runs keep their fingerprint
            parts += [self.jev_questions, self.jev_combine]
        blob = json.dumps(parts, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def state(self, item: dict) -> dict[str, Any]:
        if "state" in item:
            return item["state"]
        return {self.state_key: item["text"]}

    def llm_prompt(self, item: dict) -> str:
        blocks = "\n\n".join(f"<{key}>\n{value}\n</{key}>" for key, value in self.state(item).items())
        options = "\n".join(f"{code}: {as_text(name)}" for code, name in self.labels.items())
        return (
            f"{blocks}\n\n{as_text(self.instructions)}\n\n"
            f"Answer with exactly one code from this list:\n{options}"
        )

    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"label": {"type": "string", "enum": list(self.labels)}},
            "required": ["label"],
            "additionalProperties": False,
        }


def combine_nouls(nouls: dict[str, float], rule: Any) -> float:
    """P(positive) from several Noul answers: "mean", "max", or a logistic model
    {"weights": {question_id: w}, "bias": b} over the raw probabilities."""
    if rule == "mean":
        return sum(nouls.values()) / len(nouls)
    if rule == "max":
        return max(nouls.values())
    if isinstance(rule, dict):
        z = rule.get("bias", 0.0) + sum(w * nouls[qid] for qid, w in rule["weights"].items())
        return 1 / (1 + math.exp(-z))
    raise SystemExit(f"unknown jev_combine rule {rule!r}")


def as_text(value: Any) -> str:
    """Structured instructions and descriptions go to an LLM as the same JSON Jev receives."""
    return value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)


def label_name(description: Any) -> str:
    """One-line name of a label for report headings."""
    if isinstance(description, dict):
        description = description.get("what") or next(iter(description.values()), "")
    return as_text(description)


def item_text(item: dict) -> str:
    """Flat text of an item, for baselines and spreadsheets."""
    if "text" in item:
        return item["text"]
    return "\n".join(f"{key}: {value}" for key, value in item["state"].items())


def dataset_paths(dataset: str, split: str | None) -> tuple[Path, Path, Path]:
    """Returns (task.json, items file, published dir) for a dataset name and split."""
    data = DATASETS_DIR / dataset / "data"
    if not data.is_dir():
        known = sorted(p.name for p in DATASETS_DIR.iterdir() if (p / "data").is_dir())
        raise SystemExit(f"no dataset {dataset!r} in {DATASETS_DIR}. Prepared datasets: {known}")
    candidates = [data / f"items.{split}.jsonl"] if split else [data / "items.test.jsonl", data / "items.jsonl"]
    items = next((p for p in candidates if p.exists()), None)
    if items is None:
        have = sorted(p.name for p in data.glob("items*.jsonl"))
        raise SystemExit(f"{dataset}: no items file for split {split!r}. Found: {have}")
    return data / "task.json", items, data / "published"


def load_items(path: Path) -> list[dict]:
    # Not splitlines(): it also breaks on U+2028 and friends, which occur inside abstracts.
    return [json.loads(line) for line in path.read_text().split("\n") if line]
