---
name: jev
description: >
  Build with TypeSafe AI's Jev, the System One model that answers typed
  questions (Choice, Score, Noul) about text with calibrated probabilities
  instead of generating text. Covers calling Jev directly or through
  OpenRouter, deciding whether a task fits Jev, writing state and questions,
  using probabilities and confidence to route and escalate, composition
  patterns (fan-out, confidence gating, composite scores,
  select-instead-of-generate, LLM cascades, tool-call gating), Jev's known
  weak spots, production settings, and validating Jev on your own labeled data
  against an LLM baseline. Use this skill whenever code calls or should call
  Jev or TypeSafe (typesafe_sdk, @typesafe-ai/sdk, /v1/systemone,
  typesafe/jev on OpenRouter), when an LLM prompt-and-parse step could become
  a structured decision, when text needs cheap and fast classification,
  routing, scoring, ranking, gating or verification, or when someone wants to
  evaluate or benchmark Jev, even if they only say "use jev for this".
---

# Jev

Jev is TypeSafe's first **System One** model. You send it text (the **state**)
and a set of typed questions. It returns, for each question, an answer that is
guaranteed to be one of the options you defined, plus a probability
distribution over those options. It does not write prose, code or
explanations. Your code owns the workflow; Jev supplies fast judgments where
ordinary code would need to understand language.

Facts here were checked on 2026-09-21 against `jev-1.13` and `typesafe-sdk`
0.7.0. TypeSafe's docs are the source of truth and change quickly:
<https://docs.typesafe.ai/llms.txt> indexes every page, and each page is served
as markdown when you append `.md` to its URL. Read the relevant page before
relying on a limit, price or signature.

## Is this a Jev task?

Ask: could a knowledgeable person answer this in about a second, from the
text in front of them, by picking from a list you could write down? If yes, it
fits Jev. Examples: which team owns this ticket, does this passage answer the
query, how frustrated is this customer, is this tool call supported by the
user's request, which of these candidate dates is the due date.

It does not fit when the answer needs arithmetic, counting, comparing dates or
numbers, several reasoning hops, or new text. Do the arithmetic in code, and
send multi-step reasoning or generation to an LLM. Often the right design
splits one task: code or an LLM proposes candidates, and Jev picks among them.

## Access: TypeSafe directly or through OpenRouter

Both use the same request and response shape, so the TypeSafe SDKs work with
either. Only the base URL, the key and the model ID change.

| | TypeSafe | OpenRouter |
|---|---|---|
| Base URL (SDK appends `/v1/systemone`) | `https://api.typesafe.ai` (default) | `https://openrouter.ai/api` |
| Key | TypeSafe key (console.typesafe.ai/keys) | OpenRouter key |
| Pinned model | `jev-1.13.0` | `jev-1.13` (routed as `typesafe/jev-1.13`) |
| Moving alias | `jev-latest` | `jev-latest` (routed as `~typesafe/jev-latest`) |
| Context listed | 64k per request; 32k for state + longest question | 32k |
| Extra response fields | | `id`, `provider`, `usage.cost` (USD) |

```python
import os
from typesafe_sdk import TypeSafeClient

# TypeSafe directly: reads TYPESAFE_API_KEY.
client = TypeSafeClient()
# Through OpenRouter: billed to OpenRouter credits.
client = TypeSafeClient(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api")
```

Setting `TYPESAFE_BASE_URL=https://openrouter.ai/api` and putting the
OpenRouter key in `TYPESAFE_API_KEY` does the same without code changes. On
OpenRouter, the SDK's `models.list()` fails because OpenRouter's Models API has
a different shape; query `GET https://openrouter.ai/api/v1/models/typesafe/jev-1.13/endpoints`
instead. OpenRouter also has an alpha `Decisions` endpoint with the same shape
plus `provider` and `session_id` fields. Prefer `/v1/systemone`, which the SDKs
target. OpenRouter is convenient when the same application also calls LLMs
(cascades, baselines), because one key and one bill cover everything.

