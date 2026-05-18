# New-Web-Market-Regime-Definition

## 1. 文档目标

本文档定义 `NW-V3-SX-001 Market Regime Definition` 的正式口径，用于把市场状态从“临时解释”升级为 **Web 最终交付可依赖的 canonical 数据契约**。

本定义服务于以下下游场景：

- `UI-V3-010 Market Regime Viewer`
- `NW-V3-SX-002 Regime-aware Backtest`
- `NW-V3-SX-003 Rule Applicability Profile`
- `NW-V3-SX-004 Regime-aware Rule Selection`

本文档只定义 **市场状态画像**，不定义规则优化闭环，不新增 CLI 专用业务入口，不把 regime 绑定为 Demo 阶段的临时输出。

---

## 2. 设计原则

### 2.1 Web canonical 优先

- 以 `Market Snapshot` 为唯一输入事实源。
- 以 `Market Regime` 作为唯一输出事实源。
- UI、Backtest、Rule Selection 都只消费同一套 regime 数据。
- 不在前端计算 regime。
- 不新增第二套“解释层”和“展示层”并行事实源。

### 2.2 可解释

- 每个标签都必须有证据来源。
- 每个特征都必须能追溯到 snapshot section / field。
- 每个低置信度结果都必须说明原因。

### 2.3 可版本化

- regime 判定规则必须有 `regime_version`。
- 特征输入必须有 `source_feature_version`。
- 历史回测必须可以按版本复现。

### 2.4 多标签而非单枚举

- Market Regime 不应该只输出一个枚举值。
- 主状态与结构标签分离。
- 主状态负责方向，结构标签负责环境特征。

### 2.5 面向最终交付

- schema 优先满足 Web UI、Artifact、Backtest、Rule Selection。
- 不为了 CLI 便利牺牲 Web 的长期数据契约。

---

## 3. 任务边界

### 3.1 本任务做什么

1. 定义 Market Regime 的字段。
2. 定义主状态标签和结构标签。
3. 定义标签判定规则。
4. 定义置信度与质量状态。
5. 定义输入数据依赖和数据缺口。
6. 为后续补数据提供清单。

### 3.2 本任务不做什么

1. 不实现完整 backtest。
2. 不实现 rule selection。
3. 不在 UI 中计算 regime。
4. 不把 regime 绑定到 CLI 输出。
5. 不定义 LLM 黑盒标签。

---

## 4. 术语定义

### 4.1 Market Regime

基于指定 `snapshot_id` 和 `regime_version` 计算得到的、可解释、可版本化、多标签的市场状态画像。

### 4.2 主状态 Primary Label

用于描述市场的大方向。

建议取值：

- `strong_bull`
- `weak_bull`
- `range`
- `weak_bear`
- `panic`

### 4.3 结构标签 Structural Label

用于描述市场结构特征，不替代主状态。

建议取值：

- `theme_hot`
- `low_liquidity`

### 4.4 Feature

用于生成 regime 的中间特征，必须能回溯来源 section、source field 和版本。

### 4.5 Confidence

对 regime 或 label 的判定可靠程度。不是“分数好看”，而是对证据完整性和边界稳定性的综合度量。

### 4.6 Quality Status

用于描述当前结果是否可直接用于 UI / Backtest。

建议取值：

- `ok`
- `partial`
- `low_confidence`

---

## 5. 总体数据流

```text
Market Snapshot
  -> Market Regime Features (V2 已有)
  -> Market Regime Definition (本任务)
  -> UI / Backtest / Rule Applicability / Rule Selection
```

说明：

- `Market Regime Features` 是中间层。
- `Market Regime Definition` 是最终层。
- 最终层不得绕过中间层直接读 provider。

---

## 6. 字段定义

### 6.1 MarketRegime

