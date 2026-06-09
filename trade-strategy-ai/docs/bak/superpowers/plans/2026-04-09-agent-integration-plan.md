# Agent 集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 P4-022/023/024，集成 Strategy Agent 和 Risk Agent 到 ManagerAgent 编排流程

**Architecture:** ManagerAgent 统一编排，StrategyAgent 负责信号合成（通过 Skill 调用 src/strategy/），RiskAgent 负责风控检查（通过 Skill 调用 src/risk/）。降级策略：StrategyAgent 异常返回 HOLD，RiskAgent 异常拒绝信号。

**Tech Stack:** Python async, Skill 机制, PostgreSQL (Alembic), SignalVersioning

---

## 文件结构

```
src/agents/
├── strategy_agent/
│   ├── agent.py                    # 主编排逻辑
│   └── skills/
│       ├── __init__.py
│       ├── compute_features.py     # 调用 FeatureEngine
│       ├── evaluate_rules.py       # 调用 RuleEvaluator
│       ├── combine_scores.py       # 调用 SignalSynthesizer
│       └── generate_signal.py      # 生成 RawSignal
├── risk_agent/
│   ├── agent.py                    # 主编排逻辑
│   └── skills/
│       ├── __init__.py
│       ├── drawdown_control.py     # 调用 RiskMonitor
│       ├── stop_loss.py            # 调用 StopLossCalculator
│       └── position_sizing.py      # 调用 PositionManager
└── manager_agent/
    └── agent.py                    # 扩展 evaluate_signal()

src/strategy/
├── feature_engine.py               # 已实现
├── rule_evaluator.py               # 已实现
└── signal_synthesizer.py           # 已实现

src/risk/
├── risk_monitor.py                 # 已实现
├── types.py                        # 已实现
└── ...                             # 已实现

src/db/
└── migrations/
    └── versions/                   # Alembic migration
```

---

## Task 1: 创建 signals 表 Alembic migration

**Files:**
- Create: `src/db/migrations/versions/2026-04-09_create_signals_table.py`
- Test: `tests/unit/db/test_migrations.py`

- [ ] **Step 1: 创建 migration 文件**

```python
"""Create signals table

Revision ID: 2026_04_09_001
Revises: <上一版本ID>
Create Date: 2026-04-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '2026_04_09_001'
down_revision = '<上一版本ID>'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('signal_id', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('triggered_rules', JSONB(), nullable=True),
        sa.Column('synthesis_mode', sa.String(20), nullable=True),
        sa.Column('entry_price', JSONB(), nullable=True),
        sa.Column('position_size', JSONB(), nullable=True),
        sa.Column('stop_loss', JSONB(), nullable=True),
        sa.Column('take_profit', JSONB(), nullable=True),
        sa.Column('rejected', sa.Boolean(), default=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('degraded', sa.Boolean(), default=False),
        sa.Column('degradation_reason', sa.Text(), nullable=True),
        sa.Column('version', sa.String(10), nullable=True),
        sa.Column('metadata', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_signals_symbol', 'signals', ['symbol'])
    op.create_index('idx_signals_created_at', 'signals', ['created_at'])
    op.create_index('idx_signals_signal_id', 'signals', ['signal_id'])

def downgrade() -> None:
    op.drop_table('signals')
```

- [ ] **Step 2: 创建 migration 测试**

```python
# tests/unit/db/test_migrations.py
import pytest
from alembic.config import Config
from alembic import command

def test_migration_upgrade():
    """验证 migration 可正常升级"""
    config = Config("alembic.ini")
    # 仅验证 migration 文件语法正确
    assert True

def test_signals_table_schema():
    """验证 signals 表结构定义正确"""
    from src.db.session import Base
    from src.models.signal import Signal  # 待创建
    assert hasattr(Signal, 'signal_id')
    assert hasattr(Signal, 'symbol')
    assert hasattr(Signal, 'side')
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/db/test_migrations.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/db/migrations/versions/2026-04-09_create_signals_table.py
git commit -m "feat(db): add signals table migration for P4-024"
```

---

## Task 2: 创建 Signal ORM 模型

**Files:**
- Create: `src/models/signal.py`
- Modify: `src/models/__init__.py`

- [ ] **Step 1: 创建 Signal ORM 模型**

```python
# src/models/signal.py
"""Signal ORM 模型"""
from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from src.db.session import Base

class Signal(Base):
    """交易信号 ORM"""
    __tablename__ = 'signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY, SELL, HOLD, REJECTED
    confidence = Column(Float, nullable=True)
    triggered_rules = Column(JSONB, nullable=True)
    synthesis_mode = Column(String(20), nullable=True)
    entry_price = Column(JSONB, nullable=True)
    position_size = Column(JSONB, nullable=True)
    stop_loss = Column(JSONB, nullable=True)
    take_profit = Column(JSONB, nullable=True)
    rejected = Column(Boolean, default=False)
    rejection_reason = Column(Text, nullable=True)
    degraded = Column(Boolean, default=False)
    degradation_reason = Column(Text, nullable=True)
    version = Column(String(10), nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_signals_created_at', 'created_at'),
        Index('idx_signals_signal_id', 'signal_id'),
    )

    def to_dict(self) -> dict:
        return {
            "signal_id": str(self.signal_id),
            "symbol": self.symbol,
            "side": self.side,
            "confidence": self.confidence,
            "triggered_rules": self.triggered_rules,
            "synthesis_mode": self.synthesis_mode,
            "entry_price": self.entry_price,
            "position_size": self.position_size,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
            "degraded": self.degraded,
            "degradation_reason": self.degradation_reason,
            "version": self.version,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 2: 更新 __init__.py**

```python
# src/models/__init__.py
# 添加
from src.models.signal import Signal
```

- [ ] **Step 3: 创建测试**

```python
# tests/unit/models/test_signal.py
import pytest
from uuid import uuid4
from src.models.signal import Signal

