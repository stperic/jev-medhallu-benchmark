# Run files

Every model answer behind every number in this repo. Each folder holds one
`<model>.jsonl` per model (one record per item: label, probabilities for Jev,
tokens, cost, latency, provider, OpenRouter request id), a `meta.json` (dataset,
split, items sha256, task fingerprint, code hashes, every invocation) and, where
scored, a `summary.md`.

Before publishing, absolute local paths in `meta.json` were made relative to
`bench/` and the host name was replaced with `redacted`. Nothing else was
edited.

`code_sha256` in `meta.json` records the harness version each run used. Jev
run 2, the four LLM rows and every run from the question search onward
(`test-v2`, the three follow-up checks, `dev-explore1`, `dev-explore2`, `dev2-*`,
`dev-*-smoke`, `icd10/full-v1`) match `run_bench.py` and `common.py` as committed. Earlier runs
(`test`, `test-repeat2`, `old-dev-sample/*`) used earlier working versions of
the harness, before this repo had version control; those versions were not
kept. `icd10/smoke` predates hash recording.

## MedHallu, test split (1,000 items)

| Folder | What it is |
|---|---|
| `medhallu/test` | **Jev run 1**: Jev asked a field-by-field mapping of MedHELM's LLM prompt (as a Noul, and as a Choice). 90.3% at threshold 0.85. |
| `medhallu/test-v2` | **Jev run 2**: Jev asked the question chosen on dev (92.9% at threshold 0.65), **plus four current fast LLMs** added on 2026-09-22: GPT-5.6 Luna (reasoning none), Gemini 3.8 Flash (reasoning minimal), Gemini 3.5 Flash Lite, Claude Haiku 4.5. |
| `medhallu/test-repeat2` | A 12-item repeat of Jev run 1, to check that Jev's answers are stable: probabilities moved by at most 0.03 (mean 0.006), no label changed. Same question as run 1, so no test information fed into run 2. |
| `medhallu/test-nosource` | Follow-up check 1: the test items with the abstract replaced by "Not provided." (`data/items.test-nosource.jsonl`, from `datasets/medhallu/ablate_source.py`), Jev and the four LLMs. Shows how much each score depends on the source. |
| `medhallu/test-llm-authors-question` | Follow-up check 2: the four LLMs asked Jev's run-2 question with Yes/No labels (`variants/llm-authors-question.task.json`). Scored with `--no-published`. |
| `medhallu/timing-interleaved` | Follow-up check 3: all five models re-timed on the first 200 test items in one session, 10 rounds of 20 with the model order rotated each round (hence 50 invocations in `meta.json`). |

The choices behind each test run and follow-up check were written down
beforehand in `datasets/medhallu/PREREGISTRATION.md`, which also reports the
results. `uv run datasets/medhallu/followup_checks.py` prints the follow-up
tables from these files.

`predictions.csv` and `results.xlsx` for `test` and `test-v2` are not committed,
because they embed Stanford MedHELM's per-item predictions, which this repo does
not re-host. Rebuild them (and the 13 Stanford columns) from `bench/`:

```bash
uv run datasets/medhallu/prepare.py        # downloads Stanford's published predictions
uv run score.py runs/medhallu/test-v2 --threshold 0.65 --ref jev-1.13 --xlsx
uv run score.py runs/medhallu/test --task datasets/medhallu/variants/test-run1.task.json \
  --threshold 0.85 --ref jev-1.13 --xlsx
```

## MedHallu, development data (tuning only)

| Folder | What it is |
|---|---|
| `medhallu/old-dev-sample/` | Runs on the **first** 500-item dev sample, later replaced (see the addendum in `PREREGISTRATION.md`). Holds `smoke`, `dev-v1`, `dev-v2` and `dev-v3-format-fixed`, which the preregistration cites as `runs/medhallu/dev-v1` and so on. Those items are no longer produced by `prepare.py`, so these runs cannot be re-scored; the `predictions.csv` files in `smoke`, `dev-v1` and `dev-v2` keep the items and answers. |
| `medhallu/dev-explore1` | Round 1 of choosing Jev's question: seven candidate questions in one request (`datasets/medhallu/variants/explore1.json`). |
| `medhallu/dev-explore2` | Round 2: six variations of the round-1 winner (`variants/explore2.json`). |
| `medhallu/dev2-confirm` | Confirmation of the choice on the disjoint `dev2` sample (`variants/confirm.json`). |
| `medhallu/dev2-final` | The chosen question alone on `dev2`. |
| `medhallu/dev-flagship-smoke` | 5 items: Claude Fable 5.1, GPT-6 Astra, Gemini 3.1 Pro, for latency and cost only. Rejected as too slow for an inline check. |
| `medhallu/dev-fast-smoke` | 20 items: fast models at default and low reasoning, for latency, cost and plumbing only. Used to pick the four LLM rows in `test-v2`. |

Re-score a dev run with its own task file, for example
`uv run score.py runs/medhallu/dev-explore1`.

## ICD-10 (smoke-level, 29 independent cases)

| Folder | What it is |
|---|---|
| `icd10/smoke` | First live test: 5 notes, Jev, Claude Opus 5 (low effort), string match. |
| `icd10/full-v1` | All 106 notes: Jev, Gemini 3.8 Flash, DeepSeek v4.1 Flash, string match. See `datasets/icd10/DATASET.md` for what this set can and cannot show. |