这是最终 canonical 对象。建议作为 `market_regimes` 的主记录或等价 JSON artifact 主体。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `regime_id` | string | 是 | regime 记录唯一 ID |
| `trade_date` | string(date) | 是 | 交易日 |
| `snapshot_id` | string | 是 | 唯一输入事实源 |
| `market` | string | 是 | 市场标识，示例 `CN` |
| `regime_version` | string | 是 | regime 规则版本 |
| `source_feature_version` | string | 是 | 依赖的 feature 版本 |
| `primary_label` | string | 是 | 主状态标签 |
| `labels` | array<RegimeLabel> | 是 | 标签明细，可含多个 |
| `features` | array<RegimeFeature> | 是 | 判定所用特征明细 |
| `confidence` | number | 是 | 整体置信度，建议 0~1 |
| `quality_status` | string | 是 | `ok / partial / low_confidence` |
| `missing_reason` | string | 否 | 关键输入缺失时的解释 |
| `created_at` | string(datetime) | 是 | 生成时间 |

### 6.2 RegimeLabel

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `label` | string | 是 | 标签名 |
| `label_type` | string | 是 | `primary / structural / risk` |
| `score` | number | 是 | 该标签的强度分 |
| `confidence` | number | 是 | 标签置信度 |
| `status` | string | 是 | `active / suppressed / low_confidence` |
| `evidence` | array<LabelEvidence> | 是 | 支撑标签的证据 |
| `reason` | string | 是 | 可读解释 |

### 6.3 RegimeFeature

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `feature_key` | string | 是 | 特征名 |
| `raw_value` | any | 是 | 原始值 |
| `normalized_value` | any | 否 | 归一化值 |
| `source_section` | string | 是 | 来源 section |
| `source_field` | string | 否 | 来源字段 |
| `source_version` | string | 是 | 来源版本 |
| `confidence` | number | 是 | 特征可信度 |
| `weight` | number | 是 | 在 regime 判定中的权重 |
| `missing_reason` | string | 否 | 缺失说明 |

### 6.4 LabelEvidence

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `feature_key` | string | 是 | 证据对应的特征 |
| `feature_value` | any | 是 | 证据值 |
| `source_section` | string | 是 | 来源 section |
| `source_field` | string | 否 | 来源字段 |
| `contribution` | number | 是 | 对标签的贡献值 |
| `note` | string | 否 | 证据说明 |

---

## 7. 标准定义

### 7.1 主状态标准

主状态负责回答“市场大方向是什么”。

| 主状态 | 标准定义 |
|---|---|
| `strong_bull` | 趋势显著向上，广度强，风险指标不高，参与度较好 |
| `weak_bull` | 趋势偏强，但广度、波动或流动性至少一项不够理想 |
| `range` | 趋势不明显，市场分歧存在，但没有明显单边风险 |
| `weak_bear` | 趋势偏弱，广度转弱，但尚未进入踩踏级风险 |
| `panic` | 趋势显著转弱，波动与风险信号同步恶化 |

### 7.2 结构标签标准

| 标签 | 标准定义 |
|---|---|
| `theme_hot` | 少数主题/题材显著强于市场平均，热点集中度高 |
| `low_liquidity` | 成交额、换手或参与度明显不足 |

### 7.3 质量状态标准

| 状态 | 定义 |
|---|---|
| `ok` | 关键输入齐全，主状态和结构标签可稳定计算 |
| `partial` | 部分输入缺失，但仍能产出可用结果 |
| `low_confidence` | 关键输入不足或边界过近，不应被当作强结论使用 |

---

## 8. 规则设计

### 8.1 规则总则

建议采用 **分层打分 + 硬门槛兜底**：

1. 先计算主状态分数。
2. 再根据风险特征修正主状态。
3. 再叠加结构标签。
4. 最后计算 confidence 和 quality_status。

这样做的原因：

- 比纯硬规则稳定。
- 比黑盒分类器更可解释。
- 更适合回测与人工校准。

### 8.2 主状态判定逻辑

主状态建议参考以下维度：

- 趋势：`ret_5d`、`ret_20d`、`ma20_gap`、`ma60_gap`
- 广度：`breadth_up_ratio`、上涨/下跌扩散情况
- 波动：`volatility`、`vol_spike`
- 流动性：`liquidity`、`turnover_level`
- 风险：`limit_down_count`、极端跌幅、跳空恶化

#### 8.2.1 `strong_bull`

建议满足：

- 近 5 日和 20 日趋势为正
- 均线偏离为正
- 广度明显偏强
- 波动没有显著失控
- 流动性不弱

#### 8.2.2 `weak_bull`

建议满足：

- 趋势偏强
- 但广度、波动、流动性至少有一项不够理想

#### 8.2.3 `range`

