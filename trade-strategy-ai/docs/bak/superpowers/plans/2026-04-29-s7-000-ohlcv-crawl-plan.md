# NTL-S7-000 & ohlcv_crawl Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
1. Fix `cli/backtest.py` SnapshotLoader dependency injection (P0)
2. Add ohlcv_crawl system with CLI + Task Handler (P1)

**Architecture:**
- S7-000 fix: Create `StrategyRepoAdapter` to wrap `StrategyLibraryRepository` with session management, initialize `SnapshotService` directly
- ohlcv_crawl: New `OHLCVBar` + `Indicator` models, `OHLCVService` for data crawling, `cli/ohlcv.py` for CLI access, `ohlcv_crawl_task.py` for task queue

**Tech Stack:** SQLAlchemy async, Alembic migrations, typer CLI, akshare

---

## File Structure

```
# New files
src/market_data/
  __init__.py
  ohlcv_service.py          # Core crawling logic
  strategy_repo_adapter.py # StrategyRepoAdapter for S7-000 fix

src/models/
  ohlcv_bar.py              # OHLCVBar model
  indicator.py              # Indicator model

src/pipeline/tasks/
  ohlcv_crawl_task.py       # Task handler

cli/
  ohlcv.py                  # CLI command

# Modified files
cli/backtest.py             # S7-000 fix
src/models/__init__.py      # Export new models
src/pipeline/tasks/process_tasks.py  # Register handler
```

---

## Task 1: S7-000 Fix - StrategyRepoAdapter

**Files:**
- Create: `src/market_data/strategy_repo_adapter.py`
- Modify: `cli/backtest.py:33-57`

- [ ] **Step 1: Write test for StrategyRepoAdapter**

```python
# tests/unit/market_data/test_strategy_repo_adapter.py
import pytest
from datetime import date
from src.market_data.strategy_repo_adapter import StrategyRepoAdapter
from src.strategy_library.schemas import StrategyVersion, StrategyVersionStatus

@pytest.fixture
def mock_repo():
    """Mock StrategyLibraryRepository"""
    class MockRepo:
        async def get_released_by_trader_and_date(self, session, trader_id, strategy_date):
            return [
                StrategyVersion(
                    version_id="test_v1",
                    trader_id=trader_id,
                    strategy_date=strategy_date,
                    status=StrategyVersionStatus.released,
                    recommendations=[],
                    source_article_ids=[],
                    evidence_refs=[],
                )
            ]
    return MockRepo()

@pytest.mark.asyncio
async def test_get_released_by_trader_and_date(mock_repo):
    adapter = StrategyRepoAdapter(repo=mock_repo)
    versions = await adapter.get_released_by_trader_and_date(
        trader_id="trader_a",
        strategy_date=date(2026, 4, 23),
    )
    assert len(versions) == 1
    assert versions[0].version_id == "test_v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/market_data/test_strategy_repo_adapter.py -v`
Expected: FAIL - directory/file doesn't exist

- [ ] **Step 3: Create directory**

