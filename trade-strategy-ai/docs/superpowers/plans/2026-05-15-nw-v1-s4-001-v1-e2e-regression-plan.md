# V1 E2E 回归 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供一条可重复的 V1 回归验证链路，用薄 Python wrapper 串起现有 Web acceptance 与 CLI smoke gate，验证 Job、Timeline、Artifact、Config Snapshot，同时不把 CLI 恢复成正式用户入口。

**Architecture:** 新增一个共享的 `tests/e2e` runner 层，复用现有 `web-acceptance.test.tsx` 和 `cli.main e2e-regression`，把它们包装成一条单向验收链。`tests/e2e/test_article_pipeline_v1.py` 只负责 orchestration，不承载业务逻辑；`docs/New-Web-V1-E2E.md` 只记录本地验收和失败定位，不定义新的正式操作入口。CLI 只作为内部验证工具存在，不进入用户文档的正式路径。

**Tech Stack:** Python 3.11+, pytest, subprocess, Typer CLI, Vitest

---

## 文件结构

```
tests/e2e/
├── e2e_runner.py               # 新增：共享的 Web acceptance / CLI smoke runner
├── test_web_acceptance.py      # 修改：改用共享 runner
└── test_article_pipeline_v1.py # 新增：V1 回归编排入口

docs/
└── New-Web-V1-E2E.md          # 新增：V1 E2E 执行与验收说明

docs/New-Web-Linked-TaskLists/
└── New-Web-TaskList.md        # 修改：收口 NW-V1-S4-001 状态

daily-sessions/
└── 2026-05-15.md              # 修改：记录恢复点与验证结果

daily-report/
└── 2026-05-15.md              # 修改：记录阶段成果
```

---

## Task 1: 提取共享 E2E runner，保持 Web acceptance 可复用

**Files:**
- Create: `tests/e2e/e2e_runner.py`
- Modify: `tests/e2e/test_web_acceptance.py`
- Test: `tests/e2e/test_e2e_runner.py`

- [ ] **Step 1: 写 failing test**

```python
from pathlib import Path
from types import SimpleNamespace
import sys

from tests.e2e.e2e_runner import run_cli_e2e_regression, run_web_acceptance_suite


def test_run_web_acceptance_suite_invokes_vitest(monkeypatch):
    calls = []

    def fake_run(cmd, cwd, env, capture_output, text, check):
        calls.append((cmd, cwd, env["CI"]))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("tests.e2e.e2e_runner.subprocess.run", fake_run)

    run_web_acceptance_suite()

    assert calls[0][0][-2:] == ["run", "src/e2e/web-acceptance.test.tsx"]
    assert calls[0][1].name == "web"
    assert calls[0][2] == "1"


def test_run_cli_e2e_regression_invokes_cli_with_expected_args(monkeypatch):
    calls = []

    def fake_run(cmd, cwd, env, capture_output, text, check):
        calls.append((cmd, cwd, env["PYTHONPATH"]))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("tests.e2e.e2e_runner.subprocess.run", fake_run)

    run_cli_e2e_regression(
        config=Path("config/app.yaml"),
        max_articles=1,
        extract_limit=1,
    )

    assert calls[0][0][0] == sys.executable
    assert calls[0][0][1:4] == ["-m", "cli.main", "e2e-regression"]
    assert calls[0][1] == Path(__file__).resolve().parents[2]
```

- [ ] **Step 2: 跑测试确认失败**

Run:

```bash
python -m pytest tests/e2e/test_e2e_runner.py -q
```

Expected:

- `ModuleNotFoundError`，因为 `tests/e2e/e2e_runner.py` 还不存在。

- [ ] **Step 3: 实现最小共享 runner**