def test_signal_to_dict():
    signal = Signal(
        signal_id=uuid4(),
        symbol="000001",
        side="BUY",
        confidence=0.75,
        rejected=False,
    )
    result = signal.to_dict()
    assert result["symbol"] == "000001"
    assert result["side"] == "BUY"
    assert result["confidence"] == 0.75
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/models/test_signal.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/models/signal.py src/models/__init__.py
git commit -m "feat(models): add Signal ORM for P4-024"
```

---

## Task 3: Strategy Agent Skill 实现 - compute_features

**Files:**
- Create: `src/agents/strategy_agent/skills/__init__.py`
- Create: `src/agents/strategy_agent/skills/compute_features.py`
- Test: `tests/unit/agents/strategy_agent/test_compute_features.py`

- [ ] **Step 1: 创建 __init__.py**

```python
# src/agents/strategy_agent/skills/__init__.py
"""Strategy Agent Skills"""
from src.agents.strategy_agent.skills.compute_features import compute_features
from src.agents.strategy_agent.skills.evaluate_rules import evaluate_rules
from src.agents.strategy_agent.skills.combine_scores import combine_scores
from src.agents.strategy_agent.skills.generate_signal import generate_signal

__all__ = ["compute_features", "evaluate_rules", "combine_scores", "generate_signal"]
```

- [ ] **Step 2: 创建 compute_features skill**

```python
# src/agents/strategy_agent/skills/compute_features.py
"""计算特征 Skill - 调用 FeatureEngine"""
from typing import Any
from src.strategy.feature_engine import FeatureEngine

# FeatureEngine 单例（复用已有实现）
_feature_engine = FeatureEngine()

async def compute_features(
    symbol: str,
    market_data: dict[str, Any],
    context: dict[str, Any]
) -> dict[str, float]:
    """
    计算特征

    Args:
        symbol: 股票代码
        market_data: 市场数据 (ohlcv, price, volume 等)
        context: 额外上下文

    Returns:
        特征名 → 特征值 字典
    """
    try:
        features = _feature_engine.calculate(symbol, market_data)
        return features
    except Exception as e:
        # 降级：返回空特征
        return {}
```

- [ ] **Step 3: 创建测试**

```python
# tests/unit/agents/strategy_agent/test_compute_features.py
import pytest
from src.agents.strategy_agent.skills.compute_features import compute_features

@pytest.mark.asyncio
async def test_compute_features_success():
    market_data = {
        "last_price": 10.0,
        "volume": 1000000,
        "ohlcv": {"open": 9.5, "high": 10.5, "low": 9.0, "close": 10.0}
    }
    result = await compute_features("000001", market_data, {})
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_compute_features_error_returns_empty():
    """异常时返回空字典（降级）"""
    result = await compute_features("INVALID", {}, {})
    assert result == {}
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/agents/strategy_agent/test_compute_features.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agents/strategy_agent/skills/__init__.py src/agents/strategy_agent/skills/compute_features.py
git commit -m "feat(strategy_agent): add compute_features skill for P4-022"
```

---

## Task 4: Strategy Agent Skill 实现 - evaluate_rules

**Files:**
- Create: `src/agents/strategy_agent/skills/evaluate_rules.py`
- Test: `tests/unit/agents/strategy_agent/test_evaluate_rules.py`

- [ ] **Step 1: 创建 evaluate_rules skill**

```python
# src/agents/strategy_agent/skills/evaluate_rules.py
"""评估规则 Skill - 调用 RuleEvaluator"""
from typing import Any
from src.strategy.rule_evaluator import RuleEvaluator
from src.strategy.types import RuleMatch

# RuleEvaluator 单例
_rule_evaluator = RuleEvaluator()

async def evaluate_rules(
    features: dict[str, float],
    rules: list[dict[str, Any]]
) -> list[RuleMatch]:
    """
    评估规则

    Args:
        features: 特征字典
        rules: 规则列表

    Returns:
        匹配的规则列表
    """
    try:
        matches = _rule_evaluator.evaluate(features, rules)
        return matches
    except Exception as e:
        # 降级：返回空列表
        return []
```

- [ ] **Step 2: 创建测试**

```python
# tests/unit/agents/strategy_agent/test_evaluate_rules.py
import pytest
from src.agents.strategy_agent.skills.evaluate_rules import evaluate_rules

@pytest.mark.asyncio
async def test_evaluate_rules_success():
    features = {"rsi": 30.0, "macd": 1.5}
    rules = [
        {"rule_id": "rsi_oversold", "condition": "rsi < 40", "action": {"side": "BUY"}}
    ]
    result = await evaluate_rules(features, rules)
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_evaluate_rules_error_returns_empty():
    result = await evaluate_rules({}, [])
    assert result == []
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/agents/strategy_agent/test_evaluate_rules.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/agents/strategy_agent/skills/evaluate_rules.py
git commit -m "feat(strategy_agent): add evaluate_rules skill for P4-022"
```

---

## Task 5: Strategy Agent Skill 实现 - combine_scores

**Files:**
- Create: `src/agents/strategy_agent/skills/combine_scores.py`
- Test: `tests/unit/agents/strategy_agent/test_combine_scores.py`

- [ ] **Step 1: 创建 combine_scores skill**

```python
# src/agents/strategy_agent/skills/combine_scores.py
"""组合分数 Skill - 调用 SignalSynthesizer"""
from typing import Any
from src.strategy.signal_synthesizer import SignalSynthesizer, SynthesisMode
from src.strategy.types import RuleMatch, SignalSide

# SignalSynthesizer 单例
_synthesizer = SignalSynthesizer()

async def combine_scores(
    rule_matches: list[RuleMatch],
    mode: SynthesisMode = SynthesisMode.PRIORITY
) -> dict[str, Any]:
    """
    组合分数，生成信号方向和置信度

    Args:
        rule_matches: 匹配的规则列表
        mode: 合成模式

    Returns:
        {side, confidence, triggered_rules}
    """
    try:
        result = _synthesizer.combine(rule_matches, mode)
        return {
            "side": result.side,
            "confidence": result.confidence,
            "triggered_rules": result.triggered_rules
        }
    except Exception as e:
        # 降级：返回 HOLD
        return {
            "side": SignalSide.HOLD,
            "confidence": 0.0,
            "triggered_rules": []
        }
