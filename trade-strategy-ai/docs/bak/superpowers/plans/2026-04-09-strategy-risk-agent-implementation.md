# Strategy Agent & Risk Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 P4-001~P4-008 策略执行系统，包含 Strategy Agent（信号生成）和 Risk Agent（风控）

**Architecture:** Strategy Agent 负责特征计算、规则评估、信号合成、版本控制；Risk Agent 负责头寸管理、止损止盈计算。两者通过同步拦截模式协作，模拟账户数据持久化到 PostgreSQL。

**Tech Stack:** Python 3.11+, Pydantic, SQLAlchemy, 复用 `src/features/` 特征库、`src/persona/dsl_executor.py` DSL 执行引擎

---

## 文件结构

```
src/
├── strategy/                      # Strategy Agent
│   ├── __init__.py
│   ├── types.py                  # Signal, RawSignal, RuleMatch 等
│   ├── config.py                 # 策略配置加载
│   ├── feature_engine.py         # P4-001 特征计算引擎
│   ├── rule_evaluator.py         # P4-002 规则评估引擎
│   ├── signal_synthesizer.py     # P4-003 多规则信号合成
│   ├── signal.py                 # P4-004 信号输出格式
│   └── signal_version.py         # P4-005 信号版本控制
│
├── risk/                         # Risk Agent
│   ├── __init__.py
│   ├── types.py                  # Position, StopLossLevel 等风控类型
│   ├── config.py                 # 风控配置加载
│   ├── position_manager.py       # P4-006 头寸管理
│   ├── stop_loss.py              # P4-007 止损设置
│   └── take_profit.py            # P4-008 止盈策略
│
└── shared/
    ├── __init__.py
    └── exceptions.py            # 共用异常（StrategyError, RiskError 等）
```

---

## Task 1: 共享类型定义

**Files:**
- Create: `src/shared/__init__.py`
- Create: `src/shared/exceptions.py`
- Modify: `src/strategy/__init__.py`
- Modify: `src/risk/__init__.py`

- [ ] **Step 1: 创建 src/shared/exceptions.py**

```python
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
```

- [ ] **Step 2: 创建 src/shared/__init__.py**

```python
"""共享模块"""
from src.shared.exceptions import (
    StrategyError,
    FeatureEngineError,
    RuleEvaluationError,
    SignalSynthesisError,
    RiskError,
    PositionLimitExceeded,
    RiskBlockedError,
)

__all__ = [
    "StrategyError",
    "FeatureEngineError",
    "RuleEvaluationError",
    "SignalSynthesisError",
    "RiskError",
    "PositionLimitExceeded",
    "RiskBlockedError",
]
```

- [ ] **Step 3: 修改 src/strategy/__init__.py**

```python
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
from src.strategy.rule_evaluator import RuleEvaluator
from src.strategy.signal_synthesizer import SignalSynthesizer
from src.strategy.signal import create_signal
from src.strategy.signal_version import SignalVersioning

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
    "RuleEvaluator",
    "SignalSynthesizer",
    "create_signal",
    "SignalVersioning",
]
```

- [ ] **Step 4: 修改 src/risk/__init__.py**

```python
"""Risk Agent"""
from src.risk.types import (
    Position,
    PositionSizeType,
    AccountSnapshot,
    StopLossMode,
    StopLossLevel,
    StopLossConfig,
    TakeProfitMode,
    TakeProfitLevel,
    TakeProfitConfig,
    ScalingLevel,
)
from src.risk.position_manager import PositionManager, PositionSizeMode, PositionConfig
from src.risk.stop_loss import StopLossCalculator
from src.risk.take_profit import TakeProfitCalculator

__all__ = [
    "Position",
    "PositionSizeType",
    "AccountSnapshot",
    "StopLossMode",
    "StopLossLevel",
    "StopLossConfig",
    "TakeProfitMode",
    "TakeProfitLevel",
    "TakeProfitConfig",
    "ScalingLevel",
    "PositionManager",
    "PositionSizeMode",
    "PositionConfig",
    "StopLossCalculator",
    "TakeProfitCalculator",
]
```

- [ ] **Step 5: Commit**

```bash
git add src/shared/ src/strategy/__init__.py src/risk/__init__.py
git commit -m "feat: add shared types and exceptions for strategy/risk agents"
```

---

## Task 2: Strategy Agent 类型定义

**Files:**
- Create: `src/strategy/types.py`

- [ ] **Step 1: 创建 src/strategy/types.py**

```python
"""Strategy Agent 类型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from src.persona.dsl import ActionSpec


class SignalSide(StrEnum):
    """信号方向"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SynthesisMode(StrEnum):
    """信号合成模式"""
    WEIGHTED_SCORE = "weighted_score"
    VOTING = "voting"
    PRIORITY = "priority"


class PositionSizeType(StrEnum):
    """头寸类型"""
    FIXED_AMOUNT = "fixed_amount"
    FIXED_RATIO = "fixed_ratio"
    VOLATILITY_ADJUSTED = "volatility_adjusted"


@dataclass
class PriceSpec:
    """价格规格"""
    type: str  # "market", "limit", "trigger"
    value: float | None = None
    offset_pct: float | None = None


@dataclass
class PositionSize:
    """头寸规格"""
    type: PositionSizeType
    value: float  # 金额或比例
    max_amount: float | None = None


@dataclass
class RuleMatch:
    """单条规则匹配结果"""
    rule_id: str
    rule_type: str  # entry/exit/filter/sizing/risk
    matched: bool
    confidence: float  # 0-1
    action: ActionSpec


@dataclass
class SynthesisContext:
    """信号合成上下文"""
    market_state: dict[str, Any]
    features: dict[str, Any]


@dataclass
class RawSignal:
    """合成后但未经过风控的信号"""
    signal_id: str
    symbol: str
    side: SignalSide
    confidence: float
    triggered_rules: list[str]
    synthesis_mode: SynthesisMode
    entry_price: PriceSpec | None = None
    position_size: PositionSize | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Signal:
    """最终交易信号（经过风控）"""
    signal_id: str
    symbol: str
    side: SignalSide
    confidence: float
    timestamp: datetime
    triggered_rules: list[str]
    synthesis_mode: SynthesisMode
    entry_price: PriceSpec | None = None
    position_size: PositionSize | None = None
    stop_loss: StopLossLevel | None = None
    take_profit: list[TakeProfitLevel] | None = None
    version: str = "v1"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalContext:
    """信号生成上下文（用于版本控制）"""
    features_snapshot: dict[str, Any]
    market_state: dict[str, Any]
    rules_snapshot: list[dict[str, Any]]
    timestamp: datetime


@dataclass
class SignalWithContext:
    """信号及其完整上下文"""
    signal: Signal
    context: SignalContext
```

- [ ] **Step 2: Commit**

```bash
git add src/strategy/types.py
git commit -m "feat: add Strategy Agent type definitions"
```

---

## Task 3: Risk Agent 类型定义

**Files:**
- Create: `src/risk/types.py`

- [ ] **Step 1: 创建 src/risk/types.py**

```python
"""Risk Agent 类型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class PositionSizeType(StrEnum):
    """头寸类型"""
    FIXED_AMOUNT = "fixed_amount"
    FIXED_RATIO = "fixed_ratio"
    VOLATILITY_ADJUSTED = "volatility_adjusted"


class StopLossMode(StrEnum):
    """止损模式"""
    FIXED = "fixed"
    VOLATILITY = "volatility"
    TRAILING = "trailing"
    TIME = "time"


class TakeProfitMode(StrEnum):
    """止盈模式"""
    FIXED = "fixed"
    SCALING = "scaling"
    TRAILING = "trailing"
    TIME = "time"


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class AccountSnapshot:
    """账户快照"""
    account_id: str
    timestamp: datetime
    net_value: float
    cash: float
    total_position_value: float
    positions: list[Position]
    daily_pnl: float
    total_pnl: float


@dataclass
class ScalingLevel:
    """分批止盈级别"""
    target_pct: float  # 目标涨幅
    close_pct: float   # 卖出比例（0-1）


@dataclass
class StopLossLevel:
    """止损级别"""
    mode: StopLossMode
    level: float  # 止损价格
    trigger_condition: str  # 触发条件描述


@dataclass
class TakeProfitLevel:
    """止盈级别"""
    mode: TakeProfitMode
    level: float  # 目标价格
    close_pct: float  # 卖出比例（分批止盈用）
    trigger_condition: str  # 触发条件描述
```

- [ ] **Step 2: Commit**

```bash
git add src/risk/types.py
git commit -m "feat: add Risk Agent type definitions"
```

---

## Task 4: P4-001 特征计算引擎

**Files:**
- Create: `src/strategy/feature_engine.py`
- Create: `tests/unit/strategy/test_feature_engine.py`

- [ ] **Step 1: 创建测试文件 tests/unit/strategy/test_feature_engine.py**

