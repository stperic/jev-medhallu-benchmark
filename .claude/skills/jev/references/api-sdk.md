# Jev API, SDKs and OpenRouter

Checked 2026-09-21 against `jev-1.13` and `typesafe-sdk` 0.7.0. Live sources:
<https://docs.typesafe.ai/api.md>, <https://docs.typesafe.ai/sdk/python.md>,
<https://docs.typesafe.ai/models.md>,
<https://openrouter.ai/docs/guides/community/typesafe-sdk.md>.

## Contents
- HTTP API
- Models, aliases, limits, price
- OpenRouter
- Python SDK
- JavaScript SDK
- Recipes: binary, ordinal, multi-label, many questions

## HTTP API

```http
POST https://api.typesafe.ai/v1/systemone        # or https://openrouter.ai/api/v1/systemone
Authorization: Bearer <key>
Content-Type: application/json
```

```json
{
  "state": {"ticket": "My checkout page is blank after I click Pay.", "customer_tier": "enterprise"},
  "model": "jev-1.13.0",
  "questions": {
    "team":    {"type": "choice", "instructions": "Which team should own `ticket`?",
                "criteria": {"payments": "Checkout, billing", "frontend": "Rendering, layout", "account": null}},
    "is_bug":  {"type": "noul", "instructions": "Does `ticket` report broken product behavior?",
                "criteria": {"true": "Something that should work does not", "false": "A question or feature request"}},
    "urgency": {"type": "score", "instructions": "How urgent is `ticket`?",
                "criteria": ["Can wait for the next release", "Fix this week", "Blocking revenue now"]}
  }
}
```

- `state`: a string, JSON object, or array. Objects with named fields work
  best; refer to fields with backticked paths.
- `instructions` and each criteria value can be a string, object or array.
  Choice criteria values can be `null` when the key speaks for itself.
- Question IDs are yours and are **not** sent to the model. Choice option keys
  **are** sent, along with their descriptions.
- Choice allows up to 255 options. Score takes 2 to 10 ordered levels.

Response:

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "team":    {"type": "choice", "choice": "payments", "confidence": 0.75,
                "probabilities": {"payments": 0.84, "frontend": 0.16, "account": 0.0}},
    "is_bug":  {"type": "noul", "noul": 0.96},
    "urgency": {"type": "score", "score": 1.99, "confidence": 0.99,
                "legend": {"0": "Can wait for the next release", "1": "Fix this week", "2": "Blocking revenue now"},
                "probabilities": {"0": 0.0, "1": 0.01, "2": 0.99}}
  },
  "usage": {"input_tokens": 476, "output_tokens": 70}
}
```

- `choice` is the highest-probability option. `probabilities` sum to 1.
- `confidence` (Choice and Score only) is derived from how concentrated
  `probabilities` is. For three options the docs approximate it as
  `(3 * max_p - 1) / 2`. It is not P(correct).
- `score` is the probability-weighted level. Use it for thresholds, not to
  recover exact magnitudes between levels.
- `noul` is P(yes).
- The response header `x-typesafe-request-id` identifies the call.

Errors: `401` bad key; `422` validation (the body names the field); `429` rate
limit (may carry `retry-after`); `529` overloaded. Retry 408, 429, 5xx and
connection errors with backoff. Do not retry other 4xx errors.

## Models, aliases, limits, price

| Item | Value |
|---|---|
| Current model | `jev-1.13.0` |
| Aliases | `jev-latest` (stable), `jev-preview` (newest, may be unofficial). Both point to `jev-1.13.0` today |
| Price | USD 0.042 per 1M input tokens; output tokens free |
| Rate limits | 250,000 tokens/s and 1,200 requests/min, "adjusting dynamically" |
| Context | 64k tokens per request; 32k for `state` + the longest single question |
| Input | Text only (string, object, array of text). English is best |
| Customization | None: the same weights serve everyone. Shape behavior through state, instructions and criteria |

`GET https://api.typesafe.ai/v1/models` lists the aliases. Versioned IDs are
accepted even when not listed.

## OpenRouter

OpenRouter serves Jev (added 2026-09-18) on its System One API, which
implements TypeSafe's request and response shapes.

- Base URL `https://openrouter.ai/api`. The SDK appends `/v1/systemone`.
  Authenticate with your OpenRouter key as the bearer token.
- Model IDs: `jev-1.13` routes to `typesafe/jev-1.13`; `jev-latest` routes to
  `~typesafe/jev-latest`; IDs with an author prefix (`typesafe/jev-1.13`) pass
  through. The response `model` is the served ID, e.g. `typesafe/jev-1.13-20260917`.
- Extra response fields: `id` (e.g. `gen-dec-...`), `provider` (`TypeSafe`)
  and `usage.cost` in USD. The SDKs ignore them; read them from
  `resp.raw_http_response.json()` in Python.
