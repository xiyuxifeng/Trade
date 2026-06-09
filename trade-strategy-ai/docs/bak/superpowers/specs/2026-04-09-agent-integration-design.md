# P4-022/023/024 Agent 集成设计文档

**日期**：2026-04-09
**状态**：草稿
**关联任务**：P4-022, P4-023, P4-024

---

## 1. 背景与目标

### 1.1 当前状态

- **Strategy Agent**：`src/agents/strategy_agent/agent.py` 为空壳，核心逻辑在 `src/strategy/` 模块（P4-001~P4-005）
- **Risk Agent**：`src/agents/risk_agent/agent.py` 为空壳，核心逻辑在 `src/risk/` 模块（P4-006~P4-012）
- **ManagerAgent**：已编排 DataAgent + TraderAgent，尚未集成 Strategy/Risk Agent
- **SignalVersioning**：P4-025 已实现 TradeIdea → Signal 的持久化

### 1.2 目标

- P4-022：实现 Strategy Agent 主控逻辑（信号合成）
- P4-023：实现 Risk Agent 主控逻辑（风控检查）
- P4-024：实现两个 Agent 的通信接口

### 1.3 设计原则

- **最小改动**：复用 `src/strategy/` 和 `src/risk/` 已有实现
- **接口与实现分离**：通过 Skill 机制调用核心模块
- **审计可追溯**：标准审计日志
- **可扩展性**：抽象接口便于未来扩展

---

## 2. 架构设计

### 2.1 整体架构

```
ManagerAgent
├── DataAgent (获取 AccountSnapshot)
├── TraderAgent (生成 TradeIdea)
│
├── StrategyAgent (信号合成)
│   ├── 输入: TradeIdea + MarketData + Features
│   ├── Skill 层: compute_features, evaluate_rules, combine_scores, generate_signal
│   ├── 调用: src/strategy/ (FeatureEngine, RuleEvaluator, SignalSynthesizer)
│   └── 输出: RawSignal
│
└── RiskAgent (风控检查)
    ├── 输入: RawSignal + AccountSnapshot
    ├── Skill 层: drawdown_control, stop_loss, position_sizing
    ├── 调用: src/risk/ (RiskMonitor, StopLossCalculator, PositionManager)
    └── 输出: 最终 Signal (rejected=False) 或 拒绝信号 (rejected=True)
```

### 2.2 数据流

```
TraderAgent 生成 TradeIdea
    ↓
ManagerAgent 编排
    ↓
StrategyAgent.compute_features()  ← Skill: compute_features.py
    ↓ (features)
StrategyAgent.evaluate_rules()    ← Skill: evaluate_rules.py
    ↓ (rule_matches)
StrategyAgent.combine_scores()    ← Skill: combine_scores.py
    ↓
StrategyAgent.generate_signal()  ← Skill: generate_signal.py
    ↓ (RawSignal)
ManagerAgent 获取 AccountSnapshot (via DataAgent)
    ↓
RiskAgent.drawdown_control()      ← Skill: drawdown_control.py
    ↓
RiskAgent.stop_loss()             ← Skill: stop_loss.py
    ↓
RiskAgent.position_sizing()       ← Skill: position_sizing.py
    ↓
RiskAgent.check_and_alert()       ← 综合风控检查
    ↓ (最终 Signal)
SignalVersioning + PostgreSQL 存储
```

---

## 3. 接口设计

### 3.1 Strategy Agent Skill 接口

```python
# src/agents/strategy_agent/skills/compute_features.py
async def compute_features(
    symbol: str,
    market_data: dict[str, Any],
    context: dict[str, Any]
) -> dict[str, float]:
    """计算特征，返回特征名→值的字典"""
    pass

# src/agents/strategy_agent/skills/evaluate_rules.py
async def evaluate_rules(
    features: dict[str, float],
    rules: list[dict[str, Any]]
) -> list[RuleMatch]:
    """评估规则，返回匹配的规则列表"""
    pass

# src/agents/strategy_agent/skills/combine_scores.py
async def combine_scores(
    rule_matches: list[RuleMatch],
    mode: SynthesisMode
) -> dict[str, Any]:
    """组合分数，返回 {side, confidence, triggered_rules}"""
    pass

# src/agents/strategy_agent/skills/generate_signal.py
async def generate_signal(
    symbol: str,
    side: SignalSide,
    confidence: float,
    triggered_rules: list[str],
    synthesis_mode: SynthesisMode,
    context: dict[str, Any]
) -> RawSignal:
    """生成原始信号"""
    pass
```

### 3.2 Risk Agent Skill 接口

```python
# src/agents/risk_agent/skills/drawdown_control.py
async def drawdown_control(
    account: AccountSnapshot,
    signal: RawSignal
) -> dict[str, Any]:
    """回撤控制检查，返回检查结果"""
    pass

# src/agents/risk_agent/skills/stop_loss.py
async def stop_loss(
    signal: RawSignal,
    market_data: dict[str, Any],
    config: dict[str, Any]
) -> StopLossLevel:
    """计算止损水平"""
    pass

# src/agents/risk_agent/skills/position_sizing.py
async def position_sizing(
    signal: RawSignal,
    account: AccountSnapshot,
    config: dict[str, Any]
) -> PositionSize:
    """计算头寸大小"""
    pass
```

### 3.3 ManagerAgent 编排接口

