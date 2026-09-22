# /// script
# requires-python = ">=3.10"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Score a run_bench.py run directory and write the report.

Writes into the run directory:
  summary.md       headline table, slices, paired tests, probability quality
  predictions.csv  one row per item, one column group per model
  results.xlsx     the same, as a spreadsheet with an accuracy chart (--xlsx)

The task and items files come from the run's meta.json. When the dataset ships
published predictions for the same items (datasets/<name>/data/published/) and
the run used the test split, they are added as extra columns, marked
"published". Their accuracy is comparable item by item. Their latency was
measured by the publisher on other infrastructure, and their cost is unknown
unless you pass --price.

Errors (refusals, exhausted retries, out-of-set labels) count as wrong answers:
a production system that fails to answer has not answered correctly. Items a
model never ran are excluded from that model's numbers and flagged.

Usage:
  uv run score.py runs/medhallu/test --xlsx
  uv run score.py runs/medhallu/dev --threshold 0.6      # re-label Jev from P(positive)
  uv run score.py runs/icd10/test --headline lang=en,kind=clinical
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from common import DATASETS_DIR, Task, item_text, label_name, load_items

# Fallback prices in USD per 1M tokens (input, output), used only for records
# without OpenRouter's usage.cost (e.g. Jev called directly). Override with
# --price SPEC=IN,OUT. Source: docs.typesafe.ai/models, 2026-09-21.
PRICES: dict[str, tuple[float, float]] = {
    "jev": (0.042, 0.0),
    "stringmatch": (0.0, 0.0),
}
CONFIDENCE_THRESHOLDS = (0.0, 0.5, 0.7, 0.9)


@dataclass
class ModelRun:
    spec: str
    published: bool = False  # someone else's predictions for the same items
    records: dict[str, dict] = field(default_factory=dict)  # item id -> repeat-0 record
    repeats: dict[str, list[str | None]] = field(default_factory=lambda: defaultdict(list))

    @property
    def is_jev(self) -> bool:
        return self.spec.startswith(("jev", "typesafe/", "~typesafe/"))

    def correct(self, item: dict) -> bool | None:
        rec = self.records.get(item["id"])
        if rec is None:
            return None
        return rec.get("error") is None and rec.get("label") == item["gold"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


def macro_f1(pairs: list[tuple[str, str | None]]) -> float:
    labels = {gold for gold, _ in pairs}
    scores = []
    for label in labels:
        tp = sum(1 for g, p in pairs if g == label and p == label)
        fp = sum(1 for g, p in pairs if g != label and p == label)
        fn = sum(1 for g, p in pairs if g == label and p != label)
        denom = 2 * tp + fp + fn
        scores.append(2 * tp / denom if denom else 0.0)
    return statistics.fmean(scores) if scores else math.nan


def percentile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    idx = (len(ordered) - 1) * q
    lo, hi = math.floor(idx), math.ceil(idx)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (idx - lo)


def price_for(spec: str, overrides: dict[str, tuple[float, float]]) -> tuple[float, float] | None:
    if spec in overrides:
        return overrides[spec]
    base = spec.split("@")[0]
    if base in overrides:
        return overrides[base]
    if base.startswith(("jev", "typesafe/", "~typesafe/")):
        return PRICES["jev"]
    return PRICES.get(base)


def load_runs(run_dir: Path, task_fp: str | None, published: bool = False) -> list[ModelRun]:
    """task_fp None skips the prompt check: published runs used their publisher's prompt."""
    runs = []
    for path in sorted(run_dir.glob("*.jsonl")):
        run: ModelRun | None = None
        stale = 0
        for line in filter(None, path.read_text().split("\n")):
            rec = json.loads(line)
            if task_fp and rec.get("task_fp") != task_fp:
                stale += 1
                continue
            run = run or ModelRun(rec["spec"], published=published)
            if rec["repeat"] == 0:
                prev = run.records.get(rec["id"])
                # A later success replaces an earlier error; never the other way round.
                if prev is None or prev.get("error") is not None or rec.get("error") is None:
                    run.records[rec["id"]] = rec
            if rec.get("error") is None:
                run.repeats[rec["id"]].append(rec.get("label"))
        if stale:
            print(f"warning: skipped {stale} records in {path.name} made with a different task")
        if run:
            runs.append(run)
    return runs


def relabel(run: ModelRun, task: Task, threshold: float) -> None:
    """Re-derive binary labels from the stored P(positive), so a threshold needs no rerun."""
    for rec in run.records.values():
        probs = rec.get("probabilities")
        if rec.get("error") is None and probs and task.positive in probs:
            rec["label"] = task.positive if probs[task.positive] >= threshold else task.negative


def slices(items: list[dict], task: Task) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"all": items}
    for key in task.slice_fields:
        values = sorted({str(it[key]) for it in items if it.get(key) is not None})
        if len(values) > 1:
            for v in values:
                out[f"{key}={v}"] = [it for it in items if str(it.get(key)) == v]
    if len(task.slice_cross) == 2 and all(all(k in it for k in task.slice_cross) for it in items):
        a, b = task.slice_cross
        for va in sorted({it[a] for it in items}):
            for vb in sorted({it[b] for it in items}):
                subset = [it for it in items if it[a] == va and it[b] == vb]
                if subset and len(subset) != len(items):
                    out[f"{va}/{vb}"] = subset
    return out


