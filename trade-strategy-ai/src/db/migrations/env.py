from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from src.models.base import Base  # noqa: E402
from src.models import (  # noqa: F401
    article_metadata,
    article_metadata_selection,
    blog_article,
    crawl_state,
    data_audit_event,
    backtest_result_run,
    evidence_pack,
    market_data,
    hot_topics_snapshot,
    ohlcv_bar,
    ranking_entry,
    job,
    job_audit_event,
    raw_article,
    market_regime,
    rule_applicability,
    workflow_run,
    signal,
    stock_info,
    stage2_canonical,
    strong_symbols_snapshot,
    topic_mapping,
    topic_constituents_snapshot,
    trader_strategy_version,
    strategy_regime_selection,
    trade_log,
    user,
)
from src.rule_pool import models as rule_pool_models  # noqa: F401,E402
from src.alerting import db as alerting_db  # noqa: F401,E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
COMPATIBILITY_VIEW_TABLES = {"market_datasets", "strategy_regime_selections", "regime_rule_selections"}


def _get_database_url() -> str:
    # 优先使用环境变量覆盖，方便 docker/.env 驱动
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    return config.get_main_option("sqlalchemy.url")


def _include_object(object_, name, type_, reflected, compare_to):
    if type_ != "table":
        return True

    object_info = getattr(object_, "info", {}) or {}
    compare_info = getattr(compare_to, "info", {}) or {}
    if object_info.get("compatibility_view") or compare_info.get("compatibility_view"):
        return False
    if reflected and name in COMPATIBILITY_VIEW_TABLES:
        return False
    return True

def run_migrations_offline():
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    # 将 url 写回 alembic config，使 async_engine_from_config 能读取
    config.set_main_option("sqlalchemy.url", _get_database_url())

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    def do_run_migrations(connection) -> None:  # connection: sqlalchemy.engine.Connection
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
