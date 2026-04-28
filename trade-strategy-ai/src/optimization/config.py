"""优化模块配置（S7-001 / S7-002）。

贝叶斯收缩参数说明：
- bayesian_alpha: 先验强度，值越大向 baseline_win_rate 收缩越强
  alpha=10 表示"10 笔先验交易"的权重，适合 A 股市场
  参考：alpha=5 收缩弱，alpha=20 收缩强
- baseline_win_rate: 先验基准胜率，A 股市场建议 0.50
- min_trades: 最小有效交易笔数，低于此值时 score 打折
"""

from dataclasses import dataclass


@dataclass
class ActiveTraderFilterConfig:
    """活跃 trader 筛选配置。

    贝叶斯收缩公式：
        adjusted_win_rate = (wins + alpha * baseline_win_rate) / (valid_trades + alpha)
        sample_confidence = min(valid_trades / min_trades, 1.0)
        composite_score = adjusted_win_rate * sample_confidence

    参数说明：
        min_win_rate: 最低原始胜率门槛（含），默认 0.40
        min_trades: 最小有效交易笔数（含），默认 10
            — 低于此值时 sample_confidence < 1.0，score 折扣
        bayesian_alpha: 贝叶斯收缩强度，默认 10.0
            — 值越大，向 baseline_win_rate 收缩越强
            — alpha=10 表示 10 笔先验交易
        baseline_win_rate: 先验基准胜率，默认 0.50
            — 用于贝叶斯收缩的先验期望
        min_rule_hit_rate: 规则最低命中率门槛（可选），默认 None
            — None 表示不启用规则质量过滤
        min_score: 综合得分门槛（含），默认 0.30
            — composite_score 低于此值则 filter_passed=False
    """

    min_win_rate: float = 0.40
    min_trades: int = 10
    bayesian_alpha: float = 10.0
    baseline_win_rate: float = 0.50
    min_rule_hit_rate: float | None = None
    min_score: float = 0.30