## Design the call

**State.** Use a JSON object with named fields (`{"ticket": ..., "policy": ...}`)
rather than one blob, and include only what the decision needs. Irrelevant
text lowers accuracy. Input is text only. English works best, and other
languages work less well.

**Pick the primitive by what the answer means:**

| Need | Primitive | Returns |
|---|---|---|
| One option from a set with no order | `Choice` (up to 255 options) | `choice`, `probabilities`, `confidence` |
| A position on ordered levels | `Score` (2 to 10 levels) | `score` (expected level, can fall between levels), `legend`, `probabilities`, `confidence` |
| Whether a condition holds | `Noul` | `noul` = P(yes), no `confidence` |
| Several labels can apply | one `Noul` per label | |

**Write each question as a complete judgment.** Question IDs are for your code
and are never sent to the model, so the full meaning belongs in
`instructions`. Choice option keys and their descriptions are sent. Write
descriptions that separate the options from each other, and add an `other` or
`none of these` option when nothing may fit. Refer to parts of the state by
backticked path (`` `ticket.messages[0].text` ``). Instructions and criteria
can be objects (definition, exclusions, examples) when a string is not enough.
Keep instructions and criteria consistent with each other; a Noul whose `true`
means "no" performs worse.

**Ask independent questions together.** All questions in one request see the
same state, run in parallel, and cannot see each other's answers. Adding
questions barely changes latency, and the state is billed once, so ask
speculative questions up front and let code ignore the irrelevant answers. Make
a second request only when its state or options depend on an earlier answer.

**Keep questions and thresholds in one module.** They are the product logic.
Reviewers need to find them, and they are what you tune.

## Use the answer

- `choice` is the highest-probability option. `probabilities` sum to 1.
- `confidence` (Choice and Score) says how concentrated the distribution is: 1.0
  when all probability sits on one option, lower as it spreads. It is not
  P(correct). If you only need the best option, take `choice` and ignore
  confidence. If you need a calibrated probability, use `probabilities`.
- `noul` near 0.5 means yes and no are equally likely, not "medium".
- Gate actions by risk: act automatically above a high threshold, confirm or
  review in the middle, and escalate below it. Destructive actions deserve a
  higher bar than reversible ones. Choose thresholds on labeled data from your
  domain; the numbers in docs and cookbooks are examples.
- A threshold tuned for one question form does not transfer to another. A
  Noul and a two-option Choice asking the same thing return different numbers,
  and P(X) + P(not X) need not equal 1.
- Pin the model version once thresholds are tuned. Aliases move, and every
  response's `model` field says what actually answered, so log it.

## Patterns

Starting points, each with a worked example in TypeSafe's docs
(`https://docs.typesafe.ai/<path>.md`):

- **Route and fill arguments:** pick a handler and its closed-set parameters in
  one request (`cookbooks/function_calling`, `patterns/intent-routing`).
- **Select instead of generate:** find candidate values or spans with code
  (regex, parser, retrieval), then a Choice picks one
  (`cookbooks/pre_parsed_value_extraction_cookbook`, `cookbooks/date_extraction_cookbook`).
- **Rerank and filter evidence:** one question per query and candidate pair, or
  per retrieved passage (`cookbooks/rerank_typesafe`, `cookbooks/classifying_rag_passages`).
- **Composite scoring:** split a broad judgment into atomic Scores and weight
  them in code, so policy changes don't need new inference (`patterns/composite-scoring`).
- **Confidence-gated escalation and cascades:** Jev handles confident cases and
  hands the rest to a person or an LLM (`patterns/confidence-routing`, `cookbooks/sde_cascade`).
- **Verify and guard:** check a claim, citation or LLM output against its
  source, or screen inputs and outputs for hazards (`cookbooks/citation_check`,
  `cookbooks/llm_guardrails`).
