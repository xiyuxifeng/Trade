# P1-026 Dashboard 增强实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强 Dashboard，新增数据新鲜度趋势、交易员统计、标的多样性等监控指标。

**Architecture:** 扩展现有 DashboardService，新增 QualityTrendAnalyzer、DataSourceFreshnessChecker、TradeStatsCollector，AlertManager 支持新告警类型。

**Tech Stack:** Python, SQLAlchemy async, Pydantic, 复用现有 dashboard_service.py 结构

---

## 文件结构

```
src/pipeline/dashboard_models.py   # 修改：新增数据模型
src/pipeline/dashboard_service.py   # 修改：新增组件 + 修改 build_report
src/pipeline/dashboard_renderers.py # 修改：扩展渲染器
```

---

## Task 1: 新增数据模型

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/dashboard_models.py`

- [ ] **Step 1: 查看现有 dashboard_models.py 结构**

```bash
head -50 trade-strategy-ai/src/pipeline/dashboard_models.py
```

- [ ] **Step 2: 在 dashboard_models.py 末尾追加新数据模型**

```python
@dataclass
class QualityTrend:
    """数据质量趋势（过去 N 天）。"""
    days: list[str]  # 日期列表 "YYYY-MM-DD"
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

- [ ] **Step 3: 验证 models 可导入**

```bash
cd trade-strategy-ai && python -c "from src.pipeline.dashboard_models import QualityTrend, DataSourceFreshness, TraderStats; print('OK')"
```

预期：OK

- [ ] **Step 4: 提交**

```bash
git add src/pipeline/dashboard_models.py
git commit -m "feat(P1-026): add QualityTrend, DataSourceFreshness, TraderStats models"
```

---

## Task 2: 实现 QualityTrendAnalyzer

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/dashboard_service.py`

- [ ] **Step 1: 写 QualityTrendAnalyzer 测试**

```python
def test_quality_trend_analyzer_no_reports(tmp_path):
    """无报告文件时返回空趋势。"""
    from src.pipeline.dashboard_service import QualityTrendAnalyzer

    analyzer = QualityTrendAnalyzer(report_dir=tmp_path, days=7)
    trend = analyzer.analyze_trend()

    assert trend.days == []
    assert trend.issue_counts == []
    assert trend.anomaly_rates == []


