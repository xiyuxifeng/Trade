from __future__ import annotations

import pytest

from src.pipeline.graph import PipelineGraphRegistry, PipelineGraphSpec, PipelineNodeSpec


def test_builtin_graphs_are_registered() -> None:
    registry = PipelineGraphRegistry.default()

    assert "data_pipeline" in registry.graph_names()
    assert "daily_cycle" in registry.graph_names()


def test_data_pipeline_graph_has_expected_order() -> None:
    graph = PipelineGraphRegistry.default().get("data_pipeline")

    assert graph.name == "data_pipeline"
    assert graph.topological_order() == ["crawl", "clean", "validate", "store", "process", "export"]


def test_graph_validation_rejects_cycles() -> None:
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
