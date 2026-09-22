# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Build a leak-free benchmark set from birgermoell/icd10-clinical-notes.

The raw dataset has 1,802 rows, but only 106 distinct notes: every ICD-10 code
has one English note (shared by 33 rows whose `name` field is a translation)
and one Swedish note (the `sv` row). The `name` field is the answer in plain
text, and the train/test split shares most notes, so neither is usable as-is.

This script keeps one item per distinct note, drops `name`/`language`/`label`,
tags each item with its note language and whether the note is templated
("Patient diagnosed with X ...", which gives the answer away), and writes:

  <out>/items.jsonl   {"id", "text", "gold", "lang", "kind"}
  <out>/task.json     label set + the question both Jev and the LLMs are asked

Usage (from bench/):
  uv run datasets/icd10/prepare.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO = "birgermoell/icd10-clinical-notes"
REVISION = "e4192bde319f7513f98796a97948168f965d461c"
TEMPLATE_PREFIXES = ("Patient diagnosed with", "Patient diagnosticerad med")
INSTRUCTIONS = (
    "Which ICD-10 category best matches the main diagnosis documented in `note`?"
)


def fetch_jsonl(path: str, revision: str) -> list[dict]:
    url = f"https://huggingface.co/datasets/{REPO}/resolve/{revision}/{path}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return [json.loads(line) for line in resp.read().decode().splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--revision", default=REVISION)
    args = parser.parse_args()

    rows = fetch_jsonl("data/train.jsonl", args.revision) + fetch_jsonl(
        "data/test.jsonl", args.revision
    )

    labels: dict[str, str] = {}
    note_codes: dict[str, set[str]] = defaultdict(set)
    note_langs: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row["language"] == "en":
            labels[row["code"]] = row["name"]
        note_codes[row["journal_note"]].add(row["code"])
        note_langs[row["journal_note"]].add(row["language"])

    conflicting = [n for n, codes in note_codes.items() if len(codes) > 1]
    if conflicting:
        raise SystemExit(f"{len(conflicting)} notes map to more than one code")

    items = []
    for note, codes in note_codes.items():
        code = next(iter(codes))
        # Swedish notes are used only by `sv` rows; every other row shares the English note.
        lang = "sv" if note_langs[note] == {"sv"} else "en"
        kind = "templated" if note.startswith(TEMPLATE_PREFIXES) else "clinical"
        items.append(
            {"id": f"{code}_{lang}", "text": note, "gold": code, "lang": lang, "kind": kind}
        )
    items.sort(key=lambda it: (it["lang"], it["gold"]))

    task = {
        "name": "icd10-clinical-notes",
        "source": f"hf://datasets/{REPO}@{args.revision}",
        "type": "choice",
        "instructions": INSTRUCTIONS,
        "state_key": "note",
        "labels": dict(sorted(labels.items())),
        # Scoring hints, not part of the prompt: see DATASET.md for why en/clinical is the headline.
        "headline": "lang=en,kind=clinical",
        "slice_fields": ["lang", "kind"],
        "slice_cross": ["lang", "kind"],
    }

    args.out.mkdir(parents=True, exist_ok=True)
    items_text = "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items)
    (args.out / "items.jsonl").write_text(items_text)
    (args.out / "task.json").write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n")

    counts: dict[tuple[str, str], int] = defaultdict(int)
    for it in items:
        counts[(it["lang"], it["kind"])] += 1
    print(f"{len(rows)} raw rows -> {len(items)} distinct notes, {len(labels)} labels")
    for (lang, kind), n in sorted(counts.items()):
        print(f"  {lang} {kind:9} {n}")
    print(f"items sha256 {hashlib.sha256(items_text.encode()).hexdigest()[:16]}")
    print(f"wrote {args.out}/items.jsonl and {args.out}/task.json")


if __name__ == "__main__":
    main()
