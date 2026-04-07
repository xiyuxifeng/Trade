# Adding New Indicators — P2-016 扩展指南

本文档说明如何在 `pattern_features.py` 中添加新的技术指标或新的 op 判断逻辑。

---

## 添加新的底层指标（engine.py）

如果新指标在 `engine.py` 中尚不存在，先在那里实现。例如添加 CCI：

```python
def cci(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, window: int = 14) -> float:
    """Commodity Channel Index (CCI)."""
    typical = (highs + lows + closes) / 3.0
    sma_tp = sma(typical, window)
    last_idx = len(closes) - 1
    tp = typical[last_idx]
    mean_dev = np.mean(np.abs(typical[-window:] - sma_tp[-1]))
    if mean_dev == 0:
        return 0.0
    return float((tp - sma_tp[-1]) / (0.015 * mean_dev))
```

**注意：** `sma()` 返回的数组比输入短（mode="valid"），始终使用 `sma_result[-1]` 取最新值，不要用下标访问末尾之外的位置。

---

## 添加新的 PatternFeatures 字段

在 `PatternFeatures` dataclass 中添加字段：

```python
# === 指标特征 ===
cci: float | None = None  # 新增
```

---

## 添加惰性计算方法

在 `PatternFeatureEngine` 中添加 `ensure_xxx()` 方法：

```python
def ensure_cci(self, window: int = 14) -> float | None:
    if "cci" in self._cache:
        return self._cache["cci"]
    if not self._ensure_min_bars(window + 1):
        return None
    highs, lows, closes = self._highs(), self._lows(), self._closes()
    val = cci(highs, lows, closes, window)
    result = float(val) if not np.isnan(val) else None
    self._cache["cci"] = result
    return result
```

---

## 添加 evaluate_condition 分支

在 `evaluate_condition()` 中添加路由：

```python
if field == "cci":
    return self._eval_cci(op, value)
```

然后实现 `_eval_cci()` 方法。

---

## 在 canonical YAML 中使用

```yaml
conditions:
  - field: cci
    op: cross_below
    value: -100
    description_zh: CCI 超卖后下穿
```

---

## 添加新的 op

例如要支持 `volume: my_custom_op`：

1. 在 `PatternFeatureEngine` 实现 `volume_my_custom_op()` 私有方法
2. 在 `evaluate_condition` 的 `volume` 分支添加：

```python
if op == "my_custom_op":
    return self._volume_my_custom_op()
```

3. 实现该方法返回 `bool`

---

## 扩展步骤速查

| 步骤 | 文件 | 操作 |
|------|------|------|
| 1 | `engine.py` | 添加底层算法函数（如 `cci()`） |
| 2 | `PatternFeatures` dataclass | 添加字段声明 |
| 3 | `PatternFeatureEngine.ensure_xxx()` | 添加惰性计算方法 |
| 4 | `evaluate_condition()` | 添加 field 路由 |
| 5 | `_eval_xxx()` | 实现 op 判断逻辑 |
| 6 | `canonical YAML` | 引用新 field/op |

---

## 常见问题

**Q: `sma()` 返回的数组长度是多少？**
`sma(closes, window)` 返回 `len(closes) - window + 1` 个元素，始终用 `sma_result[-1]` 取最后一个有效值。

**Q: 指标计算需要多少根 bar？**
每个指标不同。RSI 需要 15+ 根，MACD 需要 27+ 根，MA50 需要 50+ 根。在 `_ensure_min_bars()` 中正确设置阈值。

**Q: 某 op 不支持时怎么办？**
未知 op 在 `evaluate_condition` 中默认返回 `False`。如果该 op 需要特殊行为，可以先返回 `False` 或 `NotImplemented`。
