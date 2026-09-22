# Benchmark: icd10-clinical-notes

- Source: `hf://datasets/birgermoell/icd10-clinical-notes@e4192bde319f7513f98796a97948168f965d461c`
- Items: 106 | run dir: `runs/icd10/full-v1`
- Headline set: lang=en, kind=clinical (n=29)
- Served models: jev-1.13 -> typesafe/jev-1.13-20260917 via TypeSafe; google/gemini-3.8-flash -> google/gemini-3.8-flash via Google AI Studio; deepseek/deepseek-v4.1-flash -> deepseek/deepseek-v4.1-flash via AtlasCloud, deepseek/deepseek-v4.1-flash via Parasail, deepseek/deepseek-v4.1-flash via Wafer, deepseek/deepseek-v4.1-flash via DeepInfra, deepseek/deepseek-v4.1-flash via Morph, deepseek/deepseek-v4.1-flash via Makora, deepseek/deepseek-v4.1-flash via Fireworks, deepseek/deepseek-v4.1-flash via Venice, deepseek/deepseek-v4.1-flash via DigitalOcean; stringmatch -> stringmatch

## Headline

| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |
|---|---|---|---|---|---|---|---|---|
| jev-1.13 | 29 | 100.0% [88.3%, 100.0%] | 1.000 | 0 | 203 | 271 | 1314 / n/a | $0.0552 |
| google/gemini-3.8-flash | 29 | 100.0% [88.3%, 100.0%] | 1.000 | 0 | 1,037 | 2,113 | 543 / 127 | $0.8815 |
| deepseek/deepseek-v4.1-flash | 29 | 100.0% [88.3%, 100.0%] | 1.000 | 0 | 4,091 | 10,788 | 600 / 126 | $0.1973 |
| stringmatch | 29 | 6.9% [1.9%, 22.0%] | 0.052 | 0 | 0 | 0 | 0 / 0 | $0.0000 |

With n = 29, a 95% interval is up to about +/-18 points wide. Treat gaps smaller than that as noise unless the paired test below says otherwise.

## Accuracy by slice

| Model | all (n=106) | lang=en (n=53) | lang=sv (n=53) | kind=clinical (n=58) | kind=templated (n=48) | en/clinical (n=29) | en/templated (n=24) | sv/clinical (n=29) | sv/templated (n=24) |
|---|---|---|---|---|---|---|---|---|---|
| jev-1.13 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| google/gemini-3.8-flash | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| deepseek/deepseek-v4.1-flash | 98.1% | 100.0% | 96.2% | 96.6% | 100.0% | 100.0% | 100.0% | 93.1% | 100.0% |
| stringmatch | 25.5% | 49.1% | 1.9% | 3.4% | 52.1% | 6.9% | 100.0% | 0.0% | 4.2% |

## Paired comparison against jev-1.13

Same items, scored item by item, on the headline set. The exact McNemar test uses only the items where the two models disagree. Holm p corrects for testing several models against one reference. The difference is model minus reference: an interval that excludes 0 is a real gap, and an interval that includes 0 only shows equivalence as tightly as it is narrow.

| Model | Both right | Only reference right | Only model right | Both wrong | Accuracy difference [95% CI] | McNemar p | Holm p |
|---|---|---|---|---|---|---|---|
| google/gemini-3.8-flash | 29 | 0 | 0 | 0 | +0.0 [+0.0, +0.0] | 1.000 | 1.000 |
| deepseek/deepseek-v4.1-flash | 29 | 0 | 0 | 0 | +0.0 [+0.0, +0.0] | 1.000 | 1.000 |
| stringmatch | 2 | 27 | 0 | 0 | -93.1 [-102.3, -83.9] | 0.000 | 0.000 |

## jev-1.13: probability quality

Top-3 accuracy 100.0% | NLL 0.005 | Brier 0.001 | ECE (10 bins, top probability) 0.004 | mean confidence when right 1.00, when wrong nan (n=29)

Reliability by bin of the top probability. ECE is noisy when bins hold few items.

| Bin | Items | Mean probability | Accuracy |
|---|---|---|---|
| 0.9 to 1.0 | 29 | 1.00 | 100.0% |

Selective accuracy: answer only when confidence >= threshold (for a Noul, the probability of the chosen label).

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 100.0% | 29 |
| 0.5 | 100.0% | 100.0% | 29 |
| 0.7 | 100.0% | 100.0% | 29 |
| 0.9 | 100.0% | 100.0% | 29 |

## Notes

- Errors count as wrong. Latency percentiles use successful calls only and time the final attempt, after an untimed warm-up call per model.
- Latency depends on concurrency, network path and time of day. Quote numbers from a `--concurrency 1` run, from the same machine, close together in time.
- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, otherwise list prices applied to token counts. LLM output tokens include reasoning. Failed calls are not counted.
