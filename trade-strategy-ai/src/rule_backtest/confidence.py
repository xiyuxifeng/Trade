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

    # 无交易或零样本时，返回保守的初始置信度
    if total_trades == 0 or sample_count == 0:
        return initial_confidence * 0.8

    # 样本量过少时启用保护机制
    if sample_count < 10:
        protection_factor = sample_count / 10.0
    else:
        protection_factor = 1.0

    # ========== 2. 基本胜率评分 (0~1) ==========
    hit_rate = backtest_result.hit_rate
    # 胜率评分：线性映射，0.5 胜率得 0.5 分，满分 1.0
    hit_rate_score = max(0.0, min(1.0, hit_rate))

    # ========== 3. 盈亏比评分 (0~1) ==========
    avg_win = backtest_result.avg_win_return
    avg_loss = backtest_result.avg_loss_return

    if avg_win is not None and avg_loss is not None and avg_loss != 0:
        # 盈亏比 = 盈利均值 / 亏损均值绝对值
        profit_loss_ratio = abs(avg_win / avg_loss)
        # 盈亏比评分：阈值 1.0 得 0.5 分，2.0+ 得满分
        profit_loss_score = max(0.0, min(1.0, (profit_loss_ratio - 1.0) / 1.0))
    else:
        profit_loss_score = 0.5  # 缺数据时给中性分

    # ========== 4. 夏普比率评分 (0~1) ==========
    sharpe = backtest_result.sharpe_ratio
    if sharpe is not None:
        # 夏普评分：0 得 0.5 分，1.0+ 得满分
        sharpe_score = max(0.0, min(1.0, sharpe))
    else:
        sharpe_score = 0.5  # 缺数据时给中性分

    # ========== 5. 最大回撤惩罚 (0~1，越小越好) ==========
    max_dd = backtest_result.max_drawdown
    if max_dd is not None and max_dd > 0:
        # 回撤评分：0% 得 1.0 分，20%+ 得 0 分
        drawdown_score = max(0.0, min(1.0, 1.0 - max_dd / 0.2))
    else:
        drawdown_score = 0.5  # 缺数据时给中性分

    # ========== 6. 综合得分（加权平均） ==========
    # 各指标权重：胜率 35%，盈亏比 30%，夏普 20%，回撤 15%
    composite_score = (
        hit_rate_score * 0.35
        + profit_loss_score * 0.30
        + sharpe_score * 0.20
        + drawdown_score * 0.15
    )

    # 应用样本量保护因子
    protected_score = composite_score * protection_factor

    # ========== 7. 贝叶斯式加权更新 ==========
    # 后验置信度 ∝ (先验置信度 × 先验权重 + 回测得分 × 交易数)
    # 先验权重越大，初始置信度影响越大
    # 注意：先验权重对应 initial_confidence（代表文章提取时的先验信念）
    posterior = (prior_weight * initial_confidence + total_trades * protected_score) / (
        prior_weight + total_trades
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