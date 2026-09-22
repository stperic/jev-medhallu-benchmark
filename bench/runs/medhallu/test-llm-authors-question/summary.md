# Benchmark: medhallu

- Source: `MedHELM v4.0.0 medhallu (gs://crfm-helm-public/medhelm) over hf://datasets/UTAustin-AIHealth/MedHallu`
- Items: 1000 | run dir: `runs/medhallu/test-llm-authors-question`
- Headline set: all items (n=1000)
- Served models: openai/gpt-5.6-luna@none -> openai/gpt-5.6-luna via OpenAI; google/gemini-3.5-flash-lite -> google/gemini-3.5-flash-lite via Google AI Studio; google/gemini-3.8-flash@minimal -> google/gemini-3.8-flash via Google AI Studio; anthropic/claude-haiku-4.5 -> anthropic/claude-haiku-4.5 via Anthropic

## Headline

| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |
|---|---|---|---|---|---|---|---|---|
| openai/gpt-5.6-luna@none | 1000 | 95.1% [93.6%, 96.3%] | 0.951 | 0 | 1,158 | 1,781 | 469 / 12 | $0.1083 |
| google/gemini-3.5-flash-lite | 1000 | 95.0% [93.5%, 96.2%] | 0.950 | 0 | 650 | 774 | 453 / 10 | $0.1621 |
| google/gemini-3.8-flash@minimal | 1000 | 94.8% [93.2%, 96.0%] | 0.948 | 0 | 1,298 | 3,699 | 453 / 102 | $0.7216 |
| anthropic/claude-haiku-4.5 | 1000 | 92.4% [90.6%, 93.9%] | 0.924 | 0 | 690 | 1,405 | 659 / 9 | $0.7040 |

With n = 1000, a 95% interval is up to about +/-3 points wide. Treat gaps smaller than that as noise unless the paired test below says otherwise.

## Binary detail (positive = 1: Yes)

| Model | Balanced acc | Precision | Recall | F1 | AUROC | TP / FN / FP / TN |
|---|---|---|---|---|---|---|
| openai/gpt-5.6-luna@none | 95.1% | 95.8% | 94.0% | 0.948 | n/a | 451 / 29 / 20 / 500 |
| google/gemini-3.5-flash-lite | 94.9% | 96.3% | 93.1% | 0.947 | n/a | 447 / 33 / 17 / 503 |
| google/gemini-3.8-flash@minimal | 94.7% | 96.3% | 92.7% | 0.945 | n/a | 445 / 35 / 17 / 503 |
| anthropic/claude-haiku-4.5 | 92.3% | 93.0% | 91.0% | 0.920 | n/a | 437 / 43 / 33 / 487 |

AUROC needs probabilities, which only Jev returns.

## Accuracy by slice

| Model | all (n=1000) | gold=0 (n=520) | gold=1 (n=480) | difficulty=easy (n=255) | difficulty=hard (n=418) | difficulty=medium (n=327) | category=Incomplete Information (n=109) | category=Mechanism and Pathway Misattribution (n=15) | category=Methodological and Evidence Fabrication (n=3) | category=Misinterpretation of #Question# (n=353) |
|---|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-5.6-luna@none | 95.1% | 96.2% | 94.0% | 98.8% | 94.0% | 93.6% | 91.7% | 100.0% | 100.0% | 94.3% |
| google/gemini-3.5-flash-lite | 95.0% | 96.7% | 93.1% | 98.0% | 92.8% | 95.4% | 91.7% | 100.0% | 100.0% | 93.2% |
| google/gemini-3.8-flash@minimal | 94.8% | 96.7% | 92.7% | 96.9% | 93.1% | 95.4% | 89.0% | 93.3% | 100.0% | 93.8% |
| anthropic/claude-haiku-4.5 | 92.4% | 93.7% | 91.0% | 95.3% | 89.5% | 93.9% | 88.1% | 93.3% | 100.0% | 91.8% |

## Paired comparison against openai/gpt-5.6-luna@none

Same items, scored item by item, on the headline set. The exact McNemar test uses only the items where the two models disagree. Holm p corrects for testing several models against one reference. The difference is model minus reference: an interval that excludes 0 is a real gap, and an interval that includes 0 only shows equivalence as tightly as it is narrow.

| Model | Both right | Only reference right | Only model right | Both wrong | Accuracy difference [95% CI] | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| google/gemini-3.5-flash-lite | 926 | 25 | 24 | 25 | -0.1 [-1.5, +1.3] | 1.000 | 1.000 |
| google/gemini-3.8-flash@minimal | 928 | 23 | 20 | 29 | -0.3 [-1.6, +1.0] | 0.761 | 1.000 |
| anthropic/claude-haiku-4.5 | 911 | 40 | 13 | 36 | -2.7 [-4.1, -1.3] | 0.000 | 0.001 |

## Notes

- Errors count as wrong. Latency percentiles use successful calls only and time the final attempt, after an untimed warm-up call per model.
- Latency depends on concurrency, network path and time of day. Quote numbers from a `--concurrency 1` run, from the same machine, close together in time.
- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, otherwise list prices applied to token counts. LLM output tokens include reasoning. Failed calls are not counted.
- Items that needed more than one attempt: google/gemini-3.5-flash-lite: 2, google/gemini-3.8-flash@minimal: 6, anthropic/claude-haiku-4.5: 32.
