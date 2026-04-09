"""共享异常定义"""

class StrategyError(Exception):
    """策略执行异常基类"""
    pass


class FeatureEngineError(StrategyError):
    """特征计算异常"""
    pass


class RuleEvaluationError(StrategyError):
    """规则评估异常"""
    pass


class SignalSynthesisError(StrategyError):
    """信号合成异常"""
    pass


class RiskError(Exception):
    """风控异常基类"""
    pass


class PositionLimitExceeded(RiskError):
    """头寸超限异常"""
    pass


class RiskBlockedError(RiskError):
    """风控拦截异常（信号被风控拒绝）"""
    pass
