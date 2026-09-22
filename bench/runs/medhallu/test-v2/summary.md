# Benchmark: medhallu

- Source: `MedHELM v4.0.0 medhallu (gs://crfm-helm-public/medhelm) over hf://datasets/UTAustin-AIHealth/MedHallu`
- Items: 1000 | run dir: `runs/medhallu/test-v2`
- Headline set: all items (n=1000)
- Served models: jev-1.13 -> typesafe/jev-1.13-20260917 via TypeSafe; google/gemini-3.5-flash-lite -> google/gemini-3.5-flash-lite via Google AI Studio; openai/gpt-5.6-luna@none -> openai/gpt-5.6-luna via OpenAI; anthropic/claude-haiku-4.5 -> anthropic/claude-haiku-4.5 via Anthropic; google/gemini-3.8-flash@minimal -> google/gemini-3.8-flash via Google AI Studio
- Labels for runs with probabilities re-derived at P(1) >= 0.65

## Headline

| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |
|---|---|---|---|---|---|---|---|---|
| jev-1.13 | 1000 | 92.9% [91.1%, 94.3%] | 0.929 | 0 | 204 | 292 | 695 / n/a | $0.0292 |
| google/gemini-3.5-flash-lite | 1000 | 93.5% [91.8%, 94.9%] | 0.935 | 0 | 536 | 696 | 679 / 11 | $0.2301 |
| openai/gpt-5.6-luna@none | 1000 | 92.9% [91.1%, 94.3%] | 0.929 | 0 | 1,142 | 1,764 | 680 / 12 | $0.1505 |
| anthropic/claude-haiku-4.5 | 1000 | 92.0% [90.2%, 93.5%] | 0.920 | 0 | 680 | 1,095 | 913 / 9 | $0.9599 |
| google/gemini-3.8-flash@minimal | 1000 | 87.2% [85.0%, 89.1%] | 0.872 | 0 | 1,330 | 3,912 | 679 / 138 | $1.0286 |
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
| jev-1.13 | 92.8% | 93.8% | 91.2% | 0.925 | 0.974 | 438 / 42 / 29 / 491 |
| google/gemini-3.5-flash-lite | 93.5% | 92.8% | 93.8% | 0.933 | n/a | 450 / 30 / 35 / 485 |
| openai/gpt-5.6-luna@none | 92.9% | 91.6% | 93.8% | 0.927 | n/a | 450 / 30 / 41 / 479 |
| anthropic/claude-haiku-4.5 | 92.1% | 88.9% | 95.2% | 0.920 | n/a | 457 / 23 / 57 / 463 |
| google/gemini-3.8-flash@minimal | 87.5% | 81.3% | 95.2% | 0.877 | n/a | 457 / 23 / 105 / 415 |
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

Threshold sweep for jev-1.13 (accuracy when P(1) >= t). Pick a threshold on dev only, then apply it to test with `--threshold`.

| t | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|---|---|---|
| accuracy | 53.2% | 74.5% | 82.7% | 87.9% | 91.2% | 92.4% | 93.0% | 90.6% | 81.7% |

## Accuracy by slice

