# P1-026 数据监控 Dashboard 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现数据监控 Dashboard，支持 CLI 巡检 + 静态 HTML 输出，持续跟踪数据新鲜度和质量指标。

**Architecture:** 核心逻辑封装为 `DashboardService`，渲染层分离（`CLIRenderer` / `HTMLRenderer`），数据来自 JSONL 报告 + PostgreSQL 查询。

**Tech Stack:** Python dataclass, Jinja2, Rich（可选）, SQLAlchemy, Pydantic

---

## 文件结构

```
src/pipeline/
  ├── dashboard_models.py      # 数据模型（DashboardStats, QualityMetrics, EntityStats）
  ├── dashboard_service.py      # 核心服务（StatsCollector, QualityAnalyzer, DashboardService）
  ├── dashboard_renderers.py    # 渲染器（CLIRenderer, HTMLRenderer）
  ├── dashboard.py              # CLI 入口

src/reporting/templates/
  └── dashboard.html           # Dashboard HTML 模板

tests/unit/pipeline/
  └── test_dashboard.py        # 单元测试

config/app.yaml                # 新增 dashboard 配置节
docs/使用说明.md                # 更新使用说明
```

---

## Task 1: dashboard_models.py — 数据模型

**Files:**
- Create: `trade-strategy-ai/src/pipeline/dashboard_models.py`

- [ ] **Step 1: 创建 dashboard_models.py**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class EntityStats:
    """单个数据类型的统计信息"""
    total: int = 0
    today_new: int = 0
    last_crawled_at: datetime | None = None
    freshness_hours: float | None = None  # 距离现在多少小时


@dataclass(slots=True)
class DashboardStats:
    """Dashboard 统计汇总"""
    articles: EntityStats = field(default_factory=EntityStats)
    trades: EntityStats = field(default_factory=EntityStats)
    market_data: EntityStats = field(default_factory=EntityStats)
    generated_at: datetime | None = None


@dataclass(slots=True)
class QualityMetrics:
    """数据质量指标"""
    total_issues: int = 0
    by_severity: dict[str, int] = field(default_factory=dict)  # error/warning/info count
    by_code: dict[str, int] = field(default_factory=dict)     # 各 issue code 数量
    article_dup_count: int = 0
    article_missing_count: int = 0
    market_missing_count: int = 0
    trade_missing_count: int = 0
    anomaly_details: list[dict[str, Any]] = field(default_factory=list)  # 前 N 条详情
    generated_at: datetime | None = None


@dataclass(slots=True)
class DashboardReport:
    """完整的 Dashboard 报告"""
    stats: DashboardStats = field(default_factory=DashboardStats)
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    alerts: list[str] = field(default_factory=list)
    generated_at: datetime | None = None
```

- [ ] **Step 2: 提交**

```bash
cd /Users/wanghui/Documents/Claude/trade-strategy-ai
git add src/pipeline/dashboard_models.py
git commit -m "feat(P1-026): add dashboard data models"
```

---

## Task 2: dashboard_service.py — 核心服务

**Files:**
- Create: `trade-strategy-ai/src/pipeline/dashboard_service.py`
- Modify: `trade-strategy-ai/src/pipeline/validation.py` (import ValidationIssue)

- [ ] **Step 1: 理解现有 validation.py 的 ValidationIssue 结构**

回顾 `validation.py` 第 21-27 行，ValidationIssue 包含：
- `code: str`
- `severity: ValidationSeverity` (INFO/WARNING/ERROR)
- `message: str`
- `field_name: str | None`
- `context: dict[str, Any]`

- [ ] **Step 2: 创建 StatsCollector 类**

```python
from __future__ import annotations

from datetime import datetime, timedelta, UTC
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.blog_article import BlogArticle
from src.models.market_data import MarketData
from src.models.trade_log import TradeLog
from .dashboard_models import DashboardStats, EntityStats