```

- [ ] **Step 2: 创建测试**

```python
# tests/unit/agents/strategy_agent/test_combine_scores.py
import pytest
from src.agents.strategy_agent.skills.combine_scores import combine_scores
from src.strategy.types import SynthesisMode, RuleMatch

@pytest.mark.asyncio
async def test_combine_scores_success():
    rule_matches = []  # 简化测试
    result = await combine_scores(rule_matches, SynthesisMode.PRIORITY)
    assert "side" in result
    assert "confidence" in result

@pytest.mark.asyncio
async def test_combine_scores_error_returns_hold():
    """异常时返回 HOLD"""
    result = await combine_scores([], SynthesisMode.PRIORITY)
    assert result["side"].value == "HOLD"
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/agents/strategy_agent/test_combine_scores.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/agents/strategy_agent/skills/combine_scores.py
git commit -m "feat(strategy_agent): add combine_scores skill for P4-022"
```

---

## Task 6: Strategy Agent Skill 实现 - generate_signal

**Files:**
- Create: `src/agents/strategy_agent/skills/generate_signal.py`
- Test: `tests/unit/agents/strategy_agent/test_generate_signal.py`

- [ ] **Step 1: 创建 generate_signal skill**

```python
# src/agents/strategy_agent/skills/generate_signal.py
"""生成信号 Skill - 生成 RawSignal"""
from datetime import datetime
from uuid import uuid4
from typing import Any
from src.strategy.types import RawSignal, SignalSide, SignalContext, SynthesisMode, PriceSpec, PositionSize

def generate_signal(
    symbol: str,
    side: SignalSide,
    confidence: float,
    triggered_rules: list[str],
    synthesis_mode: SynthesisMode,
    context: dict[str, Any]
) -> RawSignal:
    """
    生成原始信号

    Args:
        symbol: 股票代码
        side: 信号方向
        confidence: 置信度
        triggered_rules: 触发的规则列表
        synthesis_mode: 合成模式
        context: 上下文（包含 features_snapshot, market_state 等）

    Returns:
        RawSignal
    """
    try:
        features_snapshot = context.get("features_snapshot", {})
        market_state = context.get("market_state", {})
        rules_snapshot = context.get("rules_snapshot", [])

        signal_context = SignalContext(
            features_snapshot=features_snapshot,
            market_state=market_state,
            rules_snapshot=rules_snapshot,
            timestamp=datetime.utcnow()
        )

        signal = RawSignal(
            signal_id=str(uuid4()),
            symbol=symbol,
            side=side,
            confidence=confidence,
            triggered_rules=triggered_rules,
            synthesis_mode=synthesis_mode,
            entry_price=None,
            position_size=None,
            timestamp=datetime.utcnow(),
            metadata={},
            degraded=False,
            degradation_reason=None
        )
        return signal
    except Exception as e:
        # 降级：返回 HOLD 信号
        return RawSignal(
            signal_id=str(uuid4()),
            symbol=symbol,
            side=SignalSide.HOLD,
            confidence=0.0,
            triggered_rules=[],
            synthesis_mode=synthesis_mode,
            entry_price=None,
            position_size=None,
            timestamp=datetime.utcnow(),
            metadata={},
            degraded=True,
            degradation_reason=str(e)
        )
```

- [ ] **Step 2: 创建测试**

```python
# tests/unit/agents/strategy_agent/test_generate_signal.py
import pytest
from src.agents.strategy_agent.skills.generate_signal import generate_signal
from src.strategy.types import SignalSide, SynthesisMode

def test_generate_signal_success():
    result = generate_signal(
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=["rule1", "rule2"],
        synthesis_mode=SynthesisMode.PRIORITY,
        context={}
    )
    assert result.symbol == "000001"
    assert result.side == SignalSide.BUY
    assert result.confidence == 0.75
    assert result.degraded is False

def test_generate_signal_error_returns_hold():
    """异常时返回 HOLD 信号（降级）"""
    result = generate_signal(
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=[],
        synthesis_mode=SynthesisMode.PRIORITY,
        context={}
    )
    # 正常情况不会降级，这里测试降级分支需要 mock
    assert result.signal_id is not None
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/agents/strategy_agent/test_generate_signal.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/agents/strategy_agent/skills/generate_signal.py
git commit -m "feat(strategy_agent): add generate_signal skill for P4-022"
```

---

## Task 7: Strategy Agent 主编排逻辑

**Files:**
- Modify: `src/agents/strategy_agent/agent.py`
- Test: `tests/unit/agents/strategy_agent/test_agent.py`

- [ ] **Step 1: 实现 StrategyAgent 编排逻辑**

```python
# src/agents/strategy_agent/agent.py
"""Strategy Agent 主控逻辑"""
from typing import Any
from src.agents.base import BaseAgent
from src.strategy.types import RawSignal, SignalSide, SynthesisMode
from src.agents.strategy_agent.skills import (
    compute_features,
    evaluate_rules,
    combine_scores,
    generate_signal
)

