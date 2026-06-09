# P4-001~P4-008 Strategy Agent & Risk Agent 设计文档

**日期**: 2026-04-09
**任务**: P4-001~P4-008 策略执行系统 - Strategy Agent + Risk Agent
**状态**: 已批准设计

---

## 一、架构概览

### 1.1 模块组织

```
src/
├── strategy/                 # Strategy Agent（信号生成）
│   ├── __init__.py
│   ├── feature_engine.py    # P4-001 特征计算引擎
│   ├── rule_evaluator.py   # P4-002 规则评估引擎
│   ├── signal_synthesizer.py # P4-003 多规则信号合成
│   ├── signal.py            # P4-004 信号输出格式
│   ├── signal_version.py    # P4-005 信号版本控制
│   └── config.py            # 策略配置
│
├── risk/                    # Risk Agent（风控）
│   ├── __init__.py
│   ├── position_manager.py  # P4-006 头寸管理
│   ├── stop_loss.py        # P4-007 止损设置
│   ├── take_profit.py      # P4-008 止盈策略
│   ├── account.py          # 账户数据管理
│   └── config.py           # 风控配置
│
└── shared/                 # 共享类型和工具
    ├── __init__.py
    ├── types.py            # 共用数据类型（Signal, Position, Order 等）
    └── exceptions.py       # 共用异常
```

### 1.2 核心设计决策

| 决策项 | 选择 | 说明 |
|--------|------|------|
| 模块组织 | `strategy/` + `risk/` 独立目录 | 职责清晰，便于独立演进 |
| 信号合成算法 | 优先级为主 + 投票筛选 + 权重微调 | 符合交易逻辑 |
| 风控关系 | 同步拦截 | 简单直接，信号必定合规 |

---

## 二、Strategy Agent（P4-001~P4-005）

### 2.1 P4-001 特征计算引擎

**功能**: 接收实时行情或预计算特征，输出标准化特征向量。

**输入模式**:
- **实时模式**: 接收 OHLCV 原始数据，自己计算特征（复用 P2-015 特征库）
- **预计算模式**: 接收已计算好的 `FeatureVector`（`src/features/feature_pipeline.py`）

**核心接口**:

```python
class FeatureEngine:
    """特征计算引擎"""

    def compute_realtime(
        self,
        bars: DailyBars | list[dict],  # OHLCV 数据
        mode: Literal["pandas", "polars", "pure_python"] = "pure_python",
    ) -> FeatureVector:
        """实时计算特征"""
        ...

    def from_precomputed(self, feature_vector: FeatureVector) -> FeatureVector:
        """直接返回预计算特征"""
        return feature_vector

    def compute_batch(
        self,
        items: list[tuple[str, DailyBars]],  # [(symbol, bars), ...]
        mode: Literal["pandas", "polars", "pure_python"] = "pure_python",
    ) -> dict[str, FeatureVector]:
        """批量计算多标的特征"""
        ...
```

**复用**:
- `src/features/feature_pipeline.py` - `compute_features()`, `FeatureVector`
- `src/indicators/engine.py` - 技术指标（RSI, MACD, Bollinger 等）

### 2.2 P4-002 规则评估引擎

**功能**: 将 DSL 规则（`CompiledRule`）作用于特征向量，返回匹配结果。

**核心接口**:

```python
class RuleEvaluator:
    """规则评估引擎"""

    def __init__(self, executor: DSLExecutor):
        self._executor = executor

    def evaluate(
        self,
        rules: list[CompiledRule],
        features: FeatureVector,
        market_state: MarketState,
    ) -> list[RuleMatch]:
        """评估单标的规则匹配"""
        ...

    def evaluate_batch(
        self,
        rules: list[CompiledRule],
        features_map: dict[str, FeatureVector],
        market_state: MarketState,
    ) -> dict[str, list[RuleMatch]]:
        """批量评估多标的规则匹配"""
        ...

@dataclass
class RuleMatch:
    """单条规则匹配结果"""
    rule_id: str
    rule_type: str           # entry/exit/filter/sizing/risk
    matched: bool
    confidence: float        # 0-1
    action: ActionSpec       # 触发动作
```

**复用**:
- `src/persona/dsl_executor.py` - `DSLExecutor`, `CompiledRule`
- `src/persona/dsl_compiler.py` - `CompiledRule`

### 2.3 P4-003 多规则信号合成

**功能**: 将多条规则匹配结果合成为最终信号。

**合成模式**（可配置）:

