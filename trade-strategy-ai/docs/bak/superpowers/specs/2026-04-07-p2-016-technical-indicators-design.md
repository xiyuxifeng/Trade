# P2-016 Technical Indicators — Pattern Feature Library Design

## 目标

为 canonical pattern 匹配系统构建可扩展的特征计算层。输入 OHLCV 数据，输出 canonical YAML 规则所需的所有派生特征，并提供 `evaluate_condition(field, op, value)` 判断接口，供 Pattern Matcher 直接调用。

---

## 架构定位

```
OHLCV 数据
    │
    ▼
┌─────────────────────────────────────────┐
│  src/indicators/pattern_features.py      │
│  PatternFeatureEngine                    │
│  ┌─────────────────────────────────────┐ │
│  │  基础特征（纯函数，直接算）           │ │
│  │  volume_ratio, price_vs_ma,          │ │
│  │  ma_slope, distance_from_high/low   │ │
│  │  gap_ratio, price_volatility        │ │
│  │  atr_ratio, close_position          │ │
│  │  high/low_breakout_ratio            │ │
│  └─────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┐ │
│  │  指标特征（惰性计算 + 缓存）          │ │
│  │  rsi, stoch_k, macd_histogram       │ │
│  │  bb_width, bb_position             │ │
│  │  cci, ma50, ma200                  │ │
│  └─────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┐ │
│  │ 形态特征（跨多根 bar 识别）           │ │
│  │  price_shape, body, upper/lower_    │ │
│  │  shadow, gap, trend, breakout       │ │
│  │  support, resistance, neckline     │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
    │ 特征字典 {field_name: value} + evaluate_condition()
    ▼
Pattern Matcher / DSL Engine / LLM Rules（调用方）
```

现有 `src/indicators/engine.py`（SMA/EMA/MACD/RSI/Bollinger/ATR/Stochastic）作为底层依赖，`pattern_features.py` 调用它们并组合出派生特征。

---

## 核心 API

### PatternFeatures dataclass

```python
@dataclass
class PatternFeatures:
    """计算出的所有模式特征。"""

    # 基础特征（纯函数计算）
    volume_ratio: float
    price_vs_ma: float
    ma_slope: float
    distance_from_high: float
    distance_from_low: float
    gap_ratio: float
    price_volatility: float
    atr_ratio: float
    close_position: float
    high_breakout_ratio: float
    low_breakout_ratio: float

    # 指标特征（惰性计算，None 表示未计算）
    rsi: float | None
    stoch_k: float | None
    macd_histogram: float | None
    bb_width: float | None        # (上轨-下轨)/中轨
    bb_position: float | None     # 价格在布林带中的位置
    cci: float | None
    ma50: float | None
    ma200: float | None

    # 形态特征（字符串或 None）
    price_shape: str | None   # head_shoulder_bottom, double_bottom, cup_handle...
    body: str | None         # doji, engulf, small
    upper_shadow: str | None # tiny, long, gt_pct, lt_pct
    lower_shadow: str | None
    trend: str | None        # up, down
    breakout: str | None     # up, down, any
    gap: str | None          # up, down, between, isolated
    gap_range: str | None    # isolated
    gap_fill: str | None     # none
    support: str | None      # rising, horizontal, higher_low
    resistance: str | None   # falling, horizontal
    neckline: str | None    # breakout_up, breakout_down
    candle1: str | None     # bullish_long, bearish_long...
    candle2: str | None
    candle3: str | None
    curr_candle: str | None  # bullish, bearish
    prev_candle: str | None
    price_action: str | None # gap_down...
    sequence: str | None     # higher_close, lower_close
    handle_depth: str | None # lt_pct
    pennant: str | None      # converging
    pole: str | None         # steep_up, steep_down
    flag_channel: str | None # up_sloping, down_sloping
    channel: str | None      # horizontal
    price_range: str | None  # narrow, wide
    trendline_lower: str | None  # rising, falling_fast...
    trendline_upper: str | None  # falling, rising_slow...
    macd: str | None         # cross_up, cross_down（从 MACDResult.histogram 交叉判断）
    first_candle: str | None
    second_candle: str | None
    third_candle: str | None
```

### PatternFeatureEngine