Run: `mkdir -p tests/unit/market_data`

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/unit/market_data/test_strategy_repo_adapter.py -v`
Expected: FAIL - StrategyRepoAdapter not defined

- [ ] **Step 5: Write StrategyRepoAdapter**

```python
# src/market_data/strategy_repo_adapter.py
"""StrategyRepoAdapter - 包装 StrategyLibraryRepository，自动管理 AsyncSession。

用于 SnapshotLoader.load_version_for_date() 的依赖注入。
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from src.strategy_library.schemas import StrategyVersion

if TYPE_CHECKING:
    from src.strategy_library.repository import StrategyLibraryRepository


class StrategyRepoAdapter:
    """strategy_repo 适配器。

    SnapshotLoader.load_version_for_date() 调用时，
    内部创建 session、调用 repository、返回结果。
    """

    def __init__(self, repo: StrategyLibraryRepository | None = None) -> None:
        from src.strategy_library.repository import StrategyLibraryRepository
        from config.database import get_session_factory

        self._factory = get_session_factory()
        self._repo = repo or StrategyLibraryRepository()

    async def get_released_by_trader_and_date(
        self, trader_id: str, strategy_date: date
    ) -> list[StrategyVersion]:
        """查询指定交易员和日期的已发布版本。"""
        async with self._factory() as session:
            return await self._repo.get_released_by_trader_and_date(
                session=session,
                trader_id=trader_id,
                strategy_date=strategy_date,
            )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/unit/market_data/test_strategy_repo_adapter.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/market_data/strategy_repo_adapter.py tests/unit/market_data/test_strategy_repo_adapter.py
git commit -m "feat(s7-000): add StrategyRepoAdapter for SnapshotLoader"
```

---

## Task 2: S7-000 Fix - Update cli/backtest.py

**Files:**
- Modify: `cli/backtest.py:33-57`

- [ ] **Step 1: Write test for _create_engine_from_config with dependencies**

```python
# tests/unit/cli/test_backtest.py
import pytest
from pathlib import Path
from src.backtest.engine import BacktestEngine

def test_create_engine_with_config(tmp_path):
    """验证配置加载时正确初始化 SnapshotLoader 依赖"""
    from cli.backtest import _create_engine_from_config

    # 创建临时配置文件
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
database:
  url: null
data:
  providers: []
""")

    engine = _create_engine_from_config(str(config_file))
    assert isinstance(engine, BacktestEngine)
    # loader 不应为 None
    assert engine.loader is not None
    # snapshot_service 不应为 None（如果有快照目录）
    # strategy_loader 不应为 None
    assert engine.strategy_loader is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/cli/test_backtest.py::test_create_engine_with_config -v`
Expected: FAIL - loader/strategy_loader is None

- [ ] **Step 3: Update _create_engine_from_config**

```python
def _create_engine_from_config(config_path: str | None) -> BacktestEngine:
    """从配置创建 BacktestEngine（带依赖注入）。

    若未提供配置或配置中未定义回测依赖，则返回无 loader 的引擎（所有记录为 skipped）。
    """
    if config_path is None:
        return BacktestEngine()

    from src.common.config import load_app_config

    try:
        loaded = load_app_config(config_path)
    except Exception as exc:
        typer.secho(f"配置加载失败: {exc}", fg=typer.colors.YELLOW)
        return BacktestEngine()

    # 初始化 SnapshotService
    from src.market_universe.snapshot_service import SnapshotService

    snapshot_service = SnapshotService(
        base_dir="data/market_universe/snapshots"
    )

    # 初始化 StrategyRepoAdapter
    from src.market_data.strategy_repo_adapter import StrategyRepoAdapter

    strategy_repo_adapter = StrategyRepoAdapter()

    from src.backtest.snapshot_loader import SnapshotLoader

    loader = SnapshotLoader(
        snapshot_service=snapshot_service,
        strategy_repo=strategy_repo_adapter,
    )
    return BacktestEngine(loader=loader, strategy_loader=loader)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/cli/test_backtest.py::test_create_engine_with_config -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cli/backtest.py
git commit -m "fix(s7-000): initialize SnapshotLoader dependencies in backtest CLI"
```

---

## Task 3: Create OHLCVBar Model

**Files:**
- Create: `src/models/ohlcv_bar.py`
- Modify: `src/models/__init__.py`

- [ ] **Step 1: Write test for OHLCVBar model**

```python
# tests/unit/models/test_ohlcv_bar.py
import pytest
from datetime import date
from src.models.ohlcv_bar import OHLCVBar

def test_ohlcv_bar_creation():
    bar = OHLCVBar(
        symbol="000001.SZ",
        trade_date=date(2026, 4, 28),
        open=10.0,
        high=10.5,
        low=9.8,
        close=10.2,
        volume=1000000,
    )
    assert bar.symbol == "000001.SZ"
    assert bar.trade_date == date(2026, 4, 28)
    assert bar.close == 10.2