建议满足：

- 趋势接近中性
- 广度接近平衡
- 波动未出现极端抬升
- 无明显踩踏风险

#### 8.2.4 `weak_bear`

建议满足：

- 趋势偏弱
- 广度走弱
- 但尚未达到恐慌级别

#### 8.2.5 `panic`

建议满足：

- 趋势显著转弱
- 波动显著升高
- 广度显著恶化
- 跌停 / 跳空 / 极端回撤信号明显

### 8.3 结构标签判定逻辑

#### 8.3.1 `theme_hot`

建议判断条件：

- `hot_topics` 数量高于常态
- `topic_constituents` 对应成分股集中度高
- `strong_symbols` 主要集中于少数主题

#### 8.3.2 `low_liquidity`

建议判断条件：

- `turnover_level` 明显偏低
- 成交额/换手相对历史均值偏弱
- 市场参与度下降

### 8.4 置信度计算原则

置信度建议由三部分组成：

1. **信号一致性**：趋势、广度、波动是否方向一致。
2. **特征完整性**：关键特征缺失越多，置信度越低。
3. **边界距离**：越接近阈值边界，置信度越低。

建议规则：

- 若关键特征缺失较多，标记 `partial` 或 `low_confidence`。
- 若主状态分数处于阈值边缘，降低 confidence。
- 若风险特征强烈恶化，优先提升 `panic` 或降级其他主状态。

### 8.5 版本化原则

建议同时固定两类版本：

- `regime_version`：regime 判定规则版本
- `source_feature_version`：输入特征版本

这两类版本都必须随结果存档，以便：

- 历史回测可复现
- UI 可解释
- 后续阈值调整不污染旧结果

---

## 9. 特征输入设计

### 9.1 最小可用特征集

首版 regime 至少应使用以下特征：

- `trend`
- `sentiment`
- `liquidity`
- `volatility`
- `breadth`
- `theme_strength`
- `limit_up_count`
- `limit_down_count`
- `turnover_level`

这些特征来自现有 `Market Regime Feature Build` 结果。

### 9.2 建议增强特征集

如果要提升阈值稳定性，建议补充：

- `ret_5d`
- `ret_20d`
- `ma20_gap`
- `ma60_gap`
- `breadth_up_ratio`
- `breadth_down_ratio`
- `vol_spike`
- `turnover_ratio`
- `theme_concentration`
- `gap_down_rate`
- `extreme_drop_count`
- `benchmark_ohlcv_window`

---

## 10. 现有数据 / 缺失数据 / 必须补数据

### 10.1 结论

当前现有抓取数据 **足够支撑首版 Market Regime Definition 落地**，尤其是：

- 主状态粗分
- 结构标签
- Web UI 展示
- Regime-aware Backtest 的第一版分桶

但如果目标是 **长期稳定、阈值可校准、回测更可信**，则还需要补充若干标准化数值字段。

### 10.2 数据清单表