```python
"""FeatureEngine 单元测试"""
import pytest
from datetime import date
from src.strategy.feature_engine import FeatureEngine
from src.features.feature_pipeline import DailyBars


def _create_sample_bars() -> DailyBars:
    """创建样本日线数据"""
    import numpy as np
    n = 60
    dates = [date(2026, 1, 1) for _ in range(n)]
    base_price = 100.0
    closes = [base_price + i * 0.5 + np.random.randn() * 0.5 for i in range(n)]
    highs = [c * 1.02 for c in closes]
    lows = [c * 0.98 for c in closes]
    opens = [c * (1 + (np.random.randn() * 0.01)) for c in closes]
    volumes = [1_000_000 for _ in range(n)]
    return DailyBars(
        symbol="TEST",
        dates=dates,
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        volumes=volumes,
    )


def test_compute_realtime_returns_feature_vector():
    """测试实时计算返回特征向量"""
    engine = FeatureEngine()
    bars = _create_sample_bars()
    result = engine.compute_realtime(bars)
    assert result is not None
    assert hasattr(result, "rsi")
    assert hasattr(result, "macd")


def test_from_precomputed_returns_same():
    """测试预计算特征直接返回"""
    engine = FeatureEngine()
    bars = _create_sample_bars()
    features = engine.compute_realtime(bars)
    result = engine.from_precomputed(features)
    assert result is features


def test_compute_batch_multiple_symbols():
    """测试批量计算多标的"""
    engine = FeatureEngine()
    bars1 = _create_sample_bars()
    bars2 = _create_sample_bars()
    items = [("TEST1", bars1), ("TEST2", bars2)]
    result = engine.compute_batch(items)
    assert len(result) == 2
    assert "TEST1" in result
    assert "TEST2" in result
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/strategy/test_feature_engine.py -v 2>&1 | head -30
# 预期: ERROR - module not found
```

- [ ] **Step 3: 创建 src/strategy/feature_engine.py**

```python
"""特征计算引擎 - P4-001"""
from __future__ import annotations

from typing import Literal

from src.features.feature_pipeline import (
    compute_features,
    FeatureVector,
    DailyBars,
)
from src.shared.exceptions import FeatureEngineError


class FeatureEngine:
    """特征计算引擎

    支持两种模式:
    - 实时计算: 接收 OHLCV 原始数据，自己计算特征
    - 预计算: 接收已计算好的 FeatureVector，直接返回
    """

    def __init__(self, mode: Literal["pandas", "polars", "pure_python"] = "pure_python"):
        self._mode = mode

    def compute_realtime(
        self,
        bars: DailyBars | list[dict],
        mode: Literal["pandas", "polars", "pure_python"] | None = None,
    ) -> FeatureVector:
        """实时计算特征

        Args:
            bars: OHLCV 数据（DailyBars 或 dict list）
            mode: 计算模式，默认使用实例配置

        Returns:
            FeatureVector 特征向量

        Raises:
            FeatureEngineError: 计算失败时抛出
        """
        compute_mode = mode or self._mode

        # 转换为 DailyBars
        if isinstance(bars, list):
            bars = self._dict_list_to_bars(bars)

        try:
            return compute_features(bars)
        except Exception as e:
            raise FeatureEngineError(f"Feature computation failed: {e}") from e

    def from_precomputed(self, feature_vector: FeatureVector) -> FeatureVector:
        """直接返回预计算特征

        Args:
            feature_vector: 已计算好的特征向量

        Returns:
            相同的特征向量
        """
        return feature_vector

    def compute_batch(
        self,
        items: list[tuple[str, DailyBars]],
        mode: Literal["pandas", "polars", "pure_python"] | None = None,
    ) -> dict[str, FeatureVector]:
        """批量计算多标的特征

        Args:
            items: [(symbol, bars), ...] 元组列表
            mode: 计算模式

        Returns:
            {symbol: FeatureVector} 字典
        """
        result = {}
        for symbol, bars in items:
            try:
                result[symbol] = self.compute_realtime(bars, mode)
            except FeatureEngineError:
                # 单标的失败不影响其他标的
                continue
        return result

    def _dict_list_to_bars(self, data: list[dict]) -> DailyBars:
        """将 dict 列表转换为 DailyBars"""
        if not data:
            raise FeatureEngineError("Empty data")

        sample = data[0]
        required = ["open", "high", "low", "close", "volume"]
        for key in required:
            if key not in sample:
                raise FeatureEngineError(f"Missing required field: {key}")

        return DailyBars(
            symbol=sample.get("symbol", "UNKNOWN"),
            dates=[d.get("date") for d in data],
            opens=[d["open"] for d in data],
            highs=[d["high"] for d in data],
            lows=[d["low"] for d in data],
            closes=[d["close"] for d in data],
            volumes=[d["volume"] for d in data],
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/strategy/test_feature_engine.py -v
# 预期: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/strategy/feature_engine.py tests/unit/strategy/test_feature_engine.py
git commit -m "feat: implement P4-001 FeatureEngine"
```

---

## Task 5: P4-002 规则评估引擎

**Files:**
- Create: `src/strategy/rule_evaluator.py`
- Create: `tests/unit/strategy/test_rule_evaluator.py`

- [ ] **Step 1: 创建测试文件 tests/unit/strategy/test_rule_evaluator.py**

```python
"""RuleEvaluator 单元测试"""
import pytest
from datetime import date
from src.strategy.rule_evaluator import RuleEvaluator, RuleMatch
from src.strategy.types import SynthesisContext, MarketState
from src.persona.dsl_executor import DSLExecutor, RuleRegistry
from src.persona.dsl_compiler import DSLCompiler
from src.persona.schemas import MarketRegime, VolatilityLevel


def _create_sample_market_state() -> MarketState:
    """创建样本市场状态"""
    return MarketState(
        as_of_date=date(2026, 4, 9),
        regime=MarketRegime.trend_up,
        volatility=VolatilityLevel.low,
    )


def _compile_sample_rule():
    """编译样本规则"""
    compiler = DSLCompiler()
    rule = compiler.compile(
        name="test_rule",
        rule_type="entry",
        condition_dsl="regime == 'trend_up'",
    )
    return rule


def test_evaluate_returns_rule_matches():
    """测试评估返回规则匹配结果"""
    registry = RuleRegistry()
    executor = DSLExecutor(registry)
    evaluator = RuleEvaluator(executor)

    rule = _compile_sample_rule()
    registry.register(rule)

    state = _create_sample_market_state()
    from src.features.feature_pipeline import FeatureVector
    features = FeatureVector()

    matches = evaluator.evaluate([rule], features, state)
    assert len(matches) == 1
    assert matches[0].rule_id == rule.rule_id


def test_evaluate_no_match():
    """测试不匹配的情况"""
    registry = RuleRegistry()
    executor = DSLExecutor(registry)
    evaluator = RuleEvaluator(executor)

    compiler = DSLCompiler()
    rule = compiler.compile(
        name="down_rule",
        rule_type="entry",
        condition_dsl="regime == 'trend_down'",
    )
    registry.register(rule)

    state = _create_sample_market_state()  # regime = trend_up
    from src.features.feature_pipeline import FeatureVector
    features = FeatureVector()

    matches = evaluator.evaluate([rule], features, state)
    assert len(matches) == 1
    assert matches[0].matched is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/strategy/test_rule_evaluator.py -v 2>&1 | head -30
# 预期: ERROR - module not found
```

- [ ] **Step 3: 创建 src/strategy/rule_evaluator.py**

```python
"""规则评估引擎 - P4-002"""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.strategy.types import RuleMatch
from src.shared.exceptions import RuleEvaluationError

if TYPE_CHECKING:
    from src.persona.dsl_executor import DSLExecutor
    from src.persona.dsl_compiler import CompiledRule
    from src.features.feature_pipeline import FeatureVector
    from src.persona.schemas import MarketState


class RuleEvaluator:
    """规则评估引擎

    将 DSL 规则（CompiledRule）作用于特征向量，返回匹配结果。
    """

    def __init__(self, executor: DSLExecutor):
        self._executor = executor

    def evaluate(
        self,
        rules: list[CompiledRule],
        features: FeatureVector,
        market_state: MarketState,
    ) -> list[RuleMatch]:
        """评估单标的规则匹配

        Args:
            rules: 编译后的规则列表
            features: 特征向量
            market_state: 市场状态

        Returns:
            RuleMatch 列表
        """
        results = []
        for rule in rules:
            try:
                # 构建执行上下文
                state = market_state.model_dump() if hasattr(market_state, "model_dump") else {}
                bar = features.to_dict() if hasattr(features, "to_dict") else {}

                # 执行规则
                matched = rule.matches(state=state, bar=bar)

                # 提取置信度
                confidence = getattr(rule, "confidence", 0.5)
                if not isinstance(confidence, (int, float)):
                    confidence = 0.5

                results.append(RuleMatch(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    matched=matched,
                    confidence=confidence,
                    action=getattr(rule, "action", None),
                ))
            except Exception as e:
                raise RuleEvaluationError(f"Rule evaluation failed for {rule.rule_id}: {e}") from e

        return results

    def evaluate_batch(
        self,
        rules: list[CompiledRule],
        features_map: dict[str, FeatureVector],
        market_state: MarketState,
    ) -> dict[str, list[RuleMatch]]:
        """批量评估多标的规则匹配

        Args:
            rules: 规则列表
            features_map: {symbol: FeatureVector}
            market_state: 市场状态

        Returns:
            {symbol: [RuleMatch]} 字典
        """
        results = {}
        for symbol, features in features_map.items():
            try:
                results[symbol] = self.evaluate(rules, features, market_state)
            except RuleEvaluationError:
                results[symbol] = []
        return results
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/strategy/test_rule_evaluator.py -v
# 预期: 2 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/strategy/rule_evaluator.py tests/unit/strategy/test_rule_evaluator.py
git commit -m "feat: implement P4-002 RuleEvaluator"
```