```python
class PatternFeatureEngine:
    """从 OHLCV 计算 canonical pattern 所需特征。"""

    def __init__(self, bars: list):
        """
        Args:
            bars: 按时间升序的 OHLCV 列表，每项为 dataclass 或 dict，
                 包含 open/high/low/close/volume 字段。
        """
        self.bars = bars
        self._cache: dict[str, Any] = {}
        self._ohlcv = self._to_arrays()

    def compute_all(self) -> PatternFeatures:
        """计算全部特征（基础 + 指标 + 形态）。"""
        ...

    def compute_fields(self, required_fields: list[str]) -> dict[str, Any]:
        """按需计算指定字段列表。"""
        ...

    def evaluate_condition(self, field: str, op: str, value: Any = None) -> bool:
        """给定 field/op/value，返回条件是否满足。

        这是核心判断接口，供 Pattern Matcher 直接调用。

        Examples:
            evaluate_condition("rsi", "lower_high", None)
            evaluate_condition("volume", "spike_3x", None)
            evaluate_condition("bb_width", "narrow", None)
            evaluate_condition("rsi", "cross_below", 70)
        """
        ...
```

---

## 字段分类与计算

### A. 基础特征（纯函数，直接算）

| 字段 | 计算逻辑 | Canonical op |
|---|---|---|
| `volume_ratio` | 成交量 / 20日均量 | `spike_3x`, `spike`, `confirm`, `drying_up`, `increasing`, `decreasing`, `u_shape` |
| `price_vs_ma` | 价格 / MA20 | `consolidation`, `breakout`, `test_level` |
| `ma_slope` | MA5斜率（近期5日均值 vs 前5日均值） | `up`, `down` |
| `distance_from_high` | (高点 - 价格) / 高点 | `higher_high`, `lower_high` |
| `distance_from_low` | (价格 - 低点) / 低点 | `higher_low`, `lower_low` |
| `gap_ratio` | (今日开盘 - 昨收盘) / 昨收盘 | `up`, `down`, `between` |
| `price_volatility` | 5日收盘价 std / mean | `narrow`, `wide` |
| `atr_ratio` | ATR / 收盘价 | 归一化辅助 |
| `close_position` | (收盘 - 低点) / (高点 - 低点) | `reversal_next` |
| `high_breakout_ratio` | (价格 - 日高点) / 日高点 | `up` (breakout) |
| `low_breakout_ratio` | (日低点 - 价格) / 日低点 | `down` (breakout) |

### B. 指标特征（调用 engine.py，惰性计算）

| 字段 | 计算逻辑 | Canonical op |
|---|---|---|
| `rsi` | RSI(14) 最新值 | `cross_above`, `cross_below`, `higher_low`, `lower_high` |
| `stoch_k` | Stochastic %K | `cross_above`, `cross_below`, `gt`, `lt` |
| `macd_histogram` | MACD 直方图 | `cross_down`, `cross_up`, `higher_low`, `lower_high` |
| `bb_width` | (上轨 - 下轨) / 中轨 | `narrow`, `squeeze_confirm` |
| `bb_position` | (价格 - 下轨) / (上轨 - 下轨) | 支撑/阻力辅助 |
| `cci` | CCI(14) | `cross_above`, `cross_below`, `higher_low`, `lower_high` |
| `ma50` | SMA(50) | `cross_above`, `cross_below` |
| `ma200` | SMA(200) | `cross_above`, `cross_below` |

### C. 单日形态特征

| 字段 | op 示例 | 计算逻辑 |
|---|---|---|
| `body` | `small`, `doji`, `engulf` | 实体长度 vs 整日振幅 |
| `upper_shadow` | `tiny`, `long`, `gt_pct(60)`, `lt_pct(10)` | 上影线 vs 实体 |
| `lower_shadow` | `tiny`, `long`, `gt_pct(60)`, `lt_pct(10)` | 下影线 vs 实体 |
| `gap` | `up`, `down`, `between`, `isolated` | 跳空类型 |
| `gap_range` | `isolated` | 跳空是否孤立 |
| `gap_fill` | `none` | 是否回补缺口 |
| `candle1/2/3` | `bullish_long`, `bearish_long`, `small_body` | 三根 K 线组合 |
| `curr_candle` | `bullish`, `bearish` | 当前 K 线方向 |
| `prev_candle` | `bullish`, `bearish` | 前一根 K 线方向 |
| `sequence` | `higher_close`, `lower_close` | 连续收盘方向 |
| `handle_depth` | `lt_pct(50)` | 旗形把手深度 |
| `pennant` | `converging` | 旗形收敛 |
| `pole` | `steep_up`, `steep_down` | 旗杆陡峭度 |
| `flag_channel` | `up_sloping`, `down_sloping` | 旗形通道倾斜 |
| `channel` | `horizontal` | 通道方向 |
| `price_range` | `narrow`, `wide` | 价格波动区间宽度 |
| `breakout` | `up`, `down`, `any` | 突破方向 |

### D. 多日形态特征

