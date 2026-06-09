# Strategy Agent & Risk Agent 使用说明

## 配置修改指南

### 策略配置（`config/app.template.yaml` / `config/app.yaml` 中的 `strategy` section）

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

### 风控配置（`config/app.template.yaml` / `config/app.yaml` 中的 `risk` section）

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