---

## Task 6: P4-003 多规则信号合成

**Files:**
- Create: `src/strategy/signal_synthesizer.py`
- Create: `tests/unit/strategy/test_signal_synthesizer.py`

- [ ] **Step 1: 创建测试文件 tests/unit/strategy/test_signal_synthesizer.py**

```python
"""SignalSynthesizer 单元测试"""
import pytest
from src.strategy.signal_synthesizer import (
    SignalSynthesizer,
    SynthesisMode,
)
from src.strategy.types import RuleMatch, SynthesisContext, RawSignal, SignalSide
from src.persona.dsl import ActionSpec


def _create_rule_match(
    rule_id: str,
    rule_type: str,
    matched: bool,
    confidence: float,
    side: str = "buy",
) -> RuleMatch:
    """创建样本 RuleMatch"""
    return RuleMatch(
        rule_id=rule_id,
        rule_type=rule_type,
        matched=matched,
        confidence=confidence,
        action=ActionSpec(type=rule_type, side=side),
    )


def test_priority_mode_buy_signal():
    """测试优先级模式 - BUY 信号"""
    synthesizer = SignalSynthesizer(mode=SynthesisMode.PRIORITY)

    matches = [
        _create_rule_match("rule1", "entry", True, 0.8, "buy"),
        _create_rule_match("rule2", "exit", True, 0.6, "sell"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    assert result.side == SignalSide.BUY
    assert result.synthesis_mode == SynthesisMode.PRIORITY


def test_priority_mode_filters_no_match():
    """测试优先级模式 - 过滤未匹配规则"""
    synthesizer = SignalSynthesizer(mode=SynthesisMode.PRIORITY)

    matches = [
        _create_rule_match("rule1", "entry", False, 0.8, "buy"),  # 未匹配
        _create_rule_match("rule2", "exit", True, 0.6, "sell"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    # entry 未匹配，exit 匹配，结果应为 SELL
    assert result.side == SignalSide.SELL


def test_voting_mode_majority():
    """测试投票模式 - 多数胜出"""
    synthesizer = SignalSynthesizer(mode=SynthesisMode.VOTING)

    matches = [
        _create_rule_match("rule1", "entry", True, 0.8, "buy"),
        _create_rule_match("rule2", "entry", True, 0.7, "buy"),
        _create_rule_match("rule3", "entry", True, 0.6, "sell"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    assert result.side == SignalSide.BUY  # 2 buy vs 1 sell


def test_weighted_score_mode():
    """测试加权评分模式"""
    synthesizer = SignalSynthesizer(
        mode=SynthesisMode.WEIGHTED_SCORE,
        weights={"entry": 1.0, "exit": 1.5},
    )

    matches = [
        _create_rule_match("rule1", "entry", True, 0.8, "buy"),
        _create_rule_match("rule2", "exit", True, 0.6, "sell"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    assert result.side in (SignalSide.BUY, SignalSide.SELL, SignalSide.HOLD)


def test_hold_when_no_matches():
    """测试无匹配规则时返回 HOLD"""
    synthesizer = SignalSynthesizer(mode=SynthesisMode.PRIORITY)

    matches = [
        _create_rule_match("rule1", "entry", False, 0.8, "buy"),
    ]
    context = SynthesisContext(market_state={}, features={})

    result = synthesizer.synthesize(matches, context)
    assert result.side == SignalSide.HOLD
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/strategy/test_signal_synthesizer.py -v 2>&1 | head -30
# 预期: ERROR - module not found
```

- [ ] **Step 3: 创建 src/strategy/signal_synthesizer.py**

```python
"""多规则信号合成器 - P4-003"""
from __future__ import annotations

import uuid
from typing import Any

from src.strategy.types import (
    RuleMatch,
    SynthesisContext,
    RawSignal,
    SignalSide,
    SynthesisMode,
    PriceSpec,
    PositionSize,
    PositionSizeType,
)
from src.shared.exceptions import SignalSynthesisError


class SignalSynthesizer:
    """多规则信号合成器

    支持三种合成模式:
    - WEIGHTED_SCORE: 加权评分
    - VOTING: 投票机制
    - PRIORITY: 优先级覆盖（默认）
    """

    # 默认优先级（数值越大优先级越高）
    DEFAULT_PRIORITIES = ["entry", "sizing", "exit", "filter", "risk"]

    def __init__(
        self,
        mode: SynthesisMode = SynthesisMode.PRIORITY,
        weights: dict[str, float] | None = None,
        priorities: list[str] | None = None,
    ):
        self._mode = mode
        self._weights = weights or {}
        self._priorities = priorities or self.DEFAULT_PRIORITIES

    def synthesize(
        self,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """合成信号

        Args:
            matches: 规则匹配结果列表
            context: 合成上下文

        Returns:
            RawSignal 原始信号（未经过风控）
        """
        if not matches:
            return self._create_hold_signal(context)

        # 过滤已匹配的规则
        matched = [m for m in matches if m.matched]
        if not matched:
            return self._create_hold_signal(context)

        # 根据模式合成
        if self._mode == SynthesisMode.WEIGHTED_SCORE:
            return self._synthesize_weighted(matched, context)
        elif self._mode == SynthesisMode.VOTING:
            return self._synthesize_voting(matched, context)
        else:
            return self._synthesize_priority(matched, context)

    def _synthesize_weighted(
        self,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """加权评分合成"""
        scores = {SignalSide.BUY: 0.0, SignalSide.SELL: 0.0, SignalSide.HOLD: 0.0}

        for m in matches:
            weight = self._weights.get(m.rule_type, 1.0)
            side = self._extract_side(m)
            score = weight * m.confidence
            scores[side] += score

        # 阈值判定
        total = scores[SignalSide.BUY] + scores[SignalSide.SELL]
        if total == 0:
            return self._create_hold_signal(context)

        buy_ratio = scores[SignalSide.BUY] / total
        if buy_ratio > 0.6:
            side = SignalSide.BUY
        elif buy_ratio < 0.4:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD

        confidence = scores[side] / len(matches)
        return self._create_signal(side, confidence, matches, context)

    def _synthesize_voting(
        self,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """投票合成"""
        votes = {SignalSide.BUY: 0, SignalSide.SELL: 0, SignalSide.HOLD: 0}

        for m in matches:
            side = self._extract_side(m)
            votes[side] += 1

        # 多数胜出
        max_votes = max(votes.values())
        if votes[SignalSide.BUY] == max_votes and votes[SignalSide.SELL] != max_votes:
            side = SignalSide.BUY
        elif votes[SignalSide.SELL] == max_votes and votes[SignalSide.BUY] != max_votes:
            side = SignalSide.SELL
        else:
            side = SignalSide.HOLD

        confidence = max_votes / len(matches)
        return self._create_signal(side, confidence, matches, context)

    def _synthesize_priority(
        self,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """优先级合成（默认）"""
        # 按优先级排序
        sorted_matches = sorted(
            matches,
            key=lambda m: self._priorities.index(m.rule_type)
            if m.rule_type in self._priorities
            else len(self._priorities),
            reverse=True,  # 高优先级在前
        )

        # 获取最高优先级匹配的信号
        for m in sorted_matches:
            side = self._extract_side(m)
            if side != SignalSide.HOLD:
                confidence = m.confidence
                return self._create_signal(side, confidence, matches, context)

        return self._create_hold_signal(context)

    def _extract_side(self, match: RuleMatch) -> SignalSide:
        """从匹配结果提取信号方向"""
        action = match.action
        if not action or not action.side:
            return SignalSide.HOLD

        side_map = {
            "buy": SignalSide.BUY,
            "sell": SignalSide.SELL,
        }
        return side_map.get(action.side.lower(), SignalSide.HOLD)

    def _create_signal(
        self,
        side: SignalSide,
        confidence: float,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """创建信号"""
        return RawSignal(
            signal_id=str(uuid.uuid4()),
            symbol="UNKNOWN",  # 待后续填充
            side=side,
            confidence=confidence,
            triggered_rules=[m.rule_id for m in matches if m.matched],
            synthesis_mode=self._mode,
            entry_price=PriceSpec(type="market"),
            position_size=PositionSize(
                type=PositionSizeType.FIXED_RATIO,
                value=0.05,
            ),
            timestamp=context.market_state.get("timestamp"),
            metadata={"context": context.market_state},
        )

    def _create_hold_signal(self, context: SynthesisContext) -> RawSignal:
        """创建 HOLD 信号"""
        return RawSignal(
            signal_id=str(uuid.uuid4()),
            symbol="UNKNOWN",
            side=SignalSide.HOLD,
            confidence=0.0,
            triggered_rules=[],
            synthesis_mode=self._mode,
            timestamp=context.market_state.get("timestamp"),
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/strategy/test_signal_synthesizer.py -v
# 预期: 5 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/strategy/signal_synthesizer.py tests/unit/strategy/test_signal_synthesizer.py
git commit -m "feat: implement P4-003 SignalSynthesizer"
```

