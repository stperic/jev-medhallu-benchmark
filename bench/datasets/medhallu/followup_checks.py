# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Tables for the follow-up checks in PREREGISTRATION.md (after the external critique).

Reads run files only; calls no model. Run from bench/ after the three runs:
  uv run datasets/medhallu/followup_checks.py
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

BENCH = Path(__file__).resolve().parents[2]
RUNS = BENCH / "runs" / "medhallu"
ITEMS = BENCH / "datasets" / "medhallu" / "data" / "items.test.jsonl"
JEV_THRESHOLD = 0.65  # run 2, chosen on dev
LLMS = {
    "openai/gpt-5.6-luna@none": "GPT-5.6 Luna, reasoning none",
    "google/gemini-3.8-flash@minimal": "Gemini 3.8 Flash, reasoning minimal",
    "google/gemini-3.5-flash-lite": "Gemini 3.5 Flash Lite",
    "anthropic/claude-haiku-4.5": "Claude Haiku 4.5",
}
NAMES = {"jev-1.13": "Jev 1.13 (run 2 question)", **LLMS}


def records(folder: str, spec: str) -> dict[str, dict]:
    path = RUNS / folder / (spec.replace("/", "_").replace("@", "_") + ".jsonl")
    lines = [line for line in path.read_text().split("\n") if line.strip()]
    return {r["id"]: r for r in map(json.loads, lines) if r.get("repeat", 0) == 0}


def labels(recs: dict[str, dict]) -> dict[str, str | None]:
    out = {}
    for i, r in recs.items():
        probs = r.get("probabilities")
        out[i] = ("1" if probs["1"] >= JEV_THRESHOLD else "0") if probs else r.get("label")
    return out


def mcnemar(a: dict, b: dict, gold: dict) -> tuple[int, int, float]:
    """Items only a got right, only b got right, exact two-sided p."""
    only_a = sum(a.get(i) == g != b.get(i) for i, g in gold.items())
    only_b = sum(b.get(i) == g != a.get(i) for i, g in gold.items())
    n, k = only_a + only_b, min(only_a, only_b)
    p = min(1.0, 2 * sum(math.comb(n, j) for j in range(k + 1)) / 2**n) if n else 1.0
    return only_a, only_b, p


def holm(ps: list[float]) -> list[float]:
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adjusted, running = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adjusted[i] = running
    return adjusted


def auroc(recs: dict[str, dict], gold: dict) -> float:
    pos = [recs[i]["probabilities"]["1"] for i, g in gold.items() if g == "1"]
    neg = [recs[i]["probabilities"]["1"] for i, g in gold.items() if g == "0"]
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def accuracy(pred: dict, gold: dict) -> float:
    return 100 * sum(pred.get(i) == g for i, g in gold.items()) / len(gold)


def check1(gold: dict) -> None:
    print("## Check 1: the same test items without the abstract\n")
    print("Floor: always 'faithful' scores 52.0%.\n")
    print("| Model | With abstract | Without abstract | Drop | Only right with | Only right without | McNemar p |")
    print("|---|---|---|---|---|---|---|")
    for spec, name in NAMES.items():
        with_src, without = labels(records("test-v2", spec)), labels(records("test-nosource", spec))
        a, b, p = mcnemar(with_src, without, gold)
        acc_w, acc_wo = accuracy(with_src, gold), accuracy(without, gold)
        print(f"| {name} | {acc_w:.1f}% | {acc_wo:.1f}% | {acc_w - acc_wo:+.1f} | {a} | {b} | {p:.2g} |")
    jev_w, jev_wo = records("test-v2", "jev-1.13"), records("test-nosource", "jev-1.13")
    print(f"\nJev AUROC: {auroc(jev_w, gold):.3f} with the abstract, {auroc(jev_wo, gold):.3f} without.\n")


def check2(gold: dict) -> None:
    print("## Check 2: the four LLMs asked Jev's question\n")
    jev = labels(records("test-v2", "jev-1.13"))
    rows = []
    for spec, name in LLMS.items():
        old, new = labels(records("test-v2", spec)), labels(records("test-llm-authors-question", spec))
        rows.append((name, accuracy(old, gold), accuracy(new, gold), mcnemar(new, old, gold), mcnemar(new, jev, gold)))
    holm_old = holm([r[3][2] for r in rows])
    holm_jev = holm([r[4][2] for r in rows])
    print(f"Jev run 2: {accuracy(jev, gold):.1f}%\n")
    print("| LLM | MedHELM-style prompt | Jev's question | Change | Holm p (vs own prompt) | Only LLM right / only Jev right | Holm p (vs Jev) |")
    print("|---|---|---|---|---|---|---|")
    for (name, a_old, a_new, _, vs_jev), p_old, p_jev in zip(rows, holm_old, holm_jev):
        print(f"| {name} | {a_old:.1f}% | {a_new:.1f}% | {a_new - a_old:+.1f} | {p_old:.2g} | {vs_jev[0]} / {vs_jev[1]} | {p_jev:.2g} |")
    print()


def check3() -> None:
    print("## Check 3: re-timing in one alternating session (first 200 test items)\n")
    stats = {}
    for spec in NAMES:
        ids = set(records("timing-interleaved", spec))  # compare the same items in both runs
        for folder in ("timing-interleaved", "test-v2"):
            lat = sorted(r["latency_ms"] for i, r in records(folder, spec).items() if i in ids and not r.get("error"))
            stats[spec, folder] = (statistics.median(lat), lat[min(len(lat) - 1, int(0.95 * len(lat)))], len(lat))
    jev_now = stats["jev-1.13", "timing-interleaved"][0]
    print("| Model | Median now | 95th pct now | x Jev now | Median in first run, same items | n |")
    print("|---|---|---|---|---|---|")
    for spec, name in NAMES.items():
        p50, p95, n = stats[spec, "timing-interleaved"]
        print(f"| {name} | {p50:,.0f} ms | {p95:,.0f} ms | {p50 / jev_now:.1f} | {stats[spec, 'test-v2'][0]:,.0f} ms | {n} |")
    print()


