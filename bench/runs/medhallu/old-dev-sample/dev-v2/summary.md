# Benchmark: medhallu

- Source: `MedHELM v4.0.0 medhallu (gs://crfm-helm-public/medhelm) over hf://datasets/UTAustin-AIHealth/MedHallu`
- Items: 500 | run dir: `runs/medhallu/dev-v2`
- Headline set: all items (n=500)
- Served models: jev-1.13@choice -> typesafe/jev-1.13-20260917 via TypeSafe; jev-1.13 -> typesafe/jev-1.13-20260917 via TypeSafe

## Headline

| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |
|---|---|---|---|---|---|---|---|---|
| jev-1.13@choice | 500 | 84.4% [81.0%, 87.3%] | 0.843 | 0 | 218 | 334 | 997 / n/a | $0.0419 |
| jev-1.13 | 500 | 81.0% [77.3%, 84.2%] | 0.808 | 0 | 210 | 289 | 981 / n/a | $0.0412 |

With n = 500, a 95% interval is up to about +/-4 points wide. Treat gaps smaller than that as noise unless the paired test below says otherwise.

## Binary detail (positive = 1: Hallucinated: `answer` falls into at least one of the hallucination types)

| Model | Balanced acc | Precision | Recall | F1 | AUROC | TP / FN / FP / TN |
|---|---|---|---|---|---|---|
| jev-1.13@choice | 84.8% | 77.6% | 95.0% | 0.854 | 0.961 | 228 / 12 / 66 / 194 |
| jev-1.13 | 81.5% | 73.3% | 95.0% | 0.828 | 0.961 | 228 / 12 / 83 / 177 |

AUROC needs probabilities, which only Jev returns.

Threshold sweep for jev-1.13@choice (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 67.0% | 74.0% | 78.2% | 81.0% | 84.2% | 87.6% | 90.0% | 91.4% | 92.6% |

Threshold sweep for jev-1.13 (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 54.4% | 65.6% | 71.6% | 76.8% | 81.0% | 86.4% | 89.2% | 92.2% | 91.8% |

## Accuracy by slice

| Model | all (n=500) | gold=0 (n=260) | gold=1 (n=240) | difficulty=easy (n=154) | difficulty=hard (n=187) | difficulty=medium (n=159) | category=Incomplete Information (n=18) | category=Mechanism and Pathway Misattribution (n=24) | category=Methodological and Evidence Fabrication (n=2) | category=Misinterpretation of #Question# (n=196) |
|---|---|---|---|---|---|---|---|---|---|---|
| jev-1.13@choice | 84.4% | 74.6% | 95.0% | 88.3% | 81.3% | 84.3% | 100.0% | 95.8% | 100.0% | 94.4% |
| jev-1.13 | 81.0% | 68.1% | 95.0% | 89.0% | 75.9% | 79.2% | 100.0% | 95.8% | 100.0% | 94.4% |

## Paired comparison against jev-1.13@choice

Same items, scored item by item, on the headline set. The exact McNemar test uses only the items where the two models disagree. Holm p corrects for testing several models against one reference. The difference is model minus reference: an interval that excludes 0 is a real gap, and an interval that includes 0 only shows equivalence as tightly as it is narrow.

| Model | Both right | Only reference right | Only model right | Both wrong | Accuracy difference [95% CI] | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| jev-1.13 | 402 | 20 | 3 | 75 | -3.4 [-5.3, -1.5] | 0.000 | 0.000 |

## jev-1.13@choice: probability quality

Top-3 accuracy 100.0% | NLL 0.368 | Brier 0.220 | ECE (10 bins, top probability) 0.057 | mean confidence when right 0.85, when wrong 0.52 (n=500)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.5 to 0.6 | 31 | 0.55 | 45.2% |
| 0.6 to 0.7 | 31 | 0.64 | 54.8% |
| 0.7 to 0.8 | 35 | 0.75 | 68.6% |
| 0.8 to 0.9 | 57 | 0.85 | 75.4% |
| 0.9 to 1.0 | 346 | 0.98 | 93.6% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 84.4% | 500 |
| 0.5 | 84.2% | 90.3% | 421 |
| 0.7 | 75.0% | 92.5% | 375 |
| 0.9 | 60.6% | 97.0% | 303 |

## jev-1.13: probability quality

Top-3 accuracy 100.0% | NLL 0.372 | Brier 0.243 | ECE (10 bins, top probability) 0.056 | mean confidence when right 0.87, when wrong 0.70 (n=500)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.5 to 0.6 | 51 | 0.55 | 43.1% |
| 0.6 to 0.7 | 43 | 0.64 | 58.1% |
| 0.7 to 0.8 | 54 | 0.74 | 66.7% |
| 0.8 to 0.9 | 104 | 0.86 | 76.9% |
| 0.9 to 1.0 | 248 | 0.95 | 97.6% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 81.0% | 500 |
| 0.5 | 100.0% | 81.0% | 500 |
| 0.7 | 81.2% | 88.2% | 406 |
| 0.9 | 49.6% | 97.6% | 248 |

## Notes

- Errors count as wrong. Latency percentiles use successful calls only and time the final attempt, after an untimed warm-up call per model.
- Latency depends on concurrency, network path and time of day. Quote numbers from a `--concurrency 1` run, from the same machine, close together in time.
- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, otherwise list prices applied to token counts. LLM output tokens include reasoning. Failed calls are not counted.