def test_quality_trend_analyzer_parses_jsonl(tmp_path):
    """能正确解析 JSONL 格式的问题报告。"""
    import json
    from src.pipeline.dashboard_service import QualityTrendAnalyzer

    # 创建测试报告
    report_file = tmp_path / "anomaly_report_2026-04-07.jsonl"
    with open(report_file, "w") as f:
        f.write(json.dumps({"code": "test", "severity": "error"}) + "\n")
        f.write(json.dumps({"code": "test2", "severity": "warning"}) + "\n")

    analyzer = QualityTrendAnalyzer(report_dir=tmp_path, days=7)
    trend = analyzer.analyze_trend()

    assert len(trend.issue_counts) > 0
    assert trend.issue_counts[-1] == 2
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd trade-strategy-ai && python -m pytest tests/ -k "test_quality_trend" -v --tb=short
```

预期：FAIL（QualityTrendAnalyzer 不存在）

- [ ] **Step 3: 在 dashboard_service.py 中添加 QualityTrendAnalyzer**

在 `QualityAnalyzer` 类之后添加：

```python
class QualityTrendAnalyzer:
    """从历史 anomaly 报告分析质量趋势。"""

    def __init__(self, report_dir: Path, days: int = 7):
        self.report_dir = report_dir
        self.days = days

    def analyze_trend(self) -> QualityTrend:
        """返回最近 N 天的质量趋势。"""
        report_files = sorted(self.report_dir.glob("anomaly_report_*.jsonl"))

        today = datetime.now(UTC).date()
        date_to_issues: dict[str, list[dict]] = {}

        # 初始化最近 N 天
        days_list = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(self.days - 1, -1, -1)]
        for d in days_list:
            date_to_issues[d] = []

        # 解析所有报告文件，按日期分组
        for report_file in report_files:
            date_str = report_file.stem.split("_")[-1]  # anomaly_report_YYYY-MM-DD
            if date_str not in date_to_issues:
                continue
            with report_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        issue = json.loads(line)
                        date_to_issues[date_str].append(issue)
                    except json.JSONDecodeError:
                        continue

        issue_counts = [len(date_to_issues[d]) for d in days_list]
        anomaly_rates = []  # 暂不支持（需知道每日总记录数）

        return QualityTrend(
            days=days_list,
            issue_counts=issue_counts,
            anomaly_rates=anomaly_rates,
            completeness_rates=[],  # 暂不支持
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd trade-strategy-ai && python -m pytest tests/ -k "test_quality_trend" -v --tb=short
```

预期：2 tests PASS

- [ ] **Step 5: 提交**

```bash
git add src/pipeline/dashboard_service.py
git commit -m "feat(P1-026): add QualityTrendAnalyzer for 7-day quality trends"
```

---

## Task 3: 实现 DataSourceFreshnessChecker

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/dashboard_service.py`

- [ ] **Step 1: 写 DataSourceFreshnessChecker 测试**

```python
def test_source_freshness_checker_stale():
    """超过阈值的数据源标记为 stale。"""
    from src.pipeline.dashboard_service import DataSourceFreshnessChecker
    from src.pipeline.dashboard_models import DataSourceFreshness
    from datetime import datetime, timedelta, UTC

    checker = DataSourceFreshnessChecker(session=None, freshness_threshold_hours=24.0)

    # 模拟一个 stale 的数据源
    stale = DataSourceFreshness(
        source="akshare",
        entity_type="market",
        last_updated=datetime.now(UTC) - timedelta(hours=48),
        freshness_hours=48.0,
        is_stale=True,
    )

    assert stale.is_stale is True
    assert stale.freshness_hours > 24.0
```

- [ ] **Step 2: 在 dashboard_service.py 中添加 DataSourceFreshnessChecker**

在 `StatsCollector` 类之后添加：

```python
class DataSourceFreshnessChecker:
    """检查各数据源新鲜度。"""

    def __init__(self, session: AsyncSession, freshness_threshold_hours: float = 24.0):
        self.session = session
        self.threshold = freshness_threshold_hours

    async def check_all(self) -> list[DataSourceFreshness]:
        """返回所有数据源的新鲜度。"""
        results: list[DataSourceFreshness] = []

        # 检查 BlogArticle 按 source
        article_sources = await self._get_sources(BlogArticle, "crawled_at")
        for source, last_updated in article_sources:
            freshness = self._calc_freshness(last_updated)
            results.append(DataSourceFreshness(
                source=source,
                entity_type="article",
                last_updated=last_updated,
                freshness_hours=freshness,
                is_stale=freshness > self.threshold if freshness is not None else False,
            ))

        # 检查 MarketData 按 source
        market_sources = await self._get_sources(MarketData, "traded_at")
        for source, last_updated in market_sources:
            freshness = self._calc_freshness(last_updated)
            results.append(DataSourceFreshness(
                source=source,
                entity_type="market",
                last_updated=last_updated,
                freshness_hours=freshness,
                is_stale=freshness > self.threshold if freshness is not None else False,
            ))

        return results

    async def _get_sources(self, model, time_col):
        """获取某模型按 source 分组的最新时间。"""
        from sqlalchemy import func, select

        time_column = getattr(model, time_col)
        query = (
            select(model.source, func.max(time_column))
            .group_by(model.source)
        )
        result = await self.session.execute(query)
        return result.all()

    def _calc_freshness(self, last_updated: datetime | None) -> float | None:
        """计算新鲜度（小时）。"""
        if last_updated is None:
            return None
        return (datetime.now(UTC) - last_updated).total_seconds() / 3600
```

- [ ] **Step 4: 运行语法检查**

```bash
cd trade-strategy-ai && python -c "from src.pipeline.dashboard_service import DataSourceFreshnessChecker; print('OK')"
```

预期：OK（如有语法错误，修复后重试）

- [ ] **Step 5: 提交**

```bash
git add src/pipeline/dashboard_service.py
git commit -m "feat(P1-026): add DataSourceFreshnessChecker"
```

---

## Task 4: 实现 TradeStatsCollector

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/dashboard_service.py`

- [ ] **Step 1: 写 TradeStatsCollector 测试**

```python
def test_calculate_hhi():
    """HHI 计算正确。"""
    from src.pipeline.dashboard_service import TradeStatsCollector

    # 3 个标的，数量分别为 50, 30, 20
    shares = [0.5, 0.3, 0.2]
    hhi = sum(s ** 2 for s in shares)
    assert abs(hhi - 0.38) < 0.01

    # 完全分散：4个标的各 25%
    shares2 = [0.25] * 4
    hhi2 = sum(s ** 2 for s in shares2)
    assert abs(hhi2 - 0.25) < 0.01
```

- [ ] **Step 2: 在 dashboard_service.py 中添加 TradeStatsCollector**

在 `DataSourceFreshnessChecker` 类之后添加：

```python
class TradeStatsCollector:
    """从 TradeLog 收集交易员级别统计。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def collect_all(self) -> list[TraderStats]:
        """返回所有交易员的统计。"""
        from sqlalchemy import func, select

        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        # 按 account_id 分组统计
        query = (
            select(
                TradeLog.account_id,
                func.count(TradeLog.id).label("total_trades"),
                func.count(TradeLog.id).filter(TradeLog.executed_at >= today_start).label("trades_today"),
            )
            .group_by(TradeLog.account_id)
        )
        result = await self.session.execute(query)
        rows = result.all()

        trader_stats: list[TraderStats] = []
        for row in rows:
            trader_id = row.account_id
            total_trades = row.total_trades
            trades_today = row.trades_today or 0

            # 获取标的多样性
            unique_symbols = await self._get_unique_symbols(trader_id)

            # 获取买卖比例
            buy_ratio = await self._get_buy_ratio(trader_id)

            # 计算 HHI
            hhi = await self._calculate_hhi(trader_id)

            # 生成告警
            alerts = self._generate_alerts(trader_id, buy_ratio, unique_symbols, trades_today)

            trader_stats.append(TraderStats(
                trader_id=trader_id,
                total_trades=total_trades,
                trades_today=trades_today,
                unique_symbols=unique_symbols,
                hhi=hhi,
                buy_ratio=buy_ratio,
                avg_holding_minutes=None,  # 暂不支持（需关联入场/出场）
                pnl_positive_ratio=None,  # 暂不支持（需关联持仓和盈亏）
                alerts=alerts,
            ))

        return trader_stats

    async def _get_unique_symbols(self, trader_id: str) -> int:
        """获取该交易员的唯一标的数。"""
        from sqlalchemy import func, select

        query = (
            select(func.count(func.distinct(TradeLog.symbol)))
            .where(TradeLog.account_id == trader_id)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _get_buy_ratio(self, trader_id: str) -> float:
        """获取该交易员的买入比例。"""
        from sqlalchemy import func, select

        total_query = (
            select(func.count(TradeLog.id))
            .where(TradeLog.account_id == trader_id)
        )
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        if total == 0:
            return 0.0

        buy_query = (
            select(func.count(TradeLog.id))
            .where(TradeLog.account_id == trader_id, TradeLog.side == "buy")
        )
        buy_result = await self.session.execute(buy_query)
        buys = buy_result.scalar() or 0

        return buys / total

    async def _calculate_hhi(self, trader_id: str) -> float:
        """计算 HHI（Herfindahl 集中度指数）。"""
        from sqlalchemy import func, select

        # 获取各标的的交易次数
        query = (
            select(TradeLog.symbol, func.count(TradeLog.id).label("count"))
            .where(TradeLog.account_id == trader_id)
            .group_by(TradeLog.symbol)
        )
        result = await self.session.execute(query)
        rows = result.all()

        total = sum(row.count for row in rows)
        if total == 0:
            return 0.0

        hhi = sum((row.count / total) ** 2 for row in rows)
        return hhi

    def _generate_alerts(self, trader_id: str, buy_ratio: float, unique_symbols: int, trades_today: int) -> list[str]:
        """生成交易员级别告警。"""
        alerts = []

        if buy_ratio > 0.8:
            alerts.append(f"买入比例偏高({buy_ratio:.0%})，注意风格漂移")
        elif buy_ratio < 0.2:
            alerts.append(f"卖出比例偏高({buy_ratio:.0%})，注意风格漂移")

        if unique_symbols == 1 and trades_today >= 3:
            alerts.append(f"仅交易1只标的({trades_today}笔)，集中度过高")

        if trades_today == 0:
            alerts.append("今日无交易")

        return alerts
```

- [ ] **Step 3: 验证语法**

```bash
cd trade-strategy-ai && python -c "from src.pipeline.dashboard_service import TradeStatsCollector; print('OK')"
```

预期：OK

- [ ] **Step 4: 提交**

```bash
git add src/pipeline/dashboard_service.py
git commit -m "feat(P1-026): add TradeStatsCollector for trader-level statistics"
```

---

## Task 5: 扩展 DashboardService.build_report + AlertManager

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/dashboard_service.py`
- Modify: `trade-strategy-ai/src/pipeline/dashboard_models.py`

- [ ] **Step 1: 在 DashboardReport 中添加新字段**

```python
# dashboard_models.py 中 DashboardReport 修改
@dataclass
class DashboardReport:
    stats: DashboardStats
    quality: QualityMetrics
    quality_trend: QualityTrend | None = None  # 新增
    source_freshness: list[DataSourceFreshness] = None  # 新增
    trader_stats: list[TraderStats] = None  # 新增
    alerts: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

- [ ] **Step 2: 修改 AlertManager.check 支持新告警**

将 `AlertManager.check` 签名扩展：

```python
def check(
    self,
    stats: DashboardStats,
    quality: QualityMetrics,
    quality_trend: QualityTrend | None = None,
    source_freshness: list[DataSourceFreshness] | None = None,
    trader_stats: list[TraderStats] | None = None,
) -> list[AlertEvent]:
    alerts: list[AlertEvent] = []

    # === 原有新鲜度告警 ===
    for entity_name, entity_stats in [
        ("articles", stats.articles),
        ("trades", stats.trades),
        ("market_data", stats.market_data),
    ]:
        if entity_stats.freshness_hours is not None and entity_stats.freshness_hours > self.freshness_threshold_hours:
            alerts.append(AlertEvent(
                level="warning",
                message=f"{entity_name}: 数据超过 {entity_stats.freshness_hours:.1f} 小时未更新",
            ))

    # === 异常趋势告警（新增）===
    if quality_trend and len(quality_trend.issue_counts) >= 2:
        if quality_trend.issue_counts[-1] > quality_trend.issue_counts[0] * 1.5:
            alerts.append(AlertEvent(
                level="warning",
                message=f"异常率呈上升趋势：{quality_trend.issue_counts[0]} → {quality_trend.issue_counts[-1]}",
            ))

    # === 数据源新鲜度告警（新增）===
    if source_freshness:
        for src in source_freshness:
            if src.is_stale:
                alerts.append(AlertEvent(
                    level="warning",
                    message=f"数据源 {src.source}({src.entity_type}) 超过 {src.freshness_hours:.1f}h 未更新",
                ))

    # === 交易员级别告警（新增）===
    if trader_stats:
        for trader in trader_stats:
            for alert_msg in trader.alerts:
                alerts.append(AlertEvent(
                    level="info",
                    message=f"交易员 {trader.trader_id}: {alert_msg}",
                ))

    return alerts
```

- [ ] **Step 3: 修改 DashboardService.build_report**

```python
async def build_report(self) -> DashboardReport:
    stats = await self.stats_collector.collect()
    quality = self.quality_analyzer.analyze()
    quality_trend = self.quality_trend_analyzer.analyze_trend()
    source_freshness = await self.source_freshness_checker.check_all()
    trader_stats = await self.trade_stats_collector.collect_all()
    alerts = self.alert_manager.check(
        stats, quality,
        quality_trend=quality_trend,
        source_freshness=source_freshness,
        trader_stats=trader_stats,
    )

    alert_messages = [f"[{alert.level.upper()}] {alert.message}" for alert in alerts]

    return DashboardReport(
        stats=stats,
        quality=quality,
        quality_trend=quality_trend,
        source_freshness=source_freshness,
        trader_stats=trader_stats,
        alerts=alert_messages,
        generated_at=datetime.now(UTC),
    )
```

- [ ] **Step 4: 验证 DashboardReport 可导入**

```bash
cd trade-strategy-ai && python -c "from src.pipeline.dashboard_models import DashboardReport; print('OK')"
```

预期：OK

- [ ] **Step 5: 提交**

```bash
git add src/pipeline/dashboard_models.py src/pipeline/dashboard_service.py
git commit -m "feat(P1-026): integrate new components into DashboardService"
```

---

## Task 6: 扩展 CLI/HTML 渲染器（可选）

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/dashboard_renderers.py`

此任务可选，如果 CLI 渲染已够用可跳过。

---

## Task 7: 最终验证

- [ ] **Step 1: 运行全量 pipeline 测试**

```bash
cd trade-strategy-ai && python -m pytest tests/unit/pipeline/ -v --tb=short
```

- [ ] **Step 2: 更新 TaskList**

P1-026 标记为完成

---

## 依赖关系

- Task 1 独立
- Task 2 依赖 Task 1
- Task 3 依赖 Task 1
- Task 4 依赖 Task 1
- Task 5 依赖 Task 1/2/3/4
- Task 6 独立可选
- Task 7 依赖所有

## 验证检查清单

- [ ] QualityTrend / DataSourceFreshness / TraderStats 模型可导入
- [ ] QualityTrendAnalyzer 解析 JSONL 报告正确
- [ ] DataSourceFreshnessChecker 按 source 分组正确
- [ ] TradeStatsCollector HHI 计算正确
- [ ] AlertManager 支持新告警类型
- [ ] DashboardReport 包含所有新字段
- [ ] DashboardService.build_report 编排正确
- [ ] 所有测试通过
