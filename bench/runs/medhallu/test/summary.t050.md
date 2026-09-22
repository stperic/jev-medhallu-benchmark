# Benchmark: medhallu

- Source: `MedHELM v4.0.0 medhallu (gs://crfm-helm-public/medhelm) over hf://datasets/UTAustin-AIHealth/MedHallu`
- Items: 1000 | run dir: `runs/medhallu/test`
- Headline set: all items (n=1000)
- Served models: jev-1.13@choice -> typesafe/jev-1.13-20260917 via TypeSafe; jev-1.13 -> typesafe/jev-1.13-20260917 via TypeSafe

## Headline

| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |
|---|---|---|---|---|---|---|---|---|
| jev-1.13@choice | 1000 | 85.7% [83.4%, 87.7%] | 0.857 | 0 | 194 | 267 | 966 / n/a | $0.0406 |
| jev-1.13 | 1000 | 81.9% [79.4%, 84.2%] | 0.817 | 0 | 205 | 281 | 950 / n/a | $0.0399 |
| medhelm/anthropic_claude-3-5-sonnet-20241022 † | 1000 | 92.6% [90.8%, 94.1%] | 0.926 | 0 | 2,693 | 5,890 | 715 / 1 | $2.16 est. |
| medhelm/google_gemini-2.0-flash-001 † | 1000 | 90.8% [88.8%, 92.4%] | 0.907 | 0 | 323 | 406 | 718 / 0 | $0.11 est. |
| medhelm/openai_gpt-5-2025-08-07 † | 1000 | 90.5% [88.5%, 92.2%] | 0.905 | 0 | 3,082 | 8,420 | 690 / 1 | >= $0.87 est. |
| medhelm/openai_o3-mini-2025-01-31 † | 1000 | 89.6% [87.6%, 91.3%] | 0.899 | 7 | 3,960 | 13,291 | 709 / 1 | >= $0.78 est. |
| medhelm/google_gemini-1.5-pro-001 † | 1000 | 89.1% [87.0%, 90.9%] | 0.891 | 0 | 525 | 607 | 718 / 0 | $0.90 est. |
| medhelm/meta_llama-3.3-70b-instruct † | 1000 | 88.2% [86.1%, 90.1%] | 0.882 | 0 | 0 | 0 | 709 / 1 | $0.07 est. |
| medhelm/anthropic_claude-3-7-sonnet-20250219 † | 1000 | 87.7% [85.5%, 89.6%] | 0.877 | 0 | 4,837 | 10,060 | 715 / 1 | $2.16 est. |
| medhelm/openai_gpt-5-mini-2025-08-07 † | 1000 | 87.4% [85.2%, 89.3%] | 0.874 | 0 | 3,164 | 7,450 | 690 / 1 | >= $0.17 est. |
| medhelm/openai_o4-mini-2025-04-16 † | 1000 | 86.8% [84.6%, 88.8%] | 0.868 | 0 | 2,749 | 7,436 | 697 / 1 | >= $0.77 est. |
| medhelm/google_gemini-2.5-pro-preview-05-06 † | 1000 | 86.4% [84.1%, 88.4%] | 0.864 | 0 | 12,450 | 17,120 | 705 / 0 | >= $0.88 est. |
| medhelm/deepseek-ai_deepseek-r1 † | 1000 | 84.7% [82.3%, 86.8%] | 0.847 | 0 | 4,841 | 17,948 | 695 / 0 | >= $0.38 est. |
| medhelm/openai_gpt-4o-2024-05-13 † | 1000 | 84.6% [82.2%, 86.7%] | 0.846 | 0 | 336 | 1,837 | 702 / 1 | $3.52 est. |
| medhelm/openai_gpt-4o-mini-2024-07-18 † | 1000 | 80.1% [77.5%, 82.5%] | 0.801 | 0 | 440 | 867 | 702 / 1 | $0.11 est. |

† Published by Stanford CRFM, MedHELM v4.0.0, not run here. Same items, scored the same way, so accuracy is comparable. The prompt was the publisher's. Latency was measured on the publisher's infrastructure and is not comparable with latency measured here. Output token counts exclude hidden reasoning tokens.

