# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Reliability of Jev's probability on the MedHallu test split (run 2 question).

Reads the run file only; calls no model. Threshold-free: bins Jev's P(hallucinated)
and compares each bin's mean probability with the share of items actually hallucinated.
Exploratory, not preregistered. Run from bench/:
  uv run datasets/medhallu/calibration.py
Writes runs/medhallu/test-v2/calibration.png and calibration.md.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BENCH = Path(__file__).resolve().parents[2]
RUN = BENCH / "runs" / "medhallu" / "test-v2" / "jev-1.13.jsonl"
ITEMS = BENCH / "datasets" / "medhallu" / "data" / "items.test.jsonl"
OUT = RUN.parent
BINS = 10

# Reference palette of the dataviz method, light mode.
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = "#2a78d6"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def load() -> list[tuple[float, bool]]:
    # split("\n"), not splitlines(): abstracts contain Unicode line separators.
    lines = [line for line in ITEMS.read_text().split("\n") if line.strip()]
    gold = {d["id"]: d["gold"] for d in map(json.loads, lines)}
    rows = []
    for line in RUN.read_text().split("\n"):
        r = json.loads(line) if line.strip() else None
        if r and r.get("repeat", 0) == 0 and r.get("error") is None:
            rows.append((r["nouls"]["authors_reject"], gold[r["id"]] == "1"))
    return rows


def reliability(rows: list[tuple[float, bool]]) -> list[dict]:
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(BINS)]
    for p, y in rows:
        bins[min(int(p * BINS), BINS - 1)].append((p, y))
    out = []
    for i, b in enumerate(bins):
        if not b:
            continue
        k = sum(y for _, y in b)
        lo, hi = wilson(k, len(b))
        out.append({"lo_edge": i / BINS, "n": len(b), "mean_p": sum(p for p, _ in b) / len(b),
                    "rate": k / len(b), "ci_lo": lo, "ci_hi": hi})
    return out


def write_md(rows: list[tuple[float, bool]], table: list[dict]) -> None:
    n = len(rows)
    ece = sum(t["n"] / n * abs(t["mean_p"] - t["rate"]) for t in table)
    brier = sum((p - y) ** 2 for p, y in rows) / n
    lines = [
        "# Jev 1.13 reliability on MedHallu test (run 2 question)",
        "",
        f"Threshold-free: Jev's P(hallucinated) against the share actually hallucinated. n={n}, "
        f"base rate {sum(y for _, y in rows) / n:.1%}. Brier {brier:.4f}, ECE ({BINS} bins) {ece:.3f}. "
        "Exploratory, not preregistered. 95% Wilson intervals.",
        "",
        "| Jev's P(hallucinated) | Items | Mean P | Actually hallucinated | 95% CI |",
        "|---|---|---|---|---|",
    ]
    for t in table:
        lines.append(f"| {t['lo_edge']:.1f} to {t['lo_edge'] + 1 / BINS:.1f} | {t['n']} | {t['mean_p']:.2f} | "
                     f"{t['rate']:.1%} | {t['ci_lo']:.1%} to {t['ci_hi']:.1%} |")
    (OUT / "calibration.md").write_text("\n".join(lines) + "\n")


def chart(table: list[dict]) -> None:
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 11, "text.color": INK,
                         "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": MUTED})
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(8, 7.2), sharex=True, facecolor=SURFACE,
                                 gridspec_kw={"height_ratios": [3.2, 1], "hspace": 0.12})
    for a in (ax, bx):
        a.set_facecolor(SURFACE)
        for side in ("top", "right", "left"):
            a.spines[side].set_visible(False)
        a.spines["bottom"].set_color(AXIS)
        a.tick_params(length=0)
        a.grid(axis="y", color=GRID, linewidth=0.8)
        a.set_axisbelow(True)

    x = [t["mean_p"] for t in table]
    y = [t["rate"] for t in table]
    err = [[t["rate"] - t["ci_lo"] for t in table], [t["ci_hi"] - t["rate"] for t in table]]
    ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.text(0.80, 0.72, "Dashed: where the dots\nwould sit if the probability\nwere a literal frequency",
            color=MUTED, fontsize=9.5, ha="left", va="top")
    ax.errorbar(x, y, yerr=err, fmt="none", ecolor=SERIES, alpha=0.35, linewidth=2, capsize=0)
    ax.plot(x, y, color=SERIES, linewidth=2, marker="o", markersize=8,
            markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
    for t, xy_text, ha in ((table[1], (0.02, 0.52), "left"), (table[8], (0.80, 0.97), "right")):
        ax.annotate(f"Jev says {t['mean_p']:.0%}:\n{t['rate']:.0%} actually hallucinated",
                    (t["mean_p"], t["rate"]), xytext=xy_text, fontsize=9.5, color=INK_2, ha=ha, va="bottom",
                    arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8, "shrinkB": 6})
    ax.set_ylim(-0.03, 1.05)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_ylabel("Share actually hallucinated")
    fig.suptitle("Jev's probability sorts answers well, but is not a literal frequency",
                 x=0.07, y=0.975, ha="left", fontsize=14, fontweight="bold", color=INK)
    fig.text(0.07, 0.925, "MedHallu test, 1,000 items, Jev 1.13. Items grouped by Jev's probability; "
             "bars show 95% intervals.", fontsize=10, color=INK_2, ha="left")

    bx.bar([t["lo_edge"] + 0.05 for t in table], [t["n"] for t in table], width=0.1 - 0.012,
           color=SERIES, alpha=0.55)
    for t in table:
        bx.text(t["lo_edge"] + 0.05, t["n"] + 8, str(t["n"]), ha="center", va="bottom", fontsize=8.5, color=INK_2)
    bx.set_ylim(0, max(t["n"] for t in table) * 1.3)
    bx.set_yticks([])
    bx.set_ylabel("Items")
    bx.set_xlim(0, 1)
    bx.set_xticks([0, 0.25, 0.5, 0.75, 1])
    bx.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    bx.set_xlabel("Jev's probability that the answer is hallucinated")
    fig.savefig(OUT / "calibration.png", dpi=200, facecolor=SURFACE, bbox_inches="tight")


if __name__ == "__main__":
    rows = load()
    table = reliability(rows)
    write_md(rows, table)
    chart(table)
    print((OUT / "calibration.md").read_text())
