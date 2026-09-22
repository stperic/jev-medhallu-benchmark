# MedHallu test run: choices fixed before the run

Written 2026-09-21, before any model was run on `items.test.jsonl`.

- **Primary result:** `jev-1.13`, asked as a Noul, with the question in
  `data/task.json` (fingerprint recorded in the run's `meta.json`). The question
  is a field-by-field mapping of MedHELM's own medhallu prompt, zero-shot like
  the original. See the comment above `INSTRUCTIONS` in `prepare.py`.
- **Threshold:** answer "hallucinated" when P(hallucinated) >= **0.85**. Chosen
  on dev (`runs/medhallu/dev-v2`, 500 items): accuracy is flat from 0.80 to 0.90
  (92.2%, 92.8%, 91.8%) and 0.85 is the middle of that plateau.
- **Also reported, not the headline:** the same run at the untuned default
  threshold 0.5, its AUROC, and `jev-1.13@choice` (same question as a 2-option
  Choice) at 0.85.
- **Metric:** accuracy on all 1,000 items, as MedHELM reports (`exact_match`),
  with a 95% Wilson interval, and paired exact McNemar tests against each
  published model, Holm-corrected.
- **One run.** Concurrency 1 for latency. No wording or threshold changes after
  seeing test results. If the run is repeated for any reason, say so in the post.

What was tried on dev before this: a first-draft wording (`dev-v1`, AUROC 0.962)
and this MedHELM-derived wording (`dev-v2`, AUROC 0.961). The second was chosen
because it follows the published prompt, not because it scored higher.

## Addendum, 2026-09-21, after the test run

A bug in `prepare.py` was found after the test run: dev items carried
`knowledge` as a JSON list of passages, while test items carried it as one
string with a passage per line. So the 0.85 threshold was chosen on a slightly
different input format than the test used. The script was fixed and now refuses
to write mixed formats. The test items did not change (same sha256,
`10e4a36157a9550e`), so the test result stands as run. Re-running the same
question on the corrected dev set (`runs/medhallu/dev-v3-format-fixed`) gives
AUROC 0.959 and the same plateau (91.0%, 92.6%, 92.0% at 0.80, 0.85, 0.90), so
the threshold choice would have been the same.

# Test run 2: Jev-specific question. Choices fixed before the run

Written 2026-09-21, after test run 1 (90.3% at threshold 0.85) and before run 2.

**Why a second run.** Run 1 asked Jev a field-by-field mapping of MedHELM's
prompt, which was written for LLMs. Run 2 asks the question in the form that
suits Jev. Both results are to be reported, run 1 first. There will be no run 3.

**Nothing below was chosen with test data.** Run 1's test predictions were not
inspected item by item, and no wording or threshold was tried against test.

- **Dev data:** a new 500-item `dev` sample and a disjoint 500-item `dev2`
  sample from `pqa_artificial`, both in the same format as test.
- **Round 1 on dev** (`runs/medhallu/dev-explore1`): seven candidate questions in
  one request. AUROC: authors_reject 0.964, signals 0.958, boundary 0.955,
  contradiction 0.951, MedHELM mapping 0.946, off_target 0.813,
  unsupported_specifics 0.728. No mean of two or three questions beat the best
  single question.
- **Round 2 on dev** (`runs/medhallu/dev-explore2`): six variations of the
  winner. None beat it (0.964; next best 0.962).
- **Confirmation on dev2** (`runs/medhallu/dev2-confirm`), which played no part
  in the choice: authors_reject 0.967, MedHELM mapping 0.957.
- **Chosen question**, a single Noul with no criteria:
  "Would the authors of the study described in `knowledge` say that `answer`
  misrepresents their findings?"
- **Threshold: 0.65**, the middle of the flat region on dev + dev2 combined
  (90.3%, 90.4%, 90.8%, 91.4% at 0.55, 0.60, 0.65, 0.70; 90.0% at 0.75).
- **Check:** asked alone instead of alongside other questions, dev2
  probabilities move by 0.008 on average and 4 of 500 labels flip at 0.65.
- **Metric and tests:** as for run 1. Output folder `runs/medhallu/test-v2`.
  Run 1 stays scoreable with
  `--task datasets/medhallu/variants/test-run1.task.json`.

**What the post must say:** the LLM columns used Stanford's generic zero-shot
prompt with no tuning. Jev's question and threshold were tuned on 1,000
separate dev items. Run 1 (LLM-style prompt) scored 90.3%.

# Added LLM rows: current fast models. Choices fixed before the run

Written 2026-09-22, before any of these four models was run on
`items.test.jsonl`. This is not a Jev run: Jev's result stays run 2
(`runs/medhallu/test-v2`, threshold 0.65).

**Why.** The 13 published LLMs date from 2024 to mid 2025. A hallucination
check sits inline in a pipeline, so the fair current comparison is a recent
*fast* model, not a flagship. Flagships were considered and rejected as too slow
for inline use (5-item dev smoke `runs/medhallu/dev-flagship-smoke`: Claude
Fable 5.1 5.8 s median, GPT-6 Astra 2.1 s, Gemini 3.1 Pro 4.0 s).

**Models, settings and providers** (provider pinned, no fallbacks,
`require_parameters`):

| Spec | Reasoning | Provider | LiteLLM list price, USD per 1M in / out (sheet main@2026-09-22) |
|---|---|---|---|
| `openai/gpt-5.6-luna@none` | effort `none` | OpenAI | 0.20 / 1.20 (`gpt-5.6-luna`) |
| `google/gemini-3.8-flash@minimal` | effort `minimal` | Google AI Studio | 0.75 / 3.75 (`gemini/gemini-3.8-flash`) |
| `google/gemini-3.5-flash-lite` | provider default | Google AI Studio | 0.30 / 2.50 (`gemini/gemini-3.5-flash-lite`) |
| `anthropic/claude-haiku-4.5` | provider default (no extended thinking) | Anthropic | 1.00 / 5.00 (`claude-haiku-4-5`) |

**How these were chosen.** One model per question a reader will ask: OpenAI's
newest fast tier (Luna), the newest fast model of the three vendors (Gemini 3.8
Flash), the fastest LLM measured (Gemini 3.5 Flash Lite) and Anthropic's fast
tier (Haiku 4.5, the newest Haiku). Settings are the lowest reasoning a
latency-sensitive pipeline would use. A 20-item dev smoke
(`runs/medhallu/dev-fast-smoke`) was used for latency, cost and plumbing only;
20 items cannot rank accuracy. Dropped: Luna and Gemini 3.8 Flash at default
reasoning (same models, about twice as slow), Claude Sonnet 5 at low effort
(slower, dearer, one `content_filter` refusal in 20 items).

**Prompt.** The same for all four and not tuned: the harness's LLM prompt
(system: "You are a classifier. Choose the single best option from the list.
Reply only in the requested JSON format."; user: the `knowledge`, `question`
and `answer` fields, then the MedHELM-derived instructions and label
descriptions in `data/task.json`, the wording Jev got in run 1), with a strict
JSON-schema enum on the label. Zero-shot. It is not Stanford's exact prompt, and
the LLMs do not get Jev's tuned question.

**Execution.** Test split, all 1,000 items, one pass per model, concurrency 1,
one untimed warm-up call per model, `max_tokens` 16000. Only transport
failures are retried (timeouts, 429, 5xx; up to 4 attempts). A refusal, content
filter, truncation or out-of-set label counts as wrong. Written into
`runs/medhallu/test-v2` next to Jev run 2 (same task fingerprint
`4a9efe880df4b922`, items sha256 `10e4a36157a9550e`), so paired tests use the
same items. That folder was backed up first to
`runs/medhallu/_backup-test-v2-before-llm-rows-2026-09-22`.

**Metric.** As for runs 1 and 2: accuracy on 1,000 items with a 95% Wilson
interval, and paired exact McNemar against `jev-1.13` (run 2, threshold 0.65),
Holm-corrected. Latency p50 and p90 measured from the same machine through
OpenRouter as Jev, so unlike the Stanford columns these rows are comparable to
Jev on time. Cost is OpenRouter's billed cost per call.

**One run per model.** Whatever each model scores is reported. An interrupted
run resumes without re-asking answered items. A model that cannot finish is
reported as such, not replaced.

**What the post must say:** Luna and Gemini 3.8 Flash ran with reasoning set to
`none` and `minimal` (a pipeline setting, unlike Stanford's defaults), and all
four got an untuned LLM prompt while Jev's question was tuned on dev.