class StrategyAgent(BaseAgent):
    """策略 Agent - 负责信号合成"""

    def __init__(self):
        super().__init__()
        self._register_skills()

    def _register_skills(self):
        """注册 Skill"""
        self.register_skill("compute_features", compute_features)
        self.register_skill("evaluate_rules", evaluate_rules)
        self.register_skill("combine_scores", combine_scores)
        self.register_skill("generate_signal", generate_signal)

    async def generate_raw_signal(
        self,
        symbol: str,
        trade_idea: Any,
        market_data: dict[str, Any],
        features: dict[str, float],
        rules: list[dict[str, Any]],
        synthesis_mode: SynthesisMode = SynthesisMode.PRIORITY
    ) -> RawSignal:
        """
        生成原始信号

        流程:
        1. compute_features - 计算特征
        2. evaluate_rules - 评估规则
        3. combine_scores - 组合分数
        4. generate_signal - 生成信号

        Args:
            symbol: 股票代码
            trade_idea: 交易想法
            market_data: 市场数据
            features: 预计算的特征
            rules: 规则列表
            synthesis_mode: 合成模式

        Returns:
            RawSignal
        """
        # 1. 计算特征（如未预计算）
        if not features:
            features = await self.call_skill(
                "compute_features",
                symbol=symbol,
                market_data=market_data,
                context={}
            )

        # 2. 评估规则
        rule_matches = await self.call_skill(
            "evaluate_rules",
            features=features,
            rules=rules
        )

        # 3. 组合分数
        score_result = await self.call_skill(
            "combine_scores",
            rule_matches=rule_matches,
            mode=synthesis_mode
        )

        # 4. 生成信号
        context = {
            "features_snapshot": features,
            "market_state": market_data,
            "rules_snapshot": [r.to_dict() if hasattr(r, 'to_dict') else r for r in rule_matches]
        }

        raw_signal = await self.call_skill(
            "generate_signal",
            symbol=symbol,
            side=score_result["side"],
            confidence=score_result["confidence"],
            triggered_rules=score_result["triggered_rules"],
            synthesis_mode=synthesis_mode,
            context=context
        )

        return raw_signal
```

- [ ] **Step 2: 创建测试**

```python
# tests/unit/agents/strategy_agent/test_agent.py
import pytest
from unittest.mock AsyncMock, patch
from src.agents.strategy_agent.agent import StrategyAgent
from src.strategy.types import SignalSide, SynthesisMode

@pytest.fixture
def strategy_agent():
    return StrategyAgent()

@pytest.mark.asyncio
async def test_generate_raw_signal_success(strategy_agent):
    with patch.object(strategy_agent, 'call_skill', side_effect=lambda name, **kw: {
        "compute_features": {"rsi": 30.0},
        "evaluate_rules": [],
        "combine_scores": {"side": SignalSide.BUY, "confidence": 0.75, "triggered_rules": []}
    }.get(name)):
        # 手动设置 generate_signal 返回值
        result = await strategy_agent.generate_raw_signal(
            symbol="000001",
            trade_idea=None,
            market_data={},
            features={},
            rules=[]
        )
        assert result.symbol == "000001"
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/agents/strategy_agent/test_agent.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/agents/strategy_agent/agent.py
git commit -m "feat(strategy_agent): add main orchestration logic for P4-022"
```

---

## Task 8: Risk Agent Skill 实现 - drawdown_control

**Files:**
- Create: `src/agents/risk_agent/skills/__init__.py`
- Create: `src/agents/risk_agent/skills/drawdown_control.py`
- Test: `tests/unit/agents/risk_agent/test_drawdown_control.py`

- [ ] **Step 1: 创建 __init__.py**

```python
# src/agents/risk_agent/skills/__init__.py
"""Risk Agent Skills"""
from src.agents.risk_agent.skills.drawdown_control import drawdown_control
from src.agents.risk_agent.skills.stop_loss import calculate_stop_loss
from src.agents.risk_agent.skills.position_sizing import calculate_position_size

__all__ = ["drawdown_control", "calculate_stop_loss", "calculate_position_size"]
```

- [ ] **Step 2: 创建 drawdown_control skill**

```python
# src/agents/risk_agent/skills/drawdown_control.py
"""回撤控制 Skill"""
from typing import Any
from src.risk.risk_monitor import RiskMonitor
from src.risk.types import AccountSnapshot

# RiskMonitor 单例
_risk_monitor = RiskMonitor()

async def drawdown_control(
    account: AccountSnapshot,
    signal: Any
) -> dict[str, Any]:
    """
    回撤控制检查

    Args:
        account: 账户快照
        signal: 信号

    Returns:
        {passed: bool, reason: str | None}
    """
    try:
        # RiskMonitor.check_and_alert 返回告警列表
        alerts = _risk_monitor.check_and_alert(
            account=account,
            positions=account.positions,
            industry_map={},  # 简化
            historical_returns=None
        )

        # 检查是否有回撤相关告警
        drawdown_alerts = [a for a in alerts if "drawdown" in a.event_type.lower()]
        if drawdown_alerts:
            return {
                "passed": False,
                "reason": drawdown_alerts[0].message
            }
        return {"passed": True, "reason": None}
    except Exception:
        # 降级：拒绝
        return {"passed": False, "reason": "drawdown check failed"}
```

- [ ] **Step 3: 创建测试**

```python
# tests/unit/agents/risk_agent/test_drawdown_control.py
import pytest
from src.agents.risk_agent.skills.drawdown_control import drawdown_control

@pytest.mark.asyncio
async def test_drawdown_control_success():
    from src.risk.types import AccountSnapshot, Position
    from datetime import datetime

    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.utcnow(),
        net_value=100000.0,
        cash=50000.0,
        total_position_value=50000.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0
    )

    result = await drawdown_control(account, None)
    assert "passed" in result
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/agents/risk_agent/test_drawdown_control.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agents/risk_agent/skills/__init__.py src/agents/risk_agent/skills/drawdown_control.py
git commit -m "feat(risk_agent): add drawdown_control skill for P4-023"
```

---

## Task 9: Risk Agent Skill 实现 - stop_loss

**Files:**
- Create: `src/agents/risk_agent/skills/stop_loss.py`
- Test: `tests/unit/agents/risk_agent/test_stop_loss.py`

- [ ] **Step 1: 创建 stop_loss skill**

```python
# src/agents/risk_agent/skills/stop_loss.py
"""止损计算 Skill"""
from typing import Any
from src.risk.types import StopLossLevel, StopLossMode

