# Validating and benchmarking Jev

Use this before shipping a Jev decision, when tuning thresholds, or when
comparing Jev with an LLM.

## Contents
- Design the comparison
- Give every model the same information
- Accuracy and its uncertainty
- Paired comparison
- Probability quality (Jev only)
- Latency
- Cost
- Vendor numbers
- Report template

## Design the comparison

1. **Fix the claim first.** "Is Jev as accurate as model X on task T?", "What
   does each cost per 1,000 items?" and "Can Jev's confidence route the hard
   cases to an LLM?" need different metrics. Write down the primary metric and
   the headline subset before running anything, so the report can't drift
   toward whichever subset looks best.
2. **Audit the data.** Look for duplicate items, fields that leak the answer,
   templated or keyword-searchable items, train/test overlap (this matters for
   trained baselines only) and language mix. Freeze the item file and record
   its hash.
3. **Add a floor.** A trivial baseline, such as keyword or string match against
   the label names, shows which items are too easy to separate models. Report
   those items as their own slice.
4. **Keep hard cases in.** Items that need arithmetic, date logic or multi-step
   reasoning are where an LLM should beat Jev. Report them as a slice rather
   than dropping them. Dropping flatters Jev, and burying them hides where Jev
   is useful.
5. **Split dev and test.** Tune wording and thresholds on dev, for Jev and the
   LLM alike, then run test once.

## Give every model the same information

- The same text, question wording, option names and descriptions.
- The same answer space. Constrain the LLM with structured output: a
  JSON-schema `enum` of the option keys, with strict mode where the provider
  supports it. Jev can't answer outside the set; the LLM shouldn't be able to either.
- Record the LLM's reasoning or effort setting. It dominates the LLM's latency
  and cost, so it is part of the contender's identity. Benchmark at least a low
  setting and the default.
- Pin versions: `jev-1.13.0` (TypeSafe) or `jev-1.13` (OpenRouter) rather than
  `jev-latest`, and dated LLM IDs where they exist. Log the served model from
  every response.
- Through OpenRouter, pin the LLM provider (`provider.order` with
  `allow_fallbacks: false`) for latency runs, and set
  `provider.require_parameters: true` so requests only reach endpoints that
  honor structured output. Routing Jev and the LLMs through the same gateway
  puts the same network hop in every measurement.

## Accuracy and its uncertainty

Report accuracy with a 95% Wilson interval. Wilson behaves at small n and
near 0% or 100%. The worst-case half-width is about `1 / sqrt(n)`:

| n | ±95% half-width (at 50%) |
|---|---|
| 30 | 18 points |
| 100 | 10 points |
| 400 | 5 points |
| 1,000 | 3 points |

On a small set only large gaps are real. Finer claims need more items;
repeating the same items only measures model noise. Report macro-F1 as well
on imbalanced label sets, so frequent labels can't hide failures on rare ones.

## Paired comparison

Every model answers the same items, so compare them item by item. The exact
McNemar test uses only the discordant items (`b` = Jev right and the other
wrong, `c` = the reverse). Its p-value is the two-sided binomial probability of
a split at least that uneven when `b + c` coin flips are fair. It is much more
sensitive than checking whether two intervals overlap. Report `b` and `c` as
well. When several models are tested against one reference, mention the
multiple comparisons, or apply Holm's correction before leaning on a borderline p.

## Probability quality (Jev only)

LLM APIs generally return no comparable probabilities, so present these as
properties of Jev, not as a contest:

- **Top-k accuracy** from `probabilities`: gold among the k most probable
  options. This matters when Jev shortlists candidates for a person or an LLM.
- **NLL:** mean `-log p(gold)`. It punishes confident misses.
- **Brier:** mean of `sum_k (p_k - 1[k = gold])^2`, from 0 to 2.
- **ECE:** 10 equal-width bins on the predicted option's probability, then the
  weighted mean of |accuracy - mean probability|. It is noisy below a few
  hundred items, so show bin counts or a reliability plot.
- **Selective accuracy:** answer only when `confidence >= t`, then report
  coverage and accuracy on the answered items. Choose `t` on dev.
- **Cascade:** Jev when `confidence >= t`, otherwise the LLM. Its blended
  accuracy, cost and latency are often the most practical headline for a
  System One model.

Jev is close to deterministic. Repeat a subset 3 times if you claim stability.

## Latency

- Time the final successful attempt, from just before the call until the parsed
  answer. Retry with your own loop (SDK retries off), so a 429 backoff never
  hides inside a latency number, and record the attempts.
- Quote p50 and p95, not the mean.
- Measure at concurrency 1, from one machine, with all models run close
  together in time. Vendor load changes through the day.
- The first calls pay connection setup. Discard them on small runs.
- Throughput (items per second at high concurrency, within rate limits) is a
  separate claim and a separate experiment.

## Cost

- Use reported token counts, or OpenRouter's `usage.cost`, which is the actual
  charge. Name the price date.
- Jev bills input only, so its cost follows state + questions + options. A
  long option list is billed on every call.
- LLM output tokens include reasoning tokens.
- Mention the levers that would cut the LLM's production cost: prompt caching
  of a static prefix, batch APIs at about 50% off (no latency claim then), and a
  smaller model or lower effort. Ignoring them makes the comparison unfair to
  the LLM.
- Report cost per 1,000 items, and cost per correct answer when accuracy
  differs a lot.

## Vendor numbers

TypeSafe's headline claims ("193.6x faster, 244.6x cheaper" than LLMs on
System One tasks) come from its "workflow evals". Those score agreement with
the average of frontier models, on TypeSafe-chosen tasks, not accuracy against
ground truth. "0% hallucination" means every answer is one of your options, not
that it is correct. Keep vendor figures out of your results table, and don't
quote third-party accuracy numbers you can't trace to a reproducible run.

## Report template

```markdown
# Jev vs <models> on <dataset>: <date>

**Claim tested:** <one sentence, fixed before the run>
**Headline slice:** <slice> (n=<n>)

| Model (version, effort) | Accuracy [95% CI] | vs Jev: b / c, McNemar p | p50 / p95 latency | $ per 1k items |
|---|---|---|---|---|

**Setup:** items <hash>, prompt <hash>, gateway <TypeSafe | OpenRouter, providers>,
machine and region, time, concurrency, prices as of <date>, SDK versions.

**Findings:** 3 to 5 bullets, each tied to a number above. Separate what the
data shows from what it cannot show at this n.

**Jev probability quality:** top-k, ECE with bin counts, and selective
accuracy at the chosen threshold.

**Caveats:** dataset limitations, slices treated separately, and anything
vendor-reported that was not reproduced.
```
