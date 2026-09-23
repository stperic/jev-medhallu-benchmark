#!/usr/bin/env bash
# Check 5 timing run (PREREGISTRATION.md): first 200 test items, 10 rounds of 20,
# Jev and the two GPT-OSS specs one after another, order rotated every round,
# one request at a time. Each round raises --limit by 20; the runner resumes, so
# only the next 20 items are asked. Run from bench/.
set -euo pipefail
ITEMS=datasets/medhallu/data/items.test.jsonl
jev() {
  uv run --env-file .env run_bench.py --task datasets/medhallu/data/task.json --items "$ITEMS" \
    --concurrency 1 --limit "$1" --out runs/medhallu/timing-oss/jev --models jev-1.13
}
oss() {  # $1 limit, $2 spec
  uv run --env-file .env run_bench.py --task datasets/medhallu/variants/llm-authors-question.task.json \
    --items "$ITEMS" --concurrency 1 --timeout 30 --limit "$1" --out runs/medhallu/timing-oss/llm --models "$2" \
    --provider openai/gpt-oss-120b=cerebras --provider openai/gpt-oss-20b=groq
}
steps=(jev "oss openai/gpt-oss-120b@low" "oss openai/gpt-oss-20b@low")
for round in $(seq 0 9); do
  limit=$(( (round + 1) * 20 ))
  for k in 0 1 2; do
    step=${steps[$(( (round + k) % 3 ))]}
    echo "round $round, limit $limit: $step"
    set -- $step
    "$1" "$limit" ${2:+"$2"}
  done
done
