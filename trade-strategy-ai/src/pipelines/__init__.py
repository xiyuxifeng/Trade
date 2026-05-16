"""Canonical pipeline specifications."""

from src.pipelines.article_pipeline_spec import (
    ARTICLE_PIPELINE_SPEC,
    ARTICLE_PIPELINE_SPECS,
    PipelineOutputArtifactSpec,
    PipelineSpec,
    PipelineStepSpec,
)
from src.pipelines.market_data_pipeline_spec import MARKET_DATA_PIPELINE_SPEC, MARKET_DATA_PIPELINE_SPECS

__all__ = [
    "ARTICLE_PIPELINE_SPEC",
    "ARTICLE_PIPELINE_SPECS",
    "MARKET_DATA_PIPELINE_SPEC",
    "MARKET_DATA_PIPELINE_SPECS",
    "PipelineOutputArtifactSpec",
    "PipelineSpec",
    "PipelineStepSpec",
]