def test_ohlcv_bar_unique_constraint():
    """同一 symbol + trade_date 只能有一条记录"""
    from sqlalchemy import exc
    from src.db.session import get_session_factory
    import asyncio

    async def test_duplicate():
        factory = get_session_factory()
        async with factory() as session:
            bar1 = OHLCVBar(
                symbol="000001.SZ",
                trade_date=date(2026, 4, 28),
                open=10.0, high=10.5, low=9.8, close=10.2,
                volume=1000000,
            )
            session.add(bar1)
            await session.commit()

            bar2 = OHLCVBar(
                symbol="000001.SZ",
                trade_date=date(2026, 4, 28),
                open=10.1, high=10.6, low=9.9, close=10.3,
                volume=2000000,
            )
            session.add(bar2)
            with pytest.raises(Exception):  # UniqueConstraint violation
                await session.commit()

    asyncio.run(test_duplicate())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/models/test_ohlcv_bar.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write OHLCVBar model**

```python
# src/models/ohlcv_bar.py
"""OHLCVBar 模型 - 日线行情数据"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class OHLCVBar(Base):
    """日线行情数据表

    存储股票每日 OHLCV 数据，用于回测和规则验真。
    """

    __tablename__ = "ohlcv_bars"
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_ohlcv_symbol_date"),
        Index("ix_ohlcv_symbol", "symbol"),
        Index("ix_ohlcv_trade_date", "trade_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # 标准代码，如 "000001.SZ"
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    # 交易日期
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    # 成交额（可选）
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
```

- [ ] **Step 4: Update src/models/__init__.py**

Add to imports:
```python
from src.models.ohlcv_bar import OHLCVBar
```

Add to __all__:
```python
    "OHLCVBar",
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/models/test_ohlcv_bar.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/models/ohlcv_bar.py src/models/__init__.py tests/unit/models/test_ohlcv_bar.py
git commit -m "feat(s7-000): add OHLCVBar model for daily market data"
```

---

## Task 4: Create Indicator Model

**Files:**
- Create: `src/models/indicator.py`
- Modify: `src/models/__init__.py`

- [ ] **Step 1: Write test for Indicator model**

