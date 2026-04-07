# Lightweight DAG Abstraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不引入 Airflow/Luigi 运行时的前提下，把现有数据主线与日常闭环统一抽象成轻量 DAG，并保留当前 CLI/scheduler 执行方式不变。

**Architecture:** 新增一层只负责“描述、注册、执行、记录”的 DAG 抽象层。图定义层描述节点依赖与产物，注册层维护系统内置图，执行层复用现有 pipeline / ManagerAgent 逻辑，健康快照层统一记录每次运行的节点状态与耗时。现有 `run_pipeline()` 和 scheduler 继续作为入口，不改业务逻辑，只改编排组织方式。

**Tech Stack:** Python 3.11+, dataclasses, pytest, SQLAlchemy async, Typer CLI, APScheduler, existing pipeline/manager agents

---

## File Map

- Create: `trade-strategy-ai/src/pipeline/graph.py`
  - DAG 图定义、节点定义、拓扑校验、图注册
- Create: `trade-strategy-ai/src/pipeline/runner.py`
  - 统一执行器，按图执行现有函数并生成运行结果
- Create: `trade-strategy-ai/src/pipeline/health.py`
  - 运行快照、节点状态、耗时和错误摘要结构
- Modify: `trade-strategy-ai/src/pipeline/dag.py`
  - 保留 `run_pipeline()`，内部改为复用图执行层
- Modify: `trade-strategy-ai/src/pipeline/scheduler.py`
  - scheduler job 改为调用图执行层或统一运行入口
- Modify: `trade-strategy-ai/cli/main.py`
  - `scheduler-start`、`e2e-regression` 继续走同一套运行入口
- Create: `trade-strategy-ai/tests/unit/pipeline/test_graph.py`
  - 图定义、注册、依赖校验测试
- Create: `trade-strategy-ai/tests/unit/pipeline/test_runner.py`
  - 执行器、失败中断、健康快照测试
- Modify: `trade-strategy-ai/tests/unit/pipeline/test_dag_audit.py`
  - 回归验证 `run_pipeline()` 仍会产生审计事件且 payload 正常
- Modify: `trade-strategy-ai/tests/e2e/test_full_flow.py`
  - 确认 smoke/e2e 仍可通过统一运行入口

---

### Task 1: 定义 DAG 图与健康快照结构

**Files:**
- Create: `trade-strategy-ai/src/pipeline/graph.py`
- Create: `trade-strategy-ai/src/pipeline/health.py`
- Test: `trade-strategy-ai/tests/unit/pipeline/test_graph.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_builtin_graphs_are_registered():
    registry = PipelineGraphRegistry.default()
    assert "data_pipeline" in registry.graph_names()
    assert "daily_cycle" in registry.graph_names()

def test_graph_validation_rejects_cycles():
    graph = PipelineGraphSpec(
        name="broken",
        nodes=[
            PipelineNodeSpec(name="a", depends_on=["b"], retries=0, timeout_seconds=None, produces="x", tags=[]),
            PipelineNodeSpec(name="b", depends_on=["a"], retries=0, timeout_seconds=None, produces="y", tags=[]),
        ],
        entrypoints=["a"],
        description="cycle test",
    )
    with pytest.raises(ValueError, match="cycle"):
        graph.validate()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest -q tests/unit/pipeline/test_graph.py -v`
Expected: FAIL because `PipelineGraphRegistry`, `PipelineGraphSpec`, and `PipelineNodeSpec` do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass(slots=True)
class PipelineNodeSpec:
    name: str
    depends_on: list[str] = field(default_factory=list)
    retries: int = 0
    timeout_seconds: int | None = None
    produces: str = ""
    tags: list[str] = field(default_factory=list)

@dataclass(slots=True)
class PipelineGraphSpec:
    name: str
    nodes: list[PipelineNodeSpec]
    entrypoints: list[str]
    description: str = ""

    def validate(self) -> None:
        node_names = {node.name for node in self.nodes}
        if len(node_names) != len(self.nodes):
            raise ValueError("duplicate node names")

        graph = defaultdict(list)
        for node in self.nodes:
            for dep in node.depends_on:
                if dep not in node_names:
                    raise ValueError(f"unknown dependency: {dep}")
                graph[dep].append(node.name)

        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(name: str) -> None:
            if name in visiting:
                raise ValueError("cycle detected")
            if name in visited:
                return
            visiting.add(name)
            for nxt in graph[name]:
                dfs(nxt)
            visiting.remove(name)
            visited.add(name)

        for entrypoint in self.entrypoints:
            if entrypoint not in node_names:
                raise ValueError(f"unknown entrypoint: {entrypoint}")
            dfs(entrypoint)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest -q tests/unit/pipeline/test_graph.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/pipeline/graph.py trade-strategy-ai/src/pipeline/health.py tests/unit/pipeline/test_graph.py
