# NTL-S7-000 & ohlcv_crawl 设计文档

> 日期：2026-04-29
> 目标：修复 cli/backtest.py 依赖注入 + 新增 ohlcv 数据抓取系统

---

## 1. S7-000 主修复：SnapshotLoader 依赖注入

### 问题

`cli/backtest.py` 第 53-56 行：
```python
loader = SnapshotLoader(
    snapshot_service=None,  # TODO: 根据配置初始化具体快照服务
    strategy_repo=None,     # TODO: 根据配置初始化策略仓库
)
```

导致：
1. `snapshot_service=None` → 所有快照加载返回空，回测所有记录 skip
2. `strategy_repo=None` → 策略版本加载返回 `None`，回测跳过所有交易日

### 修复方案

#### 1.1 `snapshot_service` 初始化

```python
from src.market_universe.snapshot_service import SnapshotService

snapshot_service = SnapshotService(
    base_dir="data/market_universe/snapshots"
)
```

**说明**：
- `SnapshotService` 基于文件系统，`load()` 是同步方法
- `SnapshotLoader._load_snapshot()` 已处理同步/异步兼容

#### 1.2 `strategy_repo` 初始化

需要创建一个适配器，包装 `StrategyLibraryRepository` 并自动管理 session：

```python
from config.database import get_session_factory
from src.strategy_library.repository import StrategyLibraryRepository
from src.strategy_library.schemas import StrategyVersion

class StrategyRepoAdapter:
    """strategy_repo 适配器，自动管理 AsyncSession。

    SnapshotLoader.load_version_for_date() 调用时，
    内部创建 session、调用 repository、返回结果。
    """

    def __init__(self) -> None:
        self._factory = get_session_factory()
        self._repo = StrategyLibraryRepository()

    async def get_released_by_trader_and_date(
        self, trader_id: str, strategy_date: date
    ) -> list[StrategyVersion]:
        async with self._factory() as session:
            return await self._repo.get_released_by_trader_and_date(
                session=session,
                trader_id=trader_id,
                strategy_date=strategy_date,
            )
```

### 修改文件

- `cli/backtest.py`：修改 `_create_engine_from_config()` 函数

---

## 2. ohlcv_crawl 系统设计

### 目标

- 支持 CLI 命令和 Task Handler 两种调用方式
- 将 ohlcv bars 数据持久化到数据库
- indicators 和 listing_dates 保留数据库字段，可后续计算更新

### 数据模型

```python
# src/models/ohlcv_bar.py

class OHLCVBar(Base):
    """日线行情数据"""
    __tablename__ = "ohlcv_bars"

    id: int
    symbol: str           # 股票代码，如 "000001.SZ"
    trade_date: date      # 交易日期
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float | None
    created_at: datetime

    # 唯一约束：symbol + trade_date
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_ohlcv_symbol_date"),
    )
```

```python
# src/models/stock_info.py 扩展

class StockInfo(Base):
    """股票基本信息（已有字段）"""
    __tablename__ = "stock_info"

    id: int
    symbol: str
    code: str
    market: str  # SZ / SH / BJ
    name: str
    security_type: str
    updated_at: datetime

    # 新增字段
    listing_date: date | None  # 上市日期，用于判断新股
```

```python
# src/models/indicator.py 新增

class Indicator(Base):
    """技术指标数据（按需计算更新）"""
    __tablename__ = "indicators"

    id: int
    symbol: str
    trade_date: date
    rsi: float | None
    macd_histogram: float | None
    bb_width: float | None
    cci: float | None
    ma50: float | None
    ma200: float | None
    volume_ratio: float | None
    atr_ratio: float | None
    close_position: float | None
    computed_at: datetime

    # 唯一约束：symbol + trade_date
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_indicator_symbol_date"),
    )
```

### 核心服务

```python
# src/market_data/ohlcv_service.py

class OHLCVService:
    """ohlcv 数据服务。

    职责：
    - 从 AkShare 批量抓取日线数据
    - 存储到数据库（upsert 模式）
    - 提供按日期/标的查询接口
    """

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._factory = session_factory

    async def crawl_bars(
        self,
        symbols: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, int]:
        """抓取并存储 ohlcv 数据。

        Returns:
            dict[symbol, count] 抓取成功的记录数
        """
        from src.providers.akshare_provider import AkshareProvider

        provider = AkshareProvider()
        results = {}

        for symbol in symbols:
            try:
                df = provider.fetch_ohlcv_1d(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )
                count = await self._upsert_bars(symbol, df)
                results[symbol] = count
            except Exception:
                results[symbol] = 0

        return results

    async def _upsert_bars(self, symbol: str, df: pd.DataFrame) -> int:
        """批量 upsert bars 到数据库"""
        # 实现 upsert 逻辑
        pass

    async def get_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[OHLCVBar]:
        """查询指定区间 ohlcv 数据"""
        pass
```

### CLI 命令

