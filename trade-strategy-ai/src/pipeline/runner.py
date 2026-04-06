from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from inspect import isawaitable
from typing import Any

from src.pipeline.graph import PipelineGraphRegistry, PipelineGraphSpec
from src.pipeline.health import PipelineHealthSnapshot, PipelineNodeResult


PipelineHandler = Callable[[dict[str, Any]], Any]


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

            started_at = datetime.now(UTC)
            try:
                output = handler(context)
                if isawaitable(output):
                    output = await output
                if output is not None:
                    context[node_name] = output

                outputs: list[str] = []
                if hasattr(output, "duckdb_path"):
                    outputs.append(str(getattr(output, "duckdb_path")))
                if hasattr(output, "html_path"):
                    outputs.append(str(getattr(output, "html_path")))
                if hasattr(output, "json_path"):
                    outputs.append(str(getattr(output, "json_path")))

                result = PipelineNodeResult(
                    name=node_name,
                    status="success",
                    started_at=started_at,
                    finished_at=datetime.now(UTC),
                    duration_seconds=(datetime.now(UTC) - started_at).total_seconds(),
                    outputs=outputs,
                )
            except Exception as exc:  # noqa: BLE001
                result = PipelineNodeResult(
                    name=node_name,
                    status="failed",
                    started_at=started_at,
                    finished_at=datetime.now(UTC),
                    duration_seconds=(datetime.now(UTC) - started_at).total_seconds(),
                    error=str(exc),
                )

            result_by_name[node_name] = result
            snapshot.add_result(result)

        return snapshot.finalize()