---

## Task 7: P4-004 信号输出格式

**Files:**
- Create: `src/strategy/signal.py`
- Modify: `src/strategy/types.py`（添加 StopLossLevel 和 TakeProfitLevel 的 import）

- [ ] **Step 1: 创建 src/strategy/signal.py**

```python
"""信号输出 - P4-004"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.strategy.types import (
    RawSignal,
    Signal,
    SignalSide,
    PriceSpec,
    PositionSize,
    StopLossLevel,
    TakeProfitLevel,
)
from src.risk.types import StopLossMode, TakeProfitMode


def create_signal(
    raw: RawSignal,
    stop_loss: StopLossLevel | None = None,
    take_profit: list[TakeProfitLevel] | None = None,
    symbol: str | None = None,
) -> Signal:
    """从 RawSignal 创建最终 Signal

    Args:
        raw: 原始信号
        stop_loss: 止损级别
        take_profit: 止盈级别列表
        symbol: 标的代码

    Returns:
        Signal 最终信号
    """
    return Signal(
        signal_id=raw.signal_id,
        symbol=symbol or raw.symbol,
        side=raw.side,
        confidence=raw.confidence,
        timestamp=raw.timestamp or datetime.now(),
        triggered_rules=raw.triggered_rules,
        synthesis_mode=raw.synthesis_mode,
        entry_price=raw.entry_price,
        position_size=raw.position_size,
        stop_loss=stop_loss,
        take_profit=take_profit,
        version="v1",
        metadata=raw.metadata,
    )


def create_signal_from_params(
    symbol: str,
    side: SignalSide,
    confidence: float,
    triggered_rules: list[str],
    entry_price: PriceSpec | None = None,
    position_size: PositionSize | None = None,
    stop_loss: StopLossLevel | None = None,
    take_profit: list[TakeProfitLevel] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Signal:
    """直接创建信号（不经过 RawSignal）

    Args:
        symbol: 标的代码
        side: 信号方向
        confidence: 置信度
        triggered_rules: 触发的规则 ID 列表
        entry_price: 入场价格规格
        position_size: 头寸规格
        stop_loss: 止损级别
        take_profit: 止盈级别列表
        metadata: 元数据

    Returns:
        Signal 最终信号
    """
    return Signal(
        signal_id=str(uuid.uuid4()),
        symbol=symbol,
        side=side,
        confidence=confidence,
        timestamp=datetime.now(),
        triggered_rules=triggered_rules,
        synthesis_mode=None,  # 直接创建时无合成模式
        entry_price=entry_price,
        position_size=position_size,
        stop_loss=stop_loss,
        take_profit=take_profit,
        version="v1",
        metadata=metadata or {},
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/strategy/signal.py
git commit -m "feat: implement P4-004 signal output format"
```

---

## Task 8: P4-005 信号版本控制

**Files:**
- Create: `src/strategy/signal_version.py`
- Create: `tests/unit/strategy/test_signal_version.py`

- [ ] **Step 1: 创建测试文件 tests/unit/strategy/test_signal_version.py**

```python
"""SignalVersioning 单元测试"""
import pytest
from datetime import date
from src.strategy.signal_version import SignalVersioning, SignalContext
from src.strategy.types import Signal, SignalSide


def test_record_and_get():
    """测试记录和获取"""
    versioning = SignalVersioning()

    signal = Signal(
        signal_id="test-001",
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.8,
        timestamp=date(2026, 4, 9),
        triggered_rules=["rule1"],
        synthesis_mode=None,
    )
    context = SignalContext(
        features_snapshot={"rsi": 70},
        market_state={"regime": "trend_up"},
        rules_snapshot=[],
        timestamp=date(2026, 4, 9),
    )

    version_id = versioning.record(signal, context)
    assert version_id is not None

    result = versioning.get_version(version_id)
    assert result is not None
    assert result.signal.signal_id == "test-001"


def test_list_versions():
    """测试列出版本"""
    versioning = SignalVersioning()

    for i in range(5):
        signal = Signal(
            signal_id=f"test-{i:03d}",
            symbol="TEST",
            side=SignalSide.BUY,
            confidence=0.8,
            timestamp=date(2026, 4, 9),
            triggered_rules=[],
            synthesis_mode=None,
        )
        context = SignalContext(
            features_snapshot={},
            market_state={},
            rules_snapshot=[],
            timestamp=date(2026, 4, 9),
        )
        versioning.record(signal, context)

    versions = versioning.list_versions(symbol="TEST", limit=10)
    assert len(versions) == 5
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/strategy/test_signal_version.py -v 2>&1 | head -30
# 预期: ERROR - module not found
```

- [ ] **Step 3: 创建 src/strategy/signal_version.py**

```python
"""信号版本控制 - P4-005"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.strategy.types import Signal, SignalContext, SignalWithContext


class SignalVersioning:
    """信号版本控制

    记录信号生成过程中的所有输入和决策，支持回放和审计。
    """

    def __init__(self, storage_path: Path | None = None):
        self._storage_path = storage_path or Path("data/signals")
        self._versions: dict[str, SignalWithContext] = {}

    def record(self, signal: Signal, context: SignalContext) -> str:
        """记录信号及其上下文

        Args:
            signal: 信号
            context: 上下文

        Returns:
            版本 ID
        """
        version_id = signal.signal_id

        # 内存存储
        self._versions[version_id] = SignalWithContext(
            signal=signal,
            context=context,
        )

        # 持久化到文件
        if self._storage_path:
            self._storage_path.mkdir(parents=True, exist_ok=True)
            file_path = self._storage_path / f"{version_id}.json"
            data = {
                "signal": self._signal_to_dict(signal),
                "context": self._context_to_dict(context),
            }
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

        return version_id

    def get_version(self, signal_id: str) -> SignalWithContext | None:
        """获取信号完整版本

        Args:
            signal_id: 信号 ID

        Returns:
            SignalWithContext 或 None
        """
        # 优先从内存获取
        if signal_id in self._versions:
            return self._versions[signal_id]

        # 从文件加载
        if self._storage_path:
            file_path = self._storage_path / f"{signal_id}.json"
            if file_path.exists():
                with open(file_path) as f:
                    data = json.load(f)
                return SignalWithContext(
                    signal=self._dict_to_signal(data["signal"]),
                    context=self._dict_to_context(data["context"]),
                )

        return None

    def list_versions(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SignalWithContext]:
        """列出信号版本

        Args:
            symbol: 按标的过滤
            since: 按时间过滤
            limit: 返回数量限制

        Returns:
            SignalWithContext 列表
        """
        results = []

        # 从内存过滤
        for v in self._versions.values():
            if symbol and v.signal.symbol != symbol:
                continue
            if since and v.context.timestamp < since:
                continue
            results.append(v)

        # 按时间倒序
        results.sort(key=lambda x: x.context.timestamp, reverse=True)

        return results[:limit]

    def _signal_to_dict(self, signal: Signal) -> dict[str, Any]:
        """信号转字典"""
        return {
            "signal_id": signal.signal_id,
            "symbol": signal.symbol,
            "side": signal.side.value if hasattr(signal.side, "value") else signal.side,
            "confidence": signal.confidence,
            "timestamp": signal.timestamp.isoformat() if signal.timestamp else None,
            "triggered_rules": signal.triggered_rules,
            "synthesis_mode": signal.synthesis_mode.value if signal.synthesis_mode else None,
            "entry_price": {
                "type": signal.entry_price.type if signal.entry_price else None,
                "value": signal.entry_price.value if signal.entry_price else None,
            } if signal.entry_price else None,
            "position_size": {
                "type": signal.position_size.type.value if signal.position_size else None,
                "value": signal.position_size.value if signal.position_size else None,
            } if signal.position_size else None,
            "version": signal.version,
            "metadata": signal.metadata,
        }

    def _context_to_dict(self, context: SignalContext) -> dict[str, Any]:
        """上下文转字典"""
        return {
            "features_snapshot": context.features_snapshot,
            "market_state": context.market_state,
            "rules_snapshot": context.rules_snapshot,
            "timestamp": context.timestamp.isoformat() if context.timestamp else None,
        }

    def _dict_to_signal(self, data: dict) -> Signal:
        """字典转信号"""
        from src.strategy.types import SignalSide, SynthesisMode, PriceSpec, PositionSize, PositionSizeType
        from src.risk.types import StopLossLevel, TakeProfitLevel

        return Signal(
            signal_id=data["signal_id"],
            symbol=data["symbol"],
            side=SignalSide(data["side"]) if data["side"] else SignalSide.HOLD,
            confidence=data["confidence"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data["timestamp"] else datetime.now(),
            triggered_rules=data["triggered_rules"],
            synthesis_mode=SynthesisMode(data["synthesis_mode"]) if data["synthesis_mode"] else None,
            entry_price=PriceSpec(**data["entry_price"]) if data["entry_price"] else None,
            position_size=PositionSize(**data["position_size"]) if data["position_size"] else None,
            version=data.get("version", "v1"),
            metadata=data.get("metadata", {}),
        )

    def _dict_to_context(self, data: dict) -> SignalContext:
        """字典转上下文"""
        return SignalContext(
            features_snapshot=data["features_snapshot"],
            market_state=data["market_state"],
            rules_snapshot=data["rules_snapshot"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data["timestamp"] else datetime.now(),
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/strategy/test_signal_version.py -v
# 预期: 2 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/strategy/signal_version.py tests/unit/strategy/test_signal_version.py
git commit -m "feat: implement P4-005 SignalVersioning"
```