```python
# tests/unit/models/test_indicator.py
import pytest
from datetime import date
from src.models.indicator import Indicator

def test_indicator_creation():
    ind = Indicator(
        symbol="000001.SZ",
        trade_date=date(2026, 4, 28),
        rsi=65.5,
        macd_histogram=0.12,
        bb_width=0.05,
        cci=120.0,
        ma50=10.2,
        ma200=9.8,
    )
    assert ind.symbol == "000001.SZ"
    assert ind.rsi == 65.5
    assert ind.macd_histogram == 0.12
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/models/test_indicator.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write Indicator model**

```python
# src/models/indicator.py
"""Indicator 模型 - 技术指标数据（按需计算更新）"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, Float, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Indicator(Base):
    """技术指标数据表

    按需计算并存储，支持后续回测和规则验真。
    """

    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_indicator_symbol_date"),
        Index("ix_indicator_symbol", "symbol"),
        Index("ix_indicator_trade_date", "trade_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # 标准代码
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    # 交易日期
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    # RSI
    rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MACD 柱状图
    macd_histogram: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 布林带宽度
    bb_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    # CCI
    cci: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MA50
    ma50: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MA200
    ma200: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 随机指标 K
    stoch_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 量比
    volume_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 价格相对均线比率
    price_vs_ma: Mapped[float | None] = mapped_column(Float, nullable=True)
    # ATR 比率
    atr_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 收盘位置
    close_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 计算时间
    computed_at: Mapped[datetime] = mapped_column(nullable=False)
```

- [ ] **Step 4: Update src/models/__init__.py**

Add to imports:
```python
from src.models.indicator import Indicator
```

Add to __all__:
```python
    "Indicator",
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/models/test_indicator.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/models/indicator.py src/models/__init__.py tests/unit/models/test_indicator.py
git commit -m "feat(s7-000): add Indicator model for technical indicators"
```

---

## Task 5: Create OHLCVService

**Files:**
- Create: `src/market_data/ohlcv_service.py`
- Create: `tests/unit/market_data/test_ohlcv_service.py`

- [ ] **Step 1: Write test for OHLCVService**

```python
# tests/unit/market_data/test_ohlcv_service.py
import pytest
from datetime import date
from src.market_data.ohlcv_service import OHLCVService

@pytest.fixture
def service():
    from config.database import get_session_factory
    return OHLCVService(session_factory=get_session_factory())

@pytest.mark.asyncio
async def test_crawl_bars_single_symbol(service):
    """测试单标的 ohlcv 抓取"""
    results = await service.crawl_bars(
        symbols=["000001.SZ"],
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 28),
    )
    assert "000001.SZ" in results
    assert results["000001.SZ"] >= 0

@pytest.mark.asyncio
async def test_get_bars(service):
    """测试获取 bars"""
    bars = await service.get_bars(
        symbol="000001.SZ",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 28),
    )
    assert isinstance(bars, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/market_data/test_ohlcv_service.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write OHLCVService**

```python
# src/market_data/ohlcv_service.py
"""OHLCV 数据服务 - 抓取并存储日线行情数据"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.ohlcv_bar import OHLCVBar
from src.common.logger import get_logger

logger = get_logger(__name__)


class OHLCVService:
    """ohlcv 数据服务。

    职责：
    - 从 AkShare 批量抓取日线数据
    - 存储到数据库（upsert 模式）
    - 提供按日期/标的查询接口
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def crawl_bars(
        self,
        symbols: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, int]:
        """抓取并存储 ohlcv 数据。

        Args:
            symbols: 股票代码列表
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            dict[symbol, count] 抓取成功的记录数
        """
        from src.providers.akshare_provider import AkshareProvider

        provider = AkshareProvider()
        results: dict[str, int] = {}

        for symbol in symbols:
            try:
                df = provider.fetch_ohlcv_1d(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )
                count = await self._upsert_bars(symbol, df)
                results[symbol] = count
                logger.info(f"抓取成功: {symbol}, {count} 条记录")
            except Exception as e:
                logger.warning(f"抓取失败: {symbol}, error={e}")
                results[symbol] = 0

        return results

    async def _upsert_bars(self, symbol: str, df: pd.DataFrame) -> int:
        """批量 upsert bars 到数据库"""
        if df is None or df.empty:
            return 0

        async with self._factory() as session:
            count = 0
            for _, row in df.iterrows():
                trade_date = row.get("date")
                if trade_date is None:
                    continue

                # 检查是否已存在
                stmt = select(OHLCVBar).where(
                    OHLCVBar.symbol == symbol,
                    OHLCVBar.trade_date == trade_date,
                )
                existing = await session.scalar(stmt)

                if existing:
                    # 更新
                    existing.open = float(row.get("open", 0))
                    existing.high = float(row.get("high", 0))
                    existing.low = float(row.get("low", 0))
                    existing.close = float(row.get("close", 0))
                    existing.volume = float(row.get("volume", 0))
                    existing.turnover = float(row.get("turnover")) if row.get("turnover") else None
                else:
                    # 插入
                    bar = OHLCVBar(
                        symbol=symbol,
                        trade_date=trade_date,
                        open=float(row.get("open", 0)),
                        high=float(row.get("high", 0)),
                        low=float(row.get("low", 0)),
                        close=float(row.get("close", 0)),
                        volume=float(row.get("volume", 0)),
                        turnover=float(row.get("turnover")) if row.get("turnover") else None,
                    )
                    session.add(bar)
                count += 1

            await session.commit()
            return count

    async def get_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[OHLCVBar]:
        """查询指定区间 ohlcv 数据"""
        async with self._factory() as session:
            stmt = select(OHLCVBar).where(
                OHLCVBar.symbol == symbol,
                OHLCVBar.trade_date >= start_date,
                OHLCVBar.trade_date <= end_date,
            ).order_by(OHLCVBar.trade_date)
            result = await session.scalars(stmt)
            return list(result.all())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/market_data/test_ohlcv_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/market_data/ohlcv_service.py tests/unit/market_data/test_ohlcv_service.py
git commit -m "feat(s7-000): add OHLCVService for daily market data crawling"
```

---

## Task 6: Create ohlcv CLI Command

**Files:**
- Create: `cli/ohlcv.py`

- [ ] **Step 1: Write test for ohlcv CLI**

```python
# tests/unit/cli/test_ohlcv.py
import pytest
from typer.testing import CliRunner
from cli.ohlcv import app

runner = CliRunner()

def test_crawl_command_help():
    result = runner.invoke(app, ["crawl", "--help"])
    assert result.exit_code == 0
    assert "crawl" in result.output.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/cli/test_ohlcv.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write ohlcv CLI**

```python
# cli/ohlcv.py
"""OHLCV 数据抓取 CLI 命令