| 字段 | op 示例 | 计算逻辑 |
|---|---|---|
| `price_shape` | `head_shoulder_bottom`, `double_bottom`, `cup_handle`, `rounding`... | 逐对高低点识别形态 |
| `neckline` | `breakout_up`, `breakout_down` | 颈线突破检测 |
| `trend` | `up`, `down` | 均线方向或高低点趋势 |
| `support` | `rising`, `horizontal`, `higher_low` | 支撑线识别 |
| `resistance` | `falling`, `horizontal` | 阻力线识别 |
| `trendline_lower` | `rising`, `falling_fast` | 下趋势线 |
| `trendline_upper` | `falling`, `rising_slow` | 上趋势线 |
| `first_candle` | `bullish_long`, `bearish_long` | 组合第一根 |
| `third_candle` | `bullish_long`, `bearish_long` | 组合第三根 |
| `price_action` | `gap_down` | 价格行为 |
| `macd` | `cross_up`, `cross_down` | MACD 交叉 |
（`stoch_k`、`rsi`、`cci` 的操作通过 `evaluate_condition()` 判定，不作为独立字段存储）

---

## evaluate_condition 核心逻辑

`op` 是判断逻辑，不是独立特征值。接口返回 `True/False`。

```python
def evaluate_condition(self, field: str, op: str, value: Any = None) -> bool:

    # volume 类
    if field == "volume":
        if op == "spike_3x":   return self.volume_ratio > 3.0
        if op == "spike":      return self.volume_ratio > 2.0
        if op == "confirm":    return self.volume_ratio > 1.2
        if op == "increasing": return self.volume_ratio > 1.0
        if op == "drying_up":  return self.volume_ratio < 0.5
        if op == "dry_up":     return self.volume_ratio < 0.3
        if op == "u_shape":    return self._volume_u_shape()
        if op == "decreasing": return self.volume_ratio < 1.0

    # price_shape 类
    if field == "price_shape":
        shapes = self._detect_price_shapes()
        return shapes.get(op, False)

    # rsi 类
    if field == "rsi":
        rsi_val = self._ensure_rsi()
        if op == "cross_below":  return rsi_val is not None and rsi_val < value  # value=70
        if op == "higher_low":   return self._rsi_higher_low()
        if op == "lower_high":   return self._rsi_lower_high()
        if op == "cross_above":  return rsi_val is not None and rsi_val > value

    # bb_width 类
    if field == "bb_width":
        if op == "narrow":        return self._bb_width_narrow()
        if op == "squeeze_confirm": return self._bb_squeeze_confirm()

    # stoch_k 类
    if field == "stoch_k":
        k = self._ensure_stoch_k()
        if op == "gt":  return k is not None and k > value
        if op == "lt":  return k is not None and k < value
        if op == "cross_above":  return self._stoch_cross_above()
        if op == "cross_below":  return self._stoch_cross_below()

    # ... 其他 80+ op 类似
```

---

## 文件结构

```
src/indicators/
├── __init__.py              # 导出 PatternFeatureEngine, PatternFeatures
├── engine.py                # 已有：SMA/EMA/MACD/RSI/Bollinger/ATR/Stochastic
├── pattern_features.py      # 新建：PatternFeatureEngine + PatternFeatures
└── tests/
    ├── __init__.py
    ├── test_pattern_features.py   # 单元测试
    └── test_integration.py        # 集成测试（喂入真实 YAML 规则）
```

---

## 可扩展性

### 新增指标步骤

1. **底层算法** → `src/indicators/engine.py` 添加计算函数（如 `cci()`）
2. **字段声明** → `PatternFeatures` dataclass 添加字段
3. **惰性计算** → `PatternFeatureEngine._ensure_xxx()` 方法
4. **判断逻辑** → `evaluate_condition()` 添加 `field == "cci"` 分支
5. **使用** → 在 canonical YAML 中引用新字段/op

### 新增 op 步骤

例如要支持 `volume: my_custom_op`：
1. 在 `PatternFeatureEngine` 实现 `volume_my_custom_op()` 方法
2. 在 `evaluate_condition` 的 `volume` 分支添加 `if op == "my_custom_op": return self.volume_my_custom_op()`

### 文档

在 `docs/使用说明.md` 中新增章节：

```markdown
## 新增技术指标

1. 底层算法 → `src/indicators/engine.py`
2. 字段声明 → `PatternFeatures` dataclass
3. 判断逻辑 → `PatternFeatureEngine.evaluate_condition()`
4. 使用 → 在 canonical YAML 中引用

详见 `docs/superpowers/specs/2026-04-07-p2-016-technical-indicators-design.md`
```

---

## 依赖关系

- `engine.py`（已有）→ 底层指标数学实现
- canonical YAML → 定义所需字段/op，作为 `evaluate_condition` 的输入规范
- Pattern Matcher / DSL Engine → `evaluate_condition()` 的调用方
