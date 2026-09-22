# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""List prices for the published MedHELM models, from LiteLLM's price sheet.

MedHELM reports tokens but no cost. This writes data/published_prices.json so
score.py can estimate a cost per published column: tokens x list price. The
estimate is a floor for reasoning models, whose hidden reasoning tokens are
billed as output but missing from MedHELM's counts.

Every price comes from BerriAI/litellm `model_prices_and_context_window.json`:
the current sheet where the model is still listed, otherwise the pinned older
tag named in FALLBACK_TAG (retired models are dropped from the current sheet).

Usage (from bench/):
  uv run datasets/medhallu/prices.py
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

SHEET = "https://raw.githubusercontent.com/BerriAI/litellm/{ref}/model_prices_and_context_window.json"
FALLBACK_TAG = "v1.60.0"

# MedHELM model name -> LiteLLM key. First-party keys where they exist. Bare `gemini-*`
# keys are Vertex AI prices (MedHELM called models through Stanford Healthcare's cloud
# deployments, not AI Studio). Llama has no first-party price: OpenRouter's is used, the
# same gateway this benchmark uses; other hosts in the sheet charge up to USD 1.04 per 1M.
KEYS = {
    "anthropic_claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
    "anthropic_claude-3-7-sonnet-20250219": "claude-3-7-sonnet-20250219",
    "google_gemini-1.5-pro-001": "gemini-1.5-pro-001",
    "google_gemini-2.0-flash-001": "gemini-2.0-flash-001",
    "google_gemini-2.5-pro-preview-05-06": "gemini-2.5-pro",
    "meta_llama-3.3-70b-instruct": "openrouter/meta-llama/llama-3.3-70b-instruct",
    "openai_gpt-4o-2024-05-13": "gpt-4o-2024-05-13",
    "openai_gpt-4o-mini-2024-07-18": "gpt-4o-mini-2024-07-18",
    "deepseek-ai_deepseek-r1": "deepseek/deepseek-r1",
    "openai_gpt-5-2025-08-07": "gpt-5-2025-08-07",
    "openai_gpt-5-mini-2025-08-07": "gpt-5-mini-2025-08-07",
    "openai_o3-mini-2025-01-31": "o3-mini-2025-01-31",
    "openai_o4-mini-2025-04-16": "o4-mini-2025-04-16",
}
REASONING = {
    "google_gemini-2.5-pro-preview-05-06", "deepseek-ai_deepseek-r1", "openai_gpt-5-2025-08-07",
    "openai_gpt-5-mini-2025-08-07", "openai_o3-mini-2025-01-31", "openai_o4-mini-2025-04-16",
}


def sheet(ref: str) -> dict:
    with urllib.request.urlopen(SHEET.format(ref=ref), timeout=120) as resp:
        return json.load(resp)


def main() -> None:
    current, old = sheet("main"), None
    out = {}
    for model, key in KEYS.items():
        source = f"main@{date.today().isoformat()}"
        entry = current.get(key)
        if entry is None:
            old = old or sheet(FALLBACK_TAG)
            entry, source = old.get(key), FALLBACK_TAG
        if entry is None:
            raise SystemExit(f"{key} is in neither the current LiteLLM sheet nor {FALLBACK_TAG}")
        out[model] = {
            "litellm_key": key,
            "sheet": source,
            "input_per_m": round(entry["input_cost_per_token"] * 1e6, 6),
            "output_per_m": round(entry["output_cost_per_token"] * 1e6, 6),
            "reasoning_model": model in REASONING,
        }
        print(f"{model:42} {key:48} in {out[model]['input_per_m']:>6} out {out[model]['output_per_m']:>6}  ({source})")
    jev = current.get("typesafe/jev-1.13.0")
    if jev:
        print(f"for reference, typesafe/jev-1.13.0: in {jev['input_cost_per_token'] * 1e6:.3f} out {jev['output_cost_per_token'] * 1e6:.3f}")
    path = Path(__file__).parent / "data" / "published_prices.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
