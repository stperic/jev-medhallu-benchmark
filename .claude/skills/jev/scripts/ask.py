# /// script
# requires-python = ">=3.10"
# dependencies = ["typesafe-sdk>=0.7.0"]
# ///
"""Ask Jev questions about a state and print what came back.

For experiments while designing questions: shows each answer's probability
distribution and confidence, plus the served model, tokens, cost and latency.

Access:
  TypeSafe:    TYPESAFE_API_KEY=<TypeSafe key>
  OpenRouter:  OPENROUTER_API_KEY=<OpenRouter key>   (used when TYPESAFE_API_KEY is unset)
Keys can live in a .env file: uv run --env-file .env ask.py ...

Usage:
  uv run ask.py --state "I was charged twice." --questions questions.json
  uv run ask.py --state-file ticket.json --questions '{"refund": {"type": "noul", "instructions": "..."}}'
  uv run ask.py ... --model jev-1.13 --repeat 3 --json
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from typesafe_sdk import TypeSafeClient, TypeSafeError

PRICE_PER_INPUT_TOKEN = 0.042 / 1e6  # USD, jev-1.13 as of 2026-09-21; output is free


def load_json_arg(value: str):
    if value.lstrip().startswith(("{", "[")):
        return json.loads(value)
    return json.loads(Path(value).read_text())


def make_client() -> TypeSafeClient:
    if os.environ.get("TYPESAFE_API_KEY") or not os.environ.get("OPENROUTER_API_KEY"):
        return TypeSafeClient()  # TypeSafe directly, configured by TYPESAFE_* variables
    base_url = os.environ.get("TYPESAFE_BASE_URL", "https://openrouter.ai/api")
    return TypeSafeClient(api_key=os.environ["OPENROUTER_API_KEY"], base_url=base_url)


def show(resp, latency_ms: float, top: int) -> dict:
    raw = resp.raw_http_response.json()
    usage = raw.get("usage", {})
    cost = usage.get("cost")
    if cost is None and usage.get("input_tokens") is not None:
        cost = usage["input_tokens"] * PRICE_PER_INPUT_TOKEN
    print(f"model {resp.model}  latency {latency_ms:.0f} ms  "
          f"tokens in/out {usage.get('input_tokens')}/{usage.get('output_tokens')}  "
          f"cost ${cost:.7f}" + ("" if "cost" in usage else " (estimated)"))
    for qid, answer in resp.answers.items():
        if answer.type == "noul":
            print(f"  {qid:20} noul {answer.noul:.3f}")
            continue
        head = answer.choice if answer.type == "choice" else f"{answer.score:.2f}"
        dist = sorted(answer.probabilities.items(), key=lambda kv: -kv[1])[:top]
        spread = ", ".join(f"{k}={p:.2f}" for k, p in dist)
        print(f"  {qid:20} {answer.type} {head}  confidence {answer.confidence:.2f}  [{spread}]")
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--state", help="state as a plain string")
    source.add_argument("--state-file", type=Path, help="JSON (object/array) or text file")
    parser.add_argument("--questions", required=True, help="JSON file or inline JSON map of questions")
    parser.add_argument("--model", help="e.g. jev-1.13.0 (TypeSafe) or jev-1.13 (OpenRouter)")
    parser.add_argument("--repeat", type=int, default=1, help="send the same request N times")
    parser.add_argument("--top", type=int, default=5, help="options shown per distribution")
    parser.add_argument("--json", action="store_true", help="also print the raw responses")
    args = parser.parse_args()

    if args.state is not None:
        state = args.state
    else:
        text = args.state_file.read_text()
        try:
            state = json.loads(text)
        except json.JSONDecodeError:
            state = text
    questions = load_json_arg(args.questions)

    raws = []
    try:
        with make_client() as client:
            for _ in range(args.repeat):
                started = time.perf_counter()
                resp = client.system_one(state, questions, model=args.model)
                raws.append(show(resp, (time.perf_counter() - started) * 1000, args.top))
    except TypeSafeError as exc:
        raise SystemExit(f"error: {exc}") from exc
    if args.json:
        print(json.dumps(raws if args.repeat > 1 else raws[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