| Model | all (n=1000) | gold=0 (n=520) | gold=1 (n=480) | difficulty=easy (n=255) | difficulty=hard (n=418) | difficulty=medium (n=327) | category=Incomplete Information (n=109) | category=Mechanism and Pathway Misattribution (n=15) | category=Methodological and Evidence Fabrication (n=3) | category=Misinterpretation of #Question# (n=353) |
|---|---|---|---|---|---|---|---|---|---|---|
| jev-1.13 | 92.9% | 94.4% | 91.2% | 95.7% | 91.1% | 93.0% | 87.2% | 100.0% | 100.0% | 92.1% |
| google/gemini-3.5-flash-lite | 93.5% | 93.3% | 93.8% | 95.3% | 90.7% | 95.7% | 91.7% | 100.0% | 100.0% | 94.1% |
| openai/gpt-5.6-luna@none | 92.9% | 92.1% | 93.8% | 96.9% | 90.4% | 93.0% | 89.9% | 100.0% | 100.0% | 94.6% |
| anthropic/claude-haiku-4.5 | 92.0% | 89.0% | 95.2% | 96.1% | 88.0% | 93.9% | 89.0% | 100.0% | 100.0% | 96.9% |
| google/gemini-3.8-flash@minimal | 87.2% | 79.8% | 95.2% | 90.2% | 85.6% | 86.9% | 93.6% | 100.0% | 100.0% | 95.5% |
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
| google/gemini-3.5-flash-lite | 901 | 28 | 34 | 37 | +0.6 [-0.9, +2.1] | 0.526 | 1.000 |
| openai/gpt-5.6-luna@none | 893 | 36 | 36 | 35 | +0.0 [-1.7, +1.7] | 1.000 | 1.000 |
| anthropic/claude-haiku-4.5 | 885 | 44 | 35 | 36 | -0.9 [-2.6, +0.8] | 0.368 | 1.000 |
| google/gemini-3.8-flash@minimal | 842 | 87 | 30 | 41 | -5.7 [-7.8, -3.6] | 0.000 | 0.000 |
| medhelm/anthropic_claude-3-5-sonnet-20241022 † | 897 | 32 | 29 | 42 | -0.3 [-1.8, +1.2] | 0.798 | 1.000 |
| medhelm/google_gemini-2.0-flash-001 † | 878 | 51 | 30 | 41 | -2.1 [-3.9, -0.3] | 0.026 | 0.128 |
| medhelm/openai_gpt-5-2025-08-07 † | 882 | 47 | 23 | 48 | -2.4 [-4.0, -0.8] | 0.006 | 0.033 |
| medhelm/openai_o3-mini-2025-01-31 † | 870 | 59 | 26 | 45 | -3.3 [-5.1, -1.5] | 0.000 | 0.003 |
| medhelm/google_gemini-1.5-pro-001 † | 869 | 60 | 22 | 49 | -3.8 [-5.6, -2.0] | 0.000 | 0.000 |
| medhelm/meta_llama-3.3-70b-instruct † | 864 | 65 | 18 | 53 | -4.7 [-6.5, -2.9] | 0.000 | 0.000 |
| medhelm/anthropic_claude-3-7-sonnet-20250219 † | 847 | 82 | 30 | 41 | -5.2 [-7.2, -3.2] | 0.000 | 0.000 |
| medhelm/openai_gpt-5-mini-2025-08-07 † | 852 | 77 | 22 | 49 | -5.5 [-7.4, -3.6] | 0.000 | 0.000 |
| medhelm/openai_o4-mini-2025-04-16 † | 851 | 78 | 17 | 54 | -6.1 [-8.0, -4.2] | 0.000 | 0.000 |
| medhelm/google_gemini-2.5-pro-preview-05-06 † | 845 | 84 | 19 | 52 | -6.5 [-8.4, -4.6] | 0.000 | 0.000 |
| medhelm/deepseek-ai_deepseek-r1 † | 825 | 104 | 22 | 49 | -8.2 [-10.3, -6.1] | 0.000 | 0.000 |
| medhelm/openai_gpt-4o-2024-05-13 † | 822 | 107 | 24 | 47 | -8.3 [-10.5, -6.1] | 0.000 | 0.000 |
| medhelm/openai_gpt-4o-mini-2024-07-18 † | 773 | 156 | 28 | 43 | -12.8 [-15.3, -10.3] | 0.000 | 0.000 |

## jev-1.13: probability quality

Top-3 accuracy 100.0% | NLL 0.266 | Brier 0.146 | ECE (10 bins, top probability) 0.102 | mean confidence when right 0.83, when wrong 0.64 (n=1000)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.5 to 0.6 | 75 | 0.55 | 78.7% |
| 0.6 to 0.7 | 99 | 0.65 | 75.8% |
| 0.7 to 0.8 | 138 | 0.75 | 85.5% |
| 0.8 to 0.9 | 316 | 0.85 | 97.2% |
| 0.9 to 1.0 | 372 | 0.94 | 99.5% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 92.9% | 1000 |
| 0.5 | 94.9% | 94.4% | 949 |
| 0.7 | 82.6% | 96.2% | 826 |
| 0.9 | 37.2% | 99.5% | 372 |

## Notes

- Errors count as wrong. Latency percentiles use successful calls only and time the final attempt, after an untimed warm-up call per model.
- Latency depends on concurrency, network path and time of day. Quote numbers from a `--concurrency 1` run, from the same machine, close together in time.
- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, otherwise list prices applied to token counts. LLM output tokens include reasoning. Failed calls are not counted.
