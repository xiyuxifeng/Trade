from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field

from src.services.base import ServiceResult


class JobPermission(StrEnum):
    """Job 类型对应的最小操作权限。"""

    viewer = "viewer"
    operator = "operator"
    admin = "admin"


class JobRisk(StrEnum):
    """Job 类型的风险等级。"""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class JobFieldType(StrEnum):
    """Job 参数字段类型。"""

    string = "string"
    integer = "integer"
    number = "number"
    boolean = "boolean"
    date = "date"
    path = "path"
    object = "object"
    array = "array"


class JobParamField(BaseModel):
    """单个参数字段的 schema 描述。"""

    type: JobFieldType
    description: str
    required: bool = False
    default: Any = None
    enum: list[str] = Field(default_factory=list)


class JobParamSchema(BaseModel):
    """Job 参数 schema。"""

    description: str
    fields: dict[str, JobParamField]
    allow_additional_fields: bool = False

    def validate(self, params: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
        """校验并返回归一化后的参数。"""
        incoming = dict(params or {})
        normalized: dict[str, Any] = {}
        warnings: list[str] = []

        if not self.allow_additional_fields:
            unexpected = sorted(set(incoming) - set(self.fields))
            if unexpected:
                raise ValueError(f"unexpected params: {', '.join(unexpected)}")

        for name, field in self.fields.items():
            if name in incoming:
                value = incoming[name]
            else:
                value = field.default
            if field.required and value is None:
                raise ValueError(f"missing required param: {name}")
            if value is None:
                continue
            normalized[name] = _coerce_value(name, value, field, warnings)

        if self.allow_additional_fields:
            for name, value in incoming.items():
                if name not in normalized and name not in self.fields:
                    normalized[name] = value

        return normalized, warnings


class JobDefinition(BaseModel):
    """Job 白名单定义。"""

    job_type: str
    title: str
    service_name: str
    handler_name: str
    permission: JobPermission
    risk: JobRisk
    can_retry: bool
    can_run_concurrently: bool
    concurrency_group: str
    requires_confirmation: bool
    runnable: bool
    param_schema: JobParamSchema
    description: str

    def summary(self) -> dict[str, Any]:
        """返回前端可直接展示的定义摘要。"""
        return self.model_dump(mode="json")


def _string(description: str, *, required: bool = False, default: Any = None) -> JobParamField:
    return JobParamField(type=JobFieldType.string, description=description, required=required, default=default)


def _integer(description: str, *, required: bool = False, default: Any = None) -> JobParamField:
    return JobParamField(type=JobFieldType.integer, description=description, required=required, default=default)


def _number(description: str, *, required: bool = False, default: Any = None) -> JobParamField:
    return JobParamField(type=JobFieldType.number, description=description, required=required, default=default)


def _boolean(description: str, *, required: bool = False, default: Any = False) -> JobParamField:
    return JobParamField(type=JobFieldType.boolean, description=description, required=required, default=default)


def _date_field(description: str, *, required: bool = False, default: Any = None) -> JobParamField:
    return JobParamField(type=JobFieldType.date, description=description, required=required, default=default)


def _path_field(description: str, *, required: bool = False, default: Any = None) -> JobParamField:
    return JobParamField(type=JobFieldType.path, description=description, required=required, default=default)


def _object_field(description: str, *, required: bool = False, default: Any = None) -> JobParamField:
    return JobParamField(type=JobFieldType.object, description=description, required=required, default=default)


def _array_field(description: str, *, required: bool = False, default: Any = None) -> JobParamField:
    return JobParamField(type=JobFieldType.array, description=description, required=required, default=default)


def _schema(description: str, fields: dict[str, JobParamField], *, allow_additional_fields: bool = False) -> JobParamSchema:
    return JobParamSchema(description=description, fields=fields, allow_additional_fields=allow_additional_fields)


def _coerce_value(name: str, value: Any, field: JobParamField, warnings: list[str]) -> Any:
    coerced: Any
    if field.type == JobFieldType.string:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        coerced = value
    elif field.type == JobFieldType.integer:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        coerced = value
    elif field.type == JobFieldType.number:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number")
        coerced = value
    elif field.type == JobFieldType.boolean:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean")
        coerced = value
    elif field.type == JobFieldType.date:
        if isinstance(value, date):
            coerced = value.isoformat()
        else:
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a date string")
            date.fromisoformat(value)
            coerced = value
    elif field.type == JobFieldType.path:
        if not isinstance(value, (str, Path)):
            raise ValueError(f"{name} must be a path-like string")
        coerced = str(value)
    elif field.type == JobFieldType.object:
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be an object")
        coerced = value
    elif field.type == JobFieldType.array:
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{name} must be an array")
        coerced = list(value)
    else:
        warnings.append(f"unsupported schema type for {name}")
        coerced = value

    if field.enum and coerced not in field.enum:
        raise ValueError(f"{name} must be one of: {', '.join(field.enum)}")
    return coerced


def _def(
    *,
    job_type: str,
    title: str,
    service_name: str,
    handler_name: str,
    permission: JobPermission,
    risk: JobRisk,
    can_retry: bool,
    can_run_concurrently: bool,
    concurrency_group: str,
    requires_confirmation: bool,
    runnable: bool,
    description: str,
    param_schema: JobParamSchema,
) -> JobDefinition:
    return JobDefinition(
        job_type=job_type,
        title=title,
        service_name=service_name,
        handler_name=handler_name,
        permission=permission,
        risk=risk,
        can_retry=can_retry,
        can_run_concurrently=can_run_concurrently,
        concurrency_group=concurrency_group,
        requires_confirmation=requires_confirmation,
        runnable=runnable,
        description=description,
        param_schema=param_schema,
    )


JOB_DEFINITIONS: tuple[JobDefinition, ...] = (
    _def(
        job_type="db-migrate",
        title="数据库迁移",
        service_name="system",
        handler_name="migrate_database",
        permission=JobPermission.admin,
        risk=JobRisk.high,
        can_retry=False,
        can_run_concurrently=False,
        concurrency_group="system",
        requires_confirmation=True,
        runnable=False,
        description="执行数据库 schema 迁移。",
        param_schema=_schema(
            "数据库迁移参数",
            {
                "profile_id": _string("Profile ID"),
                "config_path": _path_field("配置文件路径"),
            },
        ),
    ),
    _def(
        job_type="init-project",
        title="初始化项目",
        service_name="setup",
        handler_name="init_project",
        permission=JobPermission.admin,
        risk=JobRisk.high,
        can_retry=False,
        can_run_concurrently=False,
        concurrency_group="system",
        requires_confirmation=True,
        runnable=False,
        description="执行数据库迁移并导入样例数据。",
        param_schema=_schema("初始化参数", {"config_path": _path_field("配置文件路径", required=True)}),
    ),
    _def(
        job_type="seed-data",
        title="导入样例数据",
        service_name="setup",
        handler_name="seed_data",
        permission=JobPermission.admin,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="system",
        requires_confirmation=False,
        runnable=False,
        description="导入样例文章和交易记录。",
        param_schema=_schema("种子数据参数", {"config_path": _path_field("配置文件路径", required=True)}),
    ),
    _def(
        job_type="backup-data",
        title="备份数据",
        service_name="backup",
        handler_name="backup_project_state",
        permission=JobPermission.admin,
        risk=JobRisk.high,
        can_retry=False,
        can_run_concurrently=False,
        concurrency_group="backup",
        requires_confirmation=True,
        runnable=True,
        description="备份数据库表和 processed 数据目录。",
        param_schema=_schema(
            "备份参数",
            {
                "profile_id": _string("Profile ID"),
                "base_dir": _path_field("项目根目录", default="trade-strategy-ai"),
                "backup_dir": _path_field("备份输出目录"),
                "backup_dir_id": _string("备份目录白名单 ID"),
                "include_processed": _boolean("是否包含 processed 目录", default=True),
            },
        ),
    ),
    _def(
        job_type="restore-data",
        title="恢复数据",
        service_name="backup",
        handler_name="restore_project_state",
        permission=JobPermission.admin,
        risk=JobRisk.critical,
        can_retry=False,
        can_run_concurrently=False,
        concurrency_group="backup",
        requires_confirmation=True,
        runnable=True,
        description="从备份包恢复数据库和 processed 数据目录。",
        param_schema=_schema(
            "恢复参数",
            {
                "profile_id": _string("Profile ID"),
                "base_dir": _path_field("项目根目录", default="trade-strategy-ai"),
                "backup_id": _string("备份包 ID"),
                "backup_dir": _path_field("备份目录"),
                "include_processed": _boolean("是否恢复 processed 目录", default=True),
                "force": _boolean("是否强制执行", default=False),
            },
        ),
    ),
    _def(
        job_type="crawl",
        title="抓取文章",
        service_name="pipeline",
        handler_name="crawl",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="pipeline",
        requires_confirmation=False,
        runnable=False,
        description="执行文章抓取 pipeline。",
        param_schema=_schema(
            "抓取参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "max_articles": _integer("最多抓取文章数"),
            },
        ),
    ),
    _def(
        job_type="import-trade-logs",
        title="导入交易记录",
        service_name="setup",
        handler_name="import_trade_logs",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="setup",
        requires_confirmation=False,
        runnable=False,
        description="导入 CSV / Excel / HTML / PDF 交易记录。",
        param_schema=_schema(
            "交易记录导入参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "csv_path": _path_field("导入文件路径", required=True),
                "source": _string("数据来源", default="csv_import"),
                "trader_account_map": _object_field("账户到交易员映射", default={}),
                "dry_run": _boolean("是否仅解析不落库", default=False),
            },
        ),
    ),
    _def(
        job_type="pipeline-run",
        title="执行完整 Pipeline",
        service_name="pipeline",
        handler_name="run_pipeline",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="pipeline",
        requires_confirmation=False,
        runnable=True,
        description="执行抓取、清洗、验证、入库和导出等完整链路。",
        param_schema=_schema(
            "Pipeline 参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "max_articles": _integer("最多文章数"),
                "force": _boolean("是否强制执行", default=False),
                "skip_crawl": _boolean("是否跳过抓取", default=False),
                "from_step": _string("起始步骤"),
                "use_db": _boolean("是否使用数据库链路", default=False),
                "new_version": _string("新版本标识"),
                "retry_failed": _boolean("是否重试失败任务", default=False),
            },
        ),
    ),
    _def(
        job_type="pipeline-step",
        title="执行 Pipeline 单步",
        service_name="pipeline",
        handler_name="run_pipeline_step",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="pipeline",
        requires_confirmation=False,
        runnable=True,
        description="从指定步骤开始执行 pipeline。",
        param_schema=_schema(
            "Pipeline 单步参数",
            {
                "step": _string("pipeline 步骤", required=True),
                "config_path": _path_field("配置文件路径", required=True),
                "max_articles": _integer("最多文章数"),
                "force": _boolean("是否强制执行", default=False),
                "use_db": _boolean("是否使用数据库链路", default=False),
                "new_version": _string("新版本标识"),
            },
        ),
    ),
    _def(
        job_type="migrate-crawl-state",
        title="迁移爬虫状态",
        service_name="setup",
        handler_name="migrate_crawl_state",
        permission=JobPermission.admin,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="setup",
        requires_confirmation=False,
        runnable=False,
        description="将本地 crawl state.json 迁移到数据库。",
        param_schema=_schema("迁移 crawl state 参数", {"config_path": _path_field("配置文件路径", required=True)}),
    ),
    _def(
        job_type="clusters-build",
        title="构建画像聚类",
        service_name="pipeline",
        handler_name="build_clusters",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="persona",
        requires_confirmation=False,
        runnable=False,
        description="从数据库构建 persona clusters。",
        param_schema=_schema(
            "聚类构建参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "dest": _path_field("输出路径", required=True),
                "max_articles": _integer("最多文章数"),
            },
        ),
    ),
    _def(
        job_type="e2e-regression",
        title="端到端回归",
        service_name="pipeline",
        handler_name="e2e_regression",
        permission=JobPermission.admin,
        risk=JobRisk.medium,
        can_retry=False,
        can_run_concurrently=False,
        concurrency_group="pipeline",
        requires_confirmation=True,
        runnable=False,
        description="串起主链路执行回归检查。",
        param_schema=_schema(
            "E2E 回归参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "max_articles": _integer("最多文章数", default=10),
                "extract_limit": _integer("抽取上限", default=10),
                "clusters_dest": _path_field("聚类输出路径", default="data/processed/persona/clusters.real.json"),
            },
        ),
    ),
    _def(
        job_type="run-pre-market",
        title="盘前执行",
        service_name="run",
        handler_name="run_pre_market",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="run",
        requires_confirmation=False,
        runnable=True,
        description="执行盘前日报流程。",
        param_schema=_schema(
            "盘前执行参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "as_of_date": _date_field("执行日期"),
                "force": _boolean("是否强制执行", default=False),
                "export_html": _boolean("是否导出 HTML", default=False),
            },
        ),
    ),
    _def(
        job_type="run-after-close",
        title="盘后执行",
        service_name="run",
        handler_name="run_after_close",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="run",
        requires_confirmation=False,
        runnable=True,
        description="执行盘后考核流程。",
        param_schema=_schema(
            "盘后执行参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "as_of_date": _date_field("执行日期"),
                "force": _boolean("是否强制执行", default=False),
                "export_html": _boolean("是否导出 HTML", default=False),
            },
        ),
    ),
    _def(
        job_type="persona-init-sample",
        title="生成示例画像",
        service_name="persona",
        handler_name="build_sample_clusters",
        permission=JobPermission.admin,
        risk=JobRisk.low,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="persona",
        requires_confirmation=False,
        runnable=False,
        description="生成可运行的样例 persona clusters 文件。",
        param_schema=_schema(
            "示例画像参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "dest": _path_field("输出路径"),
            },
        ),
    ),
    _def(
        job_type="market-state-build",
        title="构建市场状态",
        service_name="persona",
        handler_name="build_market_state",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="persona",
        requires_confirmation=False,
        runnable=True,
        description="构建 MarketState JSON。",
        param_schema=_schema(
            "市场状态参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "benchmark_symbol": _string("基准指数代码", required=True),
                "as_of": _date_field("基准日期"),
                "dest": _path_field("输出路径"),
                "from_akshare": _boolean("是否从 AkShare 构建", default=False),
                "cache_csv": _boolean("是否缓存 CSV", default=True),
            },
        ),
    ),
    _def(
        job_type="snapshot-build",
        title="构建快照",
        service_name="snapshot",
        handler_name="build_snapshot",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="snapshot",
        requires_confirmation=False,
        runnable=True,
        description="构建候选池快照。",
        param_schema=_schema(
            "快照构建参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "benchmark_symbol": _string("基准指数代码", required=True),
                "date": _date_field("单日快照日期"),
                "start_date": _date_field("区间开始日期"),
                "end_date": _date_field("区间结束日期"),
                "slot": _string("时间槽", default="17-30"),
                "snapshot_type": _string("快照类型", default="all"),
                "force": _boolean("是否强制执行", default=False),
                "offline": _boolean("是否离线模式", default=False),
            },
        ),
    ),
    _def(
        job_type="strategy-build",
        title="构建策略版本",
        service_name="strategy",
        handler_name="build_strategy_version",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="strategy",
        requires_confirmation=False,
        runnable=True,
        description="生成交易员策略版本。",
        param_schema=_schema(
            "策略构建参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "trader_id": _string("交易员 ID", required=True),
                "strategy_date": _date_field("策略日期", required=True),
                "snapshot_id": _string("当前 Market Snapshot ID"),
                "market_regime_version": _string("市场状态版本", default="market-regime-v3"),
                "source_feature_version": _string("Market Regime 特征版本", default="market-regime-features-v3"),
                "applicability_profile_version": _string("规则适用性画像版本", default="rule-applicability-v1"),
                "selected_by": _string("选择来源", default="web"),
                "regime_selection": _object_field("Regime selection 摘要"),
                "force": _boolean("是否强制执行", default=False),
            },
        ),
    ),
    _def(
        job_type="ohlcv-crawl",
        title="抓取 OHLCV",
        service_name="market",
        handler_name="crawl_ohlcv",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="market",
        requires_confirmation=False,
        runnable=True,
        description="抓取行情 OHLCV 日线数据。",
        param_schema=_schema(
            "OHLCV 抓取参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "mode": _string("抓取模式", default="incremental"),
                "symbols": _array_field("标的列表", required=True),
                "start_date": _date_field("开始日期"),
                "end_date": _date_field("结束日期"),
                "limit": _integer("最多抓取标的数", default=100),
            },
        ),
    ),
    _def(
        job_type="backtest-run",
        title="执行回测",
        service_name="backtest",
        handler_name="run_backtest",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="backtest",
        requires_confirmation=False,
        runnable=True,
        description="执行离线回测。",
        param_schema=_schema(
            "回测参数",
            {
                "trader_id": _string("交易员 ID", required=True),
                "date_from": _date_field("开始日期", required=True),
                "date_to": _date_field("结束日期", required=True),
                "strategy_version_id": _string("策略版本 ID"),
                "symbols": _array_field("标的列表", default=[]),
                "mode": _string("回测模式", default="full"),
                "use_snapshot_only": _boolean("仅使用快照数据", default=True),
                "scoring_profile": _string("评分配置", default="stage5"),
                "config_path": _path_field("配置文件路径"),
            },
        ),
    ),
    _def(
        job_type="backtest-validate-rules",
        title="规则验真",
        service_name="backtest",
        handler_name="validate_rules",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="backtest",
        requires_confirmation=False,
        runnable=True,
        description="执行规则验真并生成报告。",
        param_schema=_schema(
            "规则验真参数",
            {
                "trader_id": _string("交易员 ID", required=True),
                "date_from": _date_field("开始日期", required=True),
                "date_to": _date_field("结束日期", required=True),
                "strategy_version_id": _string("策略版本 ID"),
                "symbols": _array_field("标的列表", default=[]),
                "mode": _string("回测模式", default="rule_validation"),
                "use_snapshot_only": _boolean("仅使用快照数据", default=True),
                "scoring_profile": _string("评分配置", default="stage5"),
                "config_path": _path_field("配置文件路径"),
            },
        ),
    ),
    _def(
        job_type="backtest-reproducibility-check",
        title="回测可复现性检查",
        service_name="backtest",
        handler_name="reproducibility_check",
        permission=JobPermission.admin,
        risk=JobRisk.medium,
        can_retry=False,
        can_run_concurrently=False,
        concurrency_group="backtest",
        requires_confirmation=True,
        runnable=True,
        description="重复运行回测并比对 fingerprint。",
        param_schema=_schema(
            "可复现性检查参数",
            {
                "trader_id": _string("交易员 ID", required=True),
                "date_from": _date_field("开始日期", required=True),
                "date_to": _date_field("结束日期", required=True),
                "strategy_version_id": _string("策略版本 ID"),
                "symbols": _array_field("标的列表", default=[]),
                "mode": _string("回测模式", default="full"),
                "use_snapshot_only": _boolean("仅使用快照数据", default=True),
                "scoring_profile": _string("评分配置", default="stage5"),
                "config_path": _path_field("配置文件路径"),
            },
        ),
    ),
    _def(
        job_type="rule-pool-backtest",
        title="规则池回测",
        service_name="backtest",
        handler_name="run_rule_pool_backtest",
        permission=JobPermission.admin,
        risk=JobRisk.high,
        can_retry=False,
        can_run_concurrently=False,
        concurrency_group="rule-pool",
        requires_confirmation=True,
        runnable=True,
        description="对规则池进行回测并回写结果。",
        param_schema=_schema(
            "规则池回测参数",
            {
                "rule_id": _string("规则 ID"),
                "start_date": _date_field("开始日期", required=True),
                "end_date": _date_field("结束日期", required=True),
                "min_confidence": _number("最小置信度", default=0.5),
                "market_regime_version": _string("市场状态版本", default="market-regime-v3"),
                "config_path": _path_field("配置文件路径"),
            },
        ),
    ),
    _def(
        job_type="optimize-create-candidate",
        title="生成优化候选版本",
        service_name="optimize",
        handler_name="create_candidate",
        permission=JobPermission.operator,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="optimize",
        requires_confirmation=False,
        runnable=False,
        description="从规则调整生成候选策略版本。",
        param_schema=_schema(
            "候选版本参数",
            {
                "parent_path": _path_field("父版本路径"),
                "adjustments_path": _path_field("调整文件路径", required=True),
                "trader_id": _string("交易员 ID"),
                "strategy_date": _date_field("策略日期"),
                "version_id": _string("版本 ID"),
                "output": _path_field("输出路径"),
                "use_db": _boolean("是否使用数据库链路", default=False),
            },
        ),
    ),
    _def(
        job_type="candidate-review",
        title="候选版本审核",
        service_name="optimize",
        handler_name="review_candidate",
        permission=JobPermission.operator,
        risk=JobRisk.high,
        can_retry=False,
        can_run_concurrently=False,
        concurrency_group="optimize-review",
        requires_confirmation=True,
        runnable=True,
        description="审核候选策略版本并写入审计结果。",
        param_schema=_schema(
            "候选版本审核参数",
            {
                "candidate_version_id": _string("候选版本 ID", required=True),
                "decision": _string("审核决策", required=True, default="pending"),
                "reviewed_by": _string("审核人", default="web"),
                "force": _boolean("是否强制覆盖", default=False),
            },
        ),
    ),
    _def(
        job_type="rule-review",
        title="规则审核",
        service_name="rule_pool",
        handler_name="review_rule",
        permission=JobPermission.operator,
        risk=JobRisk.high,
        can_retry=False,
        can_run_concurrently=False,
        concurrency_group="rule-pool-review",
        requires_confirmation=True,
        runnable=False,
        description="审核规则池条目并写入审计结果。",
        param_schema=_schema(
            "规则审核参数",
            {
                "rule_id": _string("规则 ID", required=True),
                "decision": _string("审核决策", required=True, default="pending"),
                "reviewed_by": _string("审核人", default="web"),
                "force": _boolean("是否强制覆盖", default=False),
            },
        ),
    ),
    _def(
        job_type="kaipan-fetch",
        title="Kaipan 抓取",
        service_name="kaipan",
        handler_name="fetch",
        permission=JobPermission.admin,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="kaipan",
        requires_confirmation=False,
        runnable=True,
        description="抓取指定交易日的 Kaipan 原始数据。",
        param_schema=_schema(
            "Kaipan 抓取参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "trade_date": _date_field("交易日期"),
                "slot": _string("时间槽", default="all"),
            },
        ),
    ),
    _def(
        job_type="kaipan-normalize",
        title="Kaipan 归一化",
        service_name="kaipan",
        handler_name="normalize",
        permission=JobPermission.admin,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="kaipan",
        requires_confirmation=False,
        runnable=True,
        description="仅执行 Kaipan 归一化。",
        param_schema=_schema(
            "Kaipan 归一化参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "trade_date": _date_field("交易日期"),
                "slot": _string("时间槽", default="all"),
            },
        ),
    ),
    _def(
        job_type="kaipan-run",
        title="Kaipan 一键运行",
        service_name="kaipan",
        handler_name="run",
        permission=JobPermission.admin,
        risk=JobRisk.medium,
        can_retry=True,
        can_run_concurrently=False,
        concurrency_group="kaipan",
        requires_confirmation=False,
        runnable=True,
        description="构建 Kaipan 调度计划或启动调度器。",
        param_schema=_schema(
            "Kaipan 运行参数",
            {
                "config_path": _path_field("配置文件路径", required=True),
                "trade_date": _date_field("交易日期"),
                "slot": _string("时间槽", default="all"),
                "mode": _string("抓取模式", default="incremental"),
                "symbols": _array_field("标的列表", default=[]),
                "start_date": _date_field("开始日期"),
                "end_date": _date_field("结束日期"),
                "limit": _integer("最多处理标的数", default=100),
                "date": _date_field("单日快照日期"),
                "as_of": _date_field("基准日期"),
                "dest": _path_field("输出路径"),
                "from_akshare": _boolean("是否从 AkShare 构建", default=False),
                "cache_csv": _boolean("是否缓存 CSV", default=True),
                "snapshot_type": _string("快照类型", default="all"),
                "force": _boolean("是否强制执行", default=False),
                "offline": _boolean("是否离线模式", default=False),
                "start_scheduler": _boolean("是否启动调度器", default=False),
                "block": _boolean("是否阻塞运行", default=False),
            },
        ),
    ),
)

