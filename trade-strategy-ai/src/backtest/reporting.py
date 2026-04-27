"""NTL-S6-005: 回测报告模块

职责：
- 把 BacktestResult 渲染为可读报告（Markdown / JSON）
- 把 RuleValidationResult 列表渲染为规则验真报告
"""

from __future__ import annotations

import json
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
                    # 比例口径字段：统一用格式化字符串输出（与 Markdown 报告一致）
                    "win_rate": f"{result.summary.win_rate:.2%}" if result.summary.win_rate is not None else None,
                    "avg_return_pct": f"{result.summary.avg_return_pct:.2%}" if result.summary.avg_return_pct is not None else None,
                }
                if result.summary
                else None
            ),
        },
        ensure_ascii=False,
        indent=2,
    )


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
