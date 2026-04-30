from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import re
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.common.exceptions import ConfigError


class ScheduleConfig(BaseModel):
    enable: bool = False
    pre_market_time: str | None = None  # HH:MM
    after_close_time: str | None = None  # HH:MM


class TradeConstraintConfig(BaseModel):
    """A股交易规则约束配置（NTL-S5-010 扩展）。"""

    # 是否启用 T+1 约束（买入当日不能卖出）
    t_plus_one: bool = True
    # 涨停幅度比例（None 表示按板块类型自动推断）
    limit_up_pct: float | None = None
    # 跌停幅度比例（None 表示按板块类型自动推断）
    limit_down_pct: float | None = None
    # 板块类型：auto/main/chinext/star/st/bse
    # auto 表示根据股票代码自动推断
    board_type: str = "auto"


class EvaluationConfig(BaseModel):
    min_expected_return: float = 0.0
    loss_trigger: bool = True
    trade_constraint: TradeConstraintConfig = Field(default_factory=TradeConstraintConfig)


class TraderSourceConfig(BaseModel):
    urls: list[str] = Field(default_factory=list)
    rss: list[str] = Field(default_factory=list)
    site_type: str | None = None
    crawl_frequency_minutes: int | None = None


class TradeLogSourceConfig(BaseModel):
    csv_paths: list[str] = Field(default_factory=list)
    account_ids: list[str] = Field(default_factory=list)  # 绑定到该交易员的账户列表


