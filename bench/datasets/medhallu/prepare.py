# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Build the MedHallu benchmark from Stanford MedHELM's published runs.

MedHELM ran 13 LLMs over the same 1,000 MedHallu items and published every
prediction in a public bucket. This script turns that into:

  data/items.test.jsonl   the exact 1,000 items MedHELM used, gold included
  data/items.dev.jsonl    a separate sample from MedHallu's pqa_artificial config,
                          for tuning wording and thresholds (never reported)
  data/items.dev2.jsonl   a second, disjoint sample, to confirm what dev picked
  data/published/*.jsonl  each LLM's published prediction per item, in run_bench.py's
                          record format, so score.py shows them next to Jev
  data/task.json          the question Jev (and any LLM you run yourself) is asked

It checks that every model saw the same item ids, and that accuracy recomputed
from the downloaded predictions equals the accuracy MedHELM reports.

Usage (from bench/):
  uv run datasets/medhallu/prepare.py
  uv run datasets/medhallu/prepare.py --dev-size 500 --release v4.0.0
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import re
import urllib.parse
import urllib.request
from pathlib import Path

BUCKET_API = "https://storage.googleapis.com/storage/v1/b/crfm-helm-public/o"
BUCKET_RAW = "https://storage.googleapis.com/crfm-helm-public/"
HF_ROWS = "https://datasets-server.huggingface.co/rows"
HF_DATASET = "UTAustin-AIHealth/MedHallu"
# Whitespace around the three parts varies between MedHELM runs (older runs indent them).
INPUT_PATTERN = re.compile(r"^\s*World Knowledge:\s*(.*)\n\s*Question:\s*(.*)\n\s*Answer:\s*(.*?)\s*$", re.S)

# Jev's question, built from MedHELM's prompt (display_requests.json of any medhallu run).
# That prompt cannot be sent to Jev as is: Jev takes named state fields plus a typed
# question, and returns P(yes) instead of the text "0" or "1". So each part of the prompt
# is mapped to its Jev counterpart, keeping MedHELM's wording wherever it fits:
#   "World Knowledge / Question / Answer" blocks -> state fields knowledge, question, answer
#   "determine if the provided answer contains non-factual or hallucinated information"
#                                                 -> instructions.question
#   "factual contradiction between the answer and the world knowledge ... might be
#    fabricated"                                  -> instructions.focus
#   the four "Type:" definitions                  -> criteria.true.hallucination_types
#   "'0' if the answer is factual and '1' if ... hallucinated" -> labels "0" and "1"
# Like MedHELM's prompt, it gives no examples (zero-shot).
INSTRUCTIONS = {
    "question": "Does `answer` contain non-factual or hallucinated information?",
    "inspect": "`answer`, a proposed answer to `question`. `knowledge` is the world knowledge to judge it against.",
    "focus": (
        "Determine if there is a factual contradiction between `answer` and `knowledge`. "
        "Some information in `answer` might be fabricated."
    ),
}
LABELS = {
    "1": {
        "what": "Hallucinated: `answer` falls into at least one of the hallucination types",
        "hallucination_types": {
            "Misinterpretation of the question": (
                "`answer` misunderstands `question`, leading to an off-topic or irrelevant response"
            ),
            "Incomplete information": (
                "`answer` points out what is not true without providing the correct information"
            ),
            "Mechanism and pathway misattribution": (
                "`answer` falsely attributes biological mechanisms, molecular pathways or disease "
                "processes, contradicting established medical knowledge"
            ),
            "Methodological and evidence fabrication": (
                "`answer` invents false research methods, statistical data or specific clinical outcomes"
            ),
        },
    },
    "0": {"what": "Factual: `answer` is consistent with `knowledge` and contains no fabricated information"},
}


# Jev-specific question, chosen on dev and confirmed on dev2 (see PREREGISTRATION.md).
# The LLM-style mapping above stays as the task's main question: it is what an LLM run
# through this harness is asked, and it was test run 1. Jev is asked this instead. One
# direct sentence beat the mapped prompt and every variant with criteria or sub-questions.
JEV_QUESTIONS = {
    "authors_reject": {
        "instructions": (
            "Would the authors of the study described in `knowledge` say that `answer` "
            "misrepresents their findings?"
        )
    }
}


def fetch_json(url: str):
    with urllib.request.urlopen(url, timeout=120) as resp:
        return json.load(resp)


def list_runs(release: str) -> list[str]:
    prefix = f"medhelm/benchmark_output/runs/{release}/medhallu"
    listing = fetch_json(f"{BUCKET_API}?prefix={urllib.parse.quote(prefix)}&delimiter=/")
    return listing.get("prefixes", [])


def run_file(run: str, name: str):
    return fetch_json(BUCKET_RAW + urllib.parse.quote(run + name))


def clean_knowledge(raw) -> str:
    """One passage per line. pqa_labeled (via MedHELM) gives a Python list literal as text;
    pqa_artificial gives a real list. Both must reach the models in the same form."""
    if isinstance(raw, str):
        try:
            raw = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return raw
    if isinstance(raw, (list, tuple)):
        return "\n".join(str(p) for p in raw)
    return str(raw)


def hf_rows(config: str, offset: int, length: int) -> list[dict]:
    query = urllib.parse.urlencode(
        {"dataset": HF_DATASET, "config": config, "split": "train", "offset": offset, "length": length}
    )
    return [r["row"] for r in fetch_json(f"{HF_ROWS}?{query}")["rows"]]


def parse_input(inst: dict) -> tuple[str, str, str]:
    match = INPUT_PATTERN.match(inst["input"]["text"])
    if not match:
        raise SystemExit(f"{inst['id']}: input does not look like a MedHallu prompt")
    knowledge, question, answer = (part.strip() for part in match.groups())
    return knowledge, question, answer


def stat(stats: list[dict], name: str) -> float | None:
    for s in stats:
        n = s["name"]
        if n["name"] == name and n.get("split") == "test" and "perturbation" not in n:
            return s.get("mean")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--release", default="v4.0.0", help="MedHELM release to read")
    parser.add_argument("--dev-size", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument("--task-only", action="store_true",
                        help="rewrite task.json from INSTRUCTIONS and LABELS, leave items and published alone")
    args = parser.parse_args()

    task = {
        "name": "medhallu",
        "source": f"MedHELM {args.release} medhallu (gs://crfm-helm-public/medhelm) over hf://datasets/{HF_DATASET}",
        "published_source": f"Stanford CRFM, MedHELM {args.release}",
        "type": "noul",
        "instructions": INSTRUCTIONS,
        "labels": LABELS,
        "positive": "1",
        "jev_questions": JEV_QUESTIONS,
        "jev_combine": "mean",
        "slice_fields": ["gold", "difficulty", "category"],
    }
    if args.task_only:
        (args.out / "task.json").write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {args.out}/task.json")
        return

    runs = list_runs(args.release)
    if not runs:
        raise SystemExit(f"no medhallu runs found in MedHELM {args.release}")

    # Source rows give each test item its difficulty and hallucination category, and
    # double-check the gold label: an answer equal to "Ground Truth" must be factual.
    source: dict[tuple[str, str], dict] = {}
    try:
        for offset in range(0, 1000, 100):
            for row in hf_rows("pqa_labeled", offset, 100):
                q = row["Question"].strip()
                source[(q, row["Ground Truth"].strip())] = {"gold": "0", "difficulty": row["Difficulty Level"]}
                source[(q, row["Hallucinated Answer"].strip())] = {
                    "gold": "1", "difficulty": row["Difficulty Level"],
                    "category": row["Category of Hallucination"],
                }
    except Exception as exc:  # noqa: BLE001 - slices are optional, the items are not
        print(f"warning: could not read {HF_DATASET} ({exc}); test items get no difficulty slice")

    instances = run_file(runs[0], "instances.json")
    items, test_questions, unmatched, disagree = [], set(), 0, 0
    for inst in instances:
        knowledge, question, answer = parse_input(inst)
        gold = next(r["output"]["text"] for r in inst["references"] if "correct" in r["tags"])
        item = {
            "id": inst["id"],
            "state": {"knowledge": clean_knowledge(knowledge), "question": question, "answer": answer},
            "gold": gold,
        }
        extra = source.get((question, answer))
        if extra is None:
            unmatched += 1
        else:
            disagree += extra["gold"] != gold
            item.update({k: v for k, v in extra.items() if k != "gold"})
        items.append(item)
        test_questions.add(question)
    items.sort(key=lambda it: int(it["id"].removeprefix("id")))
    if disagree:
        raise SystemExit(f"{disagree} MedHELM gold labels contradict the source dataset")
    if source and unmatched:
        print(f"warning: {unmatched} test items not found in the source rows (no difficulty slice for them)")

    args.out.mkdir(parents=True, exist_ok=True)
    published = args.out / "published"
    published.mkdir(exist_ok=True)
    ids = [it["id"] for it in items]
    gold = {it["id"]: it["gold"] for it in items}
    content = {it["id"]: (it["state"]["question"], it["state"]["answer"]) for it in items}
    print(f"MedHELM {args.release}: {len(items)} items, {len(runs)} published models")
    for run in runs:
        model = run.split("model=")[1].split(",")[0]
        run_instances = run_file(run, "instances.json")
        if sorted(inst["id"] for inst in run_instances) != sorted(ids):
            raise SystemExit(f"{model}: item ids differ from the first run, columns would not be comparable")
        for inst in run_instances:
            if parse_input(inst)[1:] != content[inst["id"]]:
                raise SystemExit(f"{model}: {inst['id']} has a different question or answer than the first run")
        spec = f"medhelm/{model}"
        records, correct = [], 0
        for pred in run_file(run, "display_predictions.json"):
            text = (pred.get("predicted_text") or "").strip()
            stats = pred.get("stats") or {}
            rec = {
                "id": pred["instance_id"], "repeat": 0, "spec": spec,
                "label": text if text in LABELS else None,
                "probabilities": None, "confidence": None,
                "input_tokens": stats.get("num_prompt_tokens"),
                "output_tokens": stats.get("num_output_tokens"),
                "cost": None,
                "latency_ms": (stats.get("inference_runtime") or 0) * 1000,
                "served_model": model, "provider": f"MedHELM {args.release}",
                "error": None if text in LABELS else f"label {text[:40]!r} is not in the label set",
                "attempts": 1,
            }
            correct += rec["label"] == gold[rec["id"]]
            records.append(rec)
        (published / f"{model}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
        ours, theirs = correct / len(records), stat(run_file(run, "stats.json"), "exact_match")
        flag = "" if theirs is not None and abs(ours - theirs) < 1e-9 else "   <-- differs from MedHELM"
        print(f"  {model:45} accuracy {ours:.3f} (MedHELM reports {theirs}){flag}")

    # Dev: pages of pqa_artificial at seeded offsets; each row yields its factual or its
    # hallucinated answer at random. dev2 is a second, disjoint sample: tune on dev, then
    # confirm on dev2 before anything goes to test.
    def sample_dev(seed: int, skip_pages: set[int]) -> tuple[list[dict], set[int]]:
        rng = random.Random(seed)
        rows: list[dict] = []
        pages = [pg for pg in rng.sample(range(90), k=90) if pg not in skip_pages]
        used: set[int] = set()
        for page in pages:
            if len(rows) >= args.dev_size:
                break
            used.add(page)
            for offset, row in enumerate(hf_rows("pqa_artificial", page * 100, 100)):
                question = row["Question"].strip()
                if question in test_questions or len(rows) >= args.dev_size:
                    continue
                hallucinated = rng.random() < 0.5
                item = {
                    "id": f"dev{page * 100 + offset}",
                    "state": {
                        "knowledge": clean_knowledge(row["Knowledge"]),
                        "question": question,
                        "answer": (row["Hallucinated Answer"] if hallucinated else row["Ground Truth"]).strip(),
                    },
                    "gold": "1" if hallucinated else "0",
                    "difficulty": row["Difficulty Level"],
                }
                if hallucinated:
                    item["category"] = row["Category of Hallucination"]
                rows.append(item)
        return rows, used

    dev, dev_pages = sample_dev(args.seed, set())
    dev2, _ = sample_dev(args.seed + 1, dev_pages)

    def dump(path: Path, rows: list[dict]) -> str:
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        path.write_text(text)
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    for split, rows in (("test", items), ("dev", dev), ("dev2", dev2)):
        if not all(isinstance(it["state"]["knowledge"], str) for it in rows):
            raise SystemExit(f"{split}: knowledge is not a string in every item")
    test_sha = dump(args.out / "items.test.jsonl", items)
    dev_sha = dump(args.out / "items.dev.jsonl", dev)
    dev2_sha = dump(args.out / "items.dev2.jsonl", dev2)
    (args.out / "task.json").write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n")
    balance = sum(it["gold"] == "1" for it in items)
    print(f"test: {len(items)} items ({balance} hallucinated), sha256 {test_sha}")
    print(f"dev:  {len(dev)} items ({sum(it['gold'] == '1' for it in dev)} hallucinated), sha256 {dev_sha}")
    print(f"dev2: {len(dev2)} items ({sum(it['gold'] == '1' for it in dev2)} hallucinated), sha256 {dev2_sha}")
    print(f"wrote {args.out}/")


if __name__ == "__main__":
    main()
