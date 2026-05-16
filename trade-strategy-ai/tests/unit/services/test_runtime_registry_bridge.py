from __future__ import annotations


def test_runtime_registry_bridge_normalizes_job_definition() -> None:
    """Bridge 应把 JobDefinition 归一化成 canonical contract。"""
    from src.services.runtime_registry_bridge import get_job_contract, list_job_contracts

    contracts = list_job_contracts()
    contract = get_job_contract("pipeline-run")

    assert contracts
    assert contract is not None
    assert contract["job_type"] == "pipeline-run"
    assert contract["title"] == "执行完整 Pipeline"
    assert contract["permission"] == "operator"
    assert contract["risk"] == "medium"
    assert contract["runnable"] is True
    assert contract["requires_confirmation"] is False
    assert contract["param_schema"]["fields"]["config_path"]["required"] is True
    assert "service_name" not in contract
    assert "handler_name" not in contract
    assert contract["metadata"]["service_name"] == "pipeline"
    assert contract["metadata"]["handler_name"] == "run_pipeline"


def test_runtime_registry_bridge_normalizes_workflow_definition() -> None:
    """Bridge 应把 WorkflowDefinition 归一化成 canonical contract。"""
    from src.services.runtime_registry_bridge import get_workflow_contract, list_workflow_contracts

    contracts = list_workflow_contracts()
    contract = get_workflow_contract("pipeline")

    assert contracts
    assert contract is not None
    assert contract["workflow_id"] == "pipeline"
    assert contract["title"] == "数据 Pipeline"
    assert contract["job_type"] == "pipeline-run"
    assert contract["permissions"] == "operator"
    assert contract["steps"][0]["step_id"] == "crawl"
    assert contract["steps"][2]["required_job_type"] == "pipeline-run"
    assert "job_definition" not in contract
    assert "service_name" not in contract


def test_runtime_registry_bridge_normalizes_pipeline_definition() -> None:
    """Bridge 应把 PipelineSpec 归一化成 canonical contract。"""
    from src.services.runtime_registry_bridge import get_pipeline_contract, list_pipeline_contracts

    contracts = list_pipeline_contracts()
    contract = get_pipeline_contract("article_pipeline")
    strategy_contract = get_pipeline_contract("strategy")

    assert contracts
    assert contract is not None
    assert strategy_contract is not None
    assert contract["pipeline_id"] == "article_pipeline"
    assert contract["workflow_id"] == "pipeline"
    assert contract["ui_page"] == "/articles"
    assert "UI-V1-010" in contract["ui_task_ids"]
    assert contract["output_artifacts"][0]["kind"] == "result-json"
    assert strategy_contract["pipeline_id"] == "strategy"
    assert strategy_contract["workflow_id"] == "strategy"
    assert strategy_contract["ui_page"] == "/strategies"
    assert "UI-V2-006" in strategy_contract["ui_task_ids"]
    assert strategy_contract["steps"][0]["job_type"] == "strategy-build"
    assert strategy_contract["steps"][1]["depends_on"] == ["strategy-build"]