def auroc(scored: list[tuple[float, bool]]) -> float:
    """Probability that a random positive outranks a random negative (ties count half)."""
    pos = [s for s, is_pos in scored if is_pos]
    neg = [s for s, is_pos in scored if not is_pos]
    if not pos or not neg:
        return math.nan
    ordered = sorted(scored)
    rank_sum, i = 0.0, 0
    while i < len(ordered):
        j = i
        while j < len(ordered) and ordered[j][0] == ordered[i][0]:
            j += 1
        mid_rank = (i + 1 + j) / 2
        rank_sum += mid_rank * sum(1 for k in range(i, j) if ordered[k][1])
        i = j
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def binary_detail(run: ModelRun, items: list[dict], task: Task) -> dict:
    scored = [it for it in items if it["id"] in run.records]
    cnt = Counter()
    ranked: list[tuple[float, bool]] = []
    for it in scored:
        rec = run.records[it["id"]]
        gold_pos = it["gold"] == task.positive
        pred_pos = rec.get("error") is None and rec.get("label") == task.positive
        cnt[(gold_pos, pred_pos)] += 1
        probs = rec.get("probabilities")
        if rec.get("error") is None and probs and task.positive in probs:
            ranked.append((probs[task.positive], gold_pos))
    tp, fn, fp, tn = cnt[(True, True)], cnt[(True, False)], cnt[(False, True)], cnt[(False, False)]
    recall = tp / (tp + fn) if tp + fn else math.nan
    specificity = tn / (tn + fp) if tn + fp else math.nan
    precision = tp / (tp + fp) if tp + fp else math.nan
    sweep = []
    if ranked:
        for t in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
            sweep.append((t, sum((p >= t) == is_pos for p, is_pos in ranked) / len(ranked)))
    return {
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "precision": precision, "recall": recall, "specificity": specificity,
        "f1": 2 * tp / (2 * tp + fp + fn) if tp else 0.0,
        "balanced": (recall + specificity) / 2,
        "auroc": auroc(ranked) if ranked else math.nan,
        "sweep": sweep,
    }


def holm(pvalues: list[float]) -> list[float]:
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adjusted, running = [0.0] * len(pvalues), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvalues) - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def fmt_pct(x: float) -> str:
    return "n/a" if math.isnan(x) else f"{100 * x:.1f}%"


def fmt_ms(x: float) -> str:
    return "n/a" if math.isnan(x) else f"{x:,.0f}"