```python
class SynthesisMode(StrEnum):
    WEIGHTED_SCORE = "weighted_score"   # 加权评分
    VOTING = "voting"                    # 投票机制
    PRIORITY = "priority"                # 优先级覆盖

class SignalSynthesizer:
    """多规则信号合成器"""

    def __init__(
        self,
        mode: SynthesisMode = SynthesisMode.PRIORITY,
        weights: dict[str, float] | None = None,  # rule_type -> weight
        priorities: list[str] | None = None,       # rule_type 优先级顺序
    ):
        ...

    def synthesize(
        self,
        matches: list[RuleMatch],
        context: SynthesisContext,
    ) -> RawSignal:
        """合成信号"""
        ...
```

**合成算法**:

1. **加权评分模式 (Weighted Score)**:
   - 每条规则根据 `rule_type` 和 `confidence` 计算得分
   - 最终得分 = Σ(weight[rule_type] * confidence * matched)
   - 阈值判定: >0.6 → BUY, <0.4 → SELL, 其他 → HOLD

2. **投票模式 (Voting)**:
   - 按 side (BUY/SELL/HOLD) 统计票数
   - 少数服从多数，平票 → HOLD

3. **优先级模式 (Priority)** (默认):
   - 优先级顺序: `risk > filter > exit > sizing > entry`
   - 高优先级规则覆盖低优先级
   - 同优先级规则用加权评分

### 2.4 P4-004 信号输出格式

**Signal 数据结构**:

```python
@dataclass
class Signal:
    """交易信号"""
    # === 基础信息 ===
    signal_id: str                    # 唯一标识（UUID）
    symbol: str                       # 标的代码
    side: SignalSide                  # BUY / SELL / HOLD
    confidence: float                  # 置信度 0-1
    timestamp: datetime               # 生成时间

    # === 触发规则 ===
    triggered_rules: list[str]        # 触发的规则 ID 列表
    synthesis_mode: SynthesisMode     # 合成模式

    # === 执行参数 ===
    entry_price: PriceSpec | None    # 入场价格规格
    position_size: PositionSize | None  # 头寸规格
    stop_loss: StopLossSpec | None   # 止损规格
    take_profit: TakeProfitSpec | None  # 止盈规格

    # === 元数据 ===
    version: str = "v1"              # 信号版本
    metadata: dict[str, Any] = field(default_factory=dict)


class SignalSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class PriceSpec:
    """价格规格"""
    type: Literal["market", "limit", "trigger"]
    value: float | None = None       # limit price 或 trigger price
    offset_pct: float | None = None  # 相对于当前价格的百分比偏移


@dataclass
class PositionSize:
    """头寸规格"""
    type: PositionSizeType            # FIXED_AMOUNT / FIXED_RATIO / VOLATILITY_ADJUSTED
    value: float                      # 金额或比例
    max_amount: float | None = None   # 最大金额限制
```

### 2.5 P4-005 信号版本控制

**功能**: 记录信号生成过程中的所有输入和决策，支持回放和审计。

```python
class SignalVersioning:
    """信号版本控制"""

    def __init__(self, storage_path: Path | None = None):
        self._storage_path = storage_path

    def record(self, signal: Signal, context: SignalContext) -> str:
        """记录信号及其上下文"""
        ...

    def get_version(self, signal_id: str) -> SignalWithContext:
        """获取信号完整版本"""
        ...

    def list_versions(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SignalWithContext]:
        """列出信号版本"""
        ...


@dataclass
class SignalContext:
    """信号生成上下文"""
    features_snapshot: dict[str, Any]  # 特征快照
    market_state: dict[str, Any]       # 市场状态快照
    rules_snapshot: list[dict[str, Any]]  # 规则快照
    timestamp: datetime
```

---

## 三、Risk Agent（P4-006~P4-008）

### 3.1 P4-006 头寸管理模块

**功能**: 根据账户净值、风险偏好计算持仓数量。

**计算模式**:

```python
class PositionSizeMode(StrEnum):
    FIXED_AMOUNT = "fixed_amount"           # 固定金额
    FIXED_RATIO = "fixed_ratio"             # 固定比例（净值 %）
    VOLATILITY_ADJUSTED = "volatility_adjusted"  # 波动率调整


@dataclass
class PositionManager:
    """头寸管理器"""

    def __init__(
        self,
        mode: PositionSizeMode = PositionSizeMode.FIXED_RATIO,
        config: PositionConfig | None = None,
        account: AccountService | None = None,  # None = 模拟账户
    ):
        ...

    def calculate_size(
        self,
        signal: Signal,
        account: AccountSnapshot,
        market_data: MarketData,
    ) -> PositionSize:
        """计算头寸"""
        ...


@dataclass
class PositionConfig:
    """头寸配置"""
    # 固定金额模式
    fixed_amount: float = 10_000.0

    # 固定比例模式
    fixed_ratio_pct: float = 0.05        # 每次投入账户净值的 5%

    # 波动率调整模式
    target_volatility: float = 0.15       # 目标波动率 15%
    vol_window: int = 20                 # 波动率计算窗口

    # 通用限制
    max_position_pct: float = 0.20        # 单标的最大占总净值比例
    max_single_position: float = 50_000.0  # 单标的最大金额
```

**计算公式**:

1. **固定金额**: `size = floor(fixed_amount / price)`
2. **固定比例**: `size = floor(account.net_value * fixed_ratio_pct / price)`
3. **波动率调整**: `size = floor(target_volatility / atr_ratio * account.net_value / price)`

### 3.2 P4-007 止损设置

**功能**: 根据不同策略计算止损价格。

```python
class StopLossMode(StrEnum):
    FIXED = "fixed"                      # 固定止损
    VOLATILITY = "volatility"           # 波动率止损
    TRAILING = "trailing"               # 回撤止损
    TIME = "time"                        # 时间止损


@dataclass
class StopLossCalculator:
    """止损计算器"""

    def __init__(self, config: StopLossConfig):
        ...

    def calculate(
        self,
        entry_price: float,
        signal: Signal,
        market_data: MarketData,
    ) -> StopLossLevel | None:
        """计算止损"""
        ...


@dataclass
class StopLossConfig:
    """止损配置"""
    mode: StopLossMode = StopLossMode.VOLATILITY

    # 固定止损
    fixed_pct: float = 0.05             # 跌破 5% 止损

    # 波动率止损
    atr_multiplier: float = 2.0          # N * ATR
    atr_window: int = 14                 # ATR 窗口

    # 回撤止损
    drawdown_pct: float = 0.10          # 从高点回撤 10%

    # 时间止损
    max_hold_days: int = 10             # 最多持有 10 天


@dataclass
class StopLossLevel:
    """止损级别"""
    mode: StopLossMode
    level: float                        # 止损价格
    trigger_condition: str              # 触发条件描述
```

### 3.3 P4-008 止盈策略

**功能**: 根据不同策略计算止盈价格。

```python
class TakeProfitMode(StrEnum):
    FIXED = "fixed"                     # 固定止盈
    SCALING = "scaling"                 # 分批止盈
    TRAILING = "trailing"               # 移动止损
    TIME = "time"                       # 时间止盈


@dataclass
class TakeProfitCalculator:
    """止盈计算器"""

    def __init__(self, config: TakeProfitConfig):
        ...

    def calculate(
        self,
        entry_price: float,
        signal: Signal,
        market_data: MarketData,
    ) -> list[TakeProfitLevel]:
        """计算止盈（可能多个级别）"""
        ...


@dataclass
class TakeProfitConfig:
    """止盈配置"""
    mode: TakeProfitMode = TakeProfitMode.SCALING

    # 固定止盈
    fixed_pct: float = 0.15             # 上涨 15% 止盈

    # 分批止盈
    scaling_levels: list[ScalingLevel] = field(default_factory=lambda: [
        ScalingLevel(target_pct=0.05, close_pct=0.50),   # +5% 卖 50%
        ScalingLevel(target_pct=0.10, close_pct=0.30),   # +10% 再卖 30%
        ScalingLevel(target_pct=0.20, close_pct=0.20),   # +20% 最后卖 20%
    ])

    # 移动止损
    trailing_pct: float = 0.05           # 从高点回撤 5%

    # 时间止盈
    target_hold_days: int = 5            # 持有 5 天后止盈


@dataclass
class ScalingLevel:
    """分批止盈级别"""
    target_pct: float                   # 目标涨幅
    close_pct: float                    # 卖出比例（0-1）


@dataclass
class TakeProfitLevel:
    """止盈级别"""
    mode: TakeProfitMode
    level: float                        # 目标价格
    close_pct: float                    # 卖出比例（分批止盈用）
    trigger_condition: str              # 触发条件描述
```

---

## 四、模拟账户（数据库持久化）

### 4.1 账户数据模型