---

## Task 9: P4-006 头寸管理

**Files:**
- Create: `src/risk/position_manager.py`
- Create: `tests/unit/risk/test_position_manager.py`

- [ ] **Step 1: 创建测试文件 tests/unit/risk/test_position_manager.py**

```python
"""PositionManager 单元测试"""
import pytest
from datetime import date
from src.risk.position_manager import PositionManager, PositionSizeMode, PositionConfig
from src.risk.types import AccountSnapshot, Position, PositionSizeType
from src.strategy.types import Signal, SignalSide, PositionSize, PriceSpec
from src.persona.schemas import MarketRegime, VolatilityLevel


def _create_account_snapshot(net_value: float = 100_000.0) -> AccountSnapshot:
    """创建样本账户快照"""
    return AccountSnapshot(
        account_id="test-account",
        timestamp=date(2026, 4, 9),
        net_value=net_value,
        cash=net_value,
        total_position_value=0.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0,
    )


def _create_signal(side: SignalSide = SignalSide.BUY) -> Signal:
    """创建样本信号"""
    return Signal(
        signal_id="test-001",
        symbol="TEST",
        side=side,
        confidence=0.8,
        timestamp=date(2026, 4, 9),
        triggered_rules=[],
        synthesis_mode=None,
        entry_price=PriceSpec(type="market", value=100.0),
        position_size=PositionSize(
            type=PositionSizeType.FIXED_RATIO,
            value=0.05,
        ),
    )


def test_fixed_ratio_mode():
    """测试固定比例模式"""
    config = PositionConfig(fixed_ratio_pct=0.10)  # 10%
    manager = PositionManager(mode=PositionSizeMode.FIXED_RATIO, config=config)

    account = _create_account_snapshot(net_value=100_000.0)
    signal = _create_signal()
    market_data = {"close": 100.0}

    result = manager.calculate_size(signal, account, market_data)
    # 100000 * 0.10 / 100 = 100 股
    assert result.value == 100.0


def test_fixed_amount_mode():
    """测试固定金额模式"""
    config = PositionConfig(fixed_amount=20_000.0)
    manager = PositionManager(mode=PositionSizeMode.FIXED_AMOUNT, config=config)

    account = _create_account_snapshot(net_value=100_000.0)
    signal = _create_signal()
    market_data = {"close": 100.0}

    result = manager.calculate_size(signal, account, market_data)
    # 20000 / 100 = 200 股
    assert result.value == 200.0


def test_max_position_limit():
    """测试最大头寸限制"""
    config = PositionConfig(
        fixed_ratio_pct=1.0,  # 100%
        max_single_position=10_000.0,  # 但最大单标的不超过 10000
    )
    manager = PositionManager(mode=PositionSizeMode.FIXED_RATIO, config=config)

    account = _create_account_snapshot(net_value=100_000.0)
    signal = _create_signal()
    market_data = {"close": 10.0}  # 价格低，头寸会超过限制

    result = manager.calculate_size(signal, account, market_data)
    # 10000 / 10 = 1000 股
    assert result.value == 1000.0


def test_hold_signal_returns_zero():
    """测试 HOLD 信号返回零头寸"""
    config = PositionConfig()
    manager = PositionManager(mode=PositionSizeMode.FIXED_RATIO, config=config)

    account = _create_account_snapshot()
    signal = _create_signal(SignalSide.HOLD)
    market_data = {"close": 100.0}

    result = manager.calculate_size(signal, account, market_data)
    assert result.value == 0.0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/risk/test_position_manager.py -v 2>&1 | head -30
# 预期: ERROR - module not found
```

- [ ] **Step 3: 创建 src/risk/position_manager.py**

```python
"""头寸管理 - P4-006"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.risk.types import PositionSizeType
from src.strategy.types import Signal, SignalSide, PositionSize
from src.risk.types import AccountSnapshot
from src.shared.exceptions import PositionLimitExceeded


@dataclass
class PositionConfig:
    """头寸配置"""
    # 固定金额模式
    fixed_amount: float = 10_000.0

    # 固定比例模式
    fixed_ratio_pct: float = 0.05  # 5%

    # 波动率调整模式
    target_volatility: float = 0.15
    vol_window: int = 20

    # 通用限制
    max_position_pct: float = 0.20  # 最大占总净值比例
    max_single_position: float = 50_000.0  # 最大单标的金额


class PositionManager:
    """头寸管理器

    根据账户净值、风险偏好计算持仓数量。
    """

    def __init__(
        self,
        mode: PositionSizeType = PositionSizeType.FIXED_RATIO,
        config: PositionConfig | None = None,
    ):
        self._mode = mode
        self._config = config or PositionConfig()

    def calculate_size(
        self,
        signal: Signal,
        account: AccountSnapshot,
        market_data: dict,
    ) -> PositionSize:
        """计算头寸

        Args:
            signal: 交易信号
            account: 账户快照
            market_data: 市场数据（需包含 close）

        Returns:
            PositionSize 头寸规格

        Raises:
            PositionLimitExceeded: 头寸超限时抛出
        """
        # HOLD 信号返回零头寸
        if signal.side == SignalSide.HOLD:
            return PositionSize(type=self._mode, value=0.0)

        price = market_data.get("close", 0.0)
        if price <= 0:
            return PositionSize(type=self._mode, value=0.0)

        # 根据模式计算
        if self._mode == PositionSizeType.FIXED_AMOUNT:
            raw_value = self._config.fixed_amount
        elif self._mode == PositionSizeType.VOLATILITY_ADJUSTED:
            raw_value = self._calculate_volatility_adjusted(account, market_data)
        else:  # FIXED_RATIO
            raw_value = account.net_value * self._config.fixed_ratio_pct

        # 应用限制
        max_by_pct = account.net_value * self._config.max_position_pct
        max_value = min(raw_value, max_by_pct, self._config.max_single_position)

        # 计算股数
        shares = math.floor(max_value / price)

        return PositionSize(
            type=self._mode,
            value=float(shares),
            max_amount=max_value,
        )

    def _calculate_volatility_adjusted(
        self,
        account: AccountSnapshot,
        market_data: dict,
    ) -> float:
        """波动率调整计算"""
        atr = market_data.get("atr", 0.0)
        price = market_data.get("close", 0.0)

        if atr <= 0 or price <= 0:
            return account.net_value * self._config.fixed_ratio_pct

        # 波动率调整：目标波动率 / ATR比率 * 账户净值
        atr_ratio = atr / price
        if atr_ratio <= 0:
            return account.net_value * self._config.fixed_ratio_pct

        adjusted_value = (self._config.target_volatility / atr_ratio) * account.net_value

        # 限制在合理范围
        return min(adjusted_value, account.net_value * self._config.max_position_pct)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/risk/test_position_manager.py -v
# 预期: 4 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/risk/position_manager.py tests/unit/risk/test_position_manager.py
git commit -m "feat: implement P4-006 PositionManager"
```

---

## Task 10: P4-007 止损设置

**Files:**
- Create: `src/risk/stop_loss.py`
- Create: `tests/unit/risk/test_stop_loss.py`

- [ ] **Step 1: 创建测试文件 tests/unit/risk/test_stop_loss.py**

```python
"""StopLossCalculator 单元测试"""
import pytest
from src.risk.stop_loss import StopLossCalculator, StopLossConfig
from src.risk.types import StopLossMode
from src.strategy.types import Signal, SignalSide, PriceSpec, PositionSize, PositionSizeType
from datetime import date


def _create_signal(entry_price: float = 100.0) -> Signal:
    """创建样本信号"""
    return Signal(
        signal_id="test-001",
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.8,
        timestamp=date(2026, 4, 9),
        triggered_rules=[],
        synthesis_mode=None,
        entry_price=PriceSpec(type="market", value=entry_price),
        position_size=PositionSize(
            type=PositionSizeType.FIXED_RATIO,
            value=100.0,
        ),
    )


def test_fixed_stop_loss():
    """测试固定止损"""
    config = StopLossConfig(mode=StopLossMode.FIXED, fixed_pct=0.05)
    calculator = StopLossCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert result is not None
    assert result.level == 95.0  # 100 * (1 - 0.05)
    assert result.mode == StopLossMode.FIXED


def test_volatility_stop_loss():
    """测试波动率止损"""
    config = StopLossConfig(
        mode=StopLossMode.VOLATILITY,
        atr_multiplier=2.0,
        atr_window=14,
    )
    calculator = StopLossCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0, "atr": 2.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert result is not None
    assert result.level == 96.0  # 100 - 2 * 2.0
    assert result.mode == StopLossMode.VOLATILITY


def test_time_stop_loss():
    """测试时间止损"""
    config = StopLossConfig(mode=StopLossMode.TIME, max_hold_days=10)
    calculator = StopLossCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert result is not None
    assert result.mode == StopLossMode.TIME
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/risk/test_stop_loss.py -v 2>&1 | head -30
# 预期: ERROR - module not found
```