git commit -m "feat: add lightweight pipeline graph definitions"
```

### Task 2: Implement the graph runner and wire data pipeline execution

**Files:**
- Create: `trade-strategy-ai/src/pipeline/runner.py`
- Modify: `trade-strategy-ai/src/pipeline/dag.py`
- Modify: `trade-strategy-ai/src/pipeline/scheduler.py`
- Test: `trade-strategy-ai/tests/unit/pipeline/test_runner.py`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_runner_stops_on_dependency_failure():
    graph = PipelineGraphSpec(
        name="sample",
        nodes=[
            PipelineNodeSpec(name="a", depends_on=[], retries=0, timeout_seconds=None, produces="a.json", tags=["test"]),
            PipelineNodeSpec(name="b", depends_on=["a"], retries=0, timeout_seconds=None, produces="b.json", tags=["test"]),
        ],
        entrypoints=["a"],
        description="sample graph",
    )
    runner = PipelineRunner(
        handlers={
            "a": AsyncMock(side_effect=RuntimeError("boom")),
            "b": AsyncMock(),
        }
    )
    snapshot = await runner.run_graph(graph, context={})
    assert snapshot.failed_nodes == ["a"]
    assert "b" not in snapshot.executed_nodes

@pytest.mark.asyncio
async def test_run_pipeline_returns_health_snapshot():
    snapshot = await run_pipeline_via_registry(config=config, base_dir=base_dir, skip_crawl=True)
    assert snapshot.graph_name == "data_pipeline"
    assert snapshot.status in {"success", "partial"}
    assert snapshot.node_results
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest -q tests/unit/pipeline/test_runner.py -v`
Expected: FAIL because `PipelineRunner` and health snapshot plumbing are missing.

- [ ] **Step 3: Write the minimal implementation**

```python
@dataclass(slots=True)
class PipelineNodeResult:
    name: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None

class PipelineRunner:
    async def run_graph(self, graph: PipelineGraphSpec, *, context: dict[str, Any]) -> PipelineHealthSnapshot:
        snapshot = PipelineHealthSnapshot(graph_name=graph.name)
        # Topological execution over the declared entrypoints and dependencies.
        for node in graph.nodes:
            handler = self.handlers[node.name]
            started_at = datetime.now(UTC)
            try:
                await handler(context)
                snapshot.node_results.append(
                    PipelineNodeResult(
                        name=node.name,
                        status="success",
                        started_at=started_at,
                        finished_at=datetime.now(UTC),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                snapshot.node_results.append(
                    PipelineNodeResult(
                        name=node.name,
                        status="failed",
                        started_at=started_at,
                        finished_at=datetime.now(UTC),
                        error=str(exc),
                    )
                )
                snapshot.status = "failed"
                break
        return snapshot
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest -q tests/unit/pipeline/test_runner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/pipeline/runner.py trade-strategy-ai/src/pipeline/dag.py trade-strategy-ai/src/pipeline/scheduler.py tests/unit/pipeline/test_runner.py
git commit -m "feat: add lightweight pipeline runner"
```

### Task 3: Align CLI/e2e and verify regressions

**Files:**
- Modify: `trade-strategy-ai/cli/main.py`
- Modify: `trade-strategy-ai/tests/unit/pipeline/test_dag_audit.py`
- Modify: `trade-strategy-ai/tests/e2e/test_full_flow.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_scheduler_start_uses_shared_pipeline_entrypoint():
    scheduler = build_pipeline_scheduler(config=config, base_dir=base_dir)
    assert scheduler.scheduler.get_jobs()

@pytest.mark.asyncio
async def test_e2e_regression_still_passes_with_runner():
    result = await run_pipeline_via_registry(config=config, base_dir=base_dir, max_articles=1, force=True)
    assert result.graph_name == "data_pipeline"
    assert result.status == "success"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest -q tests/unit/pipeline/test_dag_audit.py tests/e2e/test_full_flow.py -v`
Expected: FAIL until CLI and e2e use the shared execution entrypoint.

- [ ] **Step 3: Write the minimal implementation**

```python
async def run_pipeline_via_registry(
    *,
    config: AppConfig,
    base_dir: Path,
    max_articles: int | None = None,
    force: bool = False,
    skip_crawl: bool = False,
):
    registry = PipelineGraphRegistry.default(config=config, base_dir=base_dir)
    runner = PipelineRunner.from_registry(registry)
    return await runner.run("data_pipeline", context={"config": config, "base_dir": base_dir})
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest -q tests/unit/pipeline/test_dag_audit.py tests/e2e/test_full_flow.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/cli/main.py trade-strategy-ai/tests/unit/pipeline/test_dag_audit.py trade-strategy-ai/tests/e2e/test_full_flow.py
git commit -m "feat: unify pipeline execution via lightweight dag"
```

---

## Verification

- `python -m pytest -q tests/unit/pipeline/test_graph.py`
- `python -m pytest -q tests/unit/pipeline/test_runner.py`
- `python -m pytest -q tests/unit/pipeline/test_dag_audit.py`
- `make smoke`
- `python -m pytest -q`

## Notes

- 先只覆盖已有两条主线，不把新命令都变成 DAG 节点。
- Runner 只做编排，不复制业务逻辑。
- 若后续需要 Airflow 迁移，优先复用 `PipelineGraphSpec` 和 `PipelineHealthSnapshot`，不改节点实现。