def summarize(run: ModelRun, items: list[dict], prices: dict) -> dict:
    scored = [it for it in items if it["id"] in run.records]
    recs = [run.records[it["id"]] for it in scored]
    k = sum(bool(run.correct(it)) for it in scored)
    n = len(scored)
    lo, hi = wilson(k, n)
    ok_lat = [r["latency_ms"] for r in recs if r.get("error") is None and "latency_ms" in r]
    price = price_for(run.spec, prices)
    cost: float | None = 0.0
    for r in recs:
        if r.get("error") is not None:
            continue  # failed calls carry no reported cost
        if r.get("cost") is not None:
            cost += r["cost"]  # OpenRouter's actual charge
        elif price is not None:
            cost += ((r.get("input_tokens") or 0) * price[0] + (r.get("output_tokens") or 0) * price[1]) / 1e6
        else:
            cost = None
            break
    served = Counter(
        f"{r['served_model']} via {r['provider']}" if r.get("provider") else r["served_model"]
        for r in recs if r.get("served_model")
    )
    return {
        "spec": run.spec,
        "published": run.published,
        "is_jev": run.is_jev,
        "n": n,
        "missing": len(items) - n,
        "correct": k,
        "accuracy": k / n if n else math.nan,
        "ci": (lo, hi),
        "macro_f1": macro_f1([(it["gold"], run.records[it["id"]].get("label")) for it in scored]),
        "errors": sum(r.get("error") is not None for r in recs),
        "retried": sum((r.get("attempts") or 1) > 1 for r in recs),
        "p50_ms": percentile(ok_lat, 0.5),
        "p95_ms": percentile(ok_lat, 0.95),
        "cost": cost,
        "cost_per_1k": cost / n * 1000 if cost is not None and n else None,
        "served": dict(served),
        "mean_in_tokens": statistics.fmean([r.get("input_tokens") or 0 for r in recs]) if recs else math.nan,
        "mean_out_tokens": statistics.fmean([r.get("output_tokens") or 0 for r in recs]) if recs else math.nan,
    }


def jev_probability_quality(run: ModelRun, items: list[dict]) -> dict:
    rows = []
    for it in items:
        rec = run.records.get(it["id"])
        if rec and rec.get("error") is None and rec.get("probabilities"):
            rows.append((it, rec))
    if not rows:
        return {}
    nll, brier, top3 = [], [], 0
    bins: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    conf_right, conf_wrong = [], []
    for it, rec in rows:
        probs = rec["probabilities"]
        gold_p = probs.get(it["gold"], 0.0)
        nll.append(-math.log(max(gold_p, 1e-6)))
        brier.append(sum((p - (lab == it["gold"])) ** 2 for lab, p in probs.items()))
        ranked = sorted(probs, key=probs.get, reverse=True)
        top3 += it["gold"] in ranked[:3]
        top_p = probs[ranked[0]]
        right = rec["label"] == it["gold"]
        bins[min(int(top_p * 10), 9)].append((top_p, right))
        # A Noul has no confidence field: use the probability of the chosen label.
        rec["_conf"] = rec["confidence"] if rec.get("confidence") is not None else probs.get(rec["label"], top_p)
        (conf_right if right else conf_wrong).append(rec["_conf"])
    n = len(rows)
    ece = sum(
        len(b) / n * abs(statistics.fmean(p for p, _ in b) - statistics.fmean(r for _, r in b))
        for b in bins.values()
    )
    selective = []
    for t in CONFIDENCE_THRESHOLDS:
        kept = [(it, rec) for it, rec in rows if rec["_conf"] >= t]
        acc = sum(rec["label"] == it["gold"] for it, rec in kept) / len(kept) if kept else math.nan
        selective.append((t, len(kept) / n, acc, len(kept)))
    return {
        "n": n,
        "top3": top3 / n,
        "nll": statistics.fmean(nll),
        "brier": statistics.fmean(brier),
        "ece": ece,
        "bins": sorted((b, len(v), statistics.fmean(p for p, _ in v), statistics.fmean(r for _, r in v))
                       for b, v in bins.items()),
        "conf_right": statistics.fmean(conf_right) if conf_right else math.nan,
        "conf_wrong": statistics.fmean(conf_wrong) if conf_wrong else math.nan,
        "selective": selective,
    }


