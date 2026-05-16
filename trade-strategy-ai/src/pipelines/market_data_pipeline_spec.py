from __future__ import annotations

from src.pipelines.article_pipeline_spec import PipelineOutputArtifactSpec, PipelineSpec, PipelineStepSpec


MARKET_DATA_PIPELINE_SPEC = PipelineSpec(
    pipeline_id="market_data",
    title="市场数据链路",
    description="把 Kaipan、OHLCV、市场状态和快照构建收敛成单一市场数据管线。",
    required_profile_sections=("market", "profile", "provider"),
    input_schema={
        "description": "Market Data Pipeline 参数",
        "allow_additional_fields": False,
        "fields": {
            "config_path": {
                "type": "path",
                "description": "配置文件路径",
                "required": True,
                "default": None,
                "enum": [],
            },
            "profile_id": {
                "type": "string",
                "description": "Profile ID",
                "required": False,
                "default": "default",
                "enum": [],
            },
            "trade_date": {
                "type": "date",
                "description": "交易日期",
                "required": False,
                "default": None,
                "enum": [],
            },
            "start_date": {
                "type": "date",
                "description": "开始日期",
                "required": False,
                "default": None,
                "enum": [],
            },
            "end_date": {
                "type": "date",
                "description": "结束日期",
                "required": False,
                "default": None,
                "enum": [],
            },
            "symbols": {
                "type": "array",
                "description": "标的列表",
                "required": False,
                "default": [],
                "enum": [],
            },
            "limit": {
                "type": "integer",
                "description": "最多处理标的数",
                "required": False,
                "default": 100,
                "enum": [],
            },
            "force": {
                "type": "boolean",
                "description": "是否强制执行",
                "required": False,
                "default": False,
                "enum": [],
            },
            "offline": {
                "type": "boolean",
                "description": "是否离线模式",
                "required": False,
                "default": False,
                "enum": [],
            },
        },
    },
    output_artifacts=(
        PipelineOutputArtifactSpec(
            kind="raw-json",
            title="原始数据 JSON",
            description="Kaipan 抓取的原始数据，供后续归一化与追踪。",
            previewable=True,
            extensions={"required": False},
        ),
        PipelineOutputArtifactSpec(
            kind="normalized-json",
            title="归一化 JSON",
            description="标准化后的市场数据结果，供 Job Detail 和下游消费。",
            previewable=True,
            extensions={"required": False},
        ),
        PipelineOutputArtifactSpec(
            kind="ohlcv-bundle",
            title="OHLCV 数据包",
            description="OHLCV 行情结果摘要。",
            previewable=True,
            extensions={"required": False},
        ),
        PipelineOutputArtifactSpec(
            kind="market-state-json",
            title="市场状态 JSON",
            description="Market State 输出。",
            previewable=True,
            extensions={"required": False},
        ),
        PipelineOutputArtifactSpec(
            kind="snapshot-json",
            title="市场快照 JSON",
            description="snapshot-build 的输出结果。",
            previewable=True,
            extensions={"required": False},
        ),
    ),
    workflow_id="scheduler",
    job_types=("kaipan-fetch", "kaipan-normalize", "kaipan-run", "ohlcv-crawl", "market-state-build", "snapshot-build"),
    steps=(
        PipelineStepSpec(
            step_id="kaipan-fetch",
            title="Kaipan 抓取",
            description="抓取原始市场数据。",
            job_type="kaipan-fetch",
            output_artifacts=("raw-json",),
        ),
        PipelineStepSpec(
            step_id="kaipan-normalize",
            title="Kaipan 归一化",
            description="把原始数据转换成标准结构。",
            job_type="kaipan-normalize",
            depends_on=("kaipan-fetch",),
            output_artifacts=("normalized-json",),
        ),
        PipelineStepSpec(
            step_id="kaipan-run",
            title="Kaipan 一键运行",
            description="生成调度计划或启动调度器。",
            job_type="kaipan-run",
            depends_on=("kaipan-normalize",),
            output_artifacts=("normalized-json",),
        ),
        PipelineStepSpec(
            step_id="ohlcv-crawl",
            title="抓取 OHLCV",
            description="抓取并回灌日线行情。",
            job_type="ohlcv-crawl",
            output_artifacts=("ohlcv-bundle",),
        ),
        PipelineStepSpec(
            step_id="market-state-build",
            title="构建市场状态",
            description="构建市场状态上下文。",
            job_type="market-state-build",
            depends_on=("ohlcv-crawl",),
            output_artifacts=("market-state-json",),
        ),
        PipelineStepSpec(
            step_id="snapshot-build",
            title="构建快照",
            description="构建市场快照和候选池快照。",
            job_type="snapshot-build",
            depends_on=("market-state-build",),
            output_artifacts=("snapshot-json",),
        ),
    ),
    user_visible_success_criteria=(
        "用户可以把市场数据工作流理解成一个正式 Pipeline。",
        "Job Detail 和 UI 可以复用同一份输入 schema。",
        "每个步骤都能映射到已有 job_type 和 artifact kind。",
    ),
    ui_page="/market",
    ui_task_ids=("UI-V2-005", "UI-V2-007"),
    extensions={
        "supported_input_modes": ("config_path", "profile"),
        "migration_target": "profile",
        "ui_note": "市场数据工作台后续只读此 spec，不再拼接临时入口。",
    },
)

MARKET_DATA_PIPELINE_SPECS: tuple[PipelineSpec, ...] = (MARKET_DATA_PIPELINE_SPEC,)