```python
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"
VITEST_BIN = WEB_ROOT / "node_modules" / ".bin" / "vitest"


def _run_checked(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "E2E runner failed:\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def run_web_acceptance_suite() -> None:
    env = os.environ.copy()
    env.setdefault("CI", "1")
    _run_checked(
        [str(VITEST_BIN), "run", "src/e2e/web-acceptance.test.tsx"],
        cwd=WEB_ROOT,
        env=env,
    )


def run_cli_e2e_regression(
    *,
    config: Path,
    max_articles: int = 1,
    extract_limit: int = 1,
) -> None:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(PROJECT_ROOT))
    _run_checked(
        [
            sys.executable,
            "-m",
            "cli.main",
            "e2e-regression",
            "--config",
            str(config),
            "--max-articles",
            str(max_articles),
            "--extract-limit",
            str(extract_limit),
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )
```

`tests/e2e/test_web_acceptance.py` 只保留一层薄 wrapper：

```python
from tests.e2e.e2e_runner import run_web_acceptance_suite


def test_web_acceptance_suite() -> None:
    run_web_acceptance_suite()
```

- [ ] **Step 4: 跑测试验证通过**

Run:

```bash
python -m pytest tests/e2e/test_e2e_runner.py tests/e2e/test_web_acceptance.py -q
```

Expected:

- `2 passed`

- [ ] **Step 5: 提交**

```bash
git add tests/e2e/e2e_runner.py tests/e2e/test_web_acceptance.py tests/e2e/test_e2e_runner.py
git commit -m "test(e2e): extract shared acceptance runners"
```

---

## Task 2: 添加 V1 回归编排测试与执行说明

**Files:**
- Create: `tests/e2e/test_article_pipeline_v1.py`
- Create: `docs/New-Web-V1-E2E.md`
- Test: `tests/e2e/test_article_pipeline_v1.py`

- [ ] **Step 1: 写 failing test**

```python
from pathlib import Path

def test_article_pipeline_v1_runs_cli_gate_and_web_acceptance(monkeypatch):
    calls = []

    def fake_cli(*, config, max_articles, extract_limit):
        calls.append(("cli", config, max_articles, extract_limit))

    def fake_web():
        calls.append(("web",))

    monkeypatch.setattr("tests.e2e.test_article_pipeline_v1.run_cli_e2e_regression", fake_cli)
    monkeypatch.setattr("tests.e2e.test_article_pipeline_v1.run_web_acceptance_suite", fake_web)

    from tests.e2e.test_article_pipeline_v1 import run_article_pipeline_v1

    run_article_pipeline_v1(Path("config/app.yaml"))

    assert calls == [
        ("cli", Path("config/app.yaml"), 1, 1),
        ("web",),
    ]
```

- [ ] **Step 2: 跑测试确认失败**

Run:

```bash
python -m pytest tests/e2e/test_article_pipeline_v1.py -q
```

Expected:

- `ModuleNotFoundError` 或 `ImportError`，因为 `tests/e2e/test_article_pipeline_v1.py` 还不存在。

- [ ] **Step 3: 实现最小 V1 编排测试与文档**

`tests/e2e/test_article_pipeline_v1.py`：

```python
from __future__ import annotations

from pathlib import Path

from tests.e2e.e2e_runner import run_cli_e2e_regression, run_web_acceptance_suite


def test_article_pipeline_v1_runs_cli_gate_and_web_acceptance(monkeypatch):
    calls = []

    def fake_cli(*, config, max_articles, extract_limit):
        calls.append(("cli", config, max_articles, extract_limit))

    def fake_web():
        calls.append(("web",))

    monkeypatch.setattr("tests.e2e.test_article_pipeline_v1.run_cli_e2e_regression", fake_cli)
    monkeypatch.setattr("tests.e2e.test_article_pipeline_v1.run_web_acceptance_suite", fake_web)

    run_article_pipeline_v1(Path("config/app.yaml"))

    assert calls == [
        ("cli", Path("config/app.yaml"), 1, 1),
        ("web",),
    ]


def run_article_pipeline_v1(config: Path) -> None:
    # 先跑真实回归命令，再跑 Web acceptance，确保底层执行与 UI 可见性都能回收。
    run_cli_e2e_regression(config=config, max_articles=1, extract_limit=1)
    run_web_acceptance_suite()


def test_article_pipeline_v1() -> None:
    run_article_pipeline_v1(Path("config/app.yaml"))
```

`docs/New-Web-V1-E2E.md` 至少包含：

