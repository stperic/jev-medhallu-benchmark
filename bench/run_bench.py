# /// script
# requires-python = ">=3.10"
# dependencies = ["typesafe-sdk>=0.7.0", "httpx2"]
# ///
"""Run Jev and LLMs, all through OpenRouter, over a single-label classification set.

Every model gets the same item, the same question and the same label set.
Each finished call is appended to <out>/<model>.jsonl straight away, so an
interrupted run resumes where it stopped: reruns skip items that already have
an answer and retry only the ones that failed in transport (timeouts, 429,
5xx). A refusal, a truncated reply or an out-of-set label is the model's
answer and is never re-rolled. Score the run with score.py.

Datasets live in datasets/<name>/data/ (see common.py). Pick one with
--dataset and --split, or point at files with --task and --items.

Model specs:
  jev-1.13                       Jev through OpenRouter's System One API
                                 (TypeSafe SDK, base URL https://openrouter.ai/api).
                                 Asks a Choice or a Noul, as the task says.
  jev-1.13@choice  jev-1.13@noul Force the question type, to compare phrasings on dev.
  anthropic/claude-opus-5        Any OpenRouter chat model, at its default reasoning.
  anthropic/claude-opus-5@low    With reasoning effort (none|minimal|low|medium|high|xhigh|max).
  stringmatch                    No-model floor: the label whose name appears verbatim.
  constant:<label>               No-model floor for yes/no tasks: always that label.

Credentials: OPENROUTER_API_KEY. OPENROUTER_BASE_URL overrides the chat
endpoint root (default https://openrouter.ai/api/v1). To call TypeSafe directly instead, set
JEV_BASE_URL=https://api.typesafe.ai and JEV_API_KEY=<TypeSafe key>, and use
jev-1.13.0 as the model.

Usage:
  uv run run_bench.py --dataset medhallu --split dev --models jev-1.13
  uv run run_bench.py --dataset icd10 --models jev-1.13 anthropic/claude-opus-5@low stringmatch
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import SYSTEM_PROMPT, Task, combine_nouls, dataset_paths, item_text, label_name, load_items

DEFAULT_RPM = {"jev": 1000}  # TypeSafe allows 1,200 requests/min; stay under it.


class ModelRefused(Exception):
    """The model stopped before producing a usable answer."""


class HTTPFailure(Exception):
    def __init__(self, status: int, body: str, retry_after: float | None = None):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.retry_after = retry_after


def is_jev(spec: str) -> bool:
    return spec.startswith(("jev", "typesafe/", "~typesafe/"))


def openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    return key


class JevAdapter:
    def __init__(self, spec: str, task: Task, args):
        from typesafe_sdk import AsyncTypeSafeClient, Choice, RetryPolicy

        base_url = os.environ.get("JEV_BASE_URL", "https://openrouter.ai/api")
        api_key = os.environ.get("JEV_API_KEY") or openrouter_key()
        # Retries are handled by the runner so every attempt's latency is visible.
        self.client = AsyncTypeSafeClient(
            api_key=api_key, base_url=base_url, retry=RetryPolicy(max_retries=0), timeout=60.0
        )
        from typesafe_sdk import Noul

        self.model, _, mode = spec.partition("@")
        self.mode = mode or task.type
        self.task = task
        if self.mode == "noul":
            if not task.is_binary:
                raise SystemExit(f"{spec}: a noul needs a task with 2 labels and a 'positive' label")
            criteria = {"true": task.labels[task.positive], "false": task.labels[task.negative]}
            self.questions = {"label": Noul(instructions=task.instructions, criteria=criteria)}
            if task.jev_questions:  # independent Nouls, one request, combined in code
                self.questions = {
                    qid: Noul(instructions=q["instructions"], criteria=q.get("criteria"))
                    for qid, q in task.jev_questions.items()
                }
        elif self.mode == "choice":
            self.questions = {"label": Choice(instructions=task.instructions, criteria=task.labels)}
        else:
            raise SystemExit(f"{spec}: unknown question type {mode!r}, use @choice or @noul")

    async def predict(self, item: dict) -> dict[str, Any]:
        resp = await self.client.system_one(self.task.state(item), self.questions, model=self.model)
        raw = resp.raw_http_response.json()  # OpenRouter adds id, provider and usage.cost
        nouls = None
        if self.mode == "noul":
            # The label here uses 0.5; score.py --threshold re-labels from the stored probability.
            nouls = {qid: resp.nouls[qid].noul for qid in self.questions}
            p_yes = combine_nouls(nouls, self.task.jev_combine) if self.task.jev_questions else nouls["label"]
            label = self.task.positive if p_yes >= 0.5 else self.task.negative
            probabilities = {self.task.positive: p_yes, self.task.negative: 1 - p_yes}
            confidence = None
        else:
            answer = resp.answers["label"]
            label, probabilities, confidence = answer.choice, dict(answer.probabilities), answer.confidence
        return {
            "label": label,
            "nouls": nouls,
            "probabilities": probabilities,
            "confidence": confidence,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "cost": raw.get("usage", {}).get("cost"),
            "served_model": resp.model,
            "provider": raw.get("provider"),
            "request_id": raw.get("id") or resp.request_id,
        }

    def retry_after(self, exc: Exception) -> float | None:
        from typesafe_sdk import TypeSafeAPIConnectionError, TypeSafeAPIError, TypeSafeRateLimitError

        if isinstance(exc, TypeSafeRateLimitError):
            return (exc.retry_after_ms or 0) / 1000
        if isinstance(exc, TypeSafeAPIConnectionError):
            return 0.0
        if isinstance(exc, TypeSafeAPIError) and (exc.status == 408 or exc.status >= 500):
            return 0.0
        return None

    async def close(self) -> None:
        await self.client.aclose()


class OpenRouterChatAdapter:
    def __init__(self, spec: str, task: Task, args):
        import httpx2

        self.httpx = httpx2
        self.model, _, self.effort = spec.partition("@")
        self.task = task
        self.max_tokens = args.max_tokens
        self.provider: dict[str, Any] = {"require_parameters": True}
        pinned = dict(p.split("=", 1) for p in args.provider)
        if self.model in pinned:
            self.provider.update(order=pinned[self.model].split(","), allow_fallbacks=False)
        self.http = httpx2.AsyncClient(
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
            headers={"Authorization": f"Bearer {openrouter_key()}", "X-Title": "jev-icd10-benchmark"},
            timeout=args.timeout,
        )

    async def predict(self, item: dict) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self.task.llm_prompt(item)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "label", "strict": True, "schema": self.task.output_schema()},
            },
            "provider": self.provider,
            "max_tokens": self.max_tokens,
        }
        if self.effort:
            body["reasoning"] = {"effort": self.effort, "exclude": True}
        resp = await self.http.post("/chat/completions", json=body)
        if resp.status_code >= 400:
            retry_after = resp.headers.get("retry-after")
            raise HTTPFailure(resp.status_code, resp.text, float(retry_after) if retry_after else None)
        data = resp.json()
        if data.get("error"):
            err = data["error"]
            raise HTTPFailure(int(err.get("code") or 502), json.dumps(err))
        choice = data["choices"][0]
        if choice.get("finish_reason") not in (None, "stop"):
            raise ModelRefused(f"finish_reason={choice.get('finish_reason')}")
        usage = data.get("usage") or {}
        return {
            "label": json.loads(choice["message"]["content"])["label"],
            "probabilities": None,
            "confidence": None,
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "cost": usage.get("cost"),
            "served_model": data.get("model"),
            "provider": data.get("provider"),
            "request_id": data.get("id"),
        }

    def retry_after(self, exc: Exception) -> float | None:
        if isinstance(exc, HTTPFailure) and (exc.status in (408, 409, 429) or exc.status >= 500):
            return exc.retry_after or 0.0
        if isinstance(exc, self.httpx.TransportError):
            return 0.0
        return None

    async def close(self) -> None:
        await self.http.aclose()


class StringMatchAdapter:
    """Floor baseline: how much of the set a verbatim name lookup already solves."""

    def __init__(self, spec: str, task: Task, args):
        # Longest names first, so "Type 2 diabetes mellitus" beats a shorter overlapping name.
        names = {code: label_name(desc) for code, desc in task.labels.items()}
        self.names = sorted(names.items(), key=lambda kv: -len(kv[1]))

    async def predict(self, item: dict) -> dict[str, Any]:
        lowered = item_text(item).lower()
        label = next((code for code, name in self.names if name.lower() in lowered), None)
        return {
            "label": label, "probabilities": None, "confidence": None,
            "input_tokens": 0, "output_tokens": 0, "cost": 0.0,
            "served_model": "stringmatch", "provider": None, "request_id": None,
        }

    def retry_after(self, exc: Exception) -> float | None:
        return None

    async def close(self) -> None:
        pass


class ConstantAdapter(StringMatchAdapter):
    """Floor baseline for binary or skewed tasks: always the same label."""

    def __init__(self, spec: str, task: Task, args):
        self.label = spec.partition(":")[2]
        if self.label not in task.labels:
            raise SystemExit(f"{spec}: {self.label!r} is not one of the labels {list(task.labels)}")

    async def predict(self, item: dict) -> dict[str, Any]:
        return {
            "label": self.label, "probabilities": None, "confidence": None,
            "input_tokens": 0, "output_tokens": 0, "cost": 0.0,
            "served_model": f"constant:{self.label}", "provider": None, "request_id": None,
        }


def make_adapter(spec: str, task: Task, args):
    if spec == "stringmatch":
        return StringMatchAdapter(spec, task, args)
    if spec.startswith("constant:"):
        return ConstantAdapter(spec, task, args)
    if is_jev(spec):
        return JevAdapter(spec, task, args)
    if "/" in spec:
        return OpenRouterChatAdapter(spec, task, args)
    raise SystemExit(
        f"unknown model spec {spec!r}: use jev-*[@choice|@noul], vendor/model[@effort], stringmatch or constant:<label>"
    )


def slug(spec: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", spec)


class RateLimiter:
    """Spaces request starts at least 60/rpm seconds apart."""

    def __init__(self, rpm: float | None):
        self.interval = 60.0 / rpm if rpm else 0.0
        self.next_start = 0.0
        self.lock = asyncio.Lock()

    async def wait(self) -> None:
        if not self.interval:
            return
        async with self.lock:
            now = time.monotonic()
            delay = self.next_start - now
            self.next_start = max(now, self.next_start) + self.interval
        if delay > 0:
            await asyncio.sleep(delay)


def load_done(path: Path) -> set[tuple[str, int]]:
    done: set[tuple[str, int]] = set()
    if path.exists():
        for line in filter(None, path.read_text().split("\n")):
            rec = json.loads(line)
            # Only transport failures are retried. A model failure is that model's answer.
            if rec.get("error") is None or rec.get("retryable") is False:
                done.add((rec["id"], rec["repeat"]))
    return done


async def run_model(spec: str, task: Task, items: list[dict], args) -> None:
    path = args.out / f"{slug(spec)}.jsonl"
    done = load_done(path)
    todo = [(it, r) for r in range(args.repeats) for it in items if (it["id"], r) not in done]
    if not todo:
        print(f"[{spec}] nothing to do ({len(done)} results already in {path.name})")
        return

    adapter = make_adapter(spec, task, args)
    rpm = args.rpm or DEFAULT_RPM.get("jev" if is_jev(spec) else "")
    limiter = RateLimiter(rpm)
    semaphore = asyncio.Semaphore(args.concurrency)
    write_lock = asyncio.Lock()
    finished = errors = 0
    fingerprint = task.fingerprint

    if args.warmup and not isinstance(adapter, StringMatchAdapter):
        # Connection setup (DNS, TLS) lands on these untimed calls, not on the first item.
        for _ in range(args.warmup):
            try:
                await adapter.predict(todo[0][0])
            except Exception as exc:  # noqa: BLE001 - the timed attempt will record it
                print(f"[{spec}] warm-up call failed: {type(exc).__name__}: {str(exc)[:200]}")

    async def one(item: dict, repeat: int, sink) -> None:
        nonlocal finished, errors
        async with semaphore:
            record: dict[str, Any] = {"id": item["id"], "repeat": repeat, "spec": spec}
            for attempt in range(1, args.max_attempts + 1):
                await limiter.wait()
                started = time.perf_counter()
                try:
                    pred = await adapter.predict(item)
                except Exception as exc:  # noqa: BLE001 - every failure is recorded, not raised
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    wait = adapter.retry_after(exc)
                    record.update(
                        error=f"{type(exc).__name__}: {exc}"[:500], latency_ms=elapsed_ms,
                        # A refusal or unparseable reply is the model's answer. Anything else
                        # (network, 4xx such as no credits, 5xx) may be retried by a rerun.
                        retryable=not isinstance(exc, (ModelRefused, json.JSONDecodeError, TypeError)),
                    )
                    if wait is None or attempt == args.max_attempts:
                        break
                    backoff = min(30.0, 2 ** (attempt - 1)) * (0.75 + random.random() / 2)
                    await asyncio.sleep(max(wait, backoff))
                    continue
                record.update(pred, latency_ms=(time.perf_counter() - started) * 1000, error=None)
                record.pop("retryable", None)
                if pred["label"] is not None and pred["label"] not in task.labels:
                    record.update(error=f"label {pred['label']!r} is not in the label set", retryable=False)
                break
            record.update(
                attempts=attempt,
                task_fp=fingerprint,
                ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
            async with write_lock:
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                sink.flush()
                finished += 1
                errors += record["error"] is not None
                if finished % 10 == 0 or finished == len(todo):
                    print(f"[{spec}] {finished}/{len(todo)} done, {errors} errors", flush=True)

    print(f"[{spec}] running {len(todo)} calls (concurrency {args.concurrency}, rpm {rpm or 'unlimited'})")
    try:
        with path.open("a") as sink:
            await asyncio.gather(*(one(it, r, sink) for it, r in todo))
    finally:
        await adapter.close()


def package_versions() -> dict[str, str]:
    versions = {"python": sys.version.split()[0]}
    for pkg in ("typesafe-sdk", "httpx2"):
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            pass
    return versions


def update_meta(task: Task, args) -> None:
    meta_path = args.out / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if meta and meta.get("task_fp") != task.fingerprint:
        raise SystemExit(
            f"{args.out} was run with a different task (question, labels or state key). "
            "Use a new --out directory so results from different prompts never mix."
        )
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta.setdefault("created", now)
    meta.update(
        task_fp=task.fingerprint,
        dataset=args.dataset,
        split=args.split,
        task=str(args.task.resolve()),
        items=str(args.items.resolve()),
        items_sha256=hashlib.sha256(args.items.read_bytes()).hexdigest()[:16],
        jev_base_url=os.environ.get("JEV_BASE_URL", "https://openrouter.ai/api"),
    )
    meta.setdefault("runs", []).append({
        "at": now, "models": args.models, "repeats": args.repeats,
        "concurrency": args.concurrency, "providers": args.provider,
        "max_tokens": args.max_tokens, "filters": args.only, "limit": args.limit,
        "warmup": args.warmup, "host": platform.node(), "platform": platform.platform(),
        "code_sha256": {
            name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()[:16]
            for name in ("run_bench.py", "common.py")
        },
        "versions": package_versions(),
    })
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dataset", help="folder name under datasets/, e.g. medhallu or icd10")
    parser.add_argument("--split", help="items.<split>.jsonl of the dataset (default: test, else items.jsonl)")
    parser.add_argument("--task", type=Path, help="task.json, instead of --dataset")
    parser.add_argument("--items", type=Path, help="items file, instead of --dataset/--split")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--out", type=Path, help="run directory (default: runs/<dataset>/<split>)")
    parser.add_argument("--repeats", type=int, default=1, help="calls per item, for noise estimates")
    parser.add_argument("--concurrency", type=int, default=8, help="use 1 for latency numbers")
    parser.add_argument("--rpm", type=float, help="request-start cap per model (Jev defaults to 1000)")
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--warmup", type=int, default=1,
                        help="untimed calls per model before the run, so latency excludes connection setup")
    parser.add_argument("--timeout", type=float, default=600.0,
                        help="chat models: seconds per attempt; a timeout is retried like other transport failures")
    parser.add_argument("--max-tokens", type=int, default=16000,
                        help="chat models: output cap, which also bounds reasoning")
    parser.add_argument(
        "--provider", action="append", default=[], metavar="MODEL=SLUG[,SLUG]",
        help="pin an OpenRouter chat model to providers, no fallbacks "
             "(e.g. anthropic/claude-opus-5=anthropic); use for latency runs",
    )
    parser.add_argument(
        "--only", action="append", default=[], metavar="FIELD=VALUE",
        help="keep items whose FIELD equals VALUE, e.g. --only lang=en (repeatable)",
    )
    parser.add_argument("--limit", type=int, help="first N items after filtering (smoke tests)")
    args = parser.parse_args()

    if args.dataset:
        task_path, items_path, _ = dataset_paths(args.dataset, args.split)
        args.task = args.task or task_path
        args.items = args.items or items_path
        args.out = args.out or Path("runs") / args.dataset / (args.split or "test")
    if not (args.task and args.items and args.out):
        parser.error("give --dataset, or all of --task, --items and --out")

    task = Task.load(args.task)
    items = load_items(args.items)
    for flt in args.only:
        field, _, value = flt.partition("=")
        items = [it for it in items if str(it.get(field)) == value]
    if args.limit:
        items = items[: args.limit]
    if not items:
        raise SystemExit("no items left after filtering")

    args.out.mkdir(parents=True, exist_ok=True)
    update_meta(task, args)
    for spec in args.models:
        asyncio.run(run_model(spec, task, items, args))
    print(f"done. score with: uv run score.py {args.out}")


if __name__ == "__main__":
    main()
