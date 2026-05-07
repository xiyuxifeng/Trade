"""置信度计算模块 - 基于回测结果调整规则置信度"""
from __future__ import annotations

from src.rule_pool.schemas import RuleBacktestResult


def compute_confidence_adjustment(
    initial_confidence: float,
    backtest_result: RuleBacktestResult,
    prior_weight: int = 20,
) -> float:
    """
    多指标综合置信度调整

    参数：
        initial_confidence: 提取时的初始置信度
        backtest_result: 回测结果
        prior_weight: 先验权重（样本少时保护）

    返回：
        validated_confidence: 验证后的置信度

    算法说明：
        1. 样本不足保护：样本数 < 10 时，保守调整
        2. 多指标评分：胜率 + 盈亏比 + 夏普 + 回撤惩罚
        3. 贝叶斯式加权：结合先验置信度和回测证据
    """
    # ========== 1. 样本不足保护 ==========
    sample_count = backtest_result.sample_count
    total_trades = backtest_result.total_trades

    # 样本不足或零交易时保护性处理
    if sample_count < 10 or total_trades == 0:
        return initial_confidence * 0.9  # 轻微下调

    # ========== 2. 基本胜率评分 (0~1) ==========
    hit_rate = backtest_result.hit_rate

    # ========== 3. 盈亏比评分（盈利均值 / 亏损均值绝对值） ==========
    avg_win = backtest_result.avg_win_return
    avg_loss = backtest_result.avg_loss_return

    if avg_win is not None and avg_loss is not None and avg_loss != 0:
        profit_loss_ratio = abs(avg_win / avg_loss)
    else:
        # 无细分数据时，用 avg_return 做保守近似
        avg_return = backtest_result.avg_return
        profit_loss_ratio = max(avg_return * 25 + 0.5, 0) if avg_return != 0 else 0.5

    # ========== 4. 夏普比率调整 ==========
    sharpe = backtest_result.sharpe_ratio or 0
    sharpe_factor = max(min(sharpe / 2.0, 1.0), -1.0)  # 归一化到 [-1, 1]

    # ========== 5. 最大回撤惩罚 ==========
    max_dd = backtest_result.max_drawdown or 0
    dd_penalty = max_dd * 0.5  # 回撤越大，惩罚越大

    # ========== 6. 综合得分（加权平均） ==========
    # 各指标权重：胜率 40%，盈亏比 20%，夏普 20%，回撤 20%
    score = (
        0.4 * hit_rate
        + 0.2 * min(profit_loss_ratio, 1.5) / 1.5
        + 0.2 * (sharpe_factor + 1) / 2
        + 0.2 * (1 - dd_penalty)
    )

    # ========== 7. 贝叶斯式加权更新 ==========
    # 新置信度 = (初始置信度 × 先验权重 + 回测得分 × 样本量) / (先验权重 + 样本量)
    n = backtest_result.sample_count
    posterior = (initial_confidence * prior_weight + score * n) / (
        prior_weight + n
    )

    # 确保结果在 [0.0, 1.0] 范围内
    validated_confidence = max(0.0, min(1.0, posterior))

    return validated_confidence


def get_confidence_level(confidence: float) -> str:
    """
    获取置信度等级

    参数：
        confidence: 置信度值 [0, 1]

    返回：
        等级字符串：
            A: >= 0.8 (高置信度)
            B: >= 0.6 (中高置信度)
            C: >= 0.4 (中等置信度)
            D: < 0.4 (低置信度)
    """
    if confidence >= 0.8:
        return "A"
    elif confidence >= 0.6:
        return "B"
    elif confidence >= 0.4:
        return "C"
    else:
        return "D"