```python
# cli/ohlcv.py

@app.command("crawl")
def crawl_ohlcv(
    mode: str = typer.Option("incremental", "--mode", help="full / incremental"),
    symbols_file: Path | None = typer.Option(None, "--symbols-file", help="股票列表文件"),
    start_date: str | None = typer.Option(None, "--from", help="起始日期 YYYY-MM-DD"),
    end_date: str | None = typer.Option(None, "--to", help="结束日期 YYYY-MM-DD"),
):
    """抓取 ohlcv 数据并存入数据库。

    示例：
        python -m cli.main ohlcv crawl --mode full --from 2026-01-01
        python -m cli.main ohlcv crawl --mode incremental
    """
```

### Task Handler

```python
# src/pipeline/tasks/ohlcv_crawl_task.py

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
    from src.market_data.ohlcv_service import OHLCVService
    from config.database import get_session_factory

    factory = get_session_factory()
    service = OHLCVService(session_factory=factory)

    mode = details.get("mode", "incremental")
    # ... 调用 service.crawl_bars()
```

注册到 `process_tasks.py`：
```python
# _create_handlers() 中添加
async def handle_ohlcv_crawl_wrapped(details: dict[str, Any]) -> None:
    await handle_ohlcv_crawl(details, config=config)

TASK_HANDLERS["ohlcv_crawl"] = handle_ohlcv_crawl_wrapped
```

### 持久化流程

```
CLI 命令 / Task Handler
    ↓
OHLCVService.crawl_bars()
    ↓
AkshareProvider.fetch_ohlcv_1d()  # 获取原始数据
    ↓
OHLCVService._upsert_bars()       # 写入数据库
    ↓
Indicator.compute() 可后续调用，更新 indicators 表
```

### 存储结构

| 表名 | 用途 | 更新频率 |
|------|------|----------|
| `ohlcv_bars` | 日线行情 | 每日增量 |
| `stock_info` | 股票信息 + listing_date | 定期全量 |
| `indicators` | 技术指标 | 按需计算 |

---

## 4. CSV→DB 迁移记录 (2026-04-29)

### 背景

原有的 `MarketDataCache`（CSV 缓存层）在项目初期用于 Agent 获取 `last_price` 和 Manager Agent 构建 `MarketState`。随着 `ohlcv_bars` 表的引入，需要将数据访问层从 CSV 迁移到数据库。

### 迁移内容

#### 1. Agent 侧 price 查询（data_agent）

**文件**: `src/agents/data_agent/skills/fetch_market.py`

- `to_payload()` 改为 `async` 函数
- 数据来源优先级：`mock_prices` → `ohlcv_bars` 表
- 移除了 `MarketDataCache` 依赖
- `batch_get_last_prices_async()` 使用 `asyncio.gather()` 并发查询 DB

#### 2. Manager Agent 市场状态（manager_agent）

**文件**: `src/agents/manager_agent/agent.py`

- 新增 `_load_market_state_from_db()` 异步方法
- 优先从 `ohlcv_bars` 表加载 benchmark symbol 历史数据
- 不足 30 条时 fallback 到 CSV 缓存（过渡策略）
- `run_pre_market()` 中使用 DB 作为 primary source

#### 3. OHLCVService 新增方法

**文件**: `src/market_data/ohlcv_service.py`

- `get_latest_close(symbol)`: 获取某标的最新收盘价
- `get_latest_close_sync(symbol)`: 同步包装器
- `get_bars_as_df(symbol, start_date, end_date)`: 返回 DataFrame（与 `classify_market_state` 兼容）

### 保留的 Fallback

CSV 缓存作为 fallback 保留，原因：
1. `ohlcv_bars` 表在迁移初期数据可能不完整
2. 避免系统因数据缺失而完全不可用
3. 待 `ohlcv_crawl` 填充完整数据后可考虑移除

### 待删除的废弃代码

- `MarketDataCache` 类（`src/market_data/service.py`）
- `MarketDataSyncService` 类（`src/market_data/service.py`）
- `cli/main.py` 中的 `market sync` 命令及相关导入
- `src/market_data/__init__.py` 中的相关导出
- `config.data.market_data_cache_dir` 配置项

---

## 5. 实现顺序

1. **S7-000 主修复**（优先级 P0）
   - 修改 `cli/backtest.py`
   - 添加 `StrategyRepoAdapter`
   - 测试 `backtest run` 命令

2. **数据模型**（优先级 P1）
   - 创建 `OHLCVBar` model + migration
   - 扩展 `StockInfo` model（新增 listing_date）
   - 创建 `Indicator` model

3. **OHLCVService**（优先级 P1）
   - 核心抓取逻辑
   - upsert 逻辑

4. **CLI 命令**（优先级 P2）
   - `cli/ohlcv.py`

5. **Task Handler**（优先级 P2）
   - `ohlcv_crawl_task.py`
   - 注册到 `process_tasks.py`

---

## 6. 验收标准

### S7-000 主修复
- `backtest run --trader trader_a --from 2026-04-01 --to 2026-04-10` 能正常执行
- 策略版本能从数据库加载（不再是 None）

### ohlcv_crawl
- `python -m cli.main ohlcv crawl --mode incremental` 能抓取当日数据
- 数据正确写入 `ohlcv_bars` 表
- Task Handler 能从 `pending_tasks.jsonl` 触发
