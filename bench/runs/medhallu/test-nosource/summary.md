# Benchmark: medhallu

- Source: `MedHELM v4.0.0 medhallu (gs://crfm-helm-public/medhelm) over hf://datasets/UTAustin-AIHealth/MedHallu`
- Items: 1000 | run dir: `runs/medhallu/test-nosource`
- Headline set: all items (n=1000)
- Served models: jev-1.13 -> typesafe/jev-1.13-20260917 via TypeSafe; google/gemini-3.8-flash@minimal -> google/gemini-3.8-flash via Google AI Studio; anthropic/claude-haiku-4.5 -> anthropic/claude-haiku-4.5 via Anthropic; openai/gpt-5.6-luna@none -> openai/gpt-5.6-luna via OpenAI; google/gemini-3.5-flash-lite -> google/gemini-3.5-flash-lite via Google AI Studio
- Labels for runs with probabilities re-derived at P(1) >= 0.65

## Headline

| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |
|---|---|---|---|---|---|---|---|---|
| jev-1.13 | 1000 | 66.4% [63.4%, 69.3%] | 0.609 | 0 | 218 | 312 | 377 / n/a | $0.0158 |
| google/gemini-3.8-flash@minimal | 1000 | 82.9% [80.4%, 85.1%] | 0.824 | 0 | 1,548 | 4,524 | 377 / 155 | $0.8639 |
| anthropic/claude-haiku-4.5 | 1000 | 77.9% [75.2%, 80.4%] | 0.778 | 0 | 701 | 1,264 | 583 / 9 | $0.6308 |
| openai/gpt-5.6-luna@none | 1000 | 73.5% [70.7%, 76.1%] | 0.725 | 0 | 1,105 | 1,766 | 390 / 12 | $0.0925 |
| google/gemini-3.5-flash-lite | 1000 | 71.8% [68.9%, 74.5%] | 0.700 | 0 | 654 | 791 | 377 / 10 | $0.1394 |

With n = 1000, a 95% interval is up to about +/-3 points wide. Treat gaps smaller than that as noise unless the paired test below says otherwise.

## Binary detail (positive = 1: Hallucinated: `answer` falls into at least one of the hallucination types)

| Model | Balanced acc | Precision | Recall | F1 | AUROC | TP / FN / FP / TN |
|---|---|---|---|---|---|---|
| jev-1.13 | 65.0% | 99.3% | 30.2% | 0.463 | 0.927 | 145 / 335 / 1 / 519 |
| google/gemini-3.8-flash@minimal | 82.3% | 94.8% | 68.1% | 0.793 | n/a | 327 / 153 / 18 / 502 |
| anthropic/claude-haiku-4.5 | 77.7% | 79.2% | 73.1% | 0.761 | n/a | 351 / 129 / 92 / 428 |
| openai/gpt-5.6-luna@none | 72.8% | 83.1% | 56.2% | 0.671 | n/a | 270 / 210 / 55 / 465 |
| google/gemini-3.5-flash-lite | 70.9% | 85.6% | 49.6% | 0.628 | n/a | 238 / 242 / 40 / 480 |

AUROC needs probabilities, which only Jev returns.

Threshold sweep for jev-1.13 (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 48.0% | 49.4% | 62.1% | 80.7% | 84.7% | 72.2% | 61.0% | 53.8% | 52.0% |

## Accuracy by slice

| Model | all (n=1000) | gold=0 (n=520) | gold=1 (n=480) | difficulty=easy (n=255) | difficulty=hard (n=418) | difficulty=medium (n=327) | category=Incomplete Information (n=109) | category=Mechanism and Pathway Misattribution (n=15) | category=Methodological and Evidence Fabrication (n=3) | category=Misinterpretation of #Question# (n=353) |
|---|---|---|---|---|---|---|---|---|---|---|
| jev-1.13 | 66.4% | 99.8% | 30.2% | 72.9% | 62.2% | 66.7% | 17.4% | 46.7% | 33.3% | 33.4% |
| google/gemini-3.8-flash@minimal | 82.9% | 96.5% | 68.1% | 90.6% | 74.2% | 88.1% | 59.6% | 86.7% | 100.0% | 69.7% |
| anthropic/claude-haiku-4.5 | 77.9% | 82.3% | 73.1% | 84.7% | 72.0% | 80.1% | 60.6% | 80.0% | 100.0% | 76.5% |
| openai/gpt-5.6-luna@none | 73.5% | 89.4% | 56.2% | 80.4% | 66.5% | 77.1% | 37.6% | 80.0% | 100.0% | 60.6% |
| google/gemini-3.5-flash-lite | 71.8% | 92.3% | 49.6% | 77.6% | 66.7% | 73.7% | 33.0% | 53.3% | 66.7% | 54.4% |

## Paired comparison against jev-1.13

Same items, scored item by item, on the headline set. The exact McNemar test uses only the items where the two models disagree. Holm p corrects for testing several models against one reference. The difference is model minus reference: an interval that excludes 0 is a real gap, and an interval that includes 0 only shows equivalence as tightly as it is narrow.

| Model | Both right | Only reference right | Only model right | Both wrong | Accuracy difference [95% CI] | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| google/gemini-3.8-flash@minimal | 636 | 28 | 193 | 143 | +16.5 [+13.8, +19.2] | 0.000 | 0.000 |
| anthropic/claude-haiku-4.5 | 566 | 98 | 213 | 123 | +11.5 [+8.1, +14.9] | 0.000 | 0.000 |
| openai/gpt-5.6-luna@none | 597 | 67 | 138 | 198 | +7.1 [+4.3, +9.9] | 0.000 | 0.000 |
| google/gemini-3.5-flash-lite | 607 | 57 | 111 | 225 | +5.4 [+2.9, +7.9] | 0.000 | 0.000 |

## jev-1.13: probability quality

Top-3 accuracy 100.0% | NLL 0.506 | Brier 0.323 | ECE (10 bins, top probability) 0.164 | mean confidence when right 0.66, when wrong 0.48 (n=1000)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.5 to 0.6 | 380 | 0.55 | 36.8% |
| 0.6 to 0.7 | 351 | 0.64 | 74.9% |
| 0.7 to 0.8 | 230 | 0.74 | 96.5% |
| 0.8 to 0.9 | 39 | 0.82 | 100.0% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 66.4% | 1000 |
| 0.5 | 76.1% | 83.2% | 761 |
| 0.7 | 26.9% | 97.0% | 269 |
| 0.9 | 0.0% | n/a | 0 |

## Notes

- Errors count as wrong. Latency percentiles use successful calls only and time the final attempt, after an untimed warm-up call per model.
- Latency depends on concurrency, network path and time of day. Quote numbers from a `--concurrency 1` run, from the same machine, close together in time.
- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, otherwise list prices applied to token counts. LLM output tokens include reasoning. Failed calls are not counted.
- Items that needed more than one attempt: google/gemini-3.8-flash@minimal: 5, anthropic/claude-haiku-4.5: 35.
