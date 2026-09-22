# Benchmark: medhallu

- Source: `MedHELM v4.0.0 medhallu (gs://crfm-helm-public/medhelm) over hf://datasets/UTAustin-AIHealth/MedHallu`
- Items: 20 | run dir: `runs/medhallu/smoke`
- Headline set: all items (n=20)
- Served models: jev-1.13 -> typesafe/jev-1.13-20260917 via TypeSafe; jev-1.13@choice -> typesafe/jev-1.13-20260917 via TypeSafe; constant:1 -> constant:1

## Headline

| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |
|---|---|---|---|---|---|---|---|---|
| jev-1.13 | 20 | 85.0% [64.0%, 94.8%] | 0.850 | 0 | 193 | 227 | 771 / n/a | $0.0324 |
| jev-1.13@choice | 20 | 85.0% [64.0%, 94.8%] | 0.850 | 0 | 187 | 226 | 787 / n/a | $0.0331 |
| constant:1 | 20 | 45.0% [25.8%, 65.8%] | 0.310 | 0 | 0 | 0 | 0 / 0 | $0.0000 |

With n = 20, a 95% interval is up to about +/-22 points wide. Treat gaps smaller than that as noise unless the paired test below says otherwise.

## Binary detail (positive = 1: Hallucinated: contradicts or goes beyond what `knowledge` supports, or answers a different question)

| Model | Balanced acc | Precision | Recall | F1 | AUROC | TP / FN / FP / TN |
|---|---|---|---|---|---|---|
| jev-1.13 | 85.4% | 80.0% | 88.9% | 0.842 | 0.939 | 8 / 1 / 2 / 9 |
| jev-1.13@choice | 85.4% | 80.0% | 88.9% | 0.842 | 0.924 | 8 / 1 / 2 / 9 |
| constant:1 | 50.0% | 45.0% | 100.0% | 0.621 | n/a | 9 / 0 / 11 / 0 |

AUROC needs probabilities, which only Jev returns.

Threshold sweep for jev-1.13 (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 50.0% | 80.0% | 80.0% | 85.0% | 85.0% | 85.0% | 80.0% | 90.0% | 90.0% |

Threshold sweep for jev-1.13@choice (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 70.0% | 80.0% | 85.0% | 85.0% | 85.0% | 85.0% | 85.0% | 80.0% | 90.0% |

## Accuracy by slice

| Model | all (n=20) | gold=0 (n=11) | gold=1 (n=9) | difficulty=easy (n=7) | difficulty=hard (n=9) | difficulty=medium (n=4) | category=Incomplete Information (n=1) | category=Misinterpretation of #Question# (n=8) |
|---|---|---|---|---|---|---|---|---|
| jev-1.13 | 85.0% | 81.8% | 88.9% | 100.0% | 77.8% | 75.0% | 100.0% | 87.5% |
| jev-1.13@choice | 85.0% | 81.8% | 88.9% | 100.0% | 77.8% | 75.0% | 100.0% | 87.5% |
| constant:1 | 45.0% | 0.0% | 100.0% | 28.6% | 55.6% | 50.0% | 100.0% | 100.0% |

## Paired comparison against jev-1.13

Same items, scored item by item, on the headline set. The exact McNemar test uses only the items where the two models disagree. Holm p corrects for testing several models against one reference. The difference is model minus reference: an interval that excludes 0 is a real gap, and an interval that includes 0 only shows equivalence as tightly as it is narrow.

| Model | Both right | Only reference right | Only model right | Both wrong | Accuracy difference [95% CI] | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| jev-1.13@choice | 17 | 0 | 0 | 3 | +0.0 [+0.0, +0.0] | 1.000 | 1.000 |
| constant:1 | 8 | 9 | 1 | 2 | -40.0 [-65.6, -14.4] | 0.021 | 0.043 |

## jev-1.13: probability quality

Top-3 accuracy 100.0% | NLL 0.322 | Brier 0.206 | ECE (10 bins, top probability) 0.192 | mean confidence when right 0.88, when wrong 0.74 (n=20)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.6 to 0.7 | 2 | 0.68 | 100.0% |
| 0.7 to 0.8 | 4 | 0.75 | 25.0% |
| 0.8 to 0.9 | 5 | 0.86 | 100.0% |
| 0.9 to 1.0 | 9 | 0.95 | 100.0% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 85.0% | 20 |
| 0.5 | 100.0% | 85.0% | 20 |
| 0.7 | 90.0% | 83.3% | 18 |
| 0.9 | 45.0% | 100.0% | 9 |

## jev-1.13@choice: probability quality

Top-3 accuracy 100.0% | NLL 0.352 | Brier 0.238 | ECE (10 bins, top probability) 0.144 | mean confidence when right 0.85, when wrong 0.69 (n=20)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.7 to 0.8 | 2 | 0.72 | 100.0% |
| 0.8 to 0.9 | 6 | 0.85 | 50.0% |
| 0.9 to 1.0 | 12 | 0.98 | 100.0% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 85.0% | 20 |
| 0.5 | 90.0% | 83.3% | 18 |
| 0.7 | 70.0% | 92.9% | 14 |
| 0.9 | 50.0% | 100.0% | 10 |

## Notes

- Errors count as wrong. Latency percentiles use successful calls only and time the final attempt, after an untimed warm-up call per model.
- Latency depends on concurrency, network path and time of day. Quote numbers from a `--concurrency 1` run, from the same machine, close together in time.
- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, otherwise list prices applied to token counts. LLM output tokens include reasoning. Failed calls are not counted.