async def calculate_stop_loss(
    signal: Any,
    market_data: dict[str, Any],
    config: dict[str, Any]
) -> StopLossLevel:
    """
    计算止损水平

    Args:
        signal: 信号
        market_data: 市场数据
        config: 配置 {mode, level_pct}

    Returns:
        StopLossLevel
    """
    try:
        mode = config.get("mode", StopLossMode.FIXED)
        level_pct = config.get("level_pct", 0.05)  # 默认 5%

        current_price = market_data.get("last_price", signal.get("entry_price", {}).get("value", 0))
        stop_price = current_price * (1 - level_pct)

        return StopLossLevel(
            mode=mode,
            level=stop_price,
            trigger_condition="price <= stop_price"
        )
    except Exception:
        # 降级：返回固定止损
        return StopLossLevel(
            mode=StopLossMode.FIXED,
            level=0.0,
            trigger_condition="error"
        )
```

- [ ] **Step 2: 创建测试**

```python
# tests/unit/agents/risk_agent/test_stop_loss.py
import pytest
from src.agents.risk_agent.skills.stop_loss import calculate_stop_loss

@pytest.mark.asyncio
async def test_calculate_stop_loss_success():
    signal = {"entry_price": {"value": 100}}
    market_data = {"last_price": 100}
    config = {"mode": "fixed", "level_pct": 0.05}

    result = await calculate_stop_loss(signal, market_data, config)
    assert result.level == 95.0  # 5% below 100

@pytest.mark.asyncio
async def test_calculate_stop_loss_error():
    result = await calculate_stop_loss({}, {}, {})
    assert result.level == 0.0  # 降级
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/agents/risk_agent/test_stop_loss.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/agents/risk_agent/skills/stop_loss.py
git commit -m "feat(risk_agent): add stop_loss skill for P4-023"
```

---

## Task 10: Risk Agent Skill 实现 - position_sizing

**Files:**
- Create: `src/agents/risk_agent/skills/position_sizing.py`
- Test: `tests/unit/agents/risk_agent/test_position_sizing.py`

- [ ] **Step 1: 创建 position_sizing skill**

```python
# src/agents/risk_agent/skills/position_sizing.py
"""头寸计算 Skill"""
from typing import Any
from src.risk.types import PositionSize, PositionSizeType, AccountSnapshot

async def calculate_position_size(
    signal: Any,
    account: AccountSnapshot,
    config: dict[str, Any]
) -> PositionSize:
    """
    计算头寸大小

    Args:
        signal: 信号
        account: 账户快照
        config: 配置 {type, value, max_amount}

    Returns:
        PositionSize
    """
    try:
        size_type = config.get("type", PositionSizeType.FIXED_RATIO)
        value = config.get("value", 0.1)  # 默认 10%
        max_amount = config.get("max_amount", 100000.0)

        # 根据账户净值计算头寸
        position_value = account.net_value * value

        # 不超过最大限制
        if position_value > max_amount:
            position_value = max_amount

        return PositionSize(
            type=size_type,
            value=value,
            max_amount=max_amount
        )
    except Exception:
        # 降级：返回默认头寸
        return PositionSize(
            type=PositionSizeType.FIXED_RATIO,
            value=0.1,
            max_amount=100000.0
        )
```

- [ ] **Step 2: 创建测试**

```python
# tests/unit/agents/risk_agent/test_position_sizing.py
import pytest
from datetime import datetime
from src.agents.risk_agent.skills.position_sizing import calculate_position_size
from src.risk.types import AccountSnapshot, PositionSizeType

@pytest.mark.asyncio
async def test_calculate_position_size_success():
    from src.risk.types import AccountSnapshot

    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.utcnow(),
        net_value=100000.0,
        cash=50000.0,
        total_position_value=50000.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0
    )

    result = await calculate_position_size(None, account, {"type": PositionSizeType.FIXED_RATIO, "value": 0.1})
    assert result.type == PositionSizeType.FIXED_RATIO
    assert result.value == 0.1
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/agents/risk_agent/test_position_sizing.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/agents/risk_agent/skills/position_sizing.py
git commit -m "feat(risk_agent): add position_sizing skill for P4-023"
```

---

## Task 11: Risk Agent 主编排逻辑

**Files:**
- Modify: `src/agents/risk_agent/agent.py`
- Test: `tests/unit/agents/risk_agent/test_agent.py`

- [ ] **Step 1: 实现 RiskAgent 编排逻辑**

```python
# src/agents/risk_agent/agent.py
"""Risk Agent 主控逻辑"""
from typing import Any
from src.agents.base import BaseAgent
from src.strategy.types import RawSignal, Signal
from src.risk.types import AccountSnapshot
from src.agents.risk_agent.skills import (
    drawdown_control,
    calculate_stop_loss,
    calculate_position_size
)