_JOB_TYPE_MAP: dict[str, JobDefinition] = {item.job_type: item for item in JOB_DEFINITIONS}


def list_job_definitions(*, runnable_only: bool = False) -> list[JobDefinition]:
    """列出所有 job 定义。"""
    if runnable_only:
        return [item for item in JOB_DEFINITIONS if item.runnable]
    return list(JOB_DEFINITIONS)


def get_job_definition(job_type: str) -> JobDefinition | None:
    """按 job_type 获取定义。"""
    return _JOB_TYPE_MAP.get(job_type)


def get_runnable_job_types() -> list[str]:
    """返回可由 JobRunner 执行的 job type 白名单。"""
    return [item.job_type for item in JOB_DEFINITIONS if item.runnable]


def get_job_type_limits() -> dict[str, int]:
    """返回每个 job type 的默认并发上限。"""
    return {item.job_type: (1 if not item.can_run_concurrently else 2) for item in JOB_DEFINITIONS if item.runnable}


def validate_job_submission(
    *,
    job_type: str,
    params: dict[str, Any] | None,
    created_by: str | None = None,
    confirmed: bool = False,
) -> ServiceResult:
    """校验提交到 Job Center 的任务参数。"""
    definition = get_job_definition(job_type)
    if definition is None:
        return ServiceResult(
            status="error",
            message=f"unknown job type: {job_type}",
            payload={"job_type": job_type, "known_job_types": [item.job_type for item in JOB_DEFINITIONS]},
        )

    requires_confirmation = definition.requires_confirmation or definition.risk in {JobRisk.high, JobRisk.critical}

    if not definition.runnable:
        if requires_confirmation and not confirmed:
            return ServiceResult(
                status="error",
                message="confirmation required for high-risk job",
                payload={
                    "job_type": job_type,
                    "definition": definition.summary(),
                    "created_by": created_by,
                    "requires_confirmation": True,
                },
            )

        if not requires_confirmation:
            return ServiceResult(
                status="error",
                message=f"job type is registered but not runnable yet: {job_type}",
                payload={"job_type": job_type, "definition": definition.summary(), "created_by": created_by},
            )

    if requires_confirmation and not confirmed and definition.runnable:
        return ServiceResult(
            status="error",
            message="confirmation required for high-risk job",
            payload={
                "job_type": job_type,
                "definition": definition.summary(),
                "created_by": created_by,
                "requires_confirmation": True,
            },
        )

    try:
        normalized, warnings = definition.param_schema.validate(params)
    except ValueError as exc:
        return ServiceResult(
            status="error",
            message=str(exc),
            payload={
                "job_type": job_type,
                "definition": definition.summary(),
                "created_by": created_by,
            },
        )

    return ServiceResult(
        status="ok",
        message="job submission validated",
        payload={
            "job_type": job_type,
            "definition": definition.summary(),
            "created_by": created_by,
            "params": normalized,
            "warnings": warnings,
        },
    )
