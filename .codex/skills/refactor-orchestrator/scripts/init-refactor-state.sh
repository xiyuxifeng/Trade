#!/usr/bin/env bash
set -euo pipefail

stage_id="${1:-}"
state_root="${2:-.codex/refactor-state}"

if [[ -z "$stage_id" ]]; then
  echo "Usage: $0 <stage-id> [state-root]" >&2
  exit 1
fi

dir="$state_root/$stage_id"
mkdir -p "$dir"/{contracts,tasks,handoffs,reviews}

skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cp -n "$skill_dir/templates/stage-plan.md" "$dir/stage-plan.md" || true
cp -n "$skill_dir/templates/manifest.yaml" "$dir/manifest.yaml" || true

echo "Initialized: $dir"
