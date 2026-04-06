from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class PipelineNodeSpec:
    """Describe one executable node in a pipeline graph."""

    name: str
    depends_on: list[str] = field(default_factory=list)
    retries: int = 0
    timeout_seconds: int | None = None
    produces: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PipelineGraphSpec:
    """Describe a directed acyclic graph of pipeline nodes."""

    name: str
    nodes: list[PipelineNodeSpec]
    entrypoints: list[str]
    description: str = ""

    def node_names(self) -> list[str]:
        """Return node names in declared order."""

        return [node.name for node in self.nodes]

    def node_map(self) -> dict[str, PipelineNodeSpec]:
        """Return a name-to-node mapping for quick lookup."""

        return {node.name: node for node in self.nodes}

    def validate(self) -> None:
        """Validate node uniqueness, dependencies, entrypoints, and cycles."""

        node_names = self.node_names()
        if len(set(node_names)) != len(node_names):
            raise ValueError("duplicate node names")

        node_map = self.node_map()
        for node in self.nodes:
            for dep in node.depends_on:
                if dep not in node_map:
                    raise ValueError(f"unknown dependency: {dep}")

        for entrypoint in self.entrypoints:
            if entrypoint not in node_map:
                raise ValueError(f"unknown entrypoint: {entrypoint}")

        self.topological_order()

    def topological_order(self) -> list[str]:
        """Return a stable topological order for the graph."""

        node_map = self.node_map()
        indegree: dict[str, int] = {node.name: 0 for node in self.nodes}
        children: dict[str, list[str]] = defaultdict(list)

        for node in self.nodes:
            for dep in node.depends_on:
                indegree[node.name] += 1
                children[dep].append(node.name)

        queue = deque([node.name for node in self.nodes if indegree[node.name] == 0])
        ordered: list[str] = []

        while queue:
            name = queue.popleft()
            ordered.append(name)
            for child in children.get(name, []):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

        if len(ordered) != len(node_map):
            raise ValueError("cycle detected")

        return ordered


class PipelineGraphRegistry:
    """Registry for built-in pipeline graphs."""

    def __init__(self, graphs: dict[str, PipelineGraphSpec] | None = None) -> None:
        self._graphs: dict[str, PipelineGraphSpec] = graphs or {}

    def register(self, graph: PipelineGraphSpec) -> None:
        """Register one graph and validate it first."""

        graph.validate()
        self._graphs[graph.name] = graph

    def get(self, name: str) -> PipelineGraphSpec:
        """Return one registered graph by name."""

        return self._graphs[name]

    def graph_names(self) -> list[str]:
        """Return all registered graph names in insertion order."""

        return list(self._graphs.keys())

    @classmethod
    def default(cls) -> "PipelineGraphRegistry":
        """Build the built-in graphs used by the project."""

        registry = cls()
        registry.register(
            PipelineGraphSpec(
                name="data_pipeline",
                description="Data ingestion pipeline: crawl -> clean -> validate -> store -> process -> export",
                entrypoints=["crawl"],
                nodes=[
                    PipelineNodeSpec(name="crawl", produces="data/processed/crawl/**/articles.jsonl", tags=["data"]),
                    PipelineNodeSpec(name="clean", depends_on=["crawl"], produces="data/processed/crawl/**/articles.jsonl", tags=["data"]),
                    PipelineNodeSpec(name="validate", depends_on=["clean"], produces="data/processed/crawl/**/validated.jsonl", tags=["data"]),
                    PipelineNodeSpec(name="store", depends_on=["validate"], produces="postgres:blog_articles/article_metadata", tags=["data", "db"]),
                    PipelineNodeSpec(name="process", depends_on=["store"], produces="data/processed/pipeline/pending_tasks.jsonl", tags=["pipeline"]),
                    PipelineNodeSpec(name="export", depends_on=["process"], produces="data/processed/duckdb/trade_strategy_ai.duckdb", tags=["pipeline", "analytics"]),
                ],
            )
        )
        registry.register(
            PipelineGraphSpec(
                name="daily_cycle",
                description="Daily pre-market and after-close management cycle",
                entrypoints=["run_pre_market", "run_after_close"],
                nodes=[
                    PipelineNodeSpec(name="run_pre_market", produces="daily_report", tags=["manager"]),
                    PipelineNodeSpec(name="run_after_close", produces="evaluation_report", tags=["manager"]),
                ],
            )
        )
        return registry