```python
class ManagerAgent:
    async def evaluate_signal(
        self,
        trade_idea: TradeIdea,
        market_data: dict[str, Any]
    ) -> Signal | None:
        """评估交易想法，返回最终 Signal 或 None（拒绝）"""
        # 1. StrategyAgent 生成 RawSignal
        raw_signal = await self.strategy_agent.generate_signal(
            trade_idea, market_data
        )

        # 2. 获取 AccountSnapshot
        account = await self.data_agent.get_account_snapshot()

        # 3. RiskAgent 风控检查
        final_signal = await self.risk_agent.check(
            raw_signal, account
        )

        # 4. 存储
        if final_signal and not final_signal.rejected:
            await self.signal_versioning.record(final_signal)
            await self.db_store_signal(final_signal)
        elif final_signal and final_signal.rejected:
            await self.signal_versioning.record_rejected(final_signal)

        return final_signal
```

---

## 4. 错误处理

### 4.1 降级处理策略

| Agent | 异常类型 | 降级行为 |
|-------|----------|----------|
| Strategy Agent | 任何异常 | 返回 `side=HOLD` 的 RawSignal |
| Risk Agent | 任何异常 | 拒绝信号（`rejected=True`） |

### 4.2 降级信号结构

```python
@dataclass
class RawSignal:
    # ... 已有字段 ...
    degraded: bool = False
    degradation_reason: str | None = None

@dataclass
class Signal:
    # ... 已有字段 ...
    rejected: bool = False
    rejection_reason: str | None = None
```

---

## 5. 数据库设计

### 5.1 signals 表

```sql
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    signal_id UUID NOT NULL UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- BUY, SELL, HOLD, REJECTED
    confidence FLOAT,
    triggered_rules JSONB,
    synthesis_mode VARCHAR(20),
    entry_price JSONB,
    position_size JSONB,
    stop_loss JSONB,
    take_profit JSONB,
    rejected BOOLEAN DEFAULT FALSE,
    rejection_reason TEXT,
    degraded BOOLEAN DEFAULT FALSE,
    degradation_reason TEXT,
    version VARCHAR(10),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_created_at ON signals(created_at);
CREATE INDEX idx_signals_signal_id ON signals(signal_id);
```

---

## 6. 审计日志

### 6.1 日志内容

每个 Agent 调用记录：
- 调用时间戳
- 输入参数（脱敏后）
- 输出结果
- 耗时（ms）
- 异常信息（如有）

### 6.2 日志格式

```json
{
    "timestamp": "2026-04-09T10:30:00Z",
    "agent": "strategy_agent",
    "action": "generate_signal",
    "input": {
        "symbol": "000001",
        "trade_idea_id": "uuid"
    },
    "output": {
        "signal_id": "uuid",
        "side": "BUY",
        "confidence": 0.75
    },
    "duration_ms": 45,
    "error": null
}
```

---

## 7. 盘中实时 vs 盘后批量

### 7.1 流程差异

| 维度 | 盘中实时 | 盘后批量 |
|------|----------|----------|
| 触发时机 | TraderAgent 生成 TradeIdea | run_after_close() |
| 处理流程 | 相同 | 相同 |
| 结果 | 立即存储 | 批量存储 |

### 7.2 关键决策

- 盘中实时和盘后批量**使用相同流程**，仅触发时机不同
- 盘后批量不对已有 Signal 进行覆写，而是生成**新版本**
- 盘后复盘评估（P3-101）是独立流程，不走 StrategyAgent + RiskAgent

---

## 8. 未来扩展点

### 8.1 外部信号源接入

**技术债务标记**：以下接口需要抽象，便于未来扩展

```python
class SignalProvider(ABC):
    """信号提供者接口"""
    @abstractmethod
    async def fetch_signals(self, context: dict) -> list[TradeIdea]:
        pass

# 当前实现：仅 TraderAgent
class TraderAgentSignalProvider(SignalProvider):
    async def fetch_signals(self, context: dict) -> list[TradeIdea]:
        # 调用 TraderAgent
        pass

# 未来可扩展：外部 API、爬虫、第三方量化等
class ExternalSignalProvider(SignalProvider):
    async def fetch_signals(self, context: dict) -> list[TradeIdea]:
        # 调用外部 API
        pass
```

### 8.2 AccountSnapshot 来源

当前由 ManagerAgent 通过 DataAgent 获取，未来可考虑：
- Risk Agent 自己维护账户状态
- 独立账户服务

---

## 9. 实现计划

### 9.1 P4-022: Strategy Agent 主控逻辑

1. 实现 `skills/compute_features.py`
2. 实现 `skills/evaluate_rules.py`
3. 实现 `skills/combine_scores.py`
4. 实现 `skills/generate_signal.py`
5. 实现 `agent.py` 编排逻辑
6. 单元测试

### 9.2 P4-023: Risk Agent 主控逻辑

1. 实现 `skills/drawdown_control.py`
2. 实现 `skills/stop_loss.py`
3. 实现 `skills/position_sizing.py`
4. 实现 `agent.py` 编排逻辑
5. 单元测试

### 9.3 P4-024: ManagerAgent 集成

1. 扩展 `run_pre_market()` 调用 `evaluate_signal()`
2. 扩展 `run_after_close()` 批量调用
3. 数据库表创建 Alembic migration
4. 集成测试

---

## 10. 验收标准

- [ ] P4-022: Strategy Agent 可处理 TradeIdea 并输出 RawSignal
- [ ] P4-023: Risk Agent 可处理 RawSignal + AccountSnapshot 并输出最终 Signal
- [ ] P4-024: ManagerAgent 统一编排两者
- [ ] 降级处理：Strategy Agent 异常返回 HOLD，Risk Agent 异常拒绝
- [ ] 审计日志记录每个环节
- [ ] signals 表创建并可正确写入
- [ ] 单元测试覆盖率 >80%