| 类别 | 当前状态 | 目前来源 | 用途 | 是否足够 | 备注 |
|---|---:|---|---|---:|---|
| `overview` 指数概览 | 已落地 | `overview` | 趋势、情绪、容量判断 | 是 | 首版主状态足够 |
| `sentiment` 情绪 | 已落地 | `overview` / `market_state` | 方向判断辅助 | 是 | 可用于弱/强市区分 |
| `volatility` 波动 | 已落地 | `market_state` / `overview` | 风险修正 | 基本够 | 更细粒度还需历史基线 |
| `breadth` 广度 | 已落地 | `market_state` / `sector_activity` / `overview` / `market_sentiment` | 主状态判定 | 基本够 | 已补原始上涨/下跌家数，`breadth_up/down_ratio` 由 feature 层计算 |
| `liquidity` 流动性 | 已落地 | `market_state` / `overview.capacity` | 结构标签与风险修正 | 基本够 | 当前以 band 口径为主 |
| `theme_strength` 热点强度 | 已落地 | `hot_topics` / `topic_constituents` / `strong_symbols` / `strong_fengkou_best` | `theme_hot` | 是 | 可直接用于首版 |
| `limit_up_count` / `limit_down_count` | 已落地 | `limit_up_down` | 风险修正 | 是 | 对 `panic` 很重要 |
| `ohlcv` 日线 | 已落地 | `ohlcv` + cache fallback | 趋势 / 收益窗口 | 是 | 已有 benchmark_symbol，足够支撑基准指数序列 |
| `market_state` 上下文 | 已落地 | `PersonaService.build_market_state` | 兼容旧语义 | 基本够 | 不能作为唯一事实源 |
| `breadth_up_ratio` | 已落地（计算层） | `market_regime_features` / `market_sentiment` | 主状态 / 风险修正 | 是 | 由上涨/下跌/平盘家数计算 |
| `breadth_down_ratio` | 已落地（计算层） | `market_regime_features` / `market_sentiment` | 主状态 / 风险修正 | 是 | 由上涨/下跌/平盘家数计算 |
| `ret_5d` / `ret_20d` | 已落地（计算层） | 现有 `ohlcv` + `benchmark_symbol` | 趋势判断 | 是 | 直接由基准指数序列计算 |
| `ma20_gap` / `ma60_gap` | 已落地（计算层） | 现有 `ohlcv` + `benchmark_symbol` | 趋势判断 | 是 | 直接由基准指数序列计算 |
| `vol_spike` | 已落地（计算层） | 现有 `ohlcv` 历史窗口 | 风险判断 | 是 | 需要历史窗口，但不需要新增 provider 接口 |
| `turnover_ratio` | 已落地（计算层） | `MarketCapacity` / OHLCV 历史均值 | 流动性判断 | 是 | 现有数据足够计算，不必再单独抓新接口 |
| `theme_concentration` | 已落地（计算层） | `hot_topics` / `topic_constituents` / `strong_symbols` / `strong_fengkou_best` / `WeightPerformance` | `theme_hot` 判定 | 是 | 现有题材/权重数据足够计算 |
| `gap_down_rate` | 已落地（计算层） | 现有 `ohlcv` + `benchmark_symbol` | `panic` 判定 | 是 | 当前为 benchmark 口径，后续可扩展全市场口径 |
| `extreme_drop_count` | 已落地（计算层） | 现有 `ohlcv` + `benchmark_symbol` | `panic` 判定 | 是 | 当前为 benchmark 口径，后续可扩展全市场口径 |
| `benchmark_ohlcv_window` | 已落地（计算层） | 现有 `ohlcv` 主链路 | 主要趋势基线 | 是 | 回测不做 ETF fallback，直接用指数序列 |

### 10.3 数据结论分层

#### 可直接用于首版交付

- `overview`
- `sentiment`
- `volatility`
- `breadth`
- `liquidity`
- `theme_strength`
- `limit_up_count`
- `limit_down_count`
- `turnover_level`
- `breadth_up_ratio`
- `breadth_down_ratio`
- `benchmark_ohlcv_window`
- `ret_5d`
- `ret_20d`
- `ma20_gap`
- `ma60_gap`
- `vol_spike`
- `turnover_ratio`
- `theme_concentration`

#### 需要补强但不阻塞首版

- `gap_down_rate` 的全市场版本
- `extreme_drop_count` 的全市场版本

#### 必须补充，才能让 regime 规则稳定可信

- `benchmark_ohlcv_window` 的历史覆盖
- `ret_5d` / `ret_20d` 的回看窗口校准
- `ma20_gap` / `ma60_gap` 的阈值校准
- `vol_spike` / `turnover_ratio` 的分桶校准
- `gap_down_rate` / `extreme_drop_count` 的全市场覆盖补齐（如果要做全市场版本）

### 10.4 可执行列表

#### A. 现在可以直接用于后续任务

- `overview`
- `sentiment`
- `volatility`
- `breadth`
- `liquidity`
- `theme_strength`
- `limit_up_count`
- `limit_down_count`
- `turnover_level`

说明：

- 这组数据已经足以支撑首版 `Market Regime`、`UI-V3-010` 和 `NW-V3-SX-002` 的基础链路。
- 后续任务可以先按这组数据继续推进，不需要等待全量补齐。

#### B. 应尽快补齐，但不应阻塞当前交付

- `breadth_up_ratio`
- `breadth_down_ratio`
- `theme_concentration`
- `turnover_ratio`
- `gap_down_rate`

说明：

- 这些字段主要提升稳定性、解释性和分桶精度。
- 后续任务可以先预留字段与版本位，但不要把它们硬编码为首版强依赖。

