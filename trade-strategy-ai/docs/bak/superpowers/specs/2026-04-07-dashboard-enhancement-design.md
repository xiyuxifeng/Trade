# P1-026 Dashboard 增强设计

## 目标

增强数据监控 Dashboard，新增：
1. **C：数据新鲜度 + 质量趋势** — 完整性、异常趋势、数据源级别告警
2. **B：交易数据统计** — 交易员频次、标的多样性、买卖方向比例

---

## 设计决策

| 决策项 | 选择 |
|--------|------|
| 数据新鲜度+质量趋势 | C：完整性缺失率 + 7天趋势 + 数据源级别告警 |
| 交易数据统计 | B：交易员频次 + HHI多样性 + 买卖比例 + 盈亏比 |
| 改动范围 | 扩展现有 StatsCollector / 新增 TradeStatsCollector / AlertManager 扩展 |

---

## 模块结构

```
src/pipeline/dashboard_service.py   # 修改：扩展 StatsCollector、AlertManager
src/pipeline/dashboard_models.py    # 修改：新增 TraderStats 等数据模型
src/pipeline/dashboard.py          # 修改：CLI 增加交易统计输出
src/pipeline/dashboard_renderers.py # 修改：CLI/HTML 渲染器支持新指标
```

---

## 新增数据模型

### DashboardModels（dashboard_models.py 新增）

```python
@dataclass
class QualityTrend:
    """数据质量趋势（过去 N 天）。"""
    days: list[str]  # 日期列表
    issue_counts: list[int]  # 每日问题数
    anomaly_rates: list[float]  # 每日异常率（%）
    completeness_rates: list[float]  # 每日完整性（%）


@dataclass
class DataSourceFreshness:
    """各数据源的新鲜度。"""
    source: str
    entity_type: str  # article / trade / market
    last_updated: datetime | None
    freshness_hours: float | None
    is_stale: bool  # 是否超过阈值


@dataclass
class TraderStats:
    """交易员级别统计。"""
    trader_id: str
    total_trades: int
    trades_today: int
    unique_symbols: int  # 标的多样性
    hhi: float  # Herfindahl 集中度指数（0=完全分散，1=完全集中）
    buy_ratio: float  # 买入比例 0.0~1.0
    avg_holding_minutes: float | None
    pnl_positive_ratio: float | None  # 盈利交易占比
    alerts: list[str]  # 该交易员的告警
```

---

## 新增组件

### 1. QualityTrendAnalyzer（新增）

分析过去 7 天异常趋势，从 JSONL 报告文件读取。

```python
class QualityTrendAnalyzer:
    """从历史 anomaly 报告分析质量趋势。"""

    def __init__(self, report_dir: Path, days: int = 7):
        self.report_dir = report_dir
        self.days = days

    def analyze_trend(self) -> QualityTrend:
        """返回最近 N 天的质量趋势。"""
        # 遍历 report_dir 下所有 anomaly_report_*.jsonl
        # 按日期分组统计 issue 数量
        # 计算每日异常率 = issues / total_records
```

### 2. DataSourceFreshnessChecker（新增）

检查每个 source 的新鲜度。

```python
class DataSourceFreshnessChecker:
    """检查各数据源新鲜度。"""

    def __init__(self, session: AsyncSession, freshness_threshold_hours: float = 24.0):
        self.session = session
        self.threshold = freshness_threshold_hours

    async def check_all(self) -> list[DataSourceFreshness]:
        """返回所有数据源的新鲜度。"""
        # 查询 BlogArticle / TradeLog / MarketData
        # 按 source 分组，统计 last_crawled_at / executed_at / traded_at
```

### 3. TradeStatsCollector（新增）

收集交易员级别统计。

```python
class TradeStatsCollector:
    """从 TradeLog 收集交易员级别统计。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def collect_all(self) -> list[TraderStats]:
        """返回所有交易员的统计。"""
        # 按 account_id 分组
        # 统计：总交易数、今日交易数、unique_symbols
        # 计算：HHI = sum((share_i)^2)
        # 计算：buy_ratio = buys / total
        # 关联 position_side / rationale（如有）
```

---

## AlertManager 扩展

```python
class AlertManager:
    """增强后的告警判断逻辑。"""

    def check(self, stats, quality, trends, trader_stats, source_freshness) -> list[AlertEvent]:
        alerts = []

        # 1. 新鲜度告警（原有）
        for src in source_freshness:
            if src.is_stale:
                alerts.append(AlertEvent(level="warning", message=f"数据源 {src.source} 超过 {self.freshness_threshold_hours}h 未更新"))

        # 2. 异常趋势告警（新增）
        if trends.anomaly_rates and trends.anomaly_rates[-1] > trends.anomaly_rates[0] * 1.5:
            alerts.append(AlertEvent(level="warning", message="异常率呈上升趋势"))

        # 3. 交易员级别告警（新增）
        for trader in trader_stats:
            for alert in trader.alerts:
                alerts.append(AlertEvent(level="info", message=f"交易员 {trader.trader_id}: {alert}"))

        return alerts
```

---

## DashboardService 编排

```python
class DashboardService:
    async def build_report(self) -> DashboardReport:
        stats = await self.stats_collector.collect()
        quality = self.quality_analyzer.analyze()
        trends = self.quality_trend_analyzer.analyze_trend()
        source_freshness = await self.source_freshness.check_all()
        trader_stats = await self.trade_stats_collector.collect_all()
        alerts = self.alert_manager.check(stats, quality, trends, trader_stats, source_freshness)

        return DashboardReport(
            stats=stats,
            quality=quality,
            quality_trend=trends,  # 新增
            source_freshness=source_freshness,  # 新增
            trader_stats=trader_stats,  # 新增
            alerts=alert_messages,
        )
```

---

## CLI/HTML 输出

CLI 渲染器新增板块：

```
=== 数据源新鲜度 ===
source=akshare | entity=market | last_updated=2026-04-07 09:30 | freshness=2.5h | OK

=== 异常趋势（7天）===
2026-04-01: ████ 12 issues (1.2%)
2026-04-02: ██████ 18 issues (1.8%) ↑

=== 交易员统计 ===
acc1: 5笔/日 | 3标 | HHI=0.45 | 买入=60% | 盈利=70%
  ⚠ 买入比例偏高，注意风格漂移
```

---

## 产出文件

| 文件 | 改动 |
|------|------|
| `src/pipeline/dashboard_models.py` | 新增 QualityTrend, DataSourceFreshness, TraderStats |
| `src/pipeline/dashboard_service.py` | 新增 QualityTrendAnalyzer, DataSourceFreshnessChecker, TradeStatsCollector |
| `src/pipeline/dashboard_renderers.py` | 扩展 CLI/HTML 渲染新指标 |
| `src/pipeline/dashboard.py` | CLI 可选开启交易统计（需 DB） |

---

## 依赖关系

- QualityTrendAnalyzer：依赖 `data/processed/pipeline/anomaly/` JSONL 文件
- DataSourceFreshnessChecker：依赖 PostgreSQL（已有）
- TradeStatsCollector：依赖 PostgreSQL（已有）
- 所有改动均为可选增强，现有功能不受影响
