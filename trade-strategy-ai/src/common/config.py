from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.common.exceptions import ConfigError


class ScheduleConfig(BaseModel):
    enable: bool = False
    pre_market_time: str | None = None  # HH:MM
    after_close_time: str | None = None  # HH:MM


class EvaluationConfig(BaseModel):
    min_expected_return: float = 0.0
    loss_trigger: bool = True


class TraderSourceConfig(BaseModel):
    urls: list[str] = Field(default_factory=list)
    rss: list[str] = Field(default_factory=list)
    site_type: str | None = None
    crawl_frequency_minutes: int | None = None


class TradeLogSourceConfig(BaseModel):
    csv_paths: list[str] = Field(default_factory=list)


class TraderConfig(BaseModel):
    trader_id: str
    display_name: str

    article_sources: TraderSourceConfig = Field(default_factory=TraderSourceConfig)
    trade_log_sources: TradeLogSourceConfig = Field(default_factory=TradeLogSourceConfig)

    watchlist: list[str] = Field(default_factory=list)
    default_target_pct: float = 0.05
    default_stop_pct: float = 0.03


class DataConfig(BaseModel):
    providers: list[str] = Field(default_factory=lambda: ["mock"])  # Phase 0 default
    mock_prices: dict[str, float] = Field(default_factory=dict)


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
    author_id: str
    author_name: str
    list_url: str
    enabled: bool = True


class CrawlConfig(BaseModel):
    auth: dict[str, CrawlAuthConfig] = Field(default_factory=dict)
    throttling: CrawlThrottleConfig = Field(default_factory=CrawlThrottleConfig)
    sources: list[CrawlSourceConfig] = Field(default_factory=list)


class StorageConfig(BaseModel):
    output_dir: str = "data/processed/phase0"


class LLMConfig(BaseModel):
    provider: str | None = None  # openai/anthropic
    model: str | None = None
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


class AppConfig(BaseModel):
    timezone: str = "Asia/Shanghai"
    run_mode: str = "interactive"  # interactive/service

    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    crawl: CrawlConfig = Field(default_factory=CrawlConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    persona: PersonaConfig = Field(default_factory=PersonaConfig)

    traders: list[TraderConfig] = Field(default_factory=list)


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


def _expand_env_vars(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value