Costs marked est. are not charges anyone reported: they are the published token counts times LiteLLM list prices (`published_prices.json` names the key and sheet version per model). For reasoning models (>=) this is a floor, because hidden reasoning tokens are billed as output but missing from the published counts.

With n = 1000, a 95% interval is up to about +/-3 points wide. Treat gaps smaller than that as noise unless the paired test below says otherwise.

## Binary detail (positive = 1: Hallucinated: `answer` falls into at least one of the hallucination types)

| Model | Balanced acc | Precision | Recall | F1 | AUROC | TP / FN / FP / TN |
|---|---|---|---|---|---|---|
| jev-1.13@choice | 86.1% | 79.2% | 95.2% | 0.865 | 0.958 | 457 / 23 / 120 / 400 |
| jev-1.13 | 82.5% | 73.9% | 96.2% | 0.836 | 0.959 | 462 / 18 / 163 / 357 |
| medhelm/anthropic_claude-3-5-sonnet-20241022 † | 92.6% | 91.1% | 93.8% | 0.924 | n/a | 450 / 30 / 44 / 476 |
| medhelm/google_gemini-2.0-flash-001 † | 90.6% | 94.1% | 86.2% | 0.900 | n/a | 414 / 66 / 26 / 494 |
| medhelm/openai_gpt-5-2025-08-07 † | 90.4% | 90.9% | 89.2% | 0.900 | n/a | 428 / 52 / 43 / 477 |
| medhelm/openai_o3-mini-2025-01-31 † | 90.2% | 89.0% | 90.8% | 0.899 | n/a | 436 / 44 / 54 / 466 |
| medhelm/google_gemini-1.5-pro-001 † | 89.1% | 88.1% | 89.4% | 0.887 | n/a | 429 / 51 / 58 / 462 |
| medhelm/meta_llama-3.3-70b-instruct † | 88.3% | 86.1% | 90.0% | 0.880 | n/a | 432 / 48 / 70 / 450 |
| medhelm/anthropic_claude-3-7-sonnet-20250219 † | 87.9% | 82.9% | 93.8% | 0.880 | n/a | 450 / 30 / 93 / 427 |
| medhelm/openai_gpt-5-mini-2025-08-07 † | 87.6% | 83.0% | 92.7% | 0.876 | n/a | 445 / 35 / 91 / 429 |
| medhelm/openai_o4-mini-2025-04-16 † | 87.0% | 82.6% | 91.9% | 0.870 | n/a | 441 / 39 / 93 / 427 |
| medhelm/google_gemini-2.5-pro-preview-05-06 † | 86.6% | 82.3% | 91.2% | 0.866 | n/a | 438 / 42 / 94 / 426 |
| medhelm/deepseek-ai_deepseek-r1 † | 85.0% | 78.8% | 93.1% | 0.854 | n/a | 447 / 33 / 120 / 400 |
| medhelm/openai_gpt-4o-2024-05-13 † | 84.9% | 78.9% | 92.7% | 0.852 | n/a | 445 / 35 / 119 / 401 |
| medhelm/openai_gpt-4o-mini-2024-07-18 † | 80.3% | 76.1% | 85.4% | 0.805 | n/a | 410 / 70 / 129 / 391 |

AUROC needs probabilities, which only Jev returns.