```md
# V1 E2E 回归

## 目的

验证 V1 主链路可重复执行，且 Job、Timeline、Artifact、Config Snapshot 在 Web 中可见。

## 本地执行

```bash
python -m pytest tests/e2e/test_article_pipeline_v1.py -q
```

```bash
python -m pytest tests/e2e/test_web_acceptance.py -q
```

```bash
python -m cli.main e2e-regression --config config/app.yaml --max-articles 1 --extract-limit 1
```

## 失败定位顺序

1. 先看 CLI smoke gate 是否失败。
2. 再看 Web acceptance 是否失败。
3. 再回到 Job Detail、Timeline、Artifact、Config Snapshot 的页面状态。

## 边界说明

- CLI 只作为内部验证工具。
- 正式用户路径仍然是 Web + API。
- 这份文档不是新的正式操作手册。
```

- [ ] **Step 4: 跑测试验证通过**

Run:

```bash
python -m pytest tests/e2e/test_article_pipeline_v1.py tests/e2e/test_web_acceptance.py -q
```

Expected:

- `2 passed`

- [ ] **Step 5: 提交**

```bash
git add tests/e2e/test_article_pipeline_v1.py docs/New-Web-V1-E2E.md
git commit -m "feat(e2e): add v1 regression wrapper"
```

---

## Task 3: 收口 TaskList、会话记录与最终验证

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `daily-sessions/2026-05-15.md`
- Modify: `daily-report/2026-05-15.md`

- [ ] **Step 1: 更新 TaskList**

把 `NW-V1-S4-001` 改成 `[x]`，并补充完成说明，明确：

- `tests/e2e/test_article_pipeline_v1.py` 已建立 V1 回归编排入口。
- `docs/New-Web-V1-E2E.md` 已定义本地执行与失败定位顺序。
- CLI 仅作为内部 smoke gate，不是正式用户入口。
- Web acceptance 已作为可复用验证层接入。

- [ ] **Step 2: 更新 daily-sessions / daily-report**

`daily-sessions/2026-05-15.md` 记录：

- 当前恢复点
- 已完成的 E2E 结构
- 下一步如何跑 `tests/e2e/test_article_pipeline_v1.py`

`daily-report/2026-05-15.md` 记录：

- V1 E2E 回归已建立
- CLI 的角色是验证工具，不是正式入口
- 验证命令和结果摘要

- [ ] **Step 3: 跑最终验证**

Run:

```bash
python -m pytest tests/e2e/test_e2e_runner.py tests/e2e/test_web_acceptance.py tests/e2e/test_article_pipeline_v1.py -q
git diff --check
```

Expected:

- pytest 通过
- diff check 通过

- [ ] **Step 4: 提交**

```bash
git add docs/New-Web-Linked-TaskLists/New-Web-TaskList.md daily-sessions/2026-05-15.md daily-report/2026-05-15.md
git commit -m "docs(e2e): record v1 regression completion"
```

---

## 自检清单

### 1. 规格覆盖

- `NW-V1-S4-001` 的输出 `tests/e2e/test_article_pipeline_v1.py` 已覆盖。
- `NW-V1-S4-001` 的输出 `docs/New-Web-V1-E2E.md` 已覆盖。
- “本地可执行 E2E” 通过 `pytest` 和 `cli.main e2e-regression` 双层验证。
- “覆盖成功、失败、空数据、权限不足至少一种” 由 Web acceptance 现有覆盖承接。
- “E2E 能验证 Job、Timeline、Artifact、Config Snapshot” 由 V1 acceptance 路径承接。
- “E2E 覆盖 Web UI 关键路径或提供人工 UI 验收替代方案” 已写入文档。

### 2. 占位符扫描

- 未发现占位词。
- 所有命令都有明确路径和预期结果。
- 没有引用未定义的函数名。

### 3. 类型一致性

- `run_web_acceptance_suite()` 和 `run_cli_e2e_regression()` 的职责清晰，命名一致。
- `run_article_pipeline_v1(config: Path) -> None` 是唯一 orchestration 函数。
- `tests/e2e/test_web_acceptance.py` 保持薄 wrapper，不再复制 subprocess 细节。