#### C. P0 必补，补完后再做稳定性校准

- `benchmark_ohlcv_window`
- `ret_5d`
- `ret_20d`
- `ma20_gap`
- `ma60_gap`
- `vol_spike`
- `extreme_drop_count`

说明：

- 这组字段决定 regime 主状态是否足够稳。
- 如果要做阈值校准、跨周期复用和高可信度回测，这组数据必须补。
- 但它们不是首版 Web 交付的阻塞项。

#### D. 推荐的改动影响范围

- 先做后续任务时，尽量只改 `feature layer` 和 `rule layer`。
- 不要把临时缺失字段写死成 `UI` 或 `Backtest` 的唯一前置条件。
- 后续补 P0 数据时，优先通过版本化特征和规则切换来吸收，而不是重写整个 Web 交付链路。

### 10.5 建议新增的 Kaipan 接口清单

> 说明：
>
> - 下面清单只列 **建议补充到 Kaipan provider 的接口封装**。
> - `benchmark_ohlcv_window` 仍建议走现有 `market data / ohlcv` 主链路，不建议强行塞进 Kaipan。
> - 这些接口的目标是把 `10.2` 中“需要补强”的字段尽量前移到抓取层，减少后续 feature 计算的临时分支。

| 接口名 | 目前状态 | 作用字段 / 用途 | 是否建议新增封装 | 备注 |
|---|---:|---|---:|---|
| `MarketStockZDNum` | 文档已有，provider 未封装 | `limit_up_count`、`limit_down_count`、`panic` 修正 | 是 | 直接拿涨跌停总数，适合作为基础统计接口 |
| `ZhangTingExpression` | 文档已有，provider 未封装 | 涨停晋级率、破板率、连板结构 | 是 | 对 `breadth`、`panic`、情绪分层更有价值 |
| `DailyLimitIndex` | 文档已有，provider 未封装 | 一板 / 二板 / 三板 / 高板结构 | 是 | 适合补强连板生态和广度结构 |
| `WeightPerformance` | 文档已有，provider 未封装 | 权重板块涨跌分布、热点集中度 | 是 | 适合辅助 `theme_concentration` / 指数驱动判断 |
| `GetFengKListBest` | 文档已有，provider 已封装并接入 | 收盘时全量强势标的 | 已接入 | 可作为 `theme_strength` 的增强源，当前作为 canonical 入口 |

#### 新增接口的落库建议

- 原始响应先落 `data/kaipan/raw`
- 标准化结果落 `data/kaipan/snapshots`
- 上层不要直接依赖原始字段名
- 统一由 snapshot / feature 层消费标准化后的字段

> 落表与计算分层设计见：[Kaipan Ingestion and Storage Design](./superpowers/specs/2026-05-18-kaipan-ingestion-storage-design.md)

---

## 11. 推荐的数据补齐优先级

### P0

1. `benchmark_ohlcv_window`
2. `ret_5d`
3. `ret_20d`
4. `ma20_gap`
5. `ma60_gap`

原因：

- 这是主状态最核心的趋势基线。
- 没有它们，主状态容易退化成“经验判断”。

### P1

1. `breadth_up_ratio`
2. `breadth_down_ratio`
3. `turnover_ratio`
4. `vol_spike`

原因：

- 这些字段决定 regime 的稳定性。
- 对回测分桶和 UI 解释都很关键。

### P2

1. `theme_concentration`
2. `gap_down_rate`（benchmark 版已实现，全市场版后续补）
3. `extreme_drop_count`（benchmark 版已实现，全市场版后续补）

原因：

- 提升 `theme_hot` 和 `panic` 的判定质量。
- 不是首版上线阻塞项，但建议尽快补。

---

## 12. 与现有项目边界的关系

### 12.1 与 `Market Regime Features` 的关系

现有 `Market Regime Features` 是中间派生层，负责从 snapshot 提取结构化特征。

本任务定义的 `Market Regime` 必须基于这层结果继续向上推导，而不是绕过它。

### 12.2 与旧 `trend_up / trend_down` 语义的关系

旧语义可以作为兼容参考，但不能继续作为正式 canonical：