```python
# 复用已有的 trade_logs 表结构
# 位置: src/models/ 定义（见 P1-007）

class SimulatedAccount:
    """模拟账户"""

    def __init__(self, session: Session):
        self._session = session

    async def get_snapshot(self, account_id: str) -> AccountSnapshot:
        """获取账户快照"""
        ...

    async def update_position(
        self,
        account_id: str,
        symbol: str,
        side: str,       # buy/sell
        quantity: float,
        price: float,
    ) -> TradeRecord:
        """更新持仓（记录交易）"""
        ...

    async def get_positions(self, account_id: str) -> list[Position]:
        """获取当前持仓"""
        ...
```

### 4.2 账户快照

```python
@dataclass
class AccountSnapshot:
    """账户快照"""
    account_id: str
    timestamp: datetime
    net_value: float                    # 账户净值
    cash: float                         # 现金
    total_position_value: float         # 总持仓市值
    positions: list[Position]           # 持仓列表
    daily_pnl: float                    # 当日盈亏
    total_pnl: float                    # 累计盈亏


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_cost: float                     # 平均成本
    current_price: float               # 当前价格
    market_value: float                # 市值
    unrealized_pnl: float              # 未实现盈亏
    unrealized_pnl_pct: float           # 未实现盈亏 %
```

---

## 五、配置方法

### 5.1 配置结构

```yaml
# config/strategy.yaml

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
  db_session_factory: "src.db.session"
```

### 5.2 配置加载

```python
# src/strategy/config.py
from pydantic import BaseModel
from functools import lru_cache

class StrategyConfig(BaseModel):
    feature_engine: FeatureEngineConfig
    rule_evaluator: RuleEvaluatorConfig
    signal_synthesizer: SignalSynthesizerConfig

class RiskConfig(BaseModel):
    position_manager: PositionConfig
    stop_loss: StopLossConfig
    take_profit: TakeProfitConfig

class SimulatedAccountConfig(BaseModel):
    enabled: bool = True
    initial_capital: float = 100_000.0
    persist_to_db: bool = True

@lru_cache
def get_strategy_config() -> StrategyConfig:
    """获取策略配置（单例）"""
    ...

@lru_cache
def get_risk_config() -> RiskConfig:
    """获取风控配置（单例）"""
    ...

@lru_cache
def get_simulated_account_config() -> SimulatedAccountConfig:
    """获取模拟账户配置（单例）"""
    ...
```

### 5.3 配置文件路径约定

| 文件 | 路径 | 说明 |
|------|------|------|
| 策略配置 | `config/strategy.yaml` | Strategy Agent 配置 |
| 风控配置 | `config/risk.yaml` | Risk Agent 配置 |
| 账户配置 | `config/account.yaml` | 模拟账户/真实账户配置 |

---

## 六、核心流程

### 6.1 信号生成流程

```
输入: symbol + bar/market_state (实时或批量)

1. 特征计算 (FeatureEngine)
   └── 实时模式: compute_features(bars) → FeatureVector
   └── 预计算模式: 直接返回 FeatureVector

2. 规则评估 (RuleEvaluator)
   └── rules.matches(state=market_state, bar=features) → list[RuleMatch]

3. 信号合成 (SignalSynthesizer)
   └── synthesize(matches) → RawSignal (未经过风控)

4. 风控拦截 (RiskAgent - 同步)
   ├── 头寸计算 (PositionManager)
   │   └── calculate_size(signal, account) → PositionSize
   ├── 止损计算 (StopLossCalculator)
   │   └── calculate(entry_price, signal) → StopLossLevel
   └── 止盈计算 (TakeProfitCalculator)
       └── calculate(entry_price, signal) → list[TakeProfitLevel]

5. 信号输出 (Signal)
   └── Signal(side, confidence, position_size, stop_loss, take_profit, ...)
```

### 6.2 批量处理流程

```
输入: [(symbol, bar, market_state), ...]

1. 批量特征计算
   └── compute_batch(items) → {symbol: FeatureVector}

2. 规则评估（批量）
   └── evaluate_batch(rules, features_map) → {symbol: list[RuleMatch]}

3. 信号合成（按标的）
   └── for each symbol: synthesize(matches) → RawSignal

4. 风控检查（批量）
   └── for each signal: apply_risk(signal, account) → Signal | None

5. 输出
   └── list[Signal] (过滤掉被风控拦截的)
```

---

## 七、错误处理

### 7.1 异常类型