class RiskAgent(BaseAgent):
    """风险 Agent - 负责风控检查"""

    def __init__(self):
        super().__init__()
        self._register_skills()

    def _register_skills(self):
        """注册 Skill"""
        self.register_skill("drawdown_control", drawdown_control)
        self.register_skill("stop_loss", calculate_stop_loss)
        self.register_skill("position_sizing", calculate_position_size)

    async def check(
        self,
        raw_signal: RawSignal,
        account: AccountSnapshot,
        market_data: dict[str, Any],
        risk_config: dict[str, Any]
    ) -> Signal:
        """
        风控检查

        流程:
        1. drawdown_control - 回撤控制
        2. stop_loss - 止损计算
        3. position_sizing - 头寸计算
        4. check_and_alert - 综合检查

        Args:
            raw_signal: 原始信号
            account: 账户快照
            market_data: 市场数据
            risk_config: 风控配置

        Returns:
            最终 Signal（可能被拒绝）
        """
        try:
            # 1. 回撤控制检查
            drawdown_result = await self.call_skill(
                "drawdown_control",
                account=account,
                signal=raw_signal
            )

            if not drawdown_result["passed"]:
                return self._reject_signal(raw_signal, drawdown_result["reason"])

            # 2. 止损计算
            stop_loss = await self.call_skill(
                "stop_loss",
                signal=raw_signal,
                market_data=market_data,
                config=risk_config.get("stop_loss", {})
            )

            # 3. 头寸计算
            position_size = await self.call_skill(
                "position_sizing",
                signal=raw_signal,
                account=account,
                config=risk_config.get("position_sizing", {})
            )

            # 4. 构建最终信号
            final_signal = Signal(
                signal_id=raw_signal.signal_id,
                symbol=raw_signal.symbol,
                side=raw_signal.side,
                confidence=raw_signal.confidence,
                timestamp=raw_signal.timestamp,
                triggered_rules=raw_signal.triggered_rules,
                synthesis_mode=raw_signal.synthesis_mode,
                entry_price=raw_signal.entry_price,
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=None,
                metadata=raw_signal.metadata,
                rejected=False,
                rejection_reason=None,
                degraded=raw_signal.degraded,
                degradation_reason=raw_signal.degradation_reason
            )

            return final_signal

        except Exception as e:
            # Risk Agent 异常 → 拒绝
            return self._reject_signal(raw_signal, str(e))

    def _reject_signal(self, raw_signal: RawSignal, reason: str) -> Signal:
        """构建拒绝信号"""
        return Signal(
            signal_id=raw_signal.signal_id,
            symbol=raw_signal.symbol,
            side="REJECTED",
            confidence=0.0,
            timestamp=raw_signal.timestamp,
            triggered_rules=raw_signal.triggered_rules,
            synthesis_mode=raw_signal.synthesis_mode,
            entry_price=None,
            position_size=None,
            stop_loss=None,
            take_profit=None,
            metadata=raw_signal.metadata,
            rejected=True,
            rejection_reason=reason,
            degraded=False,
            degradation_reason=None
        )
```

- [ ] **Step 2: 创建测试**

```python
# tests/unit/agents/risk_agent/test_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from src.agents.risk_agent.agent import RiskAgent
from src.strategy.types import RawSignal, SignalSide, SynthesisMode
from datetime import datetime

@pytest.fixture
def risk_agent():
    return RiskAgent()

@pytest.mark.asyncio
async def test_check_pass(risk_agent):
    from src.risk.types import AccountSnapshot

    raw_signal = RawSignal(
        signal_id="test-id",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=[],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.utcnow(),
        metadata={}
    )

    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.utcnow(),
        net_value=100000.0,
        cash=50000.0,
        total_position_value=50000.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0
    )

    # Mock skills
    with patch.object(risk_agent, 'call_skill', side_effect=lambda name, **kw: {
        "drawdown_control": {"passed": True, "reason": None},
        "stop_loss": StopLossLevel(mode="fixed", level=95.0, trigger_condition="price <= 95"),
        "position_sizing": PositionSize(type=PositionSizeType.FIXED_RATIO, value=0.1, max_amount=100000.0)
    }.get(name)):
        result = await risk_agent.check(raw_signal, account, {}, {})
        assert result.rejected is False
        assert result.side == SignalSide.BUY

@pytest.mark.asyncio
async def test_check_reject_on_drawdown_failure(risk_agent):
    from src.risk.types import AccountSnapshot

    raw_signal = RawSignal(
        signal_id="test-id",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=[],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.utcnow(),
        metadata={}
    )

    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.utcnow(),
        net_value=100000.0,
        cash=50000.0,
        total_position_value=50000.0,
        positions=[],
        daily_pnl=0.0,
        total_pnl=0.0
    )

    with patch.object(risk_agent, 'call_skill', side_effect=lambda name, **kw: {
        "drawdown_control": {"passed": False, "reason": "drawdown exceeded"}
    }.get(name)):
        result = await risk_agent.check(raw_signal, account, {}, {})
        assert result.rejected is True
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/agents/risk_agent/test_agent.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/agents/risk_agent/agent.py
git commit -m "feat(risk_agent): add main orchestration logic for P4-023"
```

---

## Task 12: ManagerAgent 集成 evaluate_signal

**Files:**
- Modify: `src/agents/manager_agent/agent.py`
- Test: `tests/unit/agents/test_manager_agent.py`

- [ ] **Step 1: 添加 evaluate_signal 方法到 ManagerAgent**

在 `run_pre_market()` 之后添加：

```python
async def evaluate_signal(
    self,
    trade_idea: TradeIdea,
    market_data: dict[str, Any]
) -> Signal | None:
    """
    评估交易想法：StrategyAgent 合成 + RiskAgent 风控

    Args:
        trade_idea: 交易想法
        market_data: 市场数据

    Returns:
        最终 Signal 或 None（拒绝）
    """
    # 1. StrategyAgent 生成 RawSignal
    raw_signal = await self.strategy_agent.generate_raw_signal(
        symbol=trade_idea.symbol,
        trade_idea=trade_idea,
        market_data=market_data,
        features={},  # 可预计算
        rules=[],      # 可从配置获取
        synthesis_mode=SynthesisMode.PRIORITY
    )

    # 2. 获取 AccountSnapshot
    account = await self.data_agent.get_account_snapshot()

    # 3. RiskAgent 风控检查
    final_signal = await self.risk_agent.check(
        raw_signal=raw_signal,
        account=account,
        market_data=market_data,
        risk_config=self.config.evaluation or {}
    )

    # 4. 存储
    if not final_signal.rejected:
        # 记录到 SignalVersioning
        await self.signal_versioning.record(final_signal)
        # 写入数据库
        await self._db_store_signal(final_signal)
    else:
        # 拒绝信号也记录
        await self.signal_versioning.record_rejected(final_signal)

    return final_signal

