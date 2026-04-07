from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
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
            # alert 格式为 "[LEVEL] message"
            if "[CRITICAL]" in alert:
                color = "red"
            elif "[WARNING]" in alert:
                color = "yellow"
            else:
                color = "blue"
            self.console.print(f"[{color}]{alert}[/{color}]")


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
