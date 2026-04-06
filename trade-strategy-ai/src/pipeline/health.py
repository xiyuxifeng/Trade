from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class PipelineNodeResult:
    """Execution record for one pipeline node."""

    name: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    error: str | None = None
    outputs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PipelineHealthSnapshot:
    """Summary of one graph run, including node-level execution results."""

    graph_name: str
    status: str = "pending"
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    node_results: list[PipelineNodeResult] = field(default_factory=list)
    executed_nodes: list[str] = field(default_factory=list)
    failed_nodes: list[str] = field(default_factory=list)
    skipped_nodes: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    error_summaries: list[str] = field(default_factory=list)

    def add_result(self, result: PipelineNodeResult) -> None:
        """Append one node result and update summary lists."""

        self.node_results.append(result)
        if result.outputs:
            self.artifacts.extend(result.outputs)
        if result.status == "success":
            self.executed_nodes.append(result.name)
            return
        if result.status == "failed":
            self.executed_nodes.append(result.name)
            self.failed_nodes.append(result.name)
            if result.error:
                self.error_summaries.append(f"{result.name}: {result.error}")
            return
        if result.status == "skipped":
            self.skipped_nodes.append(result.name)

    def finalize(self) -> "PipelineHealthSnapshot":
        """Seal the snapshot with a derived overall status."""

        if self.failed_nodes:
            self.status = "failed"
        elif self.skipped_nodes:
            self.status = "partial"
        elif self.node_results:
            self.status = "success"
        else:
            self.status = "empty"
        self.finished_at = datetime.now(UTC)
        return self