```python
class StrategyError(Exception):
    """策略执行异常"""
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
    """风控异常"""
    pass

class PositionLimitExceeded(RiskError):
    """头寸超限"""
    pass

class RiskBlockedError(RiskError):
    """风控拦截"""
    pass
```

### 7.2 错误处理策略

| 场景 | 处理策略 |
|------|----------|
| 特征计算失败 | 返回空信号，side=HOLD，记录错误 |
| 规则评估超时 | 跳过该规则，继续评估其他规则 |
| 无有效规则匹配 | 返回 side=HOLD |
| 风控拦截 | 返回 side=HOLD + 拦截原因 |
| 账户数据不可用 | 使用默认风控参数，记录警告 |

---

## 八、数据流图

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                      Strategy Agent                         │
                    │  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐  │
  Market Data ──────▶│  │   Feature   │───▶│    Rule      │───▶│    Signal       │  │
  (OHLCV)            │  │   Engine     │    │   Evaluator  │    │   Synthesizer   │  │
                    │  │  (P4-001)    │    │   (P4-002)   │    │   (P4-003)      │  │
                    │  └─────────────┘    └──────────────┘    └─────────────────┘  │
                    │                                                   │           │
                    │                    ┌──────────────────────────────▼────────┐  │
                    │                    │         Risk Agent                    │  │
                    │                    │  ┌────────────┐   ┌────────────────┐   │  │
                    └───────────────────▶│  │  Position  │──▶│  StopLoss /    │   │  │
                                         │  │  Manager   │   │  TakeProfit    │   │  │
                                         │  │  (P4-006)  │   │  (P4-007/008)  │   │  │
                                         │  └────────────┘   └────────────────┘   │  │
                                         └───────────────────────┬────────────────┘  │
                                                             │                       │
                    ┌────────────────────────────────────────▼────────────────────┐ │
                    │                     Signal Output                            │ │
                    │   Signal(side, confidence, position_size, stop_loss, ...)     │ │
                    └───────────────────────────────────────────────────────────────┘ │
                                                             │
                    ┌────────────────────────────────────────▼────────────────────┐ │
                    │                  Simulated Account (DB)                     │ │
                    │   TradeRecord → Position → AccountSnapshot → persist        │ │
                    └────────────────────────────────────────────────────────────┘ │
```

---

## 九、测试策略

### 9.1 单元测试

| 模块 | 测试内容 | 目标覆盖率 |
|------|----------|-----------|
| FeatureEngine | 实时计算、预计算、批量计算 | >80% |
| RuleEvaluator | 规则匹配、超时处理 | >80% |
| SignalSynthesizer | 三种合成模式、边界条件 | >85% |
| PositionManager | 三种头寸计算模式 | >85% |
| StopLossCalculator | 四种止损策略 | >85% |
| TakeProfitCalculator | 四种止盈策略 | >85% |

### 9.2 集成测试

| 测试 | 说明 |
|------|------|
| 端到端信号生成 | 实时行情 → 信号输出 |
| 风控拦截验证 | 不合格信号被正确拦截 |
| 批量处理性能 | 100 标的 < 1 秒 |

---

## 十、文件清单

| 文件 | 路径 | 任务 |
|------|------|------|
| `feature_engine.py` | `src/strategy/` | P4-001 |
| `rule_evaluator.py` | `src/strategy/` | P4-002 |
| `signal_synthesizer.py` | `src/strategy/` | P4-003 |
| `signal.py` | `src/strategy/` | P4-004 |
| `signal_version.py` | `src/strategy/` | P4-005 |
| `position_manager.py` | `src/risk/` | P4-006 |
| `stop_loss.py` | `src/risk/` | P4-007 |
| `take_profit.py` | `src/risk/` | P4-008 |
| `account.py` | `src/risk/` | 账户管理 |
| `config.py` | `src/strategy/` | 策略配置 |
| `config.py` | `src/risk/` | 风控配置 |
| `types.py` | `src/shared/` | 共享类型 |
| `exceptions.py` | `src/shared/` | 共享异常 |

---

## 十一、依赖关系

```
P4-001 FeatureEngine ──────────────────────┐
                                              ├── P4-004 Signal
P4-002 RuleEvaluator ────────────────────────┤
                                              │
P4-003 SignalSynthesizer ────────────────────┼──┐
                                              │  │
P4-005 SignalVersioning ──────────────────────┘  │
                                                  ├── RiskAgent ── P4-006/007/008
StrategyAgent ───────────────────────────────────┘
```
