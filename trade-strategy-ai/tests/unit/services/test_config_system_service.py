from __future__ import annotations

import asyncio
from pathlib import Path


def test_config_service_loads_and_masks_sensitive_values(tmp_path: Path) -> None:
    """配置服务应能读取配置并脱敏敏感字段。"""
    from src.services.config_service import ConfigService

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
database:
  url: postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai
  password: db-password
llm:
  api_key: llm-key
  token: llm-token
api:
  auth:
    api_keys:
      - web-key-1
crawl:
  auth:
    tgb.cn:
      cookie: cookie-value
      secret: secret-value
      nested:
        api_key: nested-key
""",
        encoding="utf-8",
    )

    service = ConfigService()
    loaded = service.load_config(config_path)
    raw = service.load_raw_config(config_path)
    masked = service.mask_config(raw)

    assert loaded.config.database.url == "postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai"
    assert masked["database"]["password"] == "***"
    assert masked["database"]["url"] == "postgresql+asyncpg://trade:***@localhost:5432/trade_strategy_ai"
    assert masked["llm"]["api_key"] == "***"
    assert masked["llm"]["token"] == "***"
    assert masked["api"]["auth"]["api_keys"] == ["***"]
    assert masked["crawl"]["auth"]["tgb.cn"]["cookie"] == "***"
    assert masked["crawl"]["auth"]["tgb.cn"]["secret"] == "***"
    assert masked["crawl"]["auth"]["tgb.cn"]["nested"]["api_key"] == "***"


def test_system_service_checks_database_and_directories(tmp_path: Path) -> None:
    """系统服务应能返回数据库与关键目录检查结果。"""
    from src.services.system_service import SystemService

    class _FakeDbChecker:
        name = "database"

        async def check(self):
            from src.health.models import ComponentCheck, HealthStatus

            return ComponentCheck(name=self.name, status=HealthStatus.OK, latency_ms=1.23)

    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
storage:
  output_dir: data/processed/phase0
data:
  market_data_cache_dir: data/processed/market_data
  market_universe_snapshot_dir: data/market_universe/snapshots
    """,
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "data" / "processed" / "phase0").mkdir(parents=True)
    (tmp_path / "data" / "processed" / "market_data").mkdir(parents=True)
    (tmp_path / "data" / "market_universe" / "snapshots").mkdir(parents=True)

    service = SystemService(db_checker=_FakeDbChecker())
    db_result = asyncio.run(service.check_database())
    dir_result = service.check_key_directories(config_path)

    assert db_result.status == "ok"
    assert db_result.payload["database"]["status"] == "ok"
    assert db_result.payload["database"]["latency_ms"] == 1.23
    assert dir_result.status == "ok"
    assert dir_result.payload["base_dir"] == str(tmp_path)
    assert dir_result.payload["directories"]["data"]["exists"] is True
    assert dir_result.payload["directories"]["logs"]["exists"] is True
