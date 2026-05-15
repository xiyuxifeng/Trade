# NW-V1-S3-001 Article Pipeline Spec Design

> 单一 canonical 规范文件，承载 `article_pipeline` 的业务定义、Web 输入契约、运行映射和后续扩展位。

## Goal

定义 `article_pipeline` 作为 V1 第一条可交付业务切片的 canonical spec，并预留后续 `NW-V1-S3-002/003` 需要的稳定扩展字段。

## Architecture

`article_pipeline` 只保留一份正式规范定义，不再拆分出平行的“业务 spec”和“运行 spec”。规范文件放在 `src/pipelines/article_pipeline_spec.py`，内部以一个 frozen dataclass 为核心，暴露固定字段和少量显式扩展位。

现有 Web/API 继续读取 `WorkflowService` 的 `pipeline` 工作流作为运行入口，而 `PipelineSpec` 则提供业务语义、输入 schema、产物定义和 UI 绑定信息，供 catalog、UI 和后续执行层复用。这样既保持单一入口，也避免提前膨胀成通用编排框架。

## Tech Stack

- Python dataclasses
- 现有 workflow / job canonical contract
- 现有 UI pipeline 路由和 job schema

## Canonical Core Fields

`PipelineSpec` 必须稳定保留以下字段：

- `pipeline_id`
- `title`
- `description`
- `required_profile_sections`
- `input_schema`
- `output_artifacts`
- `workflow_id`
- `job_types`
- `steps`
- `user_visible_success_criteria`
- `ui_page`
- `ui_task_ids`

## Explicit Extension Surface

为了支持后续 `NW-V1-S3-002/003`，规范文件额外预留：

- `extensions`
- `step.extensions`
- `output_artifact.extensions`

这些字段只作为显式扩展槽位，不承载第二套规范体系，也不引入新的通用编排抽象。

## Data Flow

1. `PipelineSpec` 从 `src/pipelines/article_pipeline_spec.py` 导出。
2. `runtime_registry_bridge` 提供 `list_pipeline_contracts()` / `get_pipeline_contract()` 读取同一份规范。
3. Web `/api/ui/v1/pipelines/article_pipeline` 继续读取现有 workflow contract，但 spec 文件补足 canonical 语义说明。
4. 后续 `NW-V1-S3-002/003` 直接复用该 spec 的 `workflow_id`、`job_types`、`steps`、`input_schema` 和 `output_artifacts`。

## Error Handling

- 未找到 pipeline 返回结构化 not found。
- spec 校验失败直接在单测中暴露，不做运行时吞错。
- 扩展字段为空时保持兼容，不影响 core contract。

## Testing

- 测试 spec 常量包含所有核心字段。
- 测试 `list_pipeline_contracts()` / `get_pipeline_contract()` 可以读取 `article_pipeline`。
- 测试 `PipelineSpec.summary()` 输出适合 catalog / UI 消费。
- 测试 spec 中明确包含 `UI-V1-010` 和 `UI-V1-007` 的关联信息。