def wilson(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = correct / n
    centre, half = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return 100 * (centre - half) / (1 + z * z / n), 100 * (centre + half) / (1 + z * z / n)


def check4(gold: dict, band: float = 0.1) -> None:
    print(f"## Check 4: Jev first, an LLM for the uncertain rest (Jev decides when P <= {band} or >= {1 - band:.1f})\n")
    jev = records("test-v2", "jev-1.13")
    p_hall = {i: r["probabilities"]["1"] for i, r in jev.items()}
    jev_alone = labels(jev)
    sure = {i for i, p in p_hall.items() if p <= band or p >= 1 - band}
    print(f"Jev decides {len(sure) / 10:.1f}% of items, {accuracy({i: jev_alone[i] for i in sure}, {i: gold[i] for i in sure}):.1f}% of them correctly.\n")

    def timing(ms: list[float]) -> str:
        ms = sorted(ms)
        return f"{statistics.mean(ms):,.0f} / {statistics.median(ms):,.0f} / {ms[int(0.95 * len(ms))]:,.0f} ms"

    jev_ms = {i: r["latency_ms"] for i, r in jev.items()}
    jev_cost = sum(r["cost"] for r in jev.values())
    rows = []
    for spec, name in LLMS.items():
        answers = records("test-llm-authors-question", spec)
        llm_ms = {i: r["latency_ms"] for i, r in records("test-v2", spec).items()}
        alone = labels(answers)
        cascade = {i: ("1" if p_hall[i] >= 0.5 else "0") if i in sure else alone[i] for i in gold}
        cost = jev_cost + sum(answers[i]["cost"] for i in gold if i not in sure)
        ms = [jev_ms[i] + (0 if i in sure else llm_ms[i]) for i in gold]
        rows.append((name, cascade, alone, cost, ms, sum(r["cost"] for r in answers.values()), list(llm_ms.values())))
    p_llm = holm([mcnemar(r[1], r[2], gold)[2] for r in rows])
    p_jev = holm([mcnemar(r[1], jev_alone, gold)[2] for r in rows])
    print("| Setup | Accuracy [95% CI] | Sent to LLM | Cost per 1,000 | Time mean / median / p95 | Holm p vs LLM alone | Holm p vs Jev alone |")
    print("|---|---|---|---|---|---|---|")
    n_ok = sum(jev_alone[i] == g for i, g in gold.items())
    lo, hi = wilson(n_ok, len(gold))
    print(f"| Jev alone | {accuracy(jev_alone, gold):.1f}% [{lo:.1f}, {hi:.1f}] | 0% | USD {jev_cost:.2f} | {timing(list(jev_ms.values()))} | | |")
    for (name, cascade, alone, cost, ms, llm_cost, llm_ms), pl, pj in zip(rows, p_llm, p_jev):
        for label, pred, c, t, extra in (
            (f"{name} alone", alone, llm_cost, llm_ms, "| |"),
            (f"Jev, then {name}", cascade, cost, ms, f"| {pl:.2g} | {pj:.2g} |"),
        ):
            ok = sum(pred[i] == g for i, g in gold.items())
            lo, hi = wilson(ok, len(gold))
            sent = "100%" if pred is alone else f"{100 - len(sure) / 10:.1f}%"
            print(f"| {label} | {ok / 10:.1f}% [{lo:.1f}, {hi:.1f}] | {sent} | USD {c:.2f} | {timing(t)} {extra}")
    print()


def check4_sweep(gold: dict) -> None:
    print("Exploratory, not preregistered: other bands (accuracy of the cascade, share sent to the LLM)\n")
    jev = records("test-v2", "jev-1.13")
    p_hall = {i: r["probabilities"]["1"] for i, r in jev.items()}
    alone = {spec: labels(records("test-llm-authors-question", spec)) for spec in LLMS}
    print("| Band | Sent to LLM | " + " | ".join(LLMS.values()) + " |")
    print("|---|---|" + "---|" * len(LLMS))
    for band in (0.05, 0.1, 0.15, 0.2, 0.25, 0.3):
        sure = {i for i, p in p_hall.items() if p <= band or p >= 1 - band}
        accs = []
        for spec in LLMS:
            pred = {i: ("1" if p_hall[i] >= 0.5 else "0") if i in sure else alone[spec][i] for i in gold}
            accs.append(f"{accuracy(pred, gold):.1f}%")
        print(f"| {band:.2f} / {1 - band:.2f} | {100 - len(sure) / 10:.1f}% | " + " | ".join(accs) + " |")
    print()


def main() -> None:
    # Not splitlines(): it also breaks on U+2028 and friends, which occur inside abstracts.
    items = [json.loads(line) for line in ITEMS.read_text().split("\n") if line.strip()]
    gold = {item["id"]: item["gold"] for item in items}
    for name, fn in (("test-nosource", check1), ("test-llm-authors-question", check2)):
        if (RUNS / name).is_dir():
            fn(gold)
    if (RUNS / "timing-interleaved").is_dir():
        check3()
    if (RUNS / "test-llm-authors-question").is_dir():
        check4(gold)
        check4_sweep(gold)


if __name__ == "__main__":
    main()