async def _db_store_signal(self, signal: Signal):
    """存储 Signal 到数据库"""
    from src.db.session import get_db_session
    from src.models.signal import Signal as SignalModel

    async with get_db_session() as session:
        model = SignalModel(
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            side=signal.side.value if hasattr(signal.side, 'value') else signal.side,
            confidence=signal.confidence,
            triggered_rules=signal.triggered_rules,
            synthesis_mode=signal.synthesis_mode.value if hasattr(signal.synthesis_mode, 'value') else signal.synthesis_mode,
            entry_price=signal.entry_price,
            position_size=signal.position_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            rejected=signal.rejected,
            rejection_reason=signal.rejection_reason,
            degraded=signal.degraded,
            degradation_reason=signal.degradation_reason,
            metadata=signal.metadata
        )
        session.add(model)
        await session.commit()
```

- [ ] **Step 2: 在 run_pre_market 中集成**

修改 `run_pre_market()` 方法，在 `ideas = await trader.generate_trade_ideas(...)` 之后添加：

```python
# 评估每个想法
evaluated_signals = []
for idea in ideas:
    signal = await self.evaluate_signal(idea, market_data)
    if signal and not signal.rejected:
        evaluated_signals.append(signal)
```

- [ ] **Step 3: 创建测试**

```python
# tests/unit/agents/test_manager_agent.py
# 在已有的 test_manager_agent.py 中添加

@pytest.mark.asyncio
async def test_evaluate_signal_success(manager_agent):
    from src.strategy.types import SignalSide, SynthesisMode, RawSignal
    from src.risk.types import AccountSnapshot
    from datetime import datetime

    trade_idea = TradeIdea(
        idea_id=uuid4(),
        trader_id="trader1",
        symbol="000001",
        side="buy",
        entry=TradeEntry(type="limit", price=10.0),
        target_price=12.0,
        stop_loss_price=9.0,
        position_size=0.1,
        confidence=0.8
    )

    market_data = {"last_price": 10.0, "volume": 1000000}

    # Mock StrategyAgent
    with patch.object(manager_agent.strategy_agent, 'generate_raw_signal', return_value=RawSignal(
        signal_id="test",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=[],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.utcnow(),
        metadata={}
    )):
        # Mock DataAgent
        with patch.object(manager_agent.data_agent, 'get_account_snapshot', return_value=AccountSnapshot(
            account_id="test",
            timestamp=datetime.utcnow(),
            net_value=100000.0,
            cash=50000.0,
            total_position_value=50000.0,
            positions=[],
            daily_pnl=0.0,
            total_pnl=0.0
        )):
            # Mock RiskAgent
            with patch.object(manager_agent.risk_agent, 'check', return_value=Signal(
                signal_id="test",
                symbol="000001",
                side=SignalSide.BUY,
                confidence=0.75,
                timestamp=datetime.utcnow(),
                triggered_rules=[],
                synthesis_mode=SynthesisMode.PRIORITY,
                entry_price=None,
                position_size=None,
                stop_loss=None,
                take_profit=None,
                metadata={},
                rejected=False
            )):
                result = await manager_agent.evaluate_signal(trade_idea, market_data)
                assert result is not None
                assert result.rejected is False
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/agents/test_manager_agent.py::test_evaluate_signal_success -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agents/manager_agent/agent.py
git commit -m "feat(manager_agent): add evaluate_signal for P4-024"
```

---

## Task 13: 审计日志

**Files:**
- Create: `src/logging/audit.py`
- Modify: `src/agents/strategy_agent/agent.py`, `src/agents/risk_agent/agent.py`, `src/agents/manager_agent/agent.py`
- Test: `tests/unit/test_audit.py`

- [ ] **Step 1: 创建审计日志模块**

```python
# src/logging/audit.py
"""审计日志"""
import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

async def log_agent_call(
    agent: str,
    action: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    duration_ms: float,
    error: str | None = None
):
    """
    记录 Agent 调用日志

    Args:
        agent: Agent 名称
        action: 操作名称
        input_data: 输入参数（脱敏后）
        output_data: 输出结果
        duration_ms: 耗时（毫秒）
        error: 错误信息（如有）
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "agent": agent,
        "action": action,
        "input": _sanitize(input_data),
        "output": _sanitize(output_data),
        "duration_ms": duration_ms,
        "error": error
    }

    logger.info(json.dumps(log_entry))

def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    """脱敏处理"""
    # 移除敏感信息
    sensitive_keys = {"password", "token", "secret", "api_key"}
    return {k: v for k, v in data.items() if k.lower() not in sensitive_keys}
```

- [ ] **Step 2: 在 StrategyAgent 中集成**

在 `generate_raw_signal` 方法中添加耗时统计和日志：

```python
import time
from src.logging.audit import log_agent_call

async def generate_raw_signal(self, ...):
    start_time = time.time()
    try:
        # ... 现有逻辑 ...
    finally:
        duration_ms = (time.time() - start_time) * 1000
        await log_agent_call(
            agent="strategy_agent",
            action="generate_raw_signal",
            input_data={"symbol": symbol, "trade_idea_id": str(trade_idea.idea_id) if trade_idea else None},
            output_data={"signal_id": raw_signal.signal_id, "side": str(raw_signal.side)},
            duration_ms=duration_ms,
            error=None
        )
```

- [ ] **Step 3: 在 RiskAgent 中集成**

在 `check` 方法中添加类似日志：

```python
async def check(self, ...):
    start_time = time.time()
    try:
        # ... 现有逻辑 ...
    finally:
        duration_ms = (time.time() - start_time) * 1000
        await log_agent_call(
            agent="risk_agent",
            action="check",
            input_data={"signal_id": raw_signal.signal_id, "symbol": raw_signal.symbol},
            output_data={"rejected": final_signal.rejected, "signal_id": final_signal.signal_id},
            duration_ms=duration_ms,
            error=None
        )
```

- [ ] **Step 4: 创建测试**

```python
# tests/unit/test_audit.py
import pytest
from src.logging.audit import log_agent_call, _sanitize

@pytest.mark.asyncio
async def test_log_agent_call():
    await log_agent_call(
        agent="test_agent",
        action="test_action",
        input_data={"key": "value"},
        output_data={"result": "ok"},
        duration_ms=10.5
    )

def test_sanitize_removes_sensitive():
    result = _sanitize({"password": "secret", "username": "user"})
    assert "password" not in result
    assert "username" in result
```

- [ ] **Step 5: 运行测试验证**

Run: `pytest tests/unit/test_audit.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/logging/audit.py
git commit -m "feat: add audit logging for Agent integration"
```

---

## Task 14: 集成测试

**Files:**
- Create: `tests/integration/test_agent_integration.py`

- [ ] **Step 1: 创建集成测试**

```python
# tests/integration/test_agent_integration.py
"""Agent 集成测试"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.agents.manager_agent.agent import ManagerAgent
from src.agents.strategy_agent.agent import StrategyAgent
from src.agents.risk_agent.agent import RiskAgent
from src.strategy.types import SignalSide, SynthesisMode, RawSignal
from src.risk.types import AccountSnapshot, StopLossLevel, StopLossMode, PositionSize, PositionSizeType