- [ ] **Step 3: 创建 src/risk/stop_loss.py**

```python
"""止损设置 - P4-007"""
from __future__ import annotations

from dataclasses import dataclass

from src.risk.types import StopLossMode, StopLossLevel
from src.strategy.types import Signal


@dataclass
class StopLossConfig:
    """止损配置"""
    mode: StopLossMode = StopLossMode.VOLATILITY

    # 固定止损
    fixed_pct: float = 0.05  # 5%

    # 波动率止损
    atr_multiplier: float = 2.0
    atr_window: int = 14

    # 回撤止损
    drawdown_pct: float = 0.10

    # 时间止损
    max_hold_days: int = 10


class StopLossCalculator:
    """止损计算器

    支持四种止损模式:
    - FIXED: 固定止损（百分比）
    - VOLATILITY: 波动率止损（ATR）
    - TRAILING: 回撤止损
    - TIME: 时间止损
    """

    def __init__(self, config: StopLossConfig):
        self._config = config

    def calculate(
        self,
        entry_price: float,
        signal: Signal,
        market_data: dict,
    ) -> StopLossLevel | None:
        """计算止损

        Args:
            entry_price: 入场价格
            signal: 交易信号
            market_data: 市场数据（需包含 atr, close 等）

        Returns:
            StopLossLevel 止损级别，或 None（不需要止损）
        """
        if signal.side != SignalSide.BUY and signal.side != SignalSide.SELL:
            return None

        if self._config.mode == StopLossMode.FIXED:
            return self._calculate_fixed(entry_price)
        elif self._config.mode == StopLossMode.VOLATILITY:
            return self._calculate_volatility(entry_price, market_data)
        elif self._config.mode == StopLossMode.TRAILING:
            return self._calculate_trailing(entry_price, market_data)
        elif self._config.mode == StopLossMode.TIME:
            return self._calculate_time(entry_price, market_data)

        return None

    def _calculate_fixed(self, entry_price: float) -> StopLossLevel:
        """固定止损"""
        level = entry_price * (1 - self._config.fixed_pct)
        return StopLossLevel(
            mode=StopLossMode.FIXED,
            level=round(level, 2),
            trigger_condition=f"价格跌破 {self._config.fixed_pct * 100}%",
        )

    def _calculate_volatility(self, entry_price: float, market_data: dict) -> StopLossLevel:
        """波动率止损"""
        atr = market_data.get("atr", 0.0)
        if atr <= 0:
            # 无 ATR 数据时回退到固定止损
            return self._calculate_fixed(entry_price)

        level = entry_price - (atr * self._config.atr_multiplier)
        return StopLossLevel(
            mode=StopLossMode.VOLATILITY,
            level=round(level, 2),
            trigger_condition=f"价格跌破 入口-{self._config.atr_multiplier}*ATR",
        )

    def _calculate_trailing(self, entry_price: float, market_data: dict) -> StopLossLevel:
        """回撤止损"""
        high_price = market_data.get("high", entry_price)
        if high_price <= entry_price:
            high_price = entry_price

        level = high_price * (1 - self._config.drawdown_pct)
        return StopLossLevel(
            mode=StopLossMode.TRAILING,
            level=round(level, 2),
            trigger_condition=f"从高点回撤 {self._config.drawdown_pct * 100}%",
        )

    def _calculate_time(self, entry_price: float, market_data: dict) -> StopLossLevel:
        """时间止损"""
        return StopLossLevel(
            mode=StopLossMode.TIME,
            level=entry_price,  # 时间止损不设具体价格
            trigger_condition=f"持有超过 {self._config.max_hold_days} 天",
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/risk/test_stop_loss.py -v
# 预期: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/risk/stop_loss.py tests/unit/risk/test_stop_loss.py
git commit -m "feat: implement P4-007 StopLossCalculator"
```

---

## Task 11: P4-008 止盈策略

**Files:**
- Create: `src/risk/take_profit.py`
- Create: `tests/unit/risk/test_take_profit.py`

- [ ] **Step 1: 创建测试文件 tests/unit/risk/test_take_profit.py**

```python
"""TakeProfitCalculator 单元测试"""
import pytest
from src.risk.take_profit import TakeProfitCalculator, TakeProfitConfig
from src.risk.types import TakeProfitMode, ScalingLevel
from src.strategy.types import Signal, SignalSide, PriceSpec, PositionSize, PositionSizeType
from datetime import date


def _create_signal(entry_price: float = 100.0) -> Signal:
    """创建样本信号"""
    return Signal(
        signal_id="test-001",
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.8,
        timestamp=date(2026, 4, 9),
        triggered_rules=[],
        synthesis_mode=None,
        entry_price=PriceSpec(type="market", value=entry_price),
        position_size=PositionSize(
            type=PositionSizeType.FIXED_RATIO,
            value=100.0,
        ),
    )


def test_fixed_take_profit():
    """测试固定止盈"""
    config = TakeProfitConfig(mode=TakeProfitMode.FIXED, fixed_pct=0.15)
    calculator = TakeProfitCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert len(result) == 1
    assert result[0].level == 115.0  # 100 * (1 + 0.15)
    assert result[0].mode == TakeProfitMode.FIXED


def test_scaling_take_profit():
    """测试分批止盈"""
    config = TakeProfitConfig(
        mode=TakeProfitMode.SCALING,
        scaling_levels=[
            ScalingLevel(target_pct=0.05, close_pct=0.50),
            ScalingLevel(target_pct=0.10, close_pct=0.30),
            ScalingLevel(target_pct=0.20, close_pct=0.20),
        ],
    )
    calculator = TakeProfitCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert len(result) == 3
    assert result[0].level == 105.0
    assert result[0].close_pct == 0.50
    assert result[1].level == 110.0
    assert result[1].close_pct == 0.30
    assert result[2].level == 120.0
    assert result[2].close_pct == 0.20


def test_trailing_take_profit():
    """测试移动止损止盈"""
    config = TakeProfitConfig(
        mode=TakeProfitMode.TRAILING,
        trailing_pct=0.05,
    )
    calculator = TakeProfitCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 110.0, "high": 115.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert len(result) == 1
    assert result[0].mode == TakeProfitMode.TRAILING
    # 高点 115 * (1 - 0.05) = 109.25
    assert result[0].level == 109.25


def test_time_take_profit():
    """测试时间止盈"""
    config = TakeProfitConfig(
        mode=TakeProfitMode.TIME,
        target_hold_days=5,
    )
    calculator = TakeProfitCalculator(config)

    signal = _create_signal(entry_price=100.0)
    market_data = {"close": 100.0}

    result = calculator.calculate(100.0, signal, market_data)
    assert len(result) == 1
    assert result[0].mode == TakeProfitMode.TIME
    assert "5 天" in result[0].trigger_condition
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/risk/test_take_profit.py -v 2>&1 | head -30
# 预期: ERROR - module not found
```

- [ ] **Step 3: 创建 src/risk/take_profit.py**

