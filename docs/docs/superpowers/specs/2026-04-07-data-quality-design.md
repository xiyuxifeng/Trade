# 数据质量体系设计

日期：2026-04-07
范围：P1-023（异常检测）、P1-024（去重去噪）、P1-025（数据质量测试）

---

## 一、整体架构

```
数据主线（pipeline）
  ├── validate_task.py          已有：格式/逻辑校验
  ├── clean_task.py             已有：评论过滤；扩展：去重去噪
  ├── anomaly_detection_task.py 新增：P1-023
  └── dedup_task.py             新增：P1-024（P1-023 之后）

DataValidator（src/pipeline/validation.py）扩展
  ├── 异常检测方法（新增）
  │   ├── detect_price_outliers()     P1-023
  │   ├── detect_missing_fields()     P1-023
  │   └── detect_sequence_gaps()      P1-023
  └── 去重去噪方法（新增/扩展）
      ├── detect_article_duplicates()  P1-024
      ├── detect_trade_duplicates()    已有，扩展
      ├── detect_market_duplicates()    P1-024
      └── detect_semantic_noise()       P1-024
```

**设计原则：**
- 异常检测和去重只检测，不修改原始数据
- clean_task 扩展才执行实际删除/过滤
- 所有检测输出标准化 `ValidationIssue`，code 格式：`{type}.{field}.{subcode}`

---

## 二、P1-023 异常检测

### 2.1 检测方法（扩展 DataValidator）

#### detect_price_outliers(records: Sequence[MarketData], iqr_multiplier: float = 1.5)
- 使用 IQR（四分位距）方法检测价格/成交量离群
- 对每只 symbol 的收盘价、成交量分别计算
- `iqr_multiplier` 阈值默认 1.5，可配置
- 输出 `ValidationIssue`，code = `market.price.outlier` / `market.volume.outlier`

#### detect_missing_fields(records: Sequence[BlogArticle | TradeLog | MarketData])
- 对必填字段做 null/空检测
- `BlogArticle`：title、content_text、source_url
- `TradeLog`：symbol、executed_at、quantity、price、side
- `MarketData`：symbol、traded_at、open、high、low、close、volume
- 输出 `ValidationIssue`，code = `{type}.field.missing`

#### detect_sequence_gaps(records: Sequence[MarketData], expected_interval_minutes: int = 1440)
- 检测市场数据时间序列缺口
- 默认按日线（1440 分钟）检测
- 输出 `ValidationIssue`，code = `market.series.gap`

### 2.2 Pipeline Task

**run_anomaly_detection_task(base_dir: Path, input_paths: list[Path], force: bool = False) -> AnomalyDetectionResult**

- 批量扫描 JSONL 数据，输出异常报告
- 输出文件：
  - `anomaly_report_{timestamp}.jsonl`（异常列表，每行一个 ValidationIssue）
  - `anomaly_summary_{timestamp}.json`（统计：按 type/code 分组计数）
- 不修改原始数据，只报告
- 幂等可重复运行

---

## 三、P1-024 去重和去噪

### 3.1 去重检测（扩展 DataValidator）

| 方法 | 去重依据 | code |
|------|---------|------|
| `detect_article_duplicates()` | `content_hash` 相同，或 `source_url` 相同 | `article.duplicate.hash` / `.url` |
| `detect_trade_duplicates()` | 复合键（account_id, symbol, executed_at, quantity, price）；扩展：external_id 匹配 | `trade.duplicate.composite_key` / `.external_id` |
| `detect_market_duplicates()` | `(symbol, market, timeframe, traded_at)` 唯一键 | `market.duplicate.key` |

### 3.2 去噪检测（新增）

| 检测类型 | 逻辑 | code | 配置 |
|---------|------|------|------|
| 文章内容噪音 | `content_text` 中广告/模板文本模式（正则） | `article.noise.semantic` | — |
| 文章策略缺失 | `strategy_rules` 为空或非有效 JSON | `article.strategy.empty` | — |
| 高交易费率 | `fee / amount > threshold` | `trade.fee.high` | `threshold` 默认 0.01（1%），通过 config 配置 |
| 市场静默价格 | `open=high=low=close` 且 volume>0 | `market.price.flat` | — |

**注：高费率阈值备注：**
- A股手续费约 0.03%~0.1%（单边），来回约 0.06%~0.2%
- 默认 1% 对 A股来说是明确异常偏高的信号，但可能因品种/券商而异
- 该阈值通过配置项 `data_quality.trade.fee_high_threshold` 设置，默认 0.01

### 3.3 clean_task.py 扩展

**run_clean_task()** 现有功能：过滤 `is_filtered=True` 的评论

**扩展后新增：**
- `--remove-duplicates` 参数：启用后自动去除检测到的重复记录
- `--high-fee-threshold` 参数：传入配置中的阈值
- 输出文件：
  - `_cleaned.jsonl`（干净数据）
  - `_dedup_report.json`（去重统计：按 type/code 分组计数）

---

## 四、P1-025 数据质量测试

### 4.1 测试文件

`tests/unit/pipeline/test_quality.py`（新增）

### 4.2 单元测试（检测逻辑）

| 测试函数 | 验证内容 |
|---------|---------|
| `test_price_outliers_detected()` | IQR 方法正确识别离群价格 |
| `test_price_outliers_no_false_positive()` | 正常数据无误报 |
| `test_missing_fields_article()` | 文章必填字段缺失被检测 |
| `test_missing_fields_trade()` | 交易必填字段缺失被检测 |
| `test_missing_fields_market_data()` | 市场数据必填字段缺失被检测 |
| `test_sequence_gap_detected()` | 日线缺失被检测 |
| `test_article_duplicate_by_hash()` | content_hash 重复被检测 |
| `test_article_duplicate_by_url()` | source_url 重复被检测 |
| `test_trade_duplicate_by_external_id()` | external_id 重复被检测 |
| `test_market_duplicate_by_key()` | 市场数据唯一键重复被检测 |
| `test_semantic_noise_article()` | 广告文本模式被识别 |
| `test_trade_high_fee_detected()` | 高费率被检测 |
| `test_trade_high_fee_threshold_configurable()` | 阈值可通过 config 传入 |

### 4.3 Task 层集成测试

| 测试函数 | 验证内容 |
|---------|---------|
| `test_anomaly_detection_task_output()` | task 输出 anomaly report |
| `test_clean_task_removes_duplicates()` | clean_task 正确去重 |

---

## 五、Issue Code 规范

格式：`{record_type}.{field}.{subcode}`

示例：
- `article.title.empty`
- `article.content.short`
- `trade.amount.mismatch`
- `trade.fee.high`
- `market.price.outlier`
- `market.series.gap`

---

## 六、配置项（新增）

```yaml
# config/app.yaml
data_quality:
  trade:
    fee_high_threshold: 0.01  # 默认 1%，超过此比例视为高费率
  anomaly:
    iqr_multiplier: 1.5      # IQR 离群检测倍数
    volume_spike_multiplier: 5.0  # 成交量 spike 阈值（已有）
```

---

## 七、文件变更清单

| 操作 | 文件路径 |
|------|---------|
| 扩展 | `src/pipeline/validation.py` |
| 扩展 | `src/pipeline/tasks/clean_task.py` |
| 新增 | `src/pipeline/tasks/anomaly_detection_task.py` |
| 新增 | `src/pipeline/tasks/dedup_task.py` |
| 新增 | `tests/unit/pipeline/test_quality.py` |
| 扩展 | `config/app.yaml`（配置项） |
