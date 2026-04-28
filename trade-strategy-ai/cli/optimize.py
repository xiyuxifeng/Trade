"""S7-001/S7-002/S7-003: 优化模块 CLI 入口

提供以下子命令：
- optimize filter：活跃 trader 筛选（S7-001）
- optimize advise：策略调整建议（S7-002）
- optimize create-candidate：生成候选版本（S7-003）
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from src.common.logger import get_logger
from src.optimization.active_trader_filter import ActiveTraderFilter
from src.optimization.config import ActiveTraderFilterConfig
from src.optimization.strategy_advisor import StrategyAdvisor
from src.backtest.schemas import RuleValidationResult

logger = get_logger(__name__)

app = typer.Typer(add_completion=False, help="S7-001/S7-002 优化相关命令")


@app.command("filter")
def optimize_filter(
    file: str = typer.Option("", "--file", "-f", help="BacktestResult JSON 文件路径（支持 glob 模式，如 data//backtest/*.json）"),
    trader: str = typer.Option("", "--trader", "-t", help="trader ID（可选，限定单个）"),
    min_win_rate: float = typer.Option(0.40, "--min-win-rate", help="最低原始胜率门槛"),
    min_trades: int = typer.Option(10, "--min-trades", help="最小有效交易笔数"),
    bayesian_alpha: float = typer.Option(10.0, "--bayesian-alpha", help="贝叶斯收缩强度"),
    baseline_win_rate: float = typer.Option(0.50, "--baseline-win-rate", help="先验基准胜率"),
    min_score: float = typer.Option(0.30, "--min-score", help="综合得分门槛"),
    output: str = typer.Option("", "--output", "-o", help="输出 JSON 文件路径（可选）"),
):
    """活跃 trader 筛选（S7-001）。

    从 BacktestResult JSON 文件加载数据，执行筛选，输出结果到控制台和可选的 JSON 文件。
    当前版本暂不接真实数据库，仅支持文件输入。
    """
    from src.backtest.schemas import BacktestResult

    config = ActiveTraderFilterConfig(
        min_win_rate=min_win_rate,
        min_trades=min_trades,
        bayesian_alpha=bayesian_alpha,
        baseline_win_rate=baseline_win_rate,
        min_score=min_score,
    )
    flt = ActiveTraderFilter(config)

    # 从文件加载 BacktestResult
    backtest_results: dict[str, BacktestResult] = {}
    if file:
        import glob
        for path_str in glob.glob(file) if '*' in file else [file]:
            path = Path(path_str)
            if not path.exists():
                typer.secho(f"文件不存在: {path}", fg=typer.colors.YELLOW)
                continue
            try:
                data = json.loads(path.read_text())
                # 单文件可能是 dict 或 list
                if isinstance(data, dict):
                    if "records" in data:
                        br = BacktestResult(**data)
                        backtest_results[br.request_trader_id] = br
                elif isinstance(data, list):
                    for item in data:
                        br = BacktestResult(**item)
                        backtest_results[br.request_trader_id] = br
            except Exception as exc:
                typer.secho(f"加载失败 {path}: {exc}", fg=typer.colors.YELLOW)

    # 限定 trader
    if trader and backtest_results and trader not in backtest_results:
        filtered = {trader: backtest_results[trader]}
    else:
        filtered = backtest_results

    if not filtered:
        typer.echo("无 BacktestResult 数据，请检查 --file 参数")
        return

    results = flt.filter(filtered)

    # 输出到控制台
    typer.echo(f"\n=== Trader 筛选结果（{len(results)} 个）===")
    for r in results:
        status = "✅ 通过" if r.filter_passed else "❌ 未通过"
        typer.echo(f"\n{trader}: {status}")
        typer.echo(f"  原始胜率: {r.raw_win_rate:.2%}" if r.raw_win_rate is not None else "  原始胜率: N/A")
        typer.echo(f"  收缩胜率: {r.adjusted_win_rate:.2%}")
        typer.echo(f"  置信度: {r.sample_confidence:.2%}")
        typer.echo(f"  综合得分: {r.composite_score:.3f}")
        if r.pass_reasons:
            typer.echo(f"  通过原因: {', '.join(r.pass_reasons)}")
        if r.fail_reasons:
            typer.echo(f"  未通过原因: {', '.join(r.fail_reasons)}")

    # 输出到文件
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        json_data = [
            {
                "trader_id": r.trader_id,
                "filter_passed": r.filter_passed,
                "raw_win_rate": r.raw_win_rate,
                "adjusted_win_rate": r.adjusted_win_rate,
                "valid_trades": r.valid_trades,
                "sample_confidence": r.sample_confidence,
                "composite_score": r.composite_score,
                "pass_reasons": r.pass_reasons,
                "fail_reasons": r.fail_reasons,
            }
            for r in results
        ]
        out_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False))
        typer.secho(f"结果已写入: {out_path}", fg=typer.colors.GREEN)


@app.command("advise")
def optimize_advise(
    file: str = typer.Option("", "--file", "-f", help="RuleValidationResult JSON 文件路径"),
    trader: str = typer.Option("", "--trader", "-t", help="trader ID（从文件自动提取）"),
    output: str = typer.Option("", "--output", "-o", help="输出 JSON 文件路径（可选）"),
):
    """策略调整建议（S7-002）。

    从规则验真结果 JSON 文件读取 RuleValidationResult[]，输出调整建议。
    """
    advisor = StrategyAdvisor()

    validations: list[RuleValidationResult] = []
    if file:
        path = Path(file)
        if not path.exists():
            typer.secho(f"文件不存在: {path}", fg=typer.colors.YELLOW)
            return
        try:
            data = json.loads(path.read_text())
            if isinstance(data, list):
                validations = [RuleValidationResult(**r) for r in data]
            else:
                validations = [RuleValidationResult(**data)]
        except Exception as exc:
            typer.secho(f"加载失败 {path}: {exc}", fg=typer.colors.YELLOW)
            return

    if not validations:
        typer.echo("无 RuleValidationResult 数据，请检查 --file 参数")
        return

    result = advisor.advise(validations)

    # 输出到控制台
    typer.echo(f"\n=== 策略调整建议（{len(result.adjustments)} 条）===")
    for adj in result.adjustments:
        typer.echo(f"\n[{adj.current_status}] {adj.rule_id}")
        typer.echo(f"  规则: {adj.rule_text}")
        typer.echo(f"  置信度: {adj.confidence:.2%}")
        typer.echo(f"  建议: {adj.suggestion}")

    if result.skipped_rules:
        typer.echo(f"\n跳过（无匹配）: {result.skipped_rules}")

    # 输出到文件
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        json_data = {
            "trader_id": result.trader_id,
            "adjustments": [
                {
                    "rule_id": adj.rule_id,
                    "rule_text": adj.rule_text,
                    "current_status": adj.current_status,
                    "suggestion": adj.suggestion,
                    "confidence": adj.confidence,
                    "hit_rate": adj.hit_rate,
                    "posterior_return_mean": adj.posterior_return_mean,
                }
                for adj in result.adjustments
            ],
            "skipped_rules": result.skipped_rules,
        }
        out_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False))
        typer.secho(f"结果已写入: {out_path}", fg=typer.colors.GREEN)


@app.command("create-candidate")
def optimize_create_candidate(
    parent: str = typer.Option("", "--parent", "-p", help="正式版本 JSON 文件路径（released_version.json）"),
    adjustments: str = typer.Option("", "--adjustments", "-a", help="S7-002 输出的调整建议 JSON 文件路径"),
    trader: str = typer.Option("", "--trader", "-t", help="trader ID（与 --parent 二选一）"),
    date: str = typer.Option("", "--date", "-d", help="策略日期 YYYY-MM-DD（与 --parent 二选一）"),
    version_id: str = typer.Option("", "--version-id", "-v", help="parent version_id"),
    output: str = typer.Option("", "--output", "-o", help="输出候选版本 JSON 文件路径"),
):
    """候选版本生成（S7-003）。

    接收正式版本（released_version.json）和 S7-002 调整建议 JSON，
    生成候选版本（draft，candidate 类型），不写 DB。
    """
    from datetime import date as Date

    from src.optimization.candidate_builder import (
        CandidateBuildInput,
        build_candidate_version,
    )
    from src.optimization.strategy_advisor import RuleAdjustment
    from src.strategy_library.schemas import StrategyVersion

    adjustments_list: list[RuleAdjustment] = []
    parent_rules_snapshot: list[dict] = []
    parent_vid = version_id
    parent_trader_id = trader
    parent_date_str = date

    # 加载调整建议
    if adjustments:
        adj_path = Path(adjustments)
        if not adj_path.exists():
            typer.secho(f"调整建议文件不存在: {adj_path}", fg=typer.colors.YELLOW)
            return
        try:
            adj_data = json.loads(adj_path.read_text())
            if isinstance(adj_data, dict) and "adjustments" in adj_data:
                adj_data = adj_data["adjustments"]
            adjustments_list = [RuleAdjustment(**adj) for adj in adj_data]
        except Exception as exc:
            typer.secho(f"加载调整建议失败 {adj_path}: {exc}", fg=typer.colors.YELLOW)
            return

    if not adjustments_list:
        typer.echo("无调整建议数据，请检查 --adjustments 参数")
        return

    # 加载正式版本
    if parent:
        parent_path = Path(parent)
        if not parent_path.exists():
            typer.secho(f"正式版本文件不存在: {parent_path}", fg=typer.colors.YELLOW)
            return
        try:
            parent_data = json.loads(parent_path.read_text())
            pv = StrategyVersion(**parent_data)
            parent_rules_snapshot = pv.rules_snapshot or []
            parent_vid = pv.version_id
            parent_trader_id = pv.trader_id
            parent_date_str = pv.strategy_date.isoformat()
        except Exception as exc:
            typer.secho(f"加载正式版本失败 {parent_path}: {exc}", fg=typer.colors.YELLOW)
            return
    else:
        if not trader or not date or not version_id:
            typer.echo("请提供 --parent（正式版本 JSON）或 --trader + --date + --version-id")
            return

    # 构建候选版本
    input_obj = CandidateBuildInput(
        trader_id=parent_trader_id,
        strategy_date=Date.fromisoformat(parent_date_str),
        parent_version_id=parent_vid,
        parent_rules_snapshot=parent_rules_snapshot,
        adjustments=adjustments_list,
        recommendations=[],
    )

    result = build_candidate_version(input_obj)

    # 输出到控制台
    typer.echo(f"\n=== 候选版本已生成 ===")
    typer.echo(f"  version_id: {result.version.version_id}")
    typer.echo(f"  parent_version_id: {result.version.parent_version_id}")
    typer.echo(f"  status: {result.version.status.value}")
    typer.echo(f"  version_type: {result.version.version_type.value}")
    typer.echo(f"  rules_snapshot 变更:")
    if result.deleted_rules:
        typer.echo(f"    删除: {result.deleted_rules}")
    if result.modified_rules:
        typer.echo(f"    修改: {result.modified_rules}")
    if result.kept_rules:
        typer.echo(f"    保留: {result.kept_rules}")
    typer.echo(f"  notes:\n{result.version.notes}")

    # 输出到文件
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        json_data = {
            "version_id": result.version.version_id,
            "trader_id": result.version.trader_id,
            "strategy_date": result.version.strategy_date.isoformat(),
            "status": result.version.status.value,
            "version_type": result.version.version_type.value,
            "parent_version_id": result.version.parent_version_id,
            "recommendations": [
                {
                    "symbol": r.symbol,
                    "decision": r.decision,
                    "confidence": r.confidence,
                    "entry_price": r.entry_price,
                    "target_price": r.target_price,
                    "stop_loss_price": r.stop_loss_price,
                    "rationale": r.rationale,
                    "evidence_refs": r.evidence_refs,
                }
                for r in result.version.recommendations
            ],
            "rules_snapshot": result.version.rules_snapshot,
            "notes": result.version.notes,
            "_build_summary": {
                "deleted_rules": result.deleted_rules,
                "modified_rules": result.modified_rules,
                "kept_rules": result.kept_rules,
            },
        }
        out_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False))
        typer.secho(f"候选版本已写入: {out_path}", fg=typer.colors.GREEN)
