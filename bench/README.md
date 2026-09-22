# Jev benchmark harness

One runner and one scorer, any number of datasets. Every model, Jev included,
is called through OpenRouter, so one key pays for everything and every latency
measured here includes the same gateway hop. How to call and design for Jev
lives in the project skill `.claude/skills/jev/`; this folder is only the
benchmark.

```
bench/
  run_bench.py   calls the models, writes runs/<dataset>/<split>/<model>.jsonl
  score.py       writes summary.md, predictions.csv and results.xlsx into the run folder
  common.py      task format and dataset paths, shared by both
  datasets/
    medhallu/    medical hallucination check, with 13 LLM columns published by Stanford MedHELM
    icd10/       ICD-10 coding of short clinical notes (smoke-level: 29 independent cases)
  runs/          every run behind the published numbers, indexed in runs/README.md
```

## Setup

- `uv`. Each script declares its own dependencies.
- `OPENROUTER_API_KEY` with credits, in `bench/.env` (git-ignored). Copy
  `.env.example` to `.env` and fill it in with an editor rather than with `echo`,
  so the key stays out of your shell history. Run everything from `bench/`
  with `uv run --env-file .env ...`. Scoring existing runs needs no key.

Jev on OpenRouter: model `jev-1.13` (served as `typesafe/jev-1.13-20260917`),
USD 0.042 per 1M input tokens, output free. LLMs you run yourself go through
chat completions with a strict JSON-schema `enum`, so they can only answer with
one of the task's labels, just like Jev.

## MedHallu: add a Jev column to Stanford's published results

The task: given a PubMed abstract, a question and an answer, is the answer
hallucinated? Stanford's MedHELM ran 13 LLMs on the same 1,000 items and
published every prediction, so only Jev needs running. See
`datasets/medhallu/DATASET.md` for what can and cannot be claimed.

```bash
cd bench

# 0. Run once after cloning. The test, dev and dev2 items are committed; this rebuilds
#    them byte for byte and downloads the 13 published columns, which are not re-hosted here.
uv run datasets/medhallu/prepare.py

# 1. Dev: tune here, as often as you like. About USD 0.02 per Jev pass.
#    jev-1.13 asks the task's question type (a Noul); @choice asks a 2-option Choice instead.
uv run --env-file .env run_bench.py --dataset medhallu --split dev \
  --models jev-1.13 jev-1.13@choice constant:1 --out runs/medhallu/dev-v1
uv run score.py runs/medhallu/dev-v1

# 2. Test: once, with the wording and threshold chosen on dev. About USD 0.03.
uv run --env-file .env run_bench.py --dataset medhallu --split test \
  --models jev-1.13 --concurrency 1
uv run score.py runs/medhallu/test --xlsx              # add --threshold T if dev picked one
```

- Results so far (2026-09-21), both recorded beforehand in
  `datasets/medhallu/PREREGISTRATION.md`: run 1 asked Jev a mapping of MedHELM's
  LLM prompt (`runs/medhallu/test`, 90.3% at threshold 0.85); run 2 asked the
  Jev-specific question now in `task.json` under `jev_questions`
  (`runs/medhallu/test-v2`, 92.9% at threshold 0.65). The test set is spent: do
  not tune against it again. Re-score with
  `uv run score.py runs/medhallu/test-v2 --threshold 0.65 --ref jev-1.13 --xlsx`, and run 1 with
  `uv run score.py runs/medhallu/test --task datasets/medhallu/variants/test-run1.task.json --threshold 0.85 --ref jev-1.13`.
- Four current fast LLMs were added to `runs/medhallu/test-v2` on 2026-09-22
  (plan in `PREREGISTRATION.md`, "Added LLM rows"): Gemini 3.5 Flash Lite 93.5%,
  GPT-5.6 Luna (reasoning none) 92.9%, Claude Haiku 4.5 92.0%, Gemini 3.8 Flash
  (reasoning minimal) 87.2%. The same re-score command above includes them.
- `jev_questions` in `task.json` (optional) replaces the main question for Jev
  only: one or more Nouls asked in a single request, combined by `jev_combine`
  (`mean`, `max` or logistic weights). Each answer is stored per item under
  `nouls`, so many candidate wordings can be compared on dev in one pass
  (see `datasets/medhallu/variants/explore1.json`).