- **Gate agent tool calls:** check each risky tool call against the user's
  request, so safe calls run, unsupported calls are refused and ambiguous ones
  pause (OpenRouter cookbook: <https://openrouter.ai/docs/cookbook/building-agents/gate-tool-calls-with-jev.md>).
- **More than 255 labels:** walk the hierarchy level by level with beam search
  over Choice probabilities (`cookbooks/hierarchical_classification`).

## Weak spots (TypeSafe's list for jev-1.13)

| Weak spot | Do this instead |
|---|---|
| Reads literally: scoping words and negations taken at face value | State the exact condition; put boundary cases in the criteria |
| Arithmetic, counting, numeric closeness, hex and RGB values | Compute in code; pass the number or a named bucket |
| Comparing dates and time windows | Extract date parts with Choices; compare in code |
| Multi-hop indirection, double negatives | Ask directly; name the relevant state field |
| Large state full of irrelevant detail | Filter first; use a Noul to test relevance if needed |
| Adversarial or self-describing content (prompt injection) | Precise criteria, and test hostile inputs before launch |
| Generating text | Use an LLM, or turn it into a Choice over candidates |

## Production settings

- SDK defaults: 10 s HTTP timeout; `RetryPolicy` retries 408, 429 and 5xx plus
  connection errors twice with backoff, within a 30 s budget, honoring
  `Retry-After`. Errors to expect: `401` bad key, `422` malformed question
  (the body names the field), `429` rate limited, `529` overloaded; OpenRouter
  adds `402` when credits run out.
- TypeSafe's rate limits are 1,200 requests/min and 250k tokens/s, and are
  "adjusting dynamically". Batch questions per state rather than sending one
  question per request.
- Price: USD 0.042 per million input tokens, and output is free, so cost scales
  with state plus question text. A long option list is billed on every call.
- Log the served `model`, the request ID (`x-typesafe-request-id`, or the
  OpenRouter `id`) and the answers, so a decision can be traced later.
- Keep API keys server-side. `TYPESAFE_LOG_LEVEL=debug` logs request and
  response bodies unredacted, so avoid it when the state holds personal data.

## Validate on your data

Typed output guarantees the interface, not correctness. Before shipping a Jev
decision, or claiming it matches an LLM, measure it on labeled examples from
your domain:

1. Collect a labeled set and split it into dev and test. Tune the wording and
   thresholds on dev only.
2. Run the same items through Jev and through the LLM step it replaces or
   competes with. Give both the same text, question and options. Constrain the
   LLM with a JSON-schema `enum`, so both answer from the same set.
3. Report accuracy with a confidence interval and a paired test, latency as
   p50/p95 from one machine, and cost per 1,000 calls. Report Jev's calibration
   and its selective accuracy at your thresholds.

`references/evaluation.md` gives the metrics, statistics, fairness checklist
and a report template.

## Try it

`scripts/ask.py` sends one request and prints each answer's distribution,
confidence, tokens, cost and latency. Use it to compare phrasings before
writing application code. It uses `TYPESAFE_API_KEY` if set, otherwise
`OPENROUTER_API_KEY` through OpenRouter. Keys can sit in a git-ignored `.env`,
loaded with `uv run --env-file .env ...` or `UV_ENV_FILE=.env`.

```bash
uv run <skill-dir>/scripts/ask.py --state "I was charged twice, please fix ASAP" \
  --questions '{"team": {"type": "choice", "instructions": "Which team should handle this?",
                "criteria": {"billing": "Charges, refunds", "technical": "Bugs, outages"}},
                "urgent": {"type": "noul", "instructions": "Does the customer say this is time-sensitive?"}}'
```

## References

- `references/api-sdk.md`: HTTP request and response shapes, models and
  limits, Python SDK (clients, typed answers, retries, exceptions), OpenRouter
  details, and question-design rules.
- `references/evaluation.md`: validating and benchmarking Jev against LLMs:
  metrics, sample size, paired tests, latency and cost measurement, and a
  report template.
- TypeSafe publishes its own agent skill as well (`typesafe-ai/skills` on
  GitHub). It is a lighter guide that sends you to the live docs.