class StatsCollector:
    """从 PostgreSQL 收集基础统计信息"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def collect(self) -> DashboardStats:
        """收集所有数据类型的统计"""
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        stats = DashboardStats(
            articles=await self._collect_entity_stats(BlogArticle, today_start),
            trades=await self._collect_entity_stats(TradeLog, today_start),
            market_data=await self._collect_entity_stats(MarketData, today_start),
            generated_at=datetime.now(UTC),
        )
        return stats

    async def _collect_entity_stats(
        self, model: type[BlogArticle | TradeLog | MarketData], today_start: datetime
    ) -> EntityStats:
        # 总数
        total_result = await self.session.execute(select(func.count(model.id)))
        total = total_result.scalar() or 0

        # 今日新增
        crawled_col = getattr(model, "crawled_at", None) or getattr(model, "executed_at", None) or getattr(model, "traded_at", None)
        if crawled_col is None:
            return EntityStats(total=total, today_new=0)

        today_query = select(func.count(model.id)).where(crawled_col >= today_start)
        today_result = await self.session.execute(today_query)
        today_new = today_result.scalar() or 0

        # 最后入库时间
        last_query = select(func.max(crawled_col))
        last_result = await self.session.execute(last_query)
        last_crawled_at = last_result.scalar()

        # 计算新鲜度
        freshness_hours = None
        if last_crawled_at:
            freshness_hours = (datetime.now(UTC) - last_crawled_at).total_seconds() / 3600

        return EntityStats(
            total=total,
            today_new=today_new,
            last_crawled_at=last_crawled_at,
            freshness_hours=freshness_hours,
        )
```

- [ ] **Step 3: 创建 QualityAnalyzer 类**

```python
import json
from datetime import datetime, UTC
from pathlib import Path

from .dashboard_models import QualityMetrics, ValidationIssue


class QualityAnalyzer:
    """从 JSONL 报告分析数据质量"""

    def __init__(self, report_dir: Path, max_details: int = 20):
        self.report_dir = report_dir
        self.max_details = max_details

    def analyze(self) -> QualityMetrics:
        """分析最新的 anomaly 报告"""
        report_files = sorted(self.report_dir.glob("anomaly_report_*.jsonl"))
        if not report_files:
            return QualityMetrics(generated_at=datetime.now(UTC))

        latest_report = report_files[-1]
        return self._parse_report(latest_report)

    def _parse_report(self, report_path: Path) -> QualityMetrics:
        issues: list[dict] = []
        by_severity: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
        by_code: dict[str, int] = {}

        with report_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                issue = json.loads(line)
                issues.append(issue)

                severity = issue.get("severity", "info")
                if severity in by_severity:
                    by_severity[severity] += 1

                code = issue.get("code", "unknown")
                by_code[code] = by_code.get(code, 0) + 1

        # 统计各类问题
        article_dup = sum(1 for i in issues if "article.duplicate" in i.get("code", ""))
        article_missing = sum(1 for i in issues if i.get("code", "").startswith("article.field"))
        market_missing = sum(1 for i in issues if i.get("code", "").startswith("market.field"))
        trade_missing = sum(1 for i in issues if i.get("code", "").startswith("trade.field"))

        return QualityMetrics(
            total_issues=len(issues),
            by_severity=by_severity,
            by_code=by_code,
            article_dup_count=article_dup,
            article_missing_count=article_missing,
            market_missing_count=market_missing,
            trade_missing_count=trade_missing,
            anomaly_details=issues[: self.max_details],
            generated_at=datetime.now(UTC),
        )
```

- [ ] **Step 4: 创建 AlertManager 类**

```python
from dataclasses import dataclass


@dataclass
class AlertEvent:
    level: str  # info / warning / critical
    message: str


class AlertManager:
    """告警判断逻辑"""

    def __init__(
        self,
        freshness_threshold_hours: float = 24.0,
        anomaly_rate_threshold: float = 5.0,
    ):
        self.freshness_threshold_hours = freshness_threshold_hours
        self.anomaly_rate_threshold = anomaly_rate_threshold

    def check(self, stats, quality) -> list[AlertEvent]:
        alerts: list[AlertEvent] = []

        # 检查新鲜度
        for entity_name, entity_stats in [
            ("articles", stats.articles),
            ("trades", stats.trades),
            ("market_data", stats.market_data),
        ]:
            if entity_stats.freshness_hours is not None and entity_stats.freshness_hours > self.freshness_threshold_hours:
                alerts.append(
                    AlertEvent(
                        level="warning",
                        message=f"{entity_name}: 数据超过 {entity_stats.freshness_hours:.1f} 小时未更新",
                    )
                )

        # 检查异常率
        total_records = stats.articles.total + stats.trades.total + stats.market_data.total
        if total_records > 0 and quality.total_issues > 0:
            anomaly_rate = (quality.total_issues / total_records) * 100
            if anomaly_rate > self.anomaly_rate_threshold:
                alerts.append(
                    AlertEvent(
                        level="critical",
                        message=f"异常率 {anomaly_rate:.1f}% 超过阈值 {self.anomaly_rate_threshold}%",
                    )
                )

        return alerts
```

- [ ] **Step 5: 创建 DashboardService 类**

```python
from datetime import datetime, UTC
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from .dashboard_models import DashboardReport
from .dashboard_service import StatsCollector, QualityAnalyzer, AlertManager


class DashboardService:
    """Dashboard 核心服务，编排各组件"""

    def __init__(
        self,
        session: AsyncSession,
        report_dir: Path,
        freshness_threshold_hours: float = 24.0,
        anomaly_rate_threshold: float = 5.0,
        max_anomaly_details: int = 20,
    ):
        self.stats_collector = StatsCollector(session)
        self.quality_analyzer = QualityAnalyzer(report_dir, max_anomaly_details)
        self.alert_manager = AlertManager(freshness_threshold_hours, anomaly_rate_threshold)

    async def build_report(self) -> DashboardReport:
        stats = await self.stats_collector.collect()
        quality = self.quality_analyzer.analyze()
        alerts = self.alert_manager.check(stats, quality)

        return DashboardReport(
            stats=stats,
            quality=quality,
            alerts=alerts,
            generated_at=datetime.now(UTC),
        )
```

- [ ] **Step 6: 提交**

```bash
git add src/pipeline/dashboard_service.py
git commit -m "feat(P1-026): add dashboard service (StatsCollector, QualityAnalyzer, AlertManager)"
```

---

## Task 3: dashboard_renderers.py — 渲染器

**Files:**
- Create: `trade-strategy-ai/src/pipeline/dashboard_renderers.py`

- [ ] **Step 1: 创建 CLIRenderer**

```python
from rich.console import Console
from rich.table import Table

from .dashboard_models import DashboardReport


class CLIRenderer:
    """CLI 渲染器，使用 Rich 库"""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def render(self, report: DashboardReport) -> None:
        self.console.print("\n[bold cyan]数据监控 Dashboard[/bold cyan]")
        self.console.print(f"生成时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S') if report.generated_at else 'N/A'}")

        self._render_stats(report)
        self._render_quality(report)
        self._render_alerts(report)

    def _render_stats(self, report: DashboardReport) -> None:
        table = Table(title="数据统计")
        table.add_column("数据类型", style="cyan")
        table.add_column("总数", justify="right")
        table.add_column("今日新增", justify="right")
        table.add_column("最后入库", justify="right")
        table.add_column("新鲜度(小时)", justify="right")

        for name, stats in [
            ("articles", report.stats.articles),
            ("trades", report.stats.trades),
            ("market_data", report.stats.market_data),
        ]:
            last_crawled = stats.last_crawled_at.strftime("%Y-%m-%d %H:%M") if stats.last_crawled_at else "N/A"
            freshness = f"{stats.freshness_hours:.1f}" if stats.freshness_hours is not None else "N/A"
            table.add_row(
                name,
                str(stats.total),
                str(stats.today_new),
                last_crawled,
                freshness,
            )

        self.console.print(table)

    def _render_quality(self, report: DashboardReport) -> None:
        table = Table(title="数据质量")
        table.add_column("指标", style="cyan")
        table.add_column("值", justify="right")

        q = report.quality
        table.add_row("总问题数", str(q.total_issues))
        table.add_row("  - Error", str(q.by_severity.get("error", 0)))
        table.add_row("  - Warning", str(q.by_severity.get("warning", 0)))
        table.add_row("  - Info", str(q.by_severity.get("info", 0)))
        table.add_row("文章重复", str(q.article_dup_count))
        table.add_row("文章字段缺失", str(q.article_missing_count))
        table.add_row("市场数据缺失", str(q.market_missing_count))
        table.add_row("交易记录缺失", str(q.trade_missing_count))

        self.console.print(table)

    def _render_alerts(self, report: DashboardReport) -> None:
        if not report.alerts:
            self.console.print("[green]✓ 无告警[/green]")
            return

        for alert in report.alerts:
            color = "red" if alert.level == "critical" else "yellow"
            self.console.print(f"[{color}]⚠ {alert.message}[/{color}]")
```

- [ ] **Step 2: 创建 HTMLRenderer**

```python
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .dashboard_models import DashboardReport


class HTMLRenderer:
    """HTML 渲染器，使用 Jinja2"""

    def __init__(self, template_path: Path, output_path: Path):
        self.template_path = template_path
        self.output_path = output_path
        self.env = Environment(
            loader=FileSystemLoader(template_path.parent),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, report: DashboardReport) -> Path:
        template = self.env.get_template(self.template_path.name)
        html = template.render(
            report=report,
            generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M:%S") if report.generated_at else "N/A",
        )

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(html, encoding="utf-8")
        return self.output_path
```

- [ ] **Step 3: 提交**

```bash
git add src/pipeline/dashboard_renderers.py
git commit -m "feat(P1-026): add dashboard renderers (CLI, HTML)"
```

---

## Task 4: dashboard.py — CLI 入口

**Files:**
- Create: `trade-strategy-ai/src/pipeline/dashboard.py`

- [ ] **Step 1: 创建 CLI 入口**

```python
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.common.config import Settings
from src.db.session import async_session_factory
from src.pipeline.dashboard_models import DashboardReport
from src.pipeline.dashboard_service import DashboardService
from src.pipeline.dashboard_renderers import CLIRenderer, HTMLRenderer


def load_config():
    settings = Settings()
    return settings


async def build_report(settings: Settings) -> DashboardReport:
    report_dir = Path("data/processed/pipeline/anomaly")
    dashboard_cfg = getattr(settings, "dashboard", None) or {}

    freshness_threshold = dashboard_cfg.get("freshness_threshold_hours", 24.0)
    anomaly_threshold = dashboard_cfg.get("anomaly_rate_threshold", 5.0)
    max_details = dashboard_cfg.get("max_anomaly_details", 20)

    async with async_session_factory() as session:
        service = DashboardService(
            session=session,
            report_dir=report_dir,
            freshness_threshold_hours=freshness_threshold,
            anomaly_rate_threshold=anomaly_threshold,
            max_anomaly_details=max_details,
        )
        return await service.build_report()


@click.command()
@click.option("--mode", type=click.Choice(["cli", "html", "both"]), default="cli", help="输出模式")
@click.option("--output", type=click.Path(path_type=Path), default=None, help="HTML 输出路径")
@click.option("--config", type=click.Path(path_type=Path), default=None, help="配置文件路径")
def main(mode: str, output: Path | None, config: Path | None):
    """数据监控 Dashboard CLI"""
    settings = load_config()

    report: DashboardReport = asyncio.run(build_report(settings))

    if mode in ("cli", "both"):
        renderer = CLIRenderer()
        renderer.render(report)

    if mode in ("html", "both"):
        template_path = Path("src/reporting/templates/dashboard.html")
        if output is None:
            output = Path("data/processed/dashboard/dashboard.html")
        html_renderer = HTMLRenderer(template_path, output)
        result_path = html_renderer.render(report)
        click.echo(f"HTML 报告已生成: {result_path}")

    # 如果有关键告警，返回非零退出码
    critical_alerts = [a for a in report.alerts if a.level == "critical"]
    if critical_alerts:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 提交**

```bash
git add src/pipeline/dashboard.py
git commit -m "feat(P1-026): add dashboard CLI entry point"
```

---

## Task 5: dashboard.html — HTML 模板

**Files:**
- Create: `trade-strategy-ai/src/reporting/templates/dashboard.html`

- [ ] **Step 1: 创建 HTML 模板（参考 daily_report.html 风格）**

```html
<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>数据监控 Dashboard {{generated_at}}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            margin: 24px;
            color: #111;
        }
        h1 { margin: 0 0 8px 0; }
        .meta { color: #555; margin: 0 0 16px 0; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
        .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border-bottom: 1px solid #eee; padding: 8px 6px; text-align: left; }
        th { color: #333; font-weight: 600; }
        .alert-warning { background: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 8px 12px; margin: 4px 0; }
        .alert-critical { background: #fee2e2; border: 1px solid #ef4444; border-radius: 6px; padding: 8px 12px; margin: 4px 0; }
        .severity-error { color: #ef4444; font-weight: 600; }
        .severity-warning { color: #f59e0b; font-weight: 600; }
        .severity-info { color: #3b82f6; }
        .freshness-ok { color: #22c55e; }
        .freshness-warn { color: #f59e0b; }
        .freshness-error { color: #ef4444; }
    </style>
</head>
<body>
    <h1>数据监控 Dashboard</h1>
    <p class="meta">生成时间: {{ generated_at }}</p>

    {% if report.alerts %}
    <div class="grid">
        <div class="card">
            <h2>告警</h2>
            {% for alert in report.alerts %}
                {% if alert.level == 'critical' %}
                <div class="alert-critical">⚠ {{ alert.message }}</div>
                {% else %}
                <div class="alert-warning">⚠ {{ alert.message }}</div>
                {% endif %}
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <div class="grid">
        <div class="card">
            <h2>数据统计</h2>
            <table>
                <thead>
                    <tr><th>数据类型</th><th>总数</th><th>今日新增</th><th>最后入库</th><th>新鲜度</th></tr>
                </thead>
                <tbody>
                    {% for name, stats in [('articles', report.stats.articles), ('trades', report.stats.trades), ('market_data', report.stats.market_data)] %}
                    <tr>
                        <td>{{ name }}</td>
                        <td>{{ stats.total }}</td>
                        <td>{{ stats.today_new }}</td>
                        <td>{{ stats.last_crawled_at.strftime('%Y-%m-%d %H:%M') if stats.last_crawled_at else 'N/A' }}</td>
                        <td>
                            {% if stats.freshness_hours is not none %}
                                {% if stats.freshness_hours < 12 %}
                                    <span class="freshness-ok">{{ "%.1f"|format(stats.freshness_hours) }}h</span>
                                {% elif stats.freshness_hours < 24 %}
                                    <span class="freshness-warn">{{ "%.1f"|format(stats.freshness_hours) }}h</span>
                                {% else %}
                                    <span class="freshness-error">{{ "%.1f"|format(stats.freshness_hours) }}h</span>
                                {% endif %}
                            {% else %}N/A{% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>数据质量</h2>
            <table>
                <tr><td>总问题数</td><td><strong>{{ report.quality.total_issues }}</strong></td></tr>
                <tr><td class="severity-error">Error</td><td>{{ report.quality.by_severity.get('error', 0) }}</td></tr>
                <tr><td class="severity-warning">Warning</td><td>{{ report.quality.by_severity.get('warning', 0) }}</td></tr>
                <tr><td class="severity-info">Info</td><td>{{ report.quality.by_severity.get('info', 0) }}</td></tr>
                <tr><td>文章重复</td><td>{{ report.quality.article_dup_count }}</td></tr>
                <tr><td>文章字段缺失</td><td>{{ report.quality.article_missing_count }}</td></tr>
                <tr><td>市场数据缺失</td><td>{{ report.quality.market_missing_count }}</td></tr>
                <tr><td>交易记录缺失</td><td>{{ report.quality.trade_missing_count }}</td></tr>
            </table>
        </div>
    </div>

    {% if report.quality.anomaly_details %}
    <div class="card" style="margin-top: 16px;">
        <h2>异常详情 (前 {{ report.quality.anomaly_details|length }} 条)</h2>
        <table>
            <thead>
                <tr><th>Severity</th><th>Code</th><th>Message</th><th>Field</th></tr>
            </thead>
            <tbody>
                {% for detail in report.quality.anomaly_details %}
                <tr>
                    <td>
                        {% if detail.severity == 'error' %}<span class="severity-error">{{ detail.severity }}</span>
                        {% elif detail.severity == 'warning' %}<span class="severity-warning">{{ detail.severity }}</span>
                        {% else %}<span class="severity-info">{{ detail.severity }}</span>{% endif %}
                    </td>
                    <td><code>{{ detail.code }}</code></td>
                    <td>{{ detail.message }}</td>
                    <td>{{ detail.field_name or '-' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}
</body>
</html>
```

- [ ] **Step 2: 提交**

```bash
git add src/reporting/templates/dashboard.html
git commit -m "feat(P1-026): add dashboard HTML template"
```

---

## Task 6: config/app.yaml — 新增配置

**Files:**
- Modify: `trade-strategy-ai/config/app.yaml`

- [ ] **Step 1: 在文件末尾添加 dashboard 配置节**

在 `data_quality` 节之后添加：

```yaml
# 数据监控 Dashboard
dashboard:
  alerts:
    # 是否启用告警
    enabled: true
    # 数据新鲜度阈值（小时），超过则告警
    freshness_threshold_hours: 24
    # 异常率阈值（%），超过则告警
    anomaly_rate_threshold: 5.0
  # HTML 输出目录
  html_output_dir: data/processed/dashboard
  # 最大显示异常详情数
  max_anomaly_details: 20
  # 告警输出模式：cli / html / both
  alert_mode: both
```

- [ ] **Step 2: 提交**

```bash
git add config/app.yaml
git commit -m "feat(P1-026): add dashboard config to app.yaml"
```

---

## Task 7: test_dashboard.py — 单元测试

**Files:**
- Create: `trade-strategy-ai/tests/unit/pipeline/test_dashboard.py`

- [ ] **Step 1: 写 StatsCollector 测试**

```python
from __future__ import annotations

from datetime import datetime, timedelta, UTC
import pytest

from src.pipeline.dashboard_models import DashboardStats, EntityStats


def test_entity_stats_freshness_calculation():
    """EntityStats 的新鲜度小时数计算"""
    stats = EntityStats(
        total=100,
        today_new=5,
        last_crawled_at=datetime.now(UTC) - timedelta(hours=6),
        freshness_hours=6.0,
    )
    assert stats.freshness_hours == 6.0
    assert stats.total == 100
    assert stats.today_new == 5


def test_dashboard_stats_defaults():
    """DashboardStats 默认值"""
    stats = DashboardStats()
    assert stats.articles.total == 0
    assert stats.trades.total == 0
    assert stats.market_data.total == 0


def test_quality_metrics_defaults():
    """QualityMetrics 默认值"""
    from src.pipeline.dashboard_models import QualityMetrics
    m = QualityMetrics()
    assert m.total_issues == 0
    assert m.by_severity == {}
    assert m.by_code == {}
```

- [ ] **Step 2: 写 AlertManager 测试**

```python
from src.pipeline.dashboard_models import DashboardStats, EntityStats, QualityMetrics
from src.pipeline.dashboard_service import AlertManager


def test_no_alert_when_fresh():
    """数据新鲜时无告警"""
    stats = DashboardStats(
        articles=EntityStats(freshness_hours=2.0),
        trades=EntityStats(freshness_hours=1.0),
        market_data=EntityStats(freshness_hours=3.0),
    )
    quality = QualityMetrics(total_issues=0)
    am = AlertManager(freshness_threshold_hours=24.0)
    alerts = am.check(stats, quality)
    assert len(alerts) == 0


def test_alert_when_stale():
    """数据过期时触发告警"""
    stats = DashboardStats(
        articles=EntityStats(freshness_hours=30.0),
        trades=EntityStats(freshness_hours=1.0),
        market_data=EntityStats(freshness_hours=1.0),
    )
    quality = QualityMetrics(total_issues=0)
    am = AlertManager(freshness_threshold_hours=24.0)
    alerts = am.check(stats, quality)
    assert len(alerts) == 1
    assert "articles" in alerts[0].message
    assert alerts[0].level == "warning"


def test_critical_alert_when_anomaly_rate_high():
    """异常率超阈值时触发 critical 告警"""
    stats = DashboardStats(
        articles=EntityStats(total=100),
        trades=EntityStats(total=0),
        market_data=EntityStats(total=0),
    )
    quality = QualityMetrics(total_issues=10)  # 10% 异常率
    am = AlertManager(anomaly_rate_threshold=5.0)
    alerts = am.check(stats, quality)
    assert len(alerts) == 1
    assert alerts[0].level == "critical"
```

- [ ] **Step 3: 写 QualityAnalyzer 测试**

```python
import json
import tempfile
from pathlib import Path
from datetime import datetime, UTC

from src.pipeline.dashboard_models import QualityMetrics
from src.pipeline.dashboard_service import QualityAnalyzer


def test_quality_analyzer_empty_dir():
    """空目录返回零值"""
    with tempfile.TemporaryDirectory() as tmpdir:
        analyzer = QualityAnalyzer(Path(tmpdir))
        result = analyzer.analyze()
        assert result.total_issues == 0


def test_quality_analyzer_parses_report():
    """正确解析 JSONL 报告"""
    with tempfile.TemporaryDirectory() as tmpdir:
        report_dir = Path(tmpdir)
        report_file = report_dir / "anomaly_report_20260407_120000.jsonl"
        report_file.write_text(
            json.dumps({"code": "article.field.missing", "severity": "error", "message": "title missing", "field_name": "title"}) + "\n"
            + json.dumps({"code": "article.duplicate.hash", "severity": "warning", "message": "dup", "field_name": None}) + "\n",
            encoding="utf-8",
        )
        analyzer = QualityAnalyzer(report_dir, max_details=10)
        result = analyzer.analyze()
        assert result.total_issues == 2
        assert result.by_severity["error"] == 1
        assert result.by_severity["warning"] == 1
        assert result.article_missing_count == 1
        assert result.article_dup_count == 1
        assert len(result.anomaly_details) == 2
```

- [ ] **Step 4: 提交**

```bash
git add tests/unit/pipeline/test_dashboard.py
git commit -m "test(P1-026): add dashboard unit tests"
```

---

## Task 8: 使用说明.md — 更新文档

**Files:**
- Modify: `docs/使用说明.md`

- [ ] **Step 1: 找到"数据管道"或"CLI 命令"相关章节，添加 Dashboard 使用说明**

在文档中添加：

```markdown
## 数据监控 Dashboard

### 概述
数据监控 Dashboard 提供数据新鲜度和质量指标的持续监控，支持 CLI 巡检和静态 HTML 输出。

### CLI 命令

```bash
# 终端巡检（输出 Rich 表格）
python -m src.pipeline.dashboard --mode cli

# 生成静态 HTML 报告
python -m src.pipeline.dashboard --mode html

# 同时输出 CLI 和 HTML
python -m src.pipeline.dashboard --mode both
```

### 配置项

`config/app.yaml` 中的 `dashboard` 配置节：

```yaml
dashboard:
  alerts:
    enabled: true
    freshness_threshold_hours: 24   # 数据新鲜度阈值（小时）
    anomaly_rate_threshold: 5.0     # 异常率阈值（%）
  html_output_dir: data/processed/dashboard
  max_anomaly_details: 20
  alert_mode: both
```

### 输出说明

- **CLI 输出**：统计摘要表（记录数/新增数/新鲜度）+ 质量指标表（异常分类统计）+ 告警列表
- **HTML 报告**：包含统计概览、质量详情、异常明细三部分，保存在 `data/processed/dashboard/dashboard.html`
- **告警退出码**：有关键告警时 CLI 返回非零退出码，可用于 cron 告警
```

- [ ] **Step 2: 提交**

```bash
git add docs/使用说明.md
git commit -m "docs(P1-026): update usage docs with dashboard instructions"
```

---

## 自检清单

1. **Spec 覆盖检查**：所有设计方案中的功能都有对应 Task 实现
2. **Placeholder 扫描**：无 TBD/TODO/模糊描述
3. **类型一致性**：各 Task 间数据模型名称一致（DashboardStats, EntityStats, QualityMetrics）
4. **无重复实现**：每个类（StatsCollector, QualityAnalyzer, AlertManager, CLIRenderer, HTMLRenderer）职责唯一
