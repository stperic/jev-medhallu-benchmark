# Benchmark: medhallu

- Source: `MedHELM v4.0.0 medhallu (gs://crfm-helm-public/medhelm) over hf://datasets/UTAustin-AIHealth/MedHallu`
- Items: 500 | run dir: `runs/medhallu/dev-v1`
- Headline set: all items (n=500)
- Served models: jev-1.13@choice -> typesafe/jev-1.13-20260917 via TypeSafe; jev-1.13 -> typesafe/jev-1.13-20260917 via TypeSafe; constant:1 -> constant:1

## Headline

| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |
|---|---|---|---|---|---|---|---|---|
| jev-1.13@choice | 500 | 84.2% [80.7%, 87.1%] | 0.841 | 0 | 191 | 267 | 827 / n/a | $0.0347 |
| jev-1.13 | 500 | 83.8% [80.3%, 86.8%] | 0.837 | 0 | 201 | 283 | 811 / n/a | $0.0341 |
| constant:1 | 500 | 48.0% [43.7%, 52.4%] | 0.324 | 0 | 0 | 0 | 0 / 0 | $0.0000 |

With n = 500, a 95% interval is up to about +/-4 points wide. Treat gaps smaller than that as noise unless the paired test below says otherwise.

## Binary detail (positive = 1: Hallucinated: contradicts or goes beyond what `knowledge` supports, or answers a different question)

| Model | Balanced acc | Precision | Recall | F1 | AUROC | TP / FN / FP / TN |
|---|---|---|---|---|---|---|
| jev-1.13@choice | 84.6% | 77.3% | 95.0% | 0.852 | 0.963 | 228 / 12 / 67 / 193 |
| jev-1.13 | 84.2% | 76.8% | 95.0% | 0.849 | 0.962 | 228 / 12 / 69 / 191 |
| constant:1 | 50.0% | 48.0% | 100.0% | 0.649 | n/a | 240 / 0 / 260 / 0 |

AUROC needs probabilities, which only Jev returns.

Threshold sweep for jev-1.13@choice (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 66.2% | 73.2% | 77.2% | 80.6% | 84.0% | 87.0% | 89.0% | 90.8% | 91.8% |

Threshold sweep for jev-1.13 (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 57.4% | 69.0% | 76.0% | 80.0% | 83.8% | 88.2% | 91.2% | 92.0% | 88.8% |

## Accuracy by slice

| Model | all (n=500) | gold=0 (n=260) | gold=1 (n=240) | difficulty=easy (n=154) | difficulty=hard (n=187) | difficulty=medium (n=159) | category=Incomplete Information (n=18) | category=Mechanism and Pathway Misattribution (n=24) | category=Methodological and Evidence Fabrication (n=2) | category=Misinterpretation of #Question# (n=196) |
|---|---|---|---|---|---|---|---|---|---|---|
| jev-1.13@choice | 84.2% | 74.2% | 95.0% | 90.9% | 79.7% | 83.0% | 100.0% | 95.8% | 100.0% | 94.4% |
| jev-1.13 | 83.8% | 73.5% | 95.0% | 90.9% | 77.5% | 84.3% | 100.0% | 95.8% | 100.0% | 94.4% |
| constant:1 | 48.0% | 0.0% | 100.0% | 51.3% | 47.6% | 45.3% | 100.0% | 100.0% | 100.0% | 100.0% |

## Paired comparison against jev-1.13@choice

Same items, scored item by item, on the headline set. The exact McNemar test uses only the items where the two models disagree. Holm p corrects for testing several models against one reference. The difference is model minus reference: an interval that excludes 0 is a real gap, and an interval that includes 0 only shows equivalence as tightly as it is narrow.

| Model | Both right | Only reference right | Only model right | Both wrong | Accuracy difference [95% CI] | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| jev-1.13 | 416 | 5 | 3 | 76 | -0.4 [-1.5, +0.7] | 0.727 | 0.727 |
| constant:1 | 228 | 193 | 12 | 67 | -36.2 [-40.8, -31.6] | 0.000 | 0.000 |

## jev-1.13@choice: probability quality

Top-3 accuracy 100.0% | NLL 0.374 | Brier 0.226 | ECE (10 bins, top probability) 0.055 | mean confidence when right 0.84, when wrong 0.53 (n=500)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.5 to 0.6 | 33 | 0.55 | 51.5% |
| 0.6 to 0.7 | 32 | 0.64 | 62.5% |
| 0.7 to 0.8 | 38 | 0.75 | 63.2% |
| 0.8 to 0.9 | 58 | 0.85 | 72.4% |
| 0.9 to 1.0 | 339 | 0.98 | 93.8% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 84.2% | 500 |
| 0.5 | 83.2% | 89.4% | 416 |
| 0.7 | 74.0% | 93.0% | 370 |
| 0.9 | 58.0% | 97.2% | 290 |

## jev-1.13: probability quality

Top-3 accuracy 100.0% | NLL 0.336 | Brier 0.212 | ECE (10 bins, top probability) 0.040 | mean confidence when right 0.87, when wrong 0.70 (n=500)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.5 to 0.6 | 41 | 0.55 | 43.9% |
| 0.6 to 0.7 | 44 | 0.65 | 54.5% |
| 0.7 to 0.8 | 58 | 0.74 | 72.4% |
| 0.8 to 0.9 | 111 | 0.85 | 83.8% |
| 0.9 to 1.0 | 246 | 0.95 | 98.4% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 83.8% | 500 |
| 0.5 | 100.0% | 83.8% | 500 |
| 0.7 | 83.0% | 90.8% | 415 |
| 0.9 | 49.2% | 98.4% | 246 |

## Notes

- Errors count as wrong. Latency percentiles use successful calls only and time the final attempt, after an untimed warm-up call per model.
- Latency depends on concurrency, network path and time of day. Quote numbers from a `--concurrency 1` run, from the same machine, close together in time.
- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, otherwise list prices applied to token counts. LLM output tokens include reasoning. Failed calls are not counted.
