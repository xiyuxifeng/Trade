from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from inspect import isawaitable
from typing import Any

from src.pipeline.graph import PipelineGraphRegistry, PipelineGraphSpec
from src.pipeline.health import PipelineHealthSnapshot, PipelineNodeResult


PipelineHandler = Callable[[dict[str, Any]], Any]


@dataclass
class NodeExecutionResult:
    """单个节点执行结果，包含重试信息。"""

    output: Any
    status: str  # "success", "failed", "retried"
    attempts: int = 1  # 总尝试次数
    last_error: str | None = None


class PipelineRunner:
    """Execute a graph of pipeline nodes using plain Python callables."""

    def __init__(
        self,
        *,
        handlers: Mapping[str, PipelineHandler],
        registry: PipelineGraphRegistry | None = None,
    ) -> None:
        self._handlers = dict(handlers)
        self._registry = registry or PipelineGraphRegistry.default()

    @classmethod
    def from_registry(
        cls,
        registry: PipelineGraphRegistry,
        *,
        handlers: Mapping[str, PipelineHandler],
    ) -> "PipelineRunner":
        """Create a runner wired to a graph registry."""

        return cls(handlers=handlers, registry=registry)

    async def run(self, graph_name: str, *, context: dict[str, Any]) -> PipelineHealthSnapshot:
        """Run one graph by name."""

        graph = self._registry.get(graph_name)
        return await self.run_graph(graph, context=context)

    async def _execute_node(
        self,
        handler: PipelineHandler,
        node: Any,  # PipelineNodeSpec
        context: dict[str, Any],
    ) -> NodeExecutionResult:
        """执行单个节点，支持重试。

        Args:
            handler: 节点处理函数
            node: 节点规格（包含 retries 字段）
            context: 执行上下文

        Returns:
            NodeExecutionResult: 执行结果
        """
        max_retries = getattr(node, "retries", 0)
        base_delay = 1.0
        last_error: str | None = None

        for attempt in range(max_retries + 1):
            try:
                output = handler(context)
                if isawaitable(output):
                    output = await output
                if attempt > 0:
                    # 重试成功后记录
                    return NodeExecutionResult(
                        output=output,
                        status="retried",
                        attempts=attempt + 1,
                        last_error=None,
                    )
                return NodeExecutionResult(output=output, status="success", attempts=1)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if attempt < max_retries:
                    # 计算延迟并等待
                    delay = min(base_delay * (2 ** attempt), 60.0)
                    await asyncio.sleep(delay)

        # 所有重试都失败
        return NodeExecutionResult(
            output=None,
            status="failed",
            attempts=max_retries + 1,
            last_error=last_error,
        )

    async def run_graph(self, graph: PipelineGraphSpec, *, context: dict[str, Any]) -> PipelineHealthSnapshot:
        """Run one graph and record a node-level health snapshot."""

        graph.validate()
        snapshot = PipelineHealthSnapshot(graph_name=graph.name)
        result_by_name: dict[str, PipelineNodeResult] = {}

        for node_name in graph.topological_order():
            node = next(node for node in graph.nodes if node.name == node_name)
            dependency_results = [result_by_name[dep] for dep in node.depends_on if dep in result_by_name]
            if any(result.status != "success" for result in dependency_results):
                skipped = PipelineNodeResult(name=node_name, status="skipped")
                result_by_name[node_name] = skipped
                snapshot.add_result(skipped)
                continue

            handler = self._handlers.get(node_name)
            if handler is None:
                raise KeyError(f"missing handler for node: {node_name}")

            # 执行节点（带重试）
            started_at = datetime.now(UTC)
            exec_result = await self._execute_node(handler, node, context)
            last_error = exec_result.last_error

            if exec_result.output is not None:
                context[node_name] = exec_result.output

            outputs: list[str] = []
            if hasattr(exec_result.output, "duckdb_path"):
                outputs.append(str(getattr(exec_result.output, "duckdb_path")))
            if hasattr(exec_result.output, "html_path"):
                outputs.append(str(getattr(exec_result.output, "html_path")))
            if hasattr(exec_result.output, "json_path"):
                outputs.append(str(getattr(exec_result.output, "json_path")))

            result = PipelineNodeResult(
                name=node_name,
                status="success" if exec_result.status == "success" else "failed",
                started_at=started_at,
                finished_at=datetime.now(UTC),
                duration_seconds=(datetime.now(UTC) - started_at).total_seconds(),
                outputs=outputs,
                error=last_error,
            )

            result_by_name[node_name] = result
            snapshot.add_result(result)

        return snapshot.finalize()
