#!/usr/bin/env bash
set -euo pipefail

failed=0

required=(
  ".codex/agents/refactor-explorer-mini.toml"
  ".codex/agents/refactor-executor-mini.toml"
  ".codex/skills/refactor-orchestrator/SKILL.md"
  ".codex/skills/refactor-orchestrator/agents/openai.yaml"
)

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "WARNING: current directory is not inside a Git repository."
else
  repo_root="$(git rev-parse --show-toplevel)"
  if [[ "$(pwd -P)" != "$(cd "$repo_root" && pwd -P)" ]]; then
    echo "WARNING: run this validation from the repository root: $repo_root"
  fi
fi

for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "MISSING: $path"
    failed=1
  else
    echo "OK: $path"
  fi
done

check_contains() {
  local file="$1"
  local pattern="$2"
  local message="$3"
  if [[ -f "$file" ]] && ! grep -Fq "$pattern" "$file"; then
    echo "INVALID: $message"
    failed=1
  fi
}

check_contains ".codex/agents/refactor-explorer-mini.toml" 'name = "refactor_explorer_mini"' "Explorer name mismatch"
check_contains ".codex/agents/refactor-explorer-mini.toml" 'model = "gpt-5.4-mini"' "Explorer model is not gpt-5.4-mini"
check_contains ".codex/agents/refactor-explorer-mini.toml" 'sandbox_mode = "read-only"' "Explorer default sandbox is not read-only"

check_contains ".codex/agents/refactor-executor-mini.toml" 'name = "refactor_executor_mini"' "Executor name mismatch"
check_contains ".codex/agents/refactor-executor-mini.toml" 'model = "gpt-5.4-mini"' "Executor model is not gpt-5.4-mini"
check_contains ".codex/agents/refactor-executor-mini.toml" 'sandbox_mode = "workspace-write"' "Executor default sandbox is not workspace-write"

check_contains ".codex/skills/refactor-orchestrator/SKILL.md" 'name: refactor-orchestrator' "SKILL.md frontmatter name missing"
check_contains ".codex/skills/refactor-orchestrator/SKILL.md" 'description:' "SKILL.md frontmatter description missing"
check_contains ".codex/skills/refactor-orchestrator/agents/openai.yaml" 'allow_implicit_invocation: false' "Implicit invocation should be disabled"

if [[ -f ".codex/config.toml" ]]; then
  check_contains ".codex/config.toml" '[agents]' ".codex/config.toml does not contain [agents]"
else
  echo "WARNING: .codex/config.toml not found. Run the installer or add the required [agents] settings."
fi

# The old, unsupported repository Skill path was .codex/skills/.
# The current supported path is .codex/skills/.
if [[ -d ".codex/skills/refactor-orchestrator" ]]; then
  echo "CONFLICT: obsolete path .codex/skills/refactor-orchestrator still exists"
  echo "Remove it after confirming the Skill is installed at .codex/skills/refactor-orchestrator."
  failed=1
fi

if [[ -d ".codex/skills/refactor-orchestrator" ]]; then
  count="$(find .codex/skills/refactor-orchestrator -maxdepth 1 -name SKILL.md | wc -l | tr -d ' ')"
  if [[ "$count" != "1" ]]; then
    echo "INVALID: expected exactly one SKILL.md in .codex/skills/refactor-orchestrator"
    failed=1
  fi
fi

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY' || failed=1
import pathlib, tomllib
for p in [
    pathlib.Path(".codex/agents/refactor-explorer-mini.toml"),
    pathlib.Path(".codex/agents/refactor-executor-mini.toml"),
    pathlib.Path(".codex/config.toml"),
]:
    if p.exists():
        with p.open("rb") as f:
            tomllib.load(f)
        print(f"TOML OK: {p}")
PY
else
  echo "WARNING: python3 unavailable; TOML parse validation skipped."
fi

if [[ "$failed" -eq 0 ]]; then
  echo "Validation passed."
fi

exit "$failed"
