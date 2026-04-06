from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.pipeline.graph import PipelineGraphSpec, PipelineNodeSpec
from src.pipeline.runner import PipelineRunner


@pytest.mark.asyncio
async def test_runner_stops_on_dependency_failure() -> None:
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

    assert snapshot.graph_name == "sample"
    assert snapshot.status == "failed"
    assert snapshot.failed_nodes == ["a"]
    assert "b" not in snapshot.executed_nodes


@pytest.mark.asyncio
async def test_runner_records_successful_nodes() -> None:
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
            "a": AsyncMock(return_value=SimpleNamespace(value="ok")),
            "b": AsyncMock(return_value=SimpleNamespace(value="ok")),
        }
    )

    snapshot = await runner.run_graph(graph, context={"base_dir": Path("/tmp"), "started_at": datetime.now(UTC)})

    assert snapshot.status == "success"
    assert snapshot.executed_nodes == ["a", "b"]
    assert [node.status for node in snapshot.node_results] == ["success", "success"]
