#!/usr/bin/env bash
set -euo pipefail

task_id="${1:-}"
round="${2:-}"
state_dir="${3:-.codex/refactor-state}"

if [[ -z "$task_id" || -z "$round" ]]; then
  echo "Usage: $0 <task-id> <round> [state-dir]" >&2
  exit 1
fi

out="$state_dir/artifacts/$task_id"
mkdir -p "$out"

git diff --binary > "$out/$task_id.round-$round.changes.diff"
git status --short > "$out/$task_id.round-$round.status.txt"

if [[ ! -f "$out/$task_id.round-$round.tests.log" ]]; then
  : > "$out/$task_id.round-$round.tests.log"
fi

echo "Captured artifacts in: $out"