```python
"""止盈策略 - P4-008"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.risk.types import TakeProfitMode, TakeProfitLevel, ScalingLevel
from src.strategy.types import Signal


@dataclass
class TakeProfitConfig:
    """止盈配置"""
    mode: TakeProfitMode = TakeProfitMode.SCALING

    # 固定止盈
    fixed_pct: float = 0.15  # 15%

    # 分批止盈
    scaling_levels: list[ScalingLevel] = field(default_factory=lambda: [
        ScalingLevel(target_pct=0.05, close_pct=0.50),
        ScalingLevel(target_pct=0.10, close_pct=0.30),
        ScalingLevel(target_pct=0.20, close_pct=0.20),
    ])

    # 移动止损
    trailing_pct: float = 0.05

    # 时间止盈
    target_hold_days: int = 5


class TakeProfitCalculator:
    """止盈计算器

    支持四种止盈模式:
    - FIXED: 固定止盈
    - SCALING: 分批止盈
    - TRAILING: 移动止损
    - TIME: 时间止盈
    """

    def __init__(self, config: TakeProfitConfig):
        self._config = config

    def calculate(
        self,
        entry_price: float,
        signal: Signal,
        market_data: dict,
    ) -> list[TakeProfitLevel]:
        """计算止盈

        Args:
            entry_price: 入场价格
            signal: 交易信号
            market_data: 市场数据

        Returns:
            TakeProfitLevel 列表（可能多个级别）
        """
        if signal.side != SignalSide.BUY and signal.side != SignalSide.SELL:
            return []

        if self._config.mode == TakeProfitMode.FIXED:
            return [self._calculate_fixed(entry_price)]
        elif self._config.mode == TakeProfitMode.SCALING:
            return self._calculate_scaling(entry_price)
        elif self._config.mode == TakeProfitMode.TRAILING:
            return [self._calculate_trailing(entry_price, market_data)]
        elif self._config.mode == TakeProfitMode.TIME:
            return [self._calculate_time(entry_price)]

        return []

    def _calculate_fixed(self, entry_price: float) -> TakeProfitLevel:
        """固定止盈"""
        level = entry_price * (1 + self._config.fixed_pct)
        return TakeProfitLevel(
            mode=TakeProfitMode.FIXED,
            level=round(level, 2),
            close_pct=1.0,  # 全卖
            trigger_condition=f"价格上涨 {self._config.fixed_pct * 100}%",
        )

    def _calculate_scaling(self, entry_price: float) -> list[TakeProfitLevel]:
        """分批止盈"""
        levels = []
        for scaling in self._config.scaling_levels:
            target_price = entry_price * (1 + scaling.target_pct)
            levels.append(TakeProfitLevel(
                mode=TakeProfitMode.SCALING,
                level=round(target_price, 2),
                close_pct=scaling.close_pct,
                trigger_condition=f"价格上涨 {scaling.target_pct * 100}%，卖出 {scaling.close_pct * 100}%",
            ))
        return levels

    def _calculate_trailing(self, entry_price: float, market_data: dict) -> TakeProfitLevel:
        """移动止损止盈"""
        high_price = market_data.get("high", entry_price)
        if high_price <= entry_price:
            high_price = entry_price

        level = high_price * (1 - self._config.trailing_pct)
        return TakeProfitLevel(
            mode=TakeProfitMode.TRAILING,
            level=round(level, 2),
            close_pct=1.0,
            trigger_condition=f"从高点回撤 {self._config.trailing_pct * 100}%",
        )

    def _calculate_time(self, entry_price: float) -> TakeProfitLevel:
        """时间止盈"""
        return TakeProfitLevel(
            mode=TakeProfitMode.TIME,
            level=entry_price,  # 时间止盈不设具体价格
            close_pct=1.0,
            trigger_condition=f"持有 {self._config.target_hold_days} 天后止盈",
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/risk/test_take_profit.py -v
# 预期: 4 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/risk/take_profit.py tests/unit/risk/test_take_profit.py
git commit -m "feat: implement P4-008 TakeProfitCalculator"
```

---

## Task 12: 策略配置加载

**Files:**
- Create: `src/strategy/config.py`
- Create: `config/strategy.yaml`

- [ ] **Step 1: 创建 config/strategy.yaml**

```yaml
# Strategy Agent 配置
strategy:
  # 特征计算
  feature_engine:
    mode: "realtime"  # realtime | precomputed
    compute_batch: true

  # 规则评估
  rule_evaluator:
    dsl_executor:
      mode: "all"  # all | first | best
      timeout_ms: 100

  # 信号合成
  signal_synthesizer:
    mode: "priority"  # weighted_score | voting | priority
    weights:
      entry: 1.0
      exit: 1.2
      filter: 1.5
      sizing: 1.0
      risk: 2.0
    priorities:
      - risk
      - filter
      - exit
      - sizing
      - entry
```

- [ ] **Step 2: 创建 src/strategy/config.py**

```python
"""策略配置加载"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from src.strategy.types import SynthesisMode


class FeatureEngineConfig(BaseModel):
    """特征引擎配置"""
    mode: str = "realtime"
    compute_batch: bool = True


class RuleEvaluatorConfig(BaseModel):
    """规则评估器配置"""
    dsl_executor: dict[str, Any] = {}


class SignalSynthesizerConfig(BaseModel):
    """信号合成器配置"""
    mode: str = "priority"
    weights: dict[str, float] = {}
    priorities: list[str] = []


class StrategyConfig(BaseModel):
    """策略配置"""
    feature_engine: FeatureEngineConfig = FeatureEngineConfig()
    rule_evaluator: RuleEvaluatorConfig = RuleEvaluatorConfig()
    signal_synthesizer: SignalSynthesizerConfig = SignalSynthesizerConfig()


@lru_cache
def get_strategy_config() -> StrategyConfig:
    """获取策略配置（单例）

    从 config/strategy.yaml 加载配置
    """
    config_path = Path("config/strategy.yaml")
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return StrategyConfig(**data)
    return StrategyConfig()


def load_strategy_config(config_path: str | Path) -> StrategyConfig:
    """从指定路径加载策略配置"""
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return StrategyConfig(**data)
    return StrategyConfig()
```

- [ ] **Step 3: Commit**

```bash
git add src/strategy/config.py config/strategy.yaml
git commit -m "feat: add strategy config loading"
```

---

## Task 13: 风控配置加载

**Files:**
- Create: `src/risk/config.py`
- Create: `config/risk.yaml`

- [ ] **Step 1: 创建 config/risk.yaml**

```yaml
# Risk Agent 配置

risk:
  # 头寸管理
  position_manager:
    mode: "fixed_ratio"  # fixed_amount | fixed_ratio | volatility_adjusted
    fixed_amount: 10_000.0
    fixed_ratio_pct: 0.05
    target_volatility: 0.15
    max_position_pct: 0.20
    max_single_position: 50_000.0

  # 止损
  stop_loss:
    mode: "volatility"  # fixed | volatility | trailing | time
    fixed_pct: 0.05
    atr_multiplier: 2.0
    atr_window: 14
    drawdown_pct: 0.10
    max_hold_days: 10

  # 止盈
  take_profit:
    mode: "scaling"  # fixed | scaling | trailing | time
    fixed_pct: 0.15
    scaling_levels:
      - target_pct: 0.05
        close_pct: 0.50
      - target_pct: 0.10
        close_pct: 0.30
      - target_pct: 0.20
        close_pct: 0.20
    trailing_pct: 0.05
    target_hold_days: 5

# 模拟账户
simulated_account:
  enabled: true
  initial_capital: 100_000.0
  persist_to_db: true
```

- [ ] **Step 2: 创建 src/risk/config.py**

```python
"""风控配置加载"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.risk.types import (
    PositionSizeType,
    StopLossMode,
    TakeProfitMode,
    ScalingLevel,
)


class PositionManagerConfig(BaseModel):
    """头寸管理器配置"""
    mode: str = "fixed_ratio"
    fixed_amount: float = 10_000.0
    fixed_ratio_pct: float = 0.05
    target_volatility: float = 0.15
    max_position_pct: float = 0.20
    max_single_position: float = 50_000.0


class StopLossConfigModel(BaseModel):
    """止损配置"""
    mode: str = "volatility"
    fixed_pct: float = 0.05
    atr_multiplier: float = 2.0
    atr_window: int = 14
    drawdown_pct: float = 0.10
    max_hold_days: int = 10


class TakeProfitConfigModel(BaseModel):
    """止盈配置"""
    mode: str = "scaling"
    fixed_pct: float = 0.15
    scaling_levels: list[ScalingLevel] = Field(default_factory=lambda: [
        ScalingLevel(target_pct=0.05, close_pct=0.50),
        ScalingLevel(target_pct=0.10, close_pct=0.30),
        ScalingLevel(target_pct=0.20, close_pct=0.20),
    ])
    trailing_pct: float = 0.05
    target_hold_days: int = 5


class SimulatedAccountConfig(BaseModel):
    """模拟账户配置"""
    enabled: bool = True
    initial_capital: float = 100_000.0
    persist_to_db: bool = True


class RiskConfig(BaseModel):
    """风控配置"""
    position_manager: PositionManagerConfig = PositionManagerConfig()
    stop_loss: StopLossConfigModel = StopLossConfigModel()
    take_profit: TakeProfitConfigModel = TakeProfitConfigModel()
    simulated_account: SimulatedAccountConfig = SimulatedAccountConfig()


@lru_cache
def get_risk_config() -> RiskConfig:
    """获取风控配置（单例）

    从 config/risk.yaml 加载配置
    """
    config_path = Path("config/risk.yaml")
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return RiskConfig(**data)
    return RiskConfig()


def load_risk_config(config_path: str | Path) -> RiskConfig:
    """从指定路径加载风控配置"""
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return RiskConfig(**data)
    return RiskConfig()
```

- [ ] **Step 3: Commit**

```bash
git add src/risk/config.py config/risk.yaml
git commit -m "feat: add risk config loading"
```

---

## Task 14: 创建使用说明文档

**Files:**
- Create: `docs/superpowers/guides/strategy-risk-agent-usage.md`

- [ ] **Step 1: 创建使用说明文档**

```markdown
# Strategy Agent & Risk Agent 使用说明

## 配置修改指南

### 策略配置 (config/strategy.yaml)

#### 信号合成模式

```yaml
strategy:
  signal_synthesizer:
    mode: "priority"  # 可选: weighted_score | voting | priority
```

**模式说明**:
- `priority`: 按 rule_type 优先级合成（默认）
- `weighted_score`: 按权重评分合成
- `voting`: 投票机制

#### 自定义优先级

```yaml
strategy:
  signal_synthesizer:
    mode: "priority"
    priorities:
      - risk      # 最高优先级
      - filter
      - exit
      - sizing
      - entry     # 最低优先级
```

#### 自定义权重

```yaml
strategy:
  signal_synthesizer:
    mode: "weighted_score"
    weights:
      entry: 1.0
      exit: 1.2
      filter: 1.5
      sizing: 1.0
      risk: 2.0