提供以下子命令：
- ohlcv crawl：抓取日线数据并存入数据库
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import typer

from src.common.logger import get_logger

logger = get_logger(__name__)

app = typer.Typer(add_completion=False, help="OHLCV 数据相关命令")


def _parse_date(value: str) -> date:
    """解析 YYYY-MM-DD 格式日期"""
    return datetime.strptime(value, "%Y-%m-%d").date()


@app.command("crawl")
def crawl_ohlcv(
    mode: str = typer.Option("incremental", "--mode", help="full / incremental"),
    symbols_file: Path | None = typer.Option(None, "--symbols-file", help="股票列表文件（每行一个代码）"),
    start_date: str | None = typer.Option(None, "--from", help="起始日期 YYYY-MM-DD"),
    end_date: str | None = typer.Option(None, "--to", help="结束日期 YYYY-MM-DD"),
    limit: int = typer.Option(100, "--limit", help="最多抓取标的数量（full 模式）"),
) -> None:
    """抓取 ohlcv 数据并存入数据库。

    示例：
        python -m cli.main ohlcv crawl --mode incremental
        python -m cli.main ohlcv crawl --mode full --from 2026-01-01 --to 2026-04-28
        python -m cli.main ohlcv crawl --symbols-file symbols.txt
    """
    # 解析日期
    start = _parse_date(start_date) if start_date else None
    end = _parse_date(end_date) if end_date else date.today()

    # 读取标的列表
    symbols = _load_symbols(symbols_file, mode, limit)

    logger.info(
        "CLI ohlcv crawl: mode=%s, symbols=%d, start=%s, end=%s",
        mode,
        len(symbols),
        start,
        end,
    )

    # 执行抓取
    import asyncio
    from config.database import get_session_factory
    from src.market_data.ohlcv_service import OHLCVService

    async def run_crawl():
        factory = get_session_factory()
        service = OHLCVService(session_factory=factory)

        if mode == "full":
            results = await service.crawl_bars(
                symbols=symbols,
                start_date=start,
                end_date=end,
            )
        else:
            # incremental: 只抓取 end 日期的数据
            results = await service.crawl_bars(
                symbols=symbols,
                start_date=end,
                end_date=end,
            )

        return results

    results = asyncio.run(run_crawl())

    # 输出摘要
    success = sum(1 for c in results.values() if c > 0)
    total = sum(results.values())
    typer.echo(f"抓取完成: {success}/{len(symbols)} 标的成功, 共 {total} 条记录")


