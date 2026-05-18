"""NTL-S6-005: 回测报告模块

职责：
- 把 BacktestResult 渲染为可读报告（Markdown / JSON）
- 把 RuleValidationResult 列表渲染为规则验真报告
"""

from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any

from src.backtest.schemas import BacktestResult, RuleValidationResult


def render_backtest_markdown(result: BacktestResult) -> str:
    """把回测结果渲染为 Markdown 摘要报告。

    Args:
        result: BacktestResult

    Returns:
        Markdown 格式报告字符串
    """
    lines = [
        "# Backtest Report",
        "",
        f"**Trader:** {result.request_trader_id}",
        f"**Date Range:** {result.request_date_from} ~ {result.request_date_to}",
        f"**Benchmark:** {result.benchmark_symbol or 'n/a'}",
        "",
    ]

    if result.summary:
        s = result.summary
        lines.append("## Summary")
        lines.append(f"- 样本覆盖天数: {s.total_days}")
        lines.append(f"- 总交易笔数: {s.total_trades}")
        lines.append(f"- 有效交易: {s.valid_trades}")
        lines.append(f"- 跳过笔数: {s.skipped_trades}")
        if s.win_rate is not None:
            lines.append(f"- 胜率: {s.win_rate:.2%}")
        if s.avg_return_pct is not None:
            lines.append(f"- 平均收益率: {s.avg_return_pct:.2%}")
        lines.append("")

    if result.regime_version or result.source_feature_version:
        lines.append("## Regime Version")
        lines.append(
            "- regime_version={regime_version} | source_feature_version={source_feature_version}".format(
                regime_version=result.regime_version or "n/a",
                source_feature_version=result.source_feature_version or "n/a",
            )
        )
        lines.append("")

    if result.records:
        lines.append("## Trade Records")
        for rec in result.records:
            status_icon = {"open": "🔓", "closed": "✅", "skipped": "⏭", "invalid": "❌"}.get(
                rec.status, "?"
            )
            return_str = f"{rec.return_pct:.2%}" if rec.return_pct is not None else "None"
            lines.append(
                f"- {status_icon} {rec.trade_date} | {rec.symbol} | "
                f"status={rec.status} | return={return_str} "
                f"| skip_reason={rec.skip_reason}"
            )
        lines.append("")

    if result.regime_metrics:
        lines.append("## Regime Breakdown")
        for metric in result.regime_metrics:
            lines.append(
                "- {label} | sample={sample} | win_rate={win_rate} | avg_return={avg_return} | max_drawdown={max_drawdown} | confidence={confidence}".format(
                    label=metric.regime_label,
                    sample=metric.sample_count,
                    win_rate="n/a" if metric.win_rate is None else f"{metric.win_rate:.2%}",
                    avg_return="n/a" if metric.avg_return is None else f"{metric.avg_return:.2%}",
                    max_drawdown="n/a" if metric.max_drawdown is None else f"{metric.max_drawdown:.2%}",
                    confidence=f"{metric.confidence:.2f}",
                )
            )
        lines.append("")

    if result.rule_regime_metrics:
        lines.append("## Rule Regime Breakdown")
        for rule_id, metrics in sorted(result.rule_regime_metrics.items()):
            lines.append(f"### {rule_id}")
            for metric in metrics:
                lines.append(
                    "- {label} | sample={sample} | win_rate={win_rate} | avg_return={avg_return} | max_drawdown={max_drawdown} | confidence={confidence}".format(
                        label=metric.regime_label,
                        sample=metric.sample_count,
                        win_rate="n/a" if metric.win_rate is None else f"{metric.win_rate:.2%}",
                        avg_return="n/a" if metric.avg_return is None else f"{metric.avg_return:.2%}",
                        max_drawdown="n/a" if metric.max_drawdown is None else f"{metric.max_drawdown:.2%}",
                        confidence=f"{metric.confidence:.2f}",
                    )
                )
            lines.append("")

    return "\n".join(lines)