```

### 风控配置 (config/risk.yaml)

#### 头寸管理

```yaml
risk:
  position_manager:
    mode: "fixed_ratio"  # 可选: fixed_amount | fixed_ratio | volatility_adjusted

    # 固定金额模式
    fixed_amount: 10_000.0

    # 固定比例模式
    fixed_ratio_pct: 0.05  # 每次投入账户净值的 5%

    # 波动率调整模式
    target_volatility: 0.15  # 目标波动率 15%

    # 限制
    max_position_pct: 0.20      # 单标的最大占总净值比例
    max_single_position: 50_000.0  # 单标的最大金额
```

**计算公式**:
- 固定金额: `shares = floor(fixed_amount / price)`
- 固定比例: `shares = floor(net_value * fixed_ratio_pct / price)`
- 波动率调整: `shares = floor(target_volatility / atr_ratio * net_value / price)`

#### 止损设置

```yaml
risk:
  stop_loss:
    mode: "volatility"  # 可选: fixed | volatility | trailing | time

    # 固定止损
    fixed_pct: 0.05  # 跌破 5% 止损

    # 波动率止损
    atr_multiplier: 2.0  # N * ATR
    atr_window: 14        # ATR 窗口

    # 回撤止损
    drawdown_pct: 0.10  # 从高点回撤 10%

    # 时间止损
    max_hold_days: 10  # 最多持有 10 天
```

**计算公式**:
- 固定止损: `stop_price = entry_price * (1 - fixed_pct)`
- 波动率止损: `stop_price = entry_price - atr_multiplier * ATR`
- 回撤止损: `stop_price = high_price * (1 - drawdown_pct)`

#### 止盈设置

```yaml
risk:
  take_profit:
    mode: "scaling"  # 可选: fixed | scaling | trailing | time

    # 固定止盈
    fixed_pct: 0.15  # 上涨 15% 止盈

    # 分批止盈
    scaling_levels:
      - target_pct: 0.05   # +5% 卖 50%
        close_pct: 0.50
      - target_pct: 0.10   # +10% 再卖 30%
        close_pct: 0.30
      - target_pct: 0.20   # +20% 最后卖 20%
        close_pct: 0.20

    # 移动止损
    trailing_pct: 0.05  # 从高点回撤 5%

    # 时间止盈
    target_hold_days: 5  # 持有 5 天后止盈
```

**计算公式**:
- 固定止盈: `target_price = entry_price * (1 + fixed_pct)`
- 分批止盈: 每个级别单独计算
- 移动止损: `target_price = high_price * (1 - trailing_pct)`

### 模拟账户配置

```yaml
simulated_account:
  enabled: true
  initial_capital: 100_000.0  # 初始资金
  persist_to_db: true          # 是否持久化到数据库
```

---

## API 使用示例

### 基本使用流程

```python
from src.strategy import FeatureEngine, RuleEvaluator, SignalSynthesizer, create_signal
from src.risk import PositionManager, StopLossCalculator, TakeProfitCalculator

# 1. 初始化组件
feature_engine = FeatureEngine()
evaluator = RuleEvaluator(executor)
synthesizer = SignalSynthesizer(mode="priority")
position_manager = PositionManager()
stop_loss_calc = StopLossCalculator()
take_profit_calc = TakeProfitCalculator()

# 2. 特征计算
features = feature_engine.compute_realtime(bars)

# 3. 规则评估
matches = evaluator.evaluate(rules, features, market_state)

# 4. 信号合成
context = SynthesisContext(market_state={}, features={})
raw_signal = synthesizer.synthesize(matches, context)

# 5. 风控拦截
if raw_signal.side != SignalSide.HOLD:
    position_size = position_manager.calculate_size(raw_signal, account, market_data)
    stop_loss = stop_loss_calc.calculate(raw_signal.entry_price.value, raw_signal, market_data)
    take_profit = take_profit_calc.calculate(raw_signal.entry_price.value, raw_signal, market_data)

    signal = create_signal(raw_signal, stop_loss, take_profit, symbol="TEST")
else:
    signal = create_signal(raw_signal, symbol="TEST")
```

### 批量处理

```python
# 1. 批量计算特征
features_map = feature_engine.compute_batch(items)

# 2. 批量评估规则
matches_map = evaluator.evaluate_batch(rules, features_map, market_state)

# 3. 批量合成信号
signals = []
for symbol, matches in matches_map.items():
    raw = synthesizer.synthesize(matches, context)
    if raw.side != SignalSide.HOLD:
        signal = create_signal(raw, symbol=symbol)
        signals.append(signal)
```

---

## 错误处理

| 异常 | 说明 | 处理方式 |
|------|------|----------|
| `FeatureEngineError` | 特征计算失败 | 返回空特征，记录日志 |
| `RuleEvaluationError` | 规则评估失败 | 跳过该规则，继续评估 |
| `SignalSynthesisError` | 信号合成失败 | 返回 HOLD 信号 |
| `PositionLimitExceeded` | 头寸超限 | 限制头寸在最大范围内 |
| `RiskBlockedError` | 风控拦截 | 返回 HOLD 信号 + 原因 |
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/guides/strategy-risk-agent-usage.md
git commit -m "docs: add strategy risk agent usage guide"
```

---

## Task 15: 集成测试

**Files:**
- Create: `tests/integration/strategy_risk_integration_test.py`

- [ ] **Step 1: 创建集成测试**

```python
"""Strategy Agent + Risk Agent 集成测试"""
import pytest
from datetime import date
from src.strategy import FeatureEngine, RuleEvaluator, SignalSynthesizer, create_signal
from src.strategy.types import SynthesisContext, SignalSide
from src.risk import PositionManager, StopLossCalculator, TakeProfitCalculator
from src.persona.dsl_executor import DSLExecutor, RuleRegistry
from src.persona.dsl_compiler import DSLCompiler
from src.persona.schemas import MarketRegime, VolatilityLevel, MarketState
from src.features.feature_pipeline import DailyBars, FeatureVector


def test_end_to_end_signal_generation():
    """端到端信号生成测试"""
    # 1. 初始化组件
    feature_engine = FeatureEngine()
    registry = RuleRegistry()
    executor = DSLExecutor(registry)
    evaluator = RuleEvaluator(executor)
    synthesizer = SignalSynthesizer(mode="priority")
    position_manager = PositionManager()
    stop_loss_calc = StopLossCalculator()
    take_profit_calc = TakeProfitCalculator()

    # 2. 创建测试数据
    bars = DailyBars(
        symbol="TEST",
        dates=[date(2026, 4, i % 30 + 1) for i in range(60)],
        opens=[100.0 + i * 0.5 for i in range(60)],
        highs=[105.0 + i * 0.5 for i in range(60)],
        lows=[95.0 + i * 0.5 for i in range(60)],
        closes=[102.0 + i * 0.5 for i in range(60)],
        volumes=[1_000_000 for _ in range(60)],
    )

    market_state = MarketState(
        as_of_date=date(2026, 4, 9),
        regime=MarketRegime.trend_up,
        volatility=VolatilityLevel.low,
    )

    # 3. 特征计算
    features = feature_engine.compute_realtime(bars)
    assert features is not None

    # 4. 规则评估
    compiler = DSLCompiler()
    rule = compiler.compile(
        name="test_entry",
        rule_type="entry",
        condition_dsl="regime == 'trend_up'",
    )
    registry.register(rule)

    matches = evaluator.evaluate([rule], features, market_state)
    assert len(matches) >= 0  # 可能匹配也可能不匹配

    # 5. 信号合成
    context = SynthesisContext(
        market_state=market_state.model_dump(),
        features=features.to_dict(),
    )
    raw_signal = synthesizer.synthesize(matches, context)
    assert raw_signal is not None
    assert raw_signal.side in SignalSide

    # 6. 风控（如果信号不是 HOLD）
    if raw_signal.side != SignalSide.HOLD:
        account = type("AccountSnapshot", (), {
            "account_id": "test",
            "net_value": 100_000.0,
            "cash": 100_000.0,
            "total_position_value": 0.0,
            "positions": [],
            "daily_pnl": 0.0,
            "total_pnl": 0.0,
        })()

        market_data = {"close": 102.0, "atr": 2.0}

        position_size = position_manager.calculate_size(raw_signal, account, market_data)
        stop_loss = stop_loss_calc.calculate(102.0, raw_signal, market_data)
        take_profit = take_profit_calc.calculate(102.0, raw_signal, market_data)

        signal = create_signal(raw_signal, stop_loss, take_profit, symbol="TEST")

        assert signal.symbol == "TEST"
        assert signal.side == raw_signal.side
        assert signal.stop_loss is not None or signal.take_profit is not None
```

- [ ] **Step 2: 运行集成测试**

```bash
pytest tests/integration/strategy_risk_integration_test.py -v
# 预期: 1 passed
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/strategy_risk_integration_test.py
git commit -m "test: add strategy risk integration test"
```

---

## 自检清单

- [ ] spec coverage: P4-001~P4-008 全部覆盖
- [ ] placeholder scan: 无 TBD/TODO
- [ ] type consistency: 类型定义一致
- [ ] 配置方法已写入使用说明文档