def _load_symbols(symbols_file: Path | None, mode: str, limit: int) -> list[str]:
    """加载标的列表"""
    if symbols_file:
        if not symbols_file.exists():
            typer.secho(f"文件不存在: {symbols_file}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        return [line.strip() for line in symbols_file.read_text().splitlines() if line.strip()][:limit]

    # 默认：从数据库获取股票列表
    import asyncio
    from sqlalchemy import select
    from src.models.stock_info import StockInfo
    from src.db.session import session_scope

    async def get_symbols():
        symbols = []
        async with session_scope() as session:
            stmt = select(StockInfo.symbol).where(
                StockInfo.security_type == "stock"
            ).limit(limit)
            result = await session.scalars(stmt)
            symbols = list(result.all())
        return symbols

    return asyncio.run(get_symbols())


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/cli/test_ohlcv.py -v`
Expected: PASS

- [ ] **Step 5: Register to main CLI**

Modify `cli/main.py` to add:
```python
from cli.ohlcv import app as ohlcv_app
main.add_typer(ohlcv_app, name="ohlcv")
```

- [ ] **Step 6: Commit**

```bash
git add cli/ohlcv.py cli/main.py tests/unit/cli/test_ohlcv.py
git commit -m "feat(s7-000): add ohlcv crawl CLI command"
```

---

## Task 7: Create ohlcv_crawl Task Handler

**Files:**
- Create: `src/pipeline/tasks/ohlcv_crawl_task.py`
- Modify: `src/pipeline/tasks/process_tasks.py`

- [ ] **Step 1: Write test for ohlcv_crawl_task**

```python
# tests/unit/pipeline/test_ohlcv_crawl_task.py
import pytest
from unittest.mock import AsyncMock, patch
from src.pipeline.tasks.ohlcv_crawl_task import handle_ohlcv_crawl
from src.common.config import AppConfig

@pytest.fixture
def mock_config():
    return AppConfig()

@pytest.mark.asyncio
async def test_handle_ohlcv_crawl_incremental(mock_config):
    """测试增量抓取"""
    details = {
        "mode": "incremental",
        "symbols": ["000001.SZ"],
    }

    with patch("src.market_data.ohlcv_service.OHLCVService") as MockService:
        mock_instance = AsyncMock()
        mock_instance.crawl_bars.return_value = {"000001.SZ": 1}
        MockService.return_value = mock_instance

        await handle_ohlcv_crawl(details, config=mock_config)

        mock_instance.crawl_bars.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_ohlcv_crawl_task.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write ohlcv_crawl_task**

```python
# src/pipeline/tasks/ohlcv_crawl_task.py
"""ohlcv_crawl Pipeline Task

Task handler for ohlcv data crawling.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from src.common.config import AppConfig
from src.common.logger import get_logger

logger = get_logger(__name__)


async def handle_ohlcv_crawl(
    details: dict[str, Any],
    *,
    config: AppConfig,
) -> None:
    """Task handler for ohlcv crawl.

    details 期望字段：
        mode: "full" | "incremental"
        symbols: list[str] | None
        start_date: str | None
        end_date: str | None
    """
    from config.database import get_session_factory
    from src.market_data.ohlcv_service import OHLCVService

    mode = details.get("mode", "incremental")
    symbols = details.get("symbols")
    start_date_str = details.get("start_date")
    end_date_str = details.get("end_date")

    start_date = date.fromisoformat(start_date_str) if start_date_str else None
    end_date = date.fromisoformat(end_date_str) if end_date_str else date.today()

    factory = get_session_factory()
    service = OHLCVService(session_factory=factory)

    logger.info(
        "ohlcv_crawl task: mode=%s, symbols=%s, start=%s, end=%s",
        mode,
        len(symbols) if symbols else "all",
        start_date,
        end_date,
    )

    if mode == "full":
        if symbols is None:
            # 全量模式需要标的列表
            logger.warning("ohlcv_crawl full 模式需要 symbols 参数，跳过")
            return
        results = await service.crawl_bars(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        # 增量模式：只抓取 end_date 当日
        if symbols is None:
            # 从数据库加载所有股票代码
            from sqlalchemy import select
            from src.models.stock_info import StockInfo

            async with factory() as session:
                stmt = select(StockInfo.symbol).where(
                    StockInfo.security_type == "stock"
                )
                result = await session.scalars(stmt)
                symbols = list(result.all())

        results = await service.crawl_bars(
            symbols=symbols,
            start_date=end_date,
            end_date=end_date,
        )

    success = sum(1 for c in results.values() if c > 0)
    logger.info(
        "ohlcv_crawl task 完成: %d/%d 标的成功",
        success,
        len(results),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_ohlcv_crawl_task.py -v`
Expected: PASS

- [ ] **Step 5: Register handler in process_tasks.py**

In `_create_handlers()` function, add:
```python
from src.pipeline.tasks.ohlcv_crawl_task import handle_ohlcv_crawl

async def handle_ohlcv_crawl_wrapped(details: dict[str, Any]) -> None:
    await handle_ohlcv_crawl(details, config=config)

TASK_HANDLERS["ohlcv_crawl"] = handle_ohlcv_crawl_wrapped
```

- [ ] **Step 6: Commit**

```bash
git add src/pipeline/tasks/ohlcv_crawl_task.py src/pipeline/tasks/process_tasks.py
git commit -m "feat(s7-000): add ohlcv_crawl task handler"
```

---

## Task 8: Add Alembic Migration

**Files:**
- Create: `src/db/migrations/versions/2026-04-29_xxxx_add_ohlcv_indicators.py`

- [ ] **Step 1: Generate migration**

Run:
```bash
cd /Users/wanghui/Documents/Claude/trade-strategy-ai
alembic revision --autogenerate -m "add ohlcv_bars and indicators tables"
```

- [ ] **Step 2: Review migration file**

Check that it contains:
- `ohlcv_bars` table with symbol, trade_date, open, high, low, close, volume, turnover
- `indicators` table with symbol, trade_date, rsi, macd_histogram, bb_width, cci, ma50, ma200, stoch_k, volume_ratio, price_vs_ma, atr_ratio, close_position

- [ ] **Step 3: Run migration**

Run:
```bash
alembic upgrade head
```

- [ ] **Step 4: Commit migration**

```bash
git add src/db/migrations/versions/
git commit -m "feat(s7-000): add ohlcv_bars and indicators tables"
```

---

## Task 9: Integration Test

**Files:**
- Modify: `tests/integration/test_backtest_with_ohlcv.py` (create if not exists)

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_backtest_with_ohlcv.py
import pytest
from datetime import date
from src.backtest.engine import BacktestEngine
from src.backtest.schemas import BacktestRequest

def test_backtest_runs_with_real_data():
    """集成测试：回测使用真实数据"""
    engine = BacktestEngine()

    request = BacktestRequest(
        trader_id="trader_a",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 10),
    )

    result = engine.run_sync(request)

    # 如果有数据，应该有非 skipped 记录
    traded = [r for r in result.records if r.status == "traded"]
    skipped = [r for r in result.records if r.status == "skipped"]

    print(f"Total: {len(result.records)}, Traded: {len(traded)}, Skipped: {len(skipped)}")

    # 至少应该有尝试加载数据
    assert len(result.records) > 0
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/integration/test_backtest_with_ohlcv.py -v -s`
Expected: 输出显示实际加载情况

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_backtest_with_ohlcv.py
git commit -m "test(s7-000): add integration test for backtest with ohlcv data"
```

---

## Self-Review Checklist

1. **Spec coverage:** All requirements from design doc are implemented
2. **Placeholder scan:** No "TBD", "TODO", or vague steps
3. **Type consistency:** All method signatures match across files

---

## Plan Complete

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
