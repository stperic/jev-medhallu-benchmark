# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Write the MedHallu test items with the abstract removed, for the source ablation.

Every item keeps its id, gold label, question and answer; only `knowledge` is
replaced by a fixed placeholder, so each prompt is identical to the original run
except for the source. If a model scores well above the 52% floor on these items,
part of its score does not come from checking the answer against the abstract.

Usage (from bench/):
  uv run datasets/medhallu/ablate_source.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PLACEHOLDER = "Not provided."
DATA = Path(__file__).parent / "data"


def main() -> None:
    src = DATA / "items.test.jsonl"
    out = DATA / "items.test-nosource.jsonl"
    # Not splitlines(): it also breaks on U+2028 and friends, which occur inside abstracts.
    items = [json.loads(line) for line in src.read_text().split("\n") if line.strip()]
    with out.open("w") as f:
        for item in items:
            item["state"] = {**item["state"], "knowledge": PLACEHOLDER}
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
    print(f"wrote {out.name}: {len(items)} items, sha256 {digest}")


if __name__ == "__main__":
    main()