- `trend_up` 可以映射到 `weak_bull` / `strong_bull`
- `trend_down` 可以映射到 `weak_bear`
- `range_bound` 可以映射到 `range`
- `panic` 保留

### 12.3 与 UI 的关系

`UI-V3-010` 只负责展示：

- `primary_label`
- `labels`
- `features`
- `confidence`
- `missing_reason`

UI 不负责计算 regime。

---

## 13. 推荐实现输出

### 13.1 DB

建议最终落一张 `market_regimes` 表，查询维度至少包括：

- `snapshot_id`
- `trade_date`
- `market`
- `regime_version`

### 13.2 Artifact

建议输出为：

```text
data/processed/market_regimes/{trade_date}/{snapshot_id}/{regime_version}.json
```

artifact 内容至少包含：

- `regime_id`
- `snapshot_id`
- `trade_date`
- `market`
- `regime_version`
- `source_feature_version`
- `primary_label`
- `labels`
- `features`
- `confidence`
- `quality_status`
- `missing_reason`

### 13.3 API

建议后续提供两个查询方向：

- 按 `snapshot_id` 查询 regime 详情
- 按 `trade_date` / `market` / `regime_version` 列表查询

### 13.4 推荐实现链路

推荐的实现顺序是：

1. **抓取**
   - 由 Provider 拉取 Kaipan / 行情 / 竞价 / 龙虎榜等原始数据。
   - 原始响应先落 raw 存储，便于复跑和排障。

2. **入库**
   - 抓取后的数据进入规范化层，写入 `market_snapshots`、`market_snapshot_sections`、`market_snapshot_items`。
   - OHLCV 相关数据写入 `ohlcv_bars`。
   - 这一步完成后，Web 和回测可以统一读取稳定的事实源。

3. **计算 feature**
   - 由 `MarketRegimeFeatureService` 基于 snapshot sections 提取结构化特征。
   - 结果写入 `market_regime_features`，并保留 `feature_version`、`quality_status`、`summary_json` 和 artifact。
   - 这一步只做“事实抽取 + 标准化”，不直接给最终 regime 下结论。

4. **计算 regime**
   - 由 `MarketRegimeService` 读取指定 `snapshot_id + feature_version` 的 feature。
   - 通过版本化规则生成 `primary_label`、`labels`、`confidence`、`missing_reason`。
   - 结果写入 `market_regimes`，并保留 `regime_version`、`source_feature_version` 和 artifact。

5. **UI 展示**
   - UI 只读取 API 暴露的查询接口，不直接参与计算。
   - UI 展示 `primary_label`、`labels`、`features`、`confidence`、`quality_status`、`missing_reason`。
   - 如果需要重算，UI 只负责触发 build / refresh 入口，不能在前端侧拼规则。

6. **版本化切换**
   - `feature_version` 和 `regime_version` 是整个链路的冻结点。
   - 后续新增 Provider 或补数据时，只要保持标准化字段语义不变，就只改抓取层和计算层，不动 UI contract。

### 13.5 Benchmark 选择规则

- `benchmark_ohlcv_window` 只允许使用**指数**，不允许回测时 fallback 到 ETF。
- 常用指数可以预置到 `stock_info`，作为可选 benchmark 列表。
- 回测请求必须显式携带 `benchmark_symbol`，例如 `000300.SH`、`000905.SH`、`000001.SH`。
- 如果某次回测未传 `benchmark_symbol`，应当视为配置缺失，而不是自动切到 ETF。
- `market_regime_features` 和 `market_regimes` 需要记录实际使用的 `benchmark_symbol`，保证可复现。
- ETF 不进入 benchmark 主链路，因此不需要为回测保留 ETF fallback 分支。

---

## 14. 验收标准摘要

本定义要满足 `NW-V3-SX-001` 的验收目标：

1. 可以基于指定 `snapshot_id` 生成 Market Regime。
2. Regime 输出可解释，能看到使用了哪些 features。
3. Regime definition 有版本。
4. Backtest 可以读取指定版本的 regime。
5. 能覆盖强势、弱势、震荡、数据缺失场景。
6. UI 可以展示 labels、features、confidence 和缺失原因。
7. 不把低置信度结果当成强结论。

---

## 15. 结论

如果按 Web 最终交付的标准，当前数据链路对 **首版 Market Regime** 是够用的，但要做到 **稳定、可复现、可校准**，必须继续补充标准化数值字段，尤其是：