def write_markdown(path: Path, ctx: dict) -> None:
    items, runs, heads, ref, task = ctx["items"], ctx["runs"], ctx["heads"], ctx["ref"], ctx["task"]
    head_items = ctx["head_items"]
    name = lambda h: h["spec"] + (" †" if h["published"] else "")  # noqa: E731
    lines = [
        f"# Benchmark: {task.name}",
        "",
        f"- Source: `{task.source}`",
        f"- Items: {len(items)} | run dir: `{ctx['run_dir']}`",
        f"- Headline set: {ctx['headline_desc']} (n={len(head_items)})",
        "- Served models: "
        + "; ".join(f"{h['spec']} -> {', '.join(h['served']) or 'n/a'}" for h in heads if not h["published"]),
    ]
    if ctx["threshold"] is not None:
        lines.append(f"- Labels for runs with probabilities re-derived at P({task.positive}) >= {ctx['threshold']}")
    lines += [
        "",
        "## Headline",
        "",
        "| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for h in heads:
        lo, hi = h["ci"]
        cost = "not reported" if h["cost_per_1k"] is None else f"${h['cost_per_1k']:.4f}"
        info = ctx["estimated"].get(h["spec"])
        if info and h["cost_per_1k"] is not None:
            cost = f"{'>= ' if info['reasoning_model'] else ''}${h['cost_per_1k']:.2f} est."
        out_tokens = "n/a" if h["is_jev"] else f"{h['mean_out_tokens']:.0f}"  # Jev bills input only
        lines.append(
            f"| {name(h)} | {h['n']} | {fmt_pct(h['accuracy'])} [{fmt_pct(lo)}, {fmt_pct(hi)}] "
            f"| {h['macro_f1']:.3f} | {h['errors']} | {fmt_ms(h['p50_ms'])} | {fmt_ms(h['p95_ms'])} "
            f"| {h['mean_in_tokens']:.0f} / {out_tokens} | {cost} |"
        )
    if any(h["published"] for h in heads):
        lines += [
            "",
            f"† Published by {ctx['published_source']}, not run here. Same items, scored the same way, "
            "so accuracy is comparable. The prompt was the publisher's. Latency was measured on the "
            "publisher's infrastructure and is not comparable with latency measured here. Output "
            "token counts exclude hidden reasoning tokens.",
        ]
        if ctx["estimated"]:
            lines += [
                "",
                "Costs marked est. are not charges anyone reported: they are the published token counts "
                "times LiteLLM list prices (`published_prices.json` names the key and sheet version per "
                "model). For reasoning models (>=) this is a floor, because hidden reasoning tokens are "
                "billed as output but missing from the published counts.",
            ]
    missing = [h for h in heads if h["missing"]]
    if missing:
        lines += ["", "Missing items (never run): " + ", ".join(f"{h['spec']}: {h['missing']}" for h in missing)]
    n = len(head_items)
    half = 1.96 * math.sqrt(0.25 / n) if n else math.nan
    lines += [
        "",
        f"With n = {n}, a 95% interval is up to about +/-{100 * half:.0f} points wide. "
        "Treat gaps smaller than that as noise unless the paired test below says otherwise.",
    ]

    if ctx["binary"]:
        lines += [
            "",
            f"## Binary detail (positive = {task.positive}: {label_name(task.labels[task.positive])})",
            "",
            "| Model | Balanced acc | Precision | Recall | F1 | AUROC | TP / FN / FP / TN |",
            "|---|---|---|---|---|---|---|",
        ]
        for h in heads:
            d = ctx["binary"][h["spec"]]
            au = "n/a" if math.isnan(d["auroc"]) else f"{d['auroc']:.3f}"
            lines.append(
                f"| {name(h)} | {fmt_pct(d['balanced'])} | {fmt_pct(d['precision'])} | {fmt_pct(d['recall'])} "
                f"| {d['f1']:.3f} | {au} | {d['tp']} / {d['fn']} / {d['fp']} / {d['tn']} |"
            )
        lines += ["", "AUROC needs probabilities, which only Jev returns."]
        for h in heads:
            sweep = ctx["binary"][h["spec"]]["sweep"]
            if sweep:
                lines += [
                    "",
                    f"Threshold sweep for {h['spec']} (accuracy when P({task.positive}) >= t). "
                    "Pick a threshold on dev only, then apply it to test with `--threshold`.",
                    "",
                    "| t | " + " | ".join(f"{t:.1f}" for t, _ in sweep) + " |",
                    "|---|" + "---|" * len(sweep),
                    "| accuracy | " + " | ".join(fmt_pct(a) for _, a in sweep) + " |",
                ]

    sl = ctx["slices"]
    if len(sl) > 1:
        lines += ["", "## Accuracy by slice", ""]
        lines.append("| Model | " + " | ".join(f"{name} (n={len(s)})" for name, s in sl.items()) + " |")
        lines.append("|---|" + "---|" * len(sl))
        for run, h in zip(runs, heads):
            cells = []
            for subset in sl.values():
                scored = [it for it in subset if it["id"] in run.records]
                k = sum(bool(run.correct(it)) for it in scored)
                cells.append(fmt_pct(k / len(scored)) if scored else "n/a")
            lines.append(f"| {name(h)} | " + " | ".join(cells) + " |")

    if ref and len(runs) > 1:
        rows = []
        for run, h in zip(runs, heads):
            if run is ref:
                continue
            both = [it for it in head_items if it["id"] in run.records and it["id"] in ref.records]
            cnt = Counter((bool(ref.correct(it)), bool(run.correct(it))) for it in both)
            b, c, m = cnt[(True, False)], cnt[(False, True)], len(both)
            diff = (c - b) / m if m else math.nan
            se = math.sqrt(max(b + c - (c - b) ** 2 / m, 0.0)) / m if m else math.nan
            rows.append((name(h), cnt, b, c, diff, se, mcnemar_exact(b, c)))
        adjusted = holm([r[-1] for r in rows])
        lines += [
            "",
            f"## Paired comparison against {ref.spec}",
            "",
            "Same items, scored item by item, on the headline set. The exact McNemar test uses only the "
            "items where the two models disagree. Holm p corrects for testing several models against one "
            "reference. The difference is model minus reference: an interval that excludes 0 is a real "
            "gap, and an interval that includes 0 only shows equivalence as tightly as it is narrow.",
            "",
            "| Model | Both right | Only reference right | Only model right | Both wrong "
            "| Accuracy difference [95% CI] | McNemar p | Holm p |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for (label, cnt, b, c, diff, se, pval), padj in zip(rows, adjusted):
            lines.append(
                f"| {label} | {cnt[(True, True)]} | {b} | {c} | {cnt[(False, False)]} "
                f"| {100 * diff:+.1f} [{100 * (diff - 1.96 * se):+.1f}, {100 * (diff + 1.96 * se):+.1f}] "
                f"| {pval:.3f} | {padj:.3f} |"
            )

    for spec, q in ctx["quality"].items():
        if not q:
            continue
        lines += [
            "",
            f"## {spec}: probability quality",
            "",
            f"Top-3 accuracy {fmt_pct(q['top3'])} | NLL {q['nll']:.3f} | Brier {q['brier']:.3f} | "
            f"ECE (10 bins, top probability) {q['ece']:.3f} | mean confidence when right "
            f"{q['conf_right']:.2f}, when wrong {q['conf_wrong']:.2f} (n={q['n']})",
            "",
            "Reliability by bin of the top probability. ECE is noisy when bins hold few items.",
            "",
            "| Bin | Items | Mean probability | Accuracy |",
            "|---|---|---|---|",
        ]
        for b, count, mean_p, acc in q["bins"]:
            lines.append(f"| {b / 10:.1f} to {(b + 1) / 10:.1f} | {count} | {mean_p:.2f} | {fmt_pct(acc)} |")
        lines += [
            "",
            "Selective accuracy: answer only when confidence >= threshold (for a Noul, the "
            "probability of the chosen label).",
            "",
            "| Threshold | Coverage | Accuracy on covered | Items kept |",
            "|---|---|---|---|",
        ]
        for t, cov, acc, kept in q["selective"]:
            lines.append(f"| {t:.1f} | {fmt_pct(cov)} | {fmt_pct(acc)} | {kept} |")

    noisy = {spec: agree for spec, agree in ctx["consistency"].items() if agree is not None}
    if noisy:
        lines += ["", "## Repeat consistency", ""]
        for spec, (agree, total) in noisy.items():
            lines.append(f"- {spec}: identical label on every repeat for {agree}/{total} items")

    retried = {h["spec"]: h["retried"] for h in heads if h["retried"]}
    unknown = [h["spec"] for h in heads if h["cost"] is None and not h["published"]]
    lines += [
        "",
        "## Notes",
        "",
        "- Errors count as wrong. Latency percentiles use successful calls only and time the "
        "final attempt, after an untimed warm-up call per model.",
        "- Latency depends on concurrency, network path and time of day. Quote numbers from a "
        "`--concurrency 1` run, from the same machine, close together in time.",
        "- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, "
        "otherwise list prices applied to token counts. LLM output tokens include reasoning. "
        "Failed calls are not counted.",
    ]
    if retried:
        lines.append("- Items that needed more than one attempt: "
                     + ", ".join(f"{spec}: {k}" for spec, k in retried.items()) + ".")
    if unknown:
        lines.append(f"- No cost reported or price known for: {', '.join(unknown)}. Pass --price SPEC=IN,OUT.")
    path.write_text("\n".join(lines) + "\n")


def write_csv(path: Path, items: list[dict], runs: list[ModelRun], labels: dict) -> list[list]:
    header = ["id", "lang", "kind", "gold", "gold_name", "text"]
    for run in runs:
        header += [f"{run.spec} pred", f"{run.spec} correct", f"{run.spec} confidence",
                   f"{run.spec} latency_ms", f"{run.spec} error"]
    rows = [header]
    for it in items:
        row = [it["id"], it.get("lang", ""), it.get("kind", ""), it["gold"],
               labels.get(it["gold"], ""), item_text(it)]
        for run in runs:
            rec = run.records.get(it["id"])
            if rec is None:
                row += ["", "", "", "", "not run"]
                continue
            row += [
                rec.get("label") or "",
                int(bool(run.correct(it))),
                "" if rec.get("confidence") is None else round(rec["confidence"], 4),
                round(rec.get("latency_ms", 0)),
                rec.get("error") or "",
            ]
        rows.append(row)
    with path.open("w", newline="") as f:
        csv.writer(f).writerows(rows)
    return rows


def write_xlsx(path: Path, heads: list[dict], rows: list[list], runs: list[ModelRun]) -> None:
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, Reference
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    cols = ["Model", "n", "Accuracy", "CI low", "CI high", "Macro-F1", "Errors",
            "p50 latency (ms)", "p95 latency (ms)", "Cost per 1k items (USD)"]
    ws.append(cols)
    for h in heads:
        ws.append([
            h["spec"], h["n"], round(h["accuracy"], 4), round(h["ci"][0], 4), round(h["ci"][1], 4),
            round(h["macro_f1"], 4), h["errors"],
            None if math.isnan(h["p50_ms"]) else round(h["p50_ms"]),
            None if math.isnan(h["p95_ms"]) else round(h["p95_ms"]),
            None if h["cost_per_1k"] is None else round(h["cost_per_1k"], 6),
        ])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in ws.iter_rows(min_row=2, min_col=3, max_col=6):
        for cell in row:
            cell.number_format = "0.0%" if cell.column <= 5 else "0.000"
    chart = BarChart()
    chart.title = "Accuracy by model"
    chart.y_axis.title = "Accuracy"
    chart.y_axis.scaling.min = 0
    chart.y_axis.scaling.max = 1
    chart.legend = None
    chart.add_data(Reference(ws, min_col=3, min_row=1, max_row=len(heads) + 1), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=len(heads) + 1))
    ws.add_chart(chart, f"A{len(heads) + 4}")

    preds = wb.create_sheet("Predictions")
    for i, row in enumerate(rows):
        if i == 0:
            preds.append(row)
            continue
        out = list(row)
        for j in range(len(runs)):
            idx = 6 + j * 5 + 1  # the "correct" column of model j
            out[idx] = "✓" if row[idx] == 1 else "✗"
        preds.append(out)
    for cell in preds[1]:
        cell.font = Font(bold=True)
    preds.freeze_panes = "G2"
    wb.save(path)


def parse_filter(spec: str) -> dict[str, str]:
    return dict(part.split("=", 1) for part in spec.split(",") if part)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--task", type=Path, help="default: the task recorded in the run's meta.json")
    parser.add_argument("--items", type=Path, help="default: the items recorded in the run's meta.json")
    parser.add_argument("--ref", help="model spec for paired tests (default: first Jev run)")
    parser.add_argument("--headline", metavar="FIELD=VALUE[,FIELD=VALUE]",
                        help="items that drive the headline, paired and probability sections "
                             "(default: task.json 'headline', else all items)")
    parser.add_argument("--threshold", type=float,
                        help="binary tasks: re-label runs that have probabilities at P(positive) >= T")
    parser.add_argument("--published", type=Path, help="directory of published predictions to add as columns")
    parser.add_argument("--no-published", action="store_true")
    parser.add_argument("--price", action="append", default=[], metavar="SPEC=IN,OUT",
                        help="USD per 1M input,output tokens for records without a reported cost")
    parser.add_argument("--xlsx", action="store_true", help="also write results.xlsx")
    args = parser.parse_args()

    meta_path = args.run_dir / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    task_path = args.task or (Path(meta["task"]) if meta.get("task") else None)
    items_path = args.items or (Path(meta["items"]) if meta.get("items") else None)
    if not (task_path and items_path):
        raise SystemExit(f"no meta.json in {args.run_dir}: pass --task and --items")

    task = Task.load(task_path)
    items = load_items(items_path)
    runs = load_runs(args.run_dir, task.fingerprint)
    if not runs:
        raise SystemExit(f"no results for this task in {args.run_dir}")
    ran_ids = set().union(*(r.records for r in runs))
    items = [it for it in items if it["id"] in ran_ids]  # respect --only/--limit used at run time

    published_dir = args.published
    if published_dir is None and meta.get("dataset") and meta.get("split") in (None, "test"):
        published_dir = DATASETS_DIR / meta["dataset"] / "data" / "published"
    if published_dir and published_dir.is_dir() and not args.no_published:
        runs += load_runs(published_dir, None, published=True)
    # Jev first, then models run here, then published columns, each by accuracy.
    accuracy = lambda r: sum(bool(r.correct(it)) for it in items)  # noqa: E731
    runs.sort(key=lambda r: (not r.is_jev, r.published, -accuracy(r), r.spec))

    if args.threshold is not None:
        if not task.is_binary:
            raise SystemExit("--threshold needs a binary task")
        for run in runs:
            relabel(run, task, args.threshold)

    headline = parse_filter(args.headline or task.raw.get("headline", ""))
    head_items = [it for it in items if all(str(it.get(k)) == v for k, v in headline.items())]
    if not head_items:
        raise SystemExit(f"no items match the headline filter {headline}")

    prices = {}
    for spec_price in args.price:
        spec, _, pair = spec_price.partition("=")
        tin, tout = (float(x) for x in pair.split(","))
        prices[spec] = (tin, tout)

    # List prices for published columns (e.g. datasets/medhallu/prices.py). --price wins.
    estimated: dict[str, dict] = {}
    price_file = published_dir.parent / "published_prices.json" if published_dir else None
    if price_file and price_file.exists():
        for model, info in json.loads(price_file.read_text()).items():
            for run in runs:
                if run.published and run.spec.endswith("/" + model) and run.spec not in prices:
                    prices[run.spec] = (info["input_per_m"], info["output_per_m"])
                    estimated[run.spec] = info

    ref = next((r for r in runs if r.spec == args.ref), None) if args.ref else None
    ref = ref or next((r for r in runs if r.is_jev), runs[0])
    consistency = {}
    for run in runs:
        multi = {i: labs for i, labs in run.repeats.items() if len(labs) > 1}
        consistency[run.spec] = (
            (sum(len(set(l)) == 1 for l in multi.values()), len(multi)) if multi else None
        )

    heads = [summarize(r, head_items, prices) for r in runs]
    ctx = {
        "task": task,
        "run_dir": str(args.run_dir),
        "items": items,
        "head_items": head_items,
        "headline_desc": ", ".join(f"{k}={v}" for k, v in headline.items()) or "all items",
        "threshold": args.threshold,
        "published_source": task.raw.get("published_source", "a third party"),
        "estimated": estimated,
        "runs": runs,
        "heads": heads,
        "ref": ref,
        "slices": slices(items, task),
        "binary": {r.spec: binary_detail(r, head_items, task) for r in runs} if task.is_binary else {},
        "quality": {r.spec: jev_probability_quality(r, head_items) for r in runs if r.is_jev},
        "consistency": consistency,
    }
    write_markdown(args.run_dir / "summary.md", ctx)
    label_names = {label: label_name(desc) for label, desc in task.labels.items()}
    rows = write_csv(args.run_dir / "predictions.csv", items, runs, label_names)
    if args.xlsx:
        write_xlsx(args.run_dir / "results.xlsx", heads, rows, runs)
    print((args.run_dir / "summary.md").read_text())


if __name__ == "__main__":
    main()