class TraderStylePreference(str, Enum):
    """Trader style preference."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class TraderConfig(BaseModel):
    trader_id: str
    display_name: str
    enabled: bool = True

    article_sources: TraderSourceConfig = Field(default_factory=TraderSourceConfig)
    trade_log_sources: TradeLogSourceConfig = Field(default_factory=TradeLogSourceConfig)

    watchlist: list[str] = Field(default_factory=list)
    default_target_pct: float = 0.05
    default_stop_pct: float = 0.03

    # P2-101: Trader 画像配置
    style_preference: TraderStylePreference = TraderStylePreference.MODERATE
    memory_path: str | None = None  # 可选自定义 memory JSONL 路径，默认使用 storage.output_dir/trader_memory.jsonl


class DataConfig(BaseModel):
    providers: list[str] = Field(default_factory=lambda: ["mock"])  # Phase 0 default
    mock_prices: dict[str, float] = Field(default_factory=dict)
    market_data_cache_dir: str = "data/processed/market_data"
    market_universe_snapshot_dir: str = "data/market_universe/snapshots"


class CrawlAuthConfig(BaseModel):
    mode: str = "cookie"
    cookie: str | None = None


class CrawlThrottleConfig(BaseModel):
    min_interval_seconds: float = 1.0
    max_interval_seconds: float = 2.0
    backoff_seconds: list[int] = Field(default_factory=lambda: [5, 15, 30])


class CrawlSourceConfig(BaseModel):
    source: str
    site: str
    trader_id: str | None = None
    author_id: str
    author_name: str
    list_url: str
    enabled: bool = True
    render_js: bool = False


class CrawlConfig(BaseModel):
    auth: dict[str, CrawlAuthConfig] = Field(default_factory=dict)
    throttling: CrawlThrottleConfig = Field(default_factory=CrawlThrottleConfig)
    sources: list[CrawlSourceConfig] = Field(default_factory=list)


class StorageConfig(BaseModel):
    output_dir: str = "data/processed/phase0"


class DatabaseConfig(BaseModel):
    """Database runtime config.

    This config is primarily used to provide a single source of truth for
    local (non-Docker) runs. CLI will sync these fields into environment
    variables (DATABASE_URL, etc.) before first DB access.
    """

    url: str | None = None
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800


class ApiAuthConfig(BaseModel):
    enabled: bool = False
    api_keys: list[str] = Field(default_factory=list)


class ApiConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    auth: ApiAuthConfig = Field(default_factory=ApiAuthConfig)
    # 运行超时（秒），0 表示不限制
    timeout_seconds: float = 0


class LLMConfig(BaseModel):
    provider: str | None = None  # openai/anthropic
    model: str | list[str] | None = None  # 支持单模型字符串或多模型数组
    url: str | None = None
    api_key: str | None = None


class PersonaConfig(BaseModel):
    """Persona & style routing config.

    Phase 0 can keep this disabled. When enabled, router will annotate TradeIdea
    with selected style cluster info.
    """

    enable: bool = False
    objective: str = "return_max"  # return_max/risk_min (reserved)
    clusters_path: str | None = None  # JSON file path
    top_k: int = 2
    market_state_path: str | None = None  # optional JSON file for MarketState

    # Phase 0.5: build MarketState from local daily CSV (index/ETF daily)
    market_state_benchmark_symbol: str | None = None
    market_state_benchmark_csv: str | None = None


class Stage4Config(BaseModel):
    """Stage 4 盘前主链路配置（NTL-S4-009）。

    控制是否启用新版盘前链路（策略版本 + 候选池快照）。
    当 enable=False 时，降级到 Phase 0 兼容路径（watchlist + last_price）。
    """

    enable: bool = True  # 默认启用 Stage 4 路径
    market_universe_slot: str = "09-25"  # 候选池快照时段
    allow_phase0_fallback: bool = True  # 允许在策略版本不可用时降级到 Phase 0

class KaipanConfig(BaseModel):
    """开盘啦私有接口运行配置。"""

    data_dir: str = "data/kaipan"
    schema_dir: str = "src/providers/kaipan_schema"
    token: str | None = None
    user_id: str | int | None = None
    fetch_schedule: dict[str, str] = Field(
        default_factory=lambda: {
            "pre_market": "9:25",
            "post_close": "17:30",
        }
    )
    trading_calendar: dict[str, str] = Field(default_factory=lambda: {"source": "akshare"})
    default_headers: dict[str, str] = Field(
        default_factory=lambda: {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
        }
    )
    min_request_interval_seconds: float = 0.8
    max_retries: int = 3
    retry_backoff_seconds: list[float] = Field(default_factory=lambda: [1.0, 2.0, 4.0])
    retry_status_codes: list[int] = Field(default_factory=lambda: [403, 429, 500, 502, 503, 504])


class AppConfig(BaseModel):
    timezone: str = "Asia/Shanghai"
    run_mode: str = "interactive"  # interactive/service

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    crawl: CrawlConfig = Field(default_factory=CrawlConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    persona: PersonaConfig = Field(default_factory=PersonaConfig)
    stage4: Stage4Config = Field(default_factory=Stage4Config)
    api: ApiConfig = Field(default_factory=ApiConfig)
    kaipan: KaipanConfig = Field(default_factory=KaipanConfig)

    traders: list[TraderConfig] = Field(default_factory=list)
    alerting: dict[str, Any] | None = None  # S7-007 告警配置


@dataclass(frozen=True)
class LoadedConfig:
    config: AppConfig
    config_path: Path


def load_app_config(path: str | Path) -> LoadedConfig:
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw: Any
        with config_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception as exc:  # noqa: BLE001
        raise ConfigError(f"Failed to load config: {config_path}: {exc}") from exc

    try:
        cfg = AppConfig.model_validate(_expand_env_vars(raw))
    except Exception as exc:  # noqa: BLE001
        raise ConfigError(f"Invalid config schema: {exc}") from exc

    return LoadedConfig(config=cfg, config_path=config_path)


def apply_database_config_to_env(config: AppConfig) -> None:
    """Apply `config.database` to environment variables if not already set.

    This keeps DB connection configuration in YAML while still being compatible
    with SQLAlchemy/Alembic that primarily read `DATABASE_URL`.
    """

    db = getattr(config, "database", None)
    if db is None:
        return

    if isinstance(db.url, str) and db.url.strip():
        url = db.url.strip()
        # If env expansion didn't resolve placeholders like "${DATABASE_URL}",
        # don't set an invalid literal into the environment.
        if not re.search(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}", url):
            os.environ.setdefault("DATABASE_URL", url)

    # Optional: map pooling knobs for Settings (if used)
    os.environ.setdefault("DATABASE_ECHO", str(bool(db.echo)).lower())
    os.environ.setdefault("DATABASE_POOL_SIZE", str(int(db.pool_size)))
    os.environ.setdefault("DATABASE_MAX_OVERFLOW", str(int(db.max_overflow)))
    os.environ.setdefault("DATABASE_POOL_TIMEOUT", str(int(db.pool_timeout)))
    os.environ.setdefault("DATABASE_POOL_RECYCLE", str(int(db.pool_recycle)))


def _expand_env_vars(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value