Threshold sweep for jev-1.13@choice (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 70.5% | 76.0% | 80.0% | 82.8% | 85.8% | 87.2% | 89.2% | 90.4% | 90.5% |

Threshold sweep for jev-1.13 (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 57.0% | 68.1% | 73.9% | 78.7% | 81.9% | 85.2% | 88.0% | 90.3% | 89.0% |

## Accuracy by slice

| Model | all (n=1000) | gold=0 (n=520) | gold=1 (n=480) | difficulty=easy (n=255) | difficulty=hard (n=418) | difficulty=medium (n=327) | category=Incomplete Information (n=109) | category=Mechanism and Pathway Misattribution (n=15) | category=Methodological and Evidence Fabrication (n=3) | category=Misinterpretation of #Question# (n=353) |
|---|---|---|---|---|---|---|---|---|---|---|
| jev-1.13@choice | 85.7% | 76.9% | 95.2% | 91.0% | 82.5% | 85.6% | 93.6% | 100.0% | 100.0% | 95.5% |
| jev-1.13 | 81.9% | 68.7% | 96.2% | 86.7% | 79.7% | 81.0% | 94.5% | 100.0% | 100.0% | 96.6% |
| medhelm/anthropic_claude-3-5-sonnet-20241022 † | 92.6% | 91.5% | 93.8% | 95.3% | 89.2% | 94.8% | 90.8% | 100.0% | 100.0% | 94.3% |
| medhelm/google_gemini-2.0-flash-001 † | 90.8% | 95.0% | 86.2% | 94.9% | 86.8% | 92.7% | 80.7% | 93.3% | 100.0% | 87.5% |
| medhelm/openai_gpt-5-2025-08-07 † | 90.5% | 91.7% | 89.2% | 94.1% | 88.0% | 90.8% | 84.4% | 80.0% | 100.0% | 90.9% |
| medhelm/openai_o3-mini-2025-01-31 † | 89.6% | 88.5% | 90.8% | 94.9% | 85.6% | 90.5% | 86.2% | 100.0% | 100.0% | 91.8% |
| medhelm/google_gemini-1.5-pro-001 † | 89.1% | 88.8% | 89.4% | 93.3% | 85.4% | 90.5% | 81.7% | 100.0% | 100.0% | 91.2% |
| medhelm/meta_llama-3.3-70b-instruct † | 88.2% | 86.5% | 90.0% | 92.2% | 83.5% | 91.1% | 82.6% | 93.3% | 100.0% | 92.1% |
| medhelm/anthropic_claude-3-7-sonnet-20250219 † | 87.7% | 82.1% | 93.8% | 90.6% | 83.7% | 90.5% | 89.9% | 100.0% | 100.0% | 94.6% |
| medhelm/openai_gpt-5-mini-2025-08-07 † | 87.4% | 82.5% | 92.7% | 90.6% | 84.9% | 88.1% | 88.1% | 100.0% | 100.0% | 93.8% |
| medhelm/openai_o4-mini-2025-04-16 † | 86.8% | 82.1% | 91.9% | 91.0% | 82.5% | 89.0% | 86.2% | 100.0% | 100.0% | 93.2% |
| medhelm/google_gemini-2.5-pro-preview-05-06 † | 86.4% | 81.9% | 91.2% | 89.4% | 83.3% | 88.1% | 87.2% | 93.3% | 100.0% | 92.4% |
| medhelm/deepseek-ai_deepseek-r1 † | 84.7% | 76.9% | 93.1% | 89.4% | 81.1% | 85.6% | 89.0% | 100.0% | 100.0% | 94.1% |
| medhelm/openai_gpt-4o-2024-05-13 † | 84.6% | 77.1% | 92.7% | 90.2% | 78.0% | 88.7% | 86.2% | 100.0% | 100.0% | 94.3% |
| medhelm/openai_gpt-4o-mini-2024-07-18 † | 80.1% | 75.2% | 85.4% | 86.7% | 73.0% | 84.1% | 74.3% | 100.0% | 100.0% | 88.1% |

## Paired comparison against jev-1.13

Same items, scored item by item, on the headline set. The exact McNemar test uses only the items where the two models disagree. Holm p corrects for testing several models against one reference. The difference is model minus reference: an interval that excludes 0 is a real gap, and an interval that includes 0 only shows equivalence as tightly as it is narrow.

| Model | Both right | Only reference right | Only model right | Both wrong | Accuracy difference [95% CI] | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| jev-1.13@choice | 813 | 6 | 44 | 137 | +3.8 [+2.4, +5.2] | 0.000 | 0.000 |
| medhelm/anthropic_claude-3-5-sonnet-20241022 † | 800 | 19 | 126 | 55 | +10.7 [+8.4, +13.0] | 0.000 | 0.000 |
| medhelm/google_gemini-2.0-flash-001 † | 763 | 56 | 145 | 36 | +8.9 [+6.2, +11.6] | 0.000 | 0.000 |
| medhelm/openai_gpt-5-2025-08-07 † | 775 | 44 | 130 | 51 | +8.6 [+6.1, +11.1] | 0.000 | 0.000 |
| medhelm/openai_o3-mini-2025-01-31 † | 775 | 44 | 121 | 60 | +7.7 [+5.2, +10.2] | 0.000 | 0.000 |
| medhelm/google_gemini-1.5-pro-001 † | 768 | 51 | 123 | 58 | +7.2 [+4.7, +9.7] | 0.000 | 0.000 |
| medhelm/meta_llama-3.3-70b-instruct † | 764 | 55 | 118 | 63 | +6.3 [+3.8, +8.8] | 0.000 | 0.000 |
| medhelm/anthropic_claude-3-7-sonnet-20250219 † | 780 | 39 | 97 | 84 | +5.8 [+3.5, +8.1] | 0.000 | 0.000 |
| medhelm/openai_gpt-5-mini-2025-08-07 † | 780 | 39 | 94 | 87 | +5.5 [+3.3, +7.7] | 0.000 | 0.000 |
| medhelm/openai_o4-mini-2025-04-16 † | 780 | 39 | 88 | 93 | +4.9 [+2.7, +7.1] | 0.000 | 0.000 |
| medhelm/google_gemini-2.5-pro-preview-05-06 † | 770 | 49 | 94 | 87 | +4.5 [+2.2, +6.8] | 0.000 | 0.001 |
| medhelm/deepseek-ai_deepseek-r1 † | 760 | 59 | 87 | 94 | +2.8 [+0.4, +5.2] | 0.025 | 0.075 |
| medhelm/openai_gpt-4o-2024-05-13 † | 754 | 65 | 92 | 89 | +2.7 [+0.2, +5.2] | 0.038 | 0.075 |
| medhelm/openai_gpt-4o-mini-2024-07-18 † | 695 | 124 | 106 | 75 | -1.8 [-4.8, +1.2] | 0.262 | 0.262 |

## jev-1.13@choice: probability quality

Top-3 accuracy 100.0% | NLL 0.367 | Brier 0.209 | ECE (10 bins, top probability) 0.046 | mean confidence when right 0.84, when wrong 0.52 (n=1000)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.5 to 0.6 | 73 | 0.55 | 58.9% |
| 0.6 to 0.7 | 64 | 0.64 | 56.2% |
| 0.7 to 0.8 | 69 | 0.75 | 69.6% |
| 0.8 to 0.9 | 100 | 0.86 | 75.0% |
| 0.9 to 1.0 | 694 | 0.98 | 94.4% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 85.7% | 1000 |
| 0.5 | 82.9% | 91.3% | 829 |
| 0.7 | 75.7% | 92.7% | 757 |
| 0.9 | 60.1% | 96.3% | 601 |

## jev-1.13: probability quality

Top-3 accuracy 100.0% | NLL 0.372 | Brier 0.241 | ECE (10 bins, top probability) 0.041 | mean confidence when right 0.87, when wrong 0.71 (n=1000)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.5 to 0.6 | 86 | 0.55 | 47.7% |
| 0.6 to 0.7 | 96 | 0.65 | 58.3% |
| 0.7 to 0.8 | 112 | 0.74 | 65.2% |
| 0.8 to 0.9 | 203 | 0.85 | 80.3% |
| 0.9 to 1.0 | 503 | 0.95 | 96.6% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 81.9% | 1000 |
| 0.5 | 100.0% | 81.9% | 1000 |
| 0.7 | 81.8% | 88.3% | 818 |
| 0.9 | 50.3% | 96.6% | 503 |

## Notes

- Errors count as wrong. Latency percentiles use successful calls only and time the final attempt, after an untimed warm-up call per model.
- Latency depends on concurrency, network path and time of day. Quote numbers from a `--concurrency 1` run, from the same machine, close together in time.
- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, otherwise list prices applied to token counts. LLM output tokens include reasoning. Failed calls are not counted.