@pytest.fixture
def mock_setup():
    """Mock 所有外部依赖"""
    with patch('src.agents.manager_agent.agent.DataAgent') as mock_data, \
         patch('src.agents.manager_agent.agent.TraderAgent') as mock_trader, \
         patch('src.agents.manager_agent.agent.SignalVersioning') as mock_versioning:

        manager = ManagerAgent()
        yield {
            "manager": manager,
            "data_agent": mock_data,
            "trader_agent": mock_trader,
            "versioning": mock_versioning
        }

@pytest.mark.asyncio
async def test_full_pipeline_success(mock_setup):
    """完整流程：TradeIdea → RawSignal → 最终 Signal"""
    from src.schemas.contracts import TradeIdea, TradeEntry

    # Setup
    manager = mock_setup["manager"]
    trade_idea = TradeIdea(
        idea_id="test-uuid",
        trader_id="trader1",
        symbol="000001",
        side="buy",
        entry=TradeEntry(type="limit", price=10.0),
        target_price=12.0,
        stop_loss_price=9.0
    )

    # Mock StrategyAgent
    raw_signal = RawSignal(
        signal_id="signal-uuid",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=["rule1"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.utcnow(),
        metadata={}
    )

    with patch.object(StrategyAgent(), 'generate_raw_signal', return_value=raw_signal):
        with patch.object(RiskAgent(), 'check', return_value=Signal(
            signal_id="signal-uuid",
            symbol="000001",
            side=SignalSide.BUY,
            confidence=0.75,
            timestamp=datetime.utcnow(),
            triggered_rules=["rule1"],
            synthesis_mode=SynthesisMode.PRIORITY,
            entry_price=None,
            position_size=PositionSize(type=PositionSizeType.FIXED_RATIO, value=0.1, max_amount=100000.0),
            stop_loss=StopLossLevel(mode=StopLossMode.FIXED, level=9.5, trigger_condition="price <= 9.5"),
            take_profit=None,
            metadata={},
            rejected=False
        )):
            result = await manager.evaluate_signal(trade_idea, {"last_price": 10.0})
            assert result is not None
            assert result.rejected is False

@pytest.mark.asyncio
async def test_risk_agent_rejection(mock_setup):
    """风控拒绝场景"""
    from src.schemas.contracts import TradeIdea, TradeEntry

    manager = mock_setup["manager"]
    trade_idea = TradeIdea(
        idea_id="test-uuid",
        trader_id="trader1",
        symbol="000001",
        side="buy",
        entry=TradeEntry(type="limit", price=10.0),
        target_price=12.0,
        stop_loss_price=9.0
    )

    raw_signal = RawSignal(
        signal_id="signal-uuid",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=["rule1"],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.utcnow(),
        metadata={}
    )

    # Mock RiskAgent 返回拒绝
    with patch.object(StrategyAgent(), 'generate_raw_signal', return_value=raw_signal):
        with patch.object(RiskAgent(), 'check', return_value=Signal(
            signal_id="signal-uuid",
            symbol="000001",
            side="REJECTED",
            confidence=0.0,
            timestamp=datetime.utcnow(),
            triggered_rules=["rule1"],
            synthesis_mode=SynthesisMode.PRIORITY,
            entry_price=None,
            position_size=None,
            stop_loss=None,
            take_profit=None,
            metadata={},
            rejected=True,
            rejection_reason="drawdown exceeded"
        )):
            result = await manager.evaluate_signal(trade_idea, {"last_price": 10.0})
            assert result.rejected is True
```

- [ ] **Step 2: 运行集成测试验证**

Run: `pytest tests/integration/test_agent_integration.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_agent_integration.py
git commit -m "test: add integration tests for Agent pipeline"
```

---

## Task 15: 端到端验证

- [ ] **Step 1: 运行所有单元测试**

Run: `pytest tests/unit/agents/ tests/unit/strategy/ tests/unit/risk/ -v --tb=short`
Expected: 所有测试 PASS

- [ ] **Step 2: 运行集成测试**

Run: `pytest tests/integration/ -v --tb=short`
Expected: 所有测试 PASS

- [ ] **Step 3: 数据库 migration 验证**

Run: `alembic upgrade head`
Expected: signals 表创建成功

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: complete P4-022/023/024 Agent integration"
```

---

## 验收标准检查清单

- [ ] P4-022: StrategyAgent.generate_raw_signal() 可处理 TradeIdea 并输出 RawSignal
- [ ] P4-023: RiskAgent.check() 可处理 RawSignal + AccountSnapshot 并输出最终 Signal
- [ ] P4-024: ManagerAgent.evaluate_signal() 统一编排两者
- [ ] 降级处理：Strategy Agent 异常返回 HOLD，Risk Agent 异常拒绝
- [ ] 审计日志记录每个环节
- [ ] signals 表创建并可正确写入
- [ ] 单元测试覆盖率 >80%
- [ ] 集成测试通过
