# Benchmark: icd10-clinical-notes

- Source: `hf://datasets/birgermoell/icd10-clinical-notes@e4192bde319f7513f98796a97948168f965d461c`
- Items: 5 | run dir: `runs/smoke`
- Served models: jev-1.13 -> typesafe/jev-1.13-20260917 via TypeSafe; anthropic/claude-opus-5@low -> anthropic/claude-opus-5 via Anthropic; stringmatch -> stringmatch

## Headline

| Model | n | Accuracy [95% CI] | Macro-F1 | Errors | p50 ms | p95 ms | Mean in/out tokens | $ per 1k items |
|---|---|---|---|---|---|---|---|---|
| jev-1.13 | 5 | 100.0% [56.6%, 100.0%] | 1.000 | 0 | 222 | 1,088 | 1300 / 496 | $0.0546 |
| anthropic/claude-opus-5@low | 5 | 100.0% [56.6%, 100.0%] | 1.000 | 0 | 2,011 | 2,333 | 1352 / 11 | $7.0370 |
| stringmatch | 5 | 60.0% [23.1%, 88.2%] | 0.600 | 0 | 0 | 0 | 0 / 0 | $0.0000 |

With n = 5, a 95% interval is up to about +/-44 points wide. Treat gaps smaller than that as noise unless the paired test below says otherwise.

## Accuracy by slice

| Model | all (n=5) | kind=clinical (n=2) | kind=templated (n=3) | en/clinical (n=2) | en/templated (n=3) |
|---|---|---|---|---|---|
| jev-1.13 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| anthropic/claude-opus-5@low | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| stringmatch | 60.0% | 0.0% | 100.0% | 0.0% | 100.0% |

## Paired comparison against jev-1.13

Same items, scored item by item. The exact McNemar test uses only the items where the two models disagree.

| Model | Both right | Only reference right | Only model right | Both wrong | McNemar p |
|---|---|---|---|---|---|
| anthropic/claude-opus-5@low | 5 | 0 | 0 | 0 | 1.000 |
| stringmatch | 3 | 2 | 0 | 0 | 0.500 |

## jev-1.13: probability quality

Top-3 accuracy 100.0% | NLL 0.019 | Brier 0.003 | ECE (10 bins, top probability) 0.018 | mean confidence when right 0.98, when wrong nan (n=5)

Selective accuracy: answer only when `confidence` >= threshold.

| Threshold | Coverage | Accuracy on covered | Items kept |
|---|---|---|---|
| 0.0 | 100.0% | 100.0% | 5 |
| 0.5 | 100.0% | 100.0% | 5 |
| 0.7 | 100.0% | 100.0% | 5 |
| 0.9 | 100.0% | 100.0% | 5 |

## Notes

- Errors count as wrong. Latency percentiles use successful calls only and time the final attempt; retries are recorded per item in the run files.
- Latency depends on concurrency, network path and time of day. Quote numbers from a `--concurrency 1` run, from the same machine, close together in time.
- Costs are OpenRouter's reported per-call charge (`usage.cost`) where present, otherwise list prices applied to token counts. LLM output tokens include reasoning. Failed calls are not counted.
