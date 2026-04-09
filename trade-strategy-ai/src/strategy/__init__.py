"""Strategy Agent"""
from src.strategy.types import (
    Signal,
    RawSignal,
    RuleMatch,
    SynthesisContext,
    SignalSide,
    PriceSpec,
    PositionSize,
    SynthesisMode,
    SignalContext,
    SignalWithContext,
)
from src.strategy.feature_engine import FeatureEngine

# TODO: 待其他任务完成后启用以下导入
# from src.strategy.rule_evaluator import RuleEvaluator
# from src.strategy.signal_synthesizer import SignalSynthesizer
# from src.strategy.signal import create_signal
# from src.strategy.signal_version import SignalVersioning

__all__ = [
    "Signal",
    "RawSignal",
    "RuleMatch",
    "SynthesisContext",
    "SignalSide",
    "PriceSpec",
    "PositionSize",
    "SynthesisMode",
    "SignalContext",
    "SignalWithContext",
    "FeatureEngine",
]