- Changing the question or labels in `data/task.json` changes the task
  fingerprint, so use a new `--out` folder for each wording you try on dev
  (`dev-v1`, `dev-v2`, ...). Edit `INSTRUCTIONS` and `LABELS` in `prepare.py`
  as well, or a rebuild will overwrite your wording.
- `--threshold` is applied at scoring time from the stored probability, so
  trying thresholds costs nothing. The summary prints a sweep. Choose on dev.
- `uv run datasets/medhallu/prices.py` writes `data/published_prices.json` from
  LiteLLM's price sheet. With it, `score.py` shows an estimated cost for each
  published column (published tokens times list price, marked "est.", and ">="
  for reasoning models whose hidden reasoning tokens are not in the counts).
- The published columns are marked † and appear automatically when a run used
  the test split. `--no-published` hides them.
- To check that this harness reproduces a published number, run one cheap LLM
  yourself on test, for example `--models openai/gpt-4o-mini`, and compare it
  with its † column. Expect a small gap: the prompt here is not MedHELM's.

## ICD-10

```bash
uv run --env-file .env run_bench.py --dataset icd10 \
  --models jev-1.13 anthropic/claude-opus-5@low stringmatch --limit 5 --out runs/icd10/smoke2
uv run score.py runs/icd10/smoke2
```

The headline set is `lang=en,kind=clinical` (n=29), set in its `task.json`.
`datasets/icd10/DATASET.md` explains why this set can only show large gaps.

## Model specs

| Spec | Meaning |
|---|---|
| `jev-1.13` | Jev, asked the task's question type |
| `jev-1.13@noul`, `jev-1.13@choice` | Jev, forced to one question type (binary tasks) |
| `vendor/model` | Any OpenRouter chat model at its default reasoning |
| `vendor/model@low` | With reasoning effort `none|minimal|low|medium|high|xhigh|max` |
| `stringmatch` | No-model floor: the label whose name appears verbatim in the text |
| `constant:<label>` | No-model floor for yes/no tasks: always that label |

For latency numbers use `--concurrency 1` and pin LLM providers, for example
`--provider anthropic/claude-opus-5=anthropic`. Each model gets one untimed
warm-up call first (`--warmup`).

## Rules the harness enforces

- Interrupted runs resume: rerun the same command. Only transport failures
  (timeouts, 429, 5xx, no credits) are retried. A refusal, a truncated reply or
  an out-of-set label is that model's answer and counts as wrong.
- A run folder holds one task fingerprint (question, labels, question type,
  system prompt, prompt template). A different one is refused.
- `meta.json` records the dataset, split, items hash, code hashes, host,
  package versions and every invocation. It holds local paths and the host
  name: strip them before publishing runs, as done for `runs/` (see
  `runs/README.md`).
- Errors count as wrong. Accuracy comes with Wilson intervals; model pairs
  with exact McNemar, Holm-corrected, and a confidence interval on the paired
  accuracy difference.

## Adding a dataset

Create `datasets/<name>/prepare.py` that writes into `datasets/<name>/data/`:

- `task.json`:

  ```json
  {
    "name": "my-task",
    "source": "where the items came from, with a pinned revision",
    "type": "choice",
    "instructions": "The question, referring to state fields in backticks",
    "labels": {"KEY": "description that separates this option from the others"},
    "state_key": "note",
    "headline": "field=value",
    "slice_fields": ["field"]
  }
  ```

  For a yes/no task use `"type": "noul"`, exactly two labels, and
  `"positive": "<the label that means yes>"`. `headline`, `slice_fields` and
  `slice_cross` only affect scoring.
- `items.test.jsonl`, and `items.dev.jsonl` if you will tune anything. One
  JSON object per line: `id`, `gold`, either `text` (one string, sent under
  `state_key`) or `state` (an object with named fields), plus any slice fields.
- Optional `published/<model>.jsonl`: other people's predictions for the same
  test items, one record per item with `id`, `repeat: 0`, `spec`, `label`,
  `error`, and if known `latency_ms`, `input_tokens`, `output_tokens`. Set
  `published_source` in `task.json`. Verify in `prepare.py` that the accuracy
  you recompute matches the published figure, as the MedHallu script does.

Before trusting a new dataset, run the free floors on it
(`--models stringmatch constant:<label>`). If a floor scores near the models,
the dataset cannot show what a model adds. Write what you find in a
`DATASET.md` next to the script.