- benchmark OHLCV 窗口
- 5 日 / 20 日收益
- 均线偏离
- 广度原始比例
- 波动历史基线
- 流动性绝对值与分位

因此，当前最合理的策略是：

1. 先按本定义落地 schema 和规则骨架。
2. 先用现有数据支撑首版交付。
3. 按 P0 / P1 / P2 顺序补数据。
4. 再进入 `NW-V3-SX-002/003/004`。

---

## 16. 剩余任务与补数据任务的推荐实现顺序

> 说明：
>
> - 下面顺序按 **最小返工** 排列。
> - 这不是“所有数据都补完才能开始后续任务”的硬性阻塞清单。
> - 但如果目标是让后续任务一次成型、少改动，建议按这个顺序冻结阶段成果。

### 16.1 主线顺序

1. **P0 数据补齐**
   - `benchmark_ohlcv_window`
   - `ret_5d`
   - `ret_20d`
   - `ma20_gap`
   - `ma60_gap`
   - 目的：先把主状态的趋势基线补稳，再进入 regime-aware backtest。

2. **`NW-V3-SX-002 P0 Regime-aware Backtest`**
   - 先把 Market Regime 接入回测分桶、分层统计和 artifact 输出。
   - 这一步会成为后续 profile / selection 的事实源。

3. **`UI-V3-011 P0 Regime Backtest Report`**
   - 把 regime-aware backtest 的整体指标、分 regime 指标、低样本提示展示出来。
   - 这一步依赖 `NW-V3-SX-002` 的输出结构。

4. **P1 数据补齐**
   - `breadth_up_ratio`
   - `breadth_down_ratio`
   - `turnover_ratio`
   - `vol_spike`
   - 目的：提升 backtest 分桶和后续 profile 的稳定性与解释性。

5. **`NW-V3-SX-003 P0 Rule Applicability Profile`**
   - 基于 regime-aware backtest 生成 rule applicability profile。
   - 这里已经可以利用 P1 数据提升 profile 置信度和 blocked / applicable 判定质量。

6. **`UI-V3-012 P0 Rule Applicability Viewer`**
   - 展示适用 / 禁用 / 中性 regime，以及来源 backtest 和 review 状态。

7. **P2 数据补齐**
   - `theme_concentration`
   - `gap_down_rate`
   - `extreme_drop_count`
   - 目的：强化 `theme_hot` 与 `panic` 的判定质量，为 selection 阶段提供更强证据。

8. **`NW-V3-SX-004 P0 Regime-aware Rule Selection`**
   - 盘前根据当前 Market Regime 和 applicability profile 选择规则。
   - 这一步最依赖稳定的 regime / profile 版本。

9. **`UI-V3-013 P0 Regime-aware Rule Selection View`**
   - 展示 selected / skipped / blocked rules 以及 selection reason 和 override 审计信息。

### 16.2 每一阶段的冻结建议

- `NW-V3-SX-002` 冻结前，优先确认 P0 数据已经到位。
- `NW-V3-SX-003` 冻结前，优先确认 P1 数据已经到位。
- `NW-V3-SX-004` 冻结前，优先确认 P2 数据已经到位。
- 每次补数据后，只需要重跑对应阶段的产物和验证，不需要回头推翻 `NW-V3-SX-001` 和 `UI-V3-010`。

### 16.3 可直接执行的短版顺序

1. 补 P0 数据：`benchmark_ohlcv_window`、`ret_5d`、`ret_20d`、`ma20_gap`、`ma60_gap`
2. 做 `NW-V3-SX-002 Regime-aware Backtest`
3. 做 `UI-V3-011 Regime Backtest Report`
4. 补 P1 数据：`breadth_up_ratio`、`breadth_down_ratio`、`turnover_ratio`、`vol_spike`
5. 做 `NW-V3-SX-003 Rule Applicability Profile`
6. 做 `UI-V3-012 Rule Applicability Viewer`
7. 补 P2 数据：`theme_concentration`、`gap_down_rate`、`extreme_drop_count`
8. 做 `NW-V3-SX-004 Regime-aware Rule Selection`
9. 做 `UI-V3-013 Regime-aware Rule Selection View`