- The endpoint listing (`/api/v1/models/typesafe/jev-1.13/endpoints`) shows one
  provider, TypeSafe, at the same price and a 32,000-token context.
- The SDK's `models.list()` does not work against OpenRouter, whose Models API
  has a different shape.
- OpenRouter-specific errors include `402` (insufficient credits).
- An alpha `POST /api/alpha/decisions` endpoint accepts the same body plus
  `provider` (routing preferences), `session_id`, `trace` and `user`. The SDKs
  target `/v1/systemone`; use the alpha endpoint only if you need those fields.

## Python SDK

```bash
uv add typesafe-sdk   # or: pip install typesafe-sdk  (Python >= 3.10)
```

```python
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score, RetryPolicy

async with AsyncTypeSafeClient() as client:
    resp = await client.system_one(
        {"ticket": text},
        {
            "team": Choice(instructions="Which team should own `ticket`?",
                           criteria={"payments": "Checkout, billing", "frontend": "Rendering"}),
            "is_bug": Noul(instructions="Does `ticket` report broken product behavior?"),
            "urgency": Score(instructions="How urgent is `ticket`?",
                             criteria=["Can wait", "This week", "Blocking revenue"]),
        },
        model="jev-1.13.0",
    )
resp.choices["team"].choice, resp.choices["team"].probabilities, resp.choices["team"].confidence
resp.nouls["is_bug"].noul
resp.scores["urgency"].score
resp.answers["team"]                       # same objects, keyed by question ID
resp.model; resp.usage.input_tokens; resp.request_id; resp.raw_http_response
```

- `TypeSafeClient` is the synchronous twin with the same signature.
- Environment: `TYPESAFE_API_KEY` (required), `TYPESAFE_BASE_URL` (default
  `https://api.typesafe.ai`), `TYPESAFE_DEFAULT_MODEL` (default `jev-latest`),
  `TYPESAFE_LOG_LEVEL` (`debug` logs request and response bodies, unredacted).
- Typed responses: pass `response_model=` a subclass of `SystemOneResponse`
  with one field per question ID (e.g. `billing: NoulAnswer`) to get
  attribute access that a type checker understands.
- Defaults: 10 s timeout per HTTP operation. `RetryPolicy()` is
  `max_retries=2`, backoff 0.5 s doubling to 5 s with 25% jitter, retrying
  408/429/5xx plus connection and timeout errors, honoring `Retry-After`, with a
  30 s total budget per call. Pass `RetryPolicy(max_retries=0)` when you want to
  own retries, for example to time each attempt separately.
- Exceptions: `TypeSafeError` is the base. `TypeSafeAPIError` has `.status`,
  `.body`, `.headers` and `.request_id`. Subclasses: `TypeSafeBadRequestError`
  (400), `TypeSafeAuthenticationError` (401), `TypeSafePermissionDeniedError`
  (403), `TypeSafeNotFoundError` (404), `TypeSafeUnprocessableEntityError`
  (422), `TypeSafeRateLimitError` (429, `.retry_after_ms`),
  `TypeSafeInternalServerError` (5xx). Also `TypeSafeAPIConnectionError`, with
  `TypeSafeAPITimeoutError` as a subclass, and `TypeSafeAPIResponseValidationError`.
- `Score(criteria=[...])` takes an ordered list (a dict before v0.6.0).
  Questions can also be plain dicts in the HTTP shape.
- `extra_body={...}` forwards request fields the SDK predates.

## JavaScript SDK

```bash
npm install @typesafe-ai/sdk
```

```typescript
import { TypeSafeClient } from "@typesafe-ai/sdk";
const client = new TypeSafeClient();   // or { apiKey: process.env.OPENROUTER_API_KEY, baseURL: "https://openrouter.ai/api" }
const result = await client.systemOne({ model: "jev-1.13.0", state, questions });
```

Reference: <https://docs.typesafe.ai/sdk/javascript.md>.

## Recipes: binary, ordinal, multi-label, many questions

**Binary decision.** Ask a Noul and threshold `noul`. Pick the threshold from
labeled dev data and the cost of each error type; 0.5 is not automatically
right. AUROC and Brier score measure it without choosing a threshold.

**Ordinal grade.** Ask a Score. For a discrete level, take the argmax of
`probabilities` (keys are string indexes). Use `score` for "at least level k"
style thresholds. Describe each level as a concrete situation that stands on
its own.

**Multi-label.** One Noul per label, all in one request. A Choice would force
exactly one answer, and its probabilities compete, while Nouls are independent.

**Many questions about one text.** Put them all in one `questions` map. They
run in parallel and are independent, and the state is billed once. In TypeSafe's
parallel-questions cookbook, 13 questions in one call came out about 12x
cheaper and 10x faster than 13 separate calls, with identical answers.

**More options than fit.** Above 255 options, or when options have natural
groups, chain Choices down a hierarchy and keep the top few paths (beam search)
instead of committing greedily.