def render_backtest_json(result: BacktestResult) -> str:
    """把回测结果渲染为 JSON 字符串。

    Args:
        result: BacktestResult

    Returns:
        JSON 格式字符串
    """
    return json.dumps(
        {
            "request_trader_id": result.request_trader_id,
            "request_date_from": str(result.request_date_from),
            "request_date_to": str(result.request_date_to),
            "trader_id": result.request_trader_id,
            "date_from": str(result.request_date_from),
            "date_to": str(result.request_date_to),
            "benchmark_symbol": result.benchmark_symbol,
            "regime_version": result.regime_version,
            "source_feature_version": result.source_feature_version,
            "result_version": result.result_version,
            "records": [
                {
                    "trade_date": str(r.trade_date),
                    "trader_id": r.trader_id,
                    "strategy_version_id": r.strategy_version_id,
                    "symbol": r.symbol,
                    "status": r.status,
                    "entry_price": r.entry_price,
                    "exit_price": r.exit_price,
                    "return_pct": r.return_pct,
                    "mfe": r.mfe,
                    "mae": r.mae,
                    "skip_reason": r.skip_reason,
                }
                for r in result.records
            ],
            "summary": (
                {
                    "total_days": result.summary.total_days,
                    "total_trades": result.summary.total_trades,
                    "valid_trades": result.summary.valid_trades,
                    "skipped_trades": result.summary.skipped_trades,
                    "win_rate": result.summary.win_rate,
                    "avg_return_pct": result.summary.avg_return_pct,
                }
                if result.summary
                else None
            ),
            "regime_metrics": [
                {
                    "regime_label": metric.regime_label,
                    "sample_count": metric.sample_count,
                    "win_trades": metric.win_trades,
                    "loss_trades": metric.loss_trades,
                    "win_rate": metric.win_rate,
                    "avg_return": metric.avg_return,
                    "avg_win_return": metric.avg_win_return,
                    "avg_loss_return": metric.avg_loss_return,
                    "max_drawdown": metric.max_drawdown,
                    "profit_factor": metric.profit_factor,
                    "confidence": metric.confidence,
                    "low_sample": metric.low_sample,
                }
                for metric in result.regime_metrics
            ],
            "rule_regime_metrics": {
                rule_id: [
                    {
                        "regime_label": metric.regime_label,
                        "sample_count": metric.sample_count,
                        "win_trades": metric.win_trades,
                        "loss_trades": metric.loss_trades,
                        "win_rate": metric.win_rate,
                        "avg_return": metric.avg_return,
                        "avg_win_return": metric.avg_win_return,
                        "avg_loss_return": metric.avg_loss_return,
                        "max_drawdown": metric.max_drawdown,
                        "profit_factor": metric.profit_factor,
                        "confidence": metric.confidence,
                        "low_sample": metric.low_sample,
                    }
                    for metric in metrics
                ]
                for rule_id, metrics in sorted(result.rule_regime_metrics.items())
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def render_backtest_csv(result: BacktestResult) -> str:
    """把回测结果渲染为 CSV 字符串。"""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "trade_date",
            "trader_id",
            "strategy_version_id",
            "symbol",
            "status",
            "entry_price",
            "exit_price",
            "entry_date",
            "exit_date",
            "return_pct",
            "mfe",
            "mae",
            "volume",
            "is_valid_lot_size",
            "skip_reason",
            "evidence_refs",
        ]
    )
    for record in result.records:
        writer.writerow(
            [
                record.trade_date.isoformat(),
                record.trader_id,
                record.strategy_version_id,
                record.symbol,
                record.status,
                record.entry_price,
                record.exit_price,
                record.entry_date,
                record.exit_date,
                record.return_pct,
                record.mfe,
                record.mae,
                record.volume,
                record.is_valid_lot_size,
                record.skip_reason,
                json.dumps(record.evidence_refs, ensure_ascii=False),
            ]
        )
    return output.getvalue()


def render_rule_validation_markdown(results: list[RuleValidationResult]) -> str:
    """把规则验真结果渲染为 Markdown 报告。

    Args:
        results: RuleValidationResult 列表

    Returns:
        Markdown 格式报告字符串
    """
    lines = ["# Rule Validation Report", ""]

    if not results:
        lines.append("*（无规则验真结果）*")
        return "\n".join(lines)

    # 覆盖率统计
    programmable = [r for r in results if r.programmable]
    validated = [r for r in results if r.validation_status == "validated"]
    coverage = len(programmable) / len(results) if results else 0.0

    lines.append(f"**规则覆盖率:** {coverage:.1%} ({len(programmable)}/{len(results)})")
    lines.append(f"**已验真:** {len(validated)}/{len(programmable)}")
    lines.append("")

    lines.append("## Rule Details")
    for r in results:
        status_icon = {
            "validated": "✅",
            "unsupported_rule": "❌",
            "missing_field": "⚠️",
            "missing_snapshot": "📦",
            "invalid_rule": "🚫",
        }.get(r.validation_status, "?")
        detail = (
            f"- {status_icon} [{r.rule_id}] {r.rule_text[:40]} "
            f"| status={r.validation_status} "
            f"| hit={r.hit_count}/{r.sample_count}"
        )
        if r.posterior_return_mean is not None:
            detail += f" | 后验收益均值={r.posterior_return_mean:.2%}"
        if r.posterior_return_median is not None:
            detail += f" | 后验收益中位={r.posterior_return_median:.2%}"
        lines.append(detail)
    lines.append("")

    return "\n".join(lines)
