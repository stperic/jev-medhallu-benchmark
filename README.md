# jev-medhallu-benchmark

Benchmarks of TypeSafe's Jev 1.13, a "System One" model that answers typed
questions about text with probabilities instead of generating text, against
LLMs on medical tasks. Every model, Jev included, is called through OpenRouter,
so one key pays for everything and every latency includes the same gateway hop.

The main study adds Jev, and four current fast LLMs, to Stanford CRFM's
published MedHELM results on **MedHallu**: given a PubMed abstract, a question
and a proposed answer, is the answer hallucinated?

## MedHallu results (test split, 1,000 items)

| Model | Accuracy [95% CI] | Median time | 95th percentile | Cost per 1,000 checks |
|---|---|---|---|---|
| Gemini 3.5 Flash Lite | 93.5% [91.8, 94.9] | 536 ms | 696 ms | USD 0.23 |
| **Jev 1.13, run 2** (question chosen on dev) | **92.9%** [91.1, 94.3] | **204 ms** | **292 ms** | **USD 0.03** |
| GPT-5.6 Luna, reasoning none | 92.9% [91.1, 94.3] | 1,142 ms | 1,764 ms | USD 0.15 |
| Claude Haiku 4.5 | 92.0% [90.2, 93.5] | 680 ms | 1,095 ms | USD 0.96 |
| Jev 1.13, run 1 (MedHELM's prompt, mapped) | 90.3% [88.3, 92.0] | 205 ms | 281 ms | USD 0.04 |
| Gemini 3.8 Flash, reasoning minimal | 87.2% [85.0, 89.1] | 1,330 ms | 3,912 ms | USD 1.03 |
| *Best of Stanford's 13 published LLMs:* Claude 3.5 Sonnet † | 92.6% [90.8, 94.1] | | | |
| *Gemini 2.0 Flash †* | 90.8% [88.8, 92.4] | | | |
| *GPT-5 †* | 90.5% [88.5, 92.2] | | | |

Compared item by item (exact McNemar, Holm-corrected), Jev run 2 is
statistically level with Gemini 3.5 Flash Lite, GPT-5.6 Luna, Claude Haiku 4.5
and Claude 3.5 Sonnet, and significantly more accurate than Gemini 3.8 Flash
and 11 of Stanford's 13 models, GPT-5 included. Gemini 2.0 Flash is
borderline (p 0.03 before the Holm correction, 0.13 after). Jev also returns a
probability (AUROC 0.974): on the 37% of items where it is at least 90%
confident, it is 99.5% accurate.

Read the numbers with these limits:

- **Tuning.** Jev's question and threshold were chosen on 1,000 separate dev
  items. The LLMs got one untuned zero-shot prompt (Stanford's for the † rows,
  a mapping of it for the four rows run here). Both Jev runs are reported.
- **Time.** Rows without † were timed from one machine through OpenRouter, one
  request at a time, on 2026-09-21 (Jev) and 2026-09-22 (the four LLMs), and are
  comparable with each other. Stanford's timings come from their own
  deployments and are not shown.
- **Cost.** OpenRouter's billed cost per call. Estimates for the † rows are in
  the full summary.
- **Choices written in advance.** Every test run was planned in
  [`PREREGISTRATION.md`](bench/datasets/medhallu/PREREGISTRATION.md) before it
  ran, including the choice of the four fast LLMs and their reasoning settings.
- **One task.** MedHallu's hallucinated answers were machine-generated.

Full table, slices and paired tests:
[`bench/runs/medhallu/test-v2/summary.md`](bench/runs/medhallu/test-v2/summary.md).

## Layout

```
bench/                 the benchmark harness (see bench/README.md)
  run_bench.py         calls the models, one JSONL of answers per model
  score.py             accuracy, intervals, paired tests, latency, cost
  datasets/medhallu/   MedHallu: prepare.py, DATASET.md, PREREGISTRATION.md, items
  datasets/icd10/      ICD-10 coding of short synthetic notes (smoke-level)
  runs/                every run behind the numbers (see bench/runs/README.md)
.claude/skills/jev/    a Claude Code skill on building with Jev (API, question design, evaluation)
```

## Reproduce

Needs [`uv`](https://docs.astral.sh/uv/). Each script declares its own
dependencies.

```bash
cd bench
uv run datasets/medhallu/prepare.py      # rebuilds the items, downloads Stanford's 13 published columns
uv run score.py runs/medhallu/test-v2 --threshold 0.65 --ref jev-1.13 --xlsx
```

Scoring needs no API key. To call models, copy `bench/.env.example` to
`bench/.env`, add an OpenRouter key and follow `bench/README.md`. Running Jev
on the 1,000 test items costs about USD 0.03.

## Data and licences

The code and documentation in this repo are MIT-licensed (see `LICENSE`). Data
keeps its own licence:

- **MedHallu** items (`bench/datasets/medhallu/data/items.*.jsonl`): MIT, from
  [UTAustin-AIHealth/MedHallu](https://huggingface.co/datasets/UTAustin-AIHealth/MedHallu),
  built on PubMedQA (MIT). Pandit et al., "MedHallu: A Comprehensive Benchmark
  for Detecting Medical Hallucinations in Large Language Models", 2025,
  arXiv:2502.14302.
- **Stanford CRFM MedHELM v4.0.0** per-item predictions: not re-hosted.
  `prepare.py` downloads them from Stanford's public results bucket, and the
  scored files that embed them are git-ignored. Aggregate figures in the
  summaries are Stanford's published results.
- **ICD-10 notes** (`bench/datasets/icd10/data/items.jsonl`): CC-BY-4.0, from
  [birgermoell/icd10-clinical-notes](https://huggingface.co/datasets/birgermoell/icd10-clinical-notes),
  synthetic notes with no patient data, reduced to one item per distinct note and
  tagged by `bench/datasets/icd10/prepare.py`.
- **Prices** in `published_prices.json` come from LiteLLM's model price sheet
  (MIT), with the key and sheet version recorded per model.
