# jev-medhallu-benchmark

Benchmarks of TypeSafe's Jev 1.13, a "System One" model that answers typed
questions about text with probabilities instead of generating text, against
LLMs on medical tasks. Every model, Jev included, is called through OpenRouter,
so one key pays for everything and every latency includes the same gateway hop.

The main study adds Jev, four current fast LLMs and two open models on fast
inference hardware, to Stanford CRFM's
published MedHELM results on **MedHallu**: given a PubMed abstract, a question
and a proposed answer, is the answer hallucinated?

## MedHallu results (test split, 1,000 items)

Accuracy [95% CI] with two prompts, and time and cost from the timed run:

| Model | Jev's question | MedHELM-style prompt | Median time | 95th percentile | Cost per 1,000 checks |
|---|---|---|---|---|---|
| GPT-5.6 Luna, reasoning none | 95.1% [93.6, 96.3] | 92.9% [91.1, 94.3] | 1,142 ms | 1,764 ms | USD 0.15 |
| Gemini 3.5 Flash Lite | 95.0% [93.5, 96.2] | 93.5% [91.8, 94.9] | 536 ms | 696 ms | USD 0.23 |
| Gemini 3.8 Flash, reasoning minimal | 94.8% [93.2, 96.0] | 87.2% [85.0, 89.1] | 1,330 ms | 3,912 ms | USD 1.03 |
| **Jev 1.13** | **92.9%** [91.1, 94.3] | 90.3% [88.3, 92.0] | **204 ms** | **292 ms** | **USD 0.03** |
| Claude Haiku 4.5 | 92.4% [90.6, 93.9] | 92.0% [90.2, 93.5] | 680 ms | 1,095 ms | USD 0.96 |
| GPT-OSS 120b on Cerebras, reasoning low ‡ | 90.0% [88.0, 91.7] | | 236 ms | 1,096 ms | USD 0.27 |
| GPT-OSS 20b on Groq, reasoning low ‡ | 86.8% [84.6, 88.8] | | 388 ms | 778 ms | USD 0.07 |
| *Claude 3.5 Sonnet †, best of Stanford's 13* | | 92.6% [90.8, 94.1] | | | |
| *GPT-5 †* | | 90.5% [88.5, 92.2] | | | |

"Jev's question" is the one plain question chosen for Jev on dev data: "Would
the authors of the study described in `knowledge` say that `answer`
misrepresents their findings?" (Jev run 2, threshold 0.65). The MedHELM-style
prompt is Stanford's instructions and labels in this harness's format (Jev run
1, threshold 0.85); the † rows used Stanford's exact prompt. The ‡ rows (check 5)
were run with Jev's question only and timed on that run.

- **Accuracy.** Given the same question, GPT-5.6 Luna, Gemini 3.5 Flash Lite and
  Gemini 3.8 Flash are significantly more accurate than Jev, by about 2 points
  (exact McNemar, Holm p 0.012 to 0.016); Claude Haiku 4.5 is level. With the
  MedHELM-style prompt, Jev is significantly behind Flash Lite and Luna. Against
  Stanford's 13 published models, Jev run 2 is level with Claude 3.5 Sonnet and
  significantly ahead of 11, GPT-5 included.
- **Time and cost.** Against the four hosted LLMs, Jev is 2.6 to 6.5 times
  faster and 5 to 35 times cheaper per check. Re-timed in one alternating
  session, the medians were 228 ms for Jev and 703 to 1,460 ms for the LLMs
  (3.1 to 6.4 times). An open model on fast hardware closes the typical-time
  gap: GPT-OSS 120b on Cerebras matched Jev's median (238 ms against 233 ms in
  one session), but was 2.9 points less accurate, 9 times dearer, had a 95th
  percentile about three times Jev's, and left some requests hanging (check 5).
- **Probability.** Jev returns one (AUROC 0.974): on the 37% of items where it
  is at least 90% confident, it is 99.5% accurate. None of these four LLMs offer
  log-probabilities through OpenRouter. The probability sorts answers well but
  its numbers are not literal odds: of the answers it put near 14%, 2% were
  hallucinated, and of those near 65%, 43% were, so set cut-offs on your own data
  ([`test-v2/calibration.md`](bench/runs/medhallu/test-v2/calibration.md),
  exploratory).
- **Jev first, LLM for the rest.** On those 37% of items, all four LLMs gave
  the same answer as Jev. Letting Jev settle them and sending the rest to an
  LLM keeps the LLM's accuracy exactly with 37% fewer LLM calls (check 4 in
  `PREREGISTRATION.md`).

Read the numbers with these limits:

- **MedHallu does not only test source checking.** With the abstract removed,
  every model still scores 66% to 83% (the floor is 52%), from the wording of
  the answer or its own medical knowledge. The abstract adds 4 to 27 points.
- **Tuning.** Jev's question and threshold were chosen on 1,000 separate dev
  items. The LLMs were not tuned; they only got Jev's question as a second
  prompt, untried on dev for them.
- **Time.** Rows without † were timed from one machine through OpenRouter, one
  request at a time, and are comparable with each other; a same-session
  re-timing confirmed the gap. Stanford's timings come from their own
  deployments and are not shown.
- **Cost.** OpenRouter's billed cost per call. Estimates for the † rows are in
  the full summary.
- **Choices written in advance.** Every test run and every follow-up check was
  planned in [`PREREGISTRATION.md`](bench/datasets/medhallu/PREREGISTRATION.md)
  before it ran, and all results are reported there.
- **One task.** MedHallu's hallucinated answers were machine-generated.

Full tables: [`test-v2/summary.md`](bench/runs/medhallu/test-v2/summary.md)
(MedHELM-style prompt, with Stanford's 13 models),
[`test-llm-authors-question/summary.md`](bench/runs/medhallu/test-llm-authors-question/summary.md)
(Jev's question), and the follow-up checks with
`uv run datasets/medhallu/followup_checks.py`.

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
