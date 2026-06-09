# Kaipan 数据抓取与快照标准化设计方案

> 日期：2026-04-20
> 状态：已确认

---

## 1. 目标

将 `kaipan` 私有接口的数据抓取和标准化落地为可运行、可验证、可回放的三层数据链路：

```
Raw JSON (原始响应 + meta)
    ↓
快照 JSON (标准化字段)
    ↓
消费层 (DataAgent / ManagerAgent)
```



---

## 2. 架构设计

### 2.1 分层职责

| 层级 | 组件 | 职责 |
|------|------|------|
| 抓取层 | `KaipanProvider` | 发起 HTTP 请求，写 raw JSON，内嵌 meta，不做数据转换 |
| 转换层 | `KaipanNormalizer` | 读取 YAML 映射文件，执行字段转换，输出 snapshots JSON |
| 调度层 | `KaipanScheduler` | CLI 命令 + APScheduler 定时调度 |

**关键约束**：`KaipanProvider` 只负责"把数据拉回来存好"，不做任何转换逻辑。转换由 `KaipanNormalizer` 独立完成。

### 2.2 多域名支持

| baseURL | 用途 | 覆盖接口（首批） |
|---------|------|------------------|
| `apphis.longhuvip.com` | 历史数据、复盘数据 | 板块强度、行业涨幅、概念风口、最强风口、区间统计-按股票、竞价列表、涨停原因、竞价总体信息、竞价数量统计、涨停信息 |
| `apphwshhq.longhuvip.com` | 股票数据、板块数据 | 股票所属板块 V2 |
| `applhb.longhuvip.com` | 龙虎榜、题材数据 | 题材详情、龙虎榜列表 |

`KaipanProvider` 持有 3 个 baseURL 配置，`build_request()` 根据接口选择对应 baseURL。

### 2.3 元信息设计

每次请求的元信息嵌入 raw JSON 顶部，不单独存 `.meta.json` 文件：

```json
{
  "meta": {
    "dataset": "hot_topics",
    "trade_date": "2026-04-18",
    "slot": "09-25",
    "fetched_at": "2026-04-19T08:31:22",
    "source": "kaipan",
    "request": {
      "endpoint": "https://apphis.longhuvip.com/w1/api/index.php",
      "controller": "ZhiShuRanking",
      "action": "RealRankingInfo",
      "params": {...}
    }
  },
  "data": {...}
}
```

---

## 3. 目录结构

```
data/
  kaipan/
    raw/
      {dataset}/
        {trade_date}_09-25/          # 盘前快照
          {dataset}.json             # 内嵌 meta + raw data
        {trade_date}_17-30/          # 盘后快照
          {dataset}.json             # 内嵌 meta + raw data
    snapshots/
      {dataset}/
        {trade_date}_09-25/          # 盘前快照
          {dataset}.json             # 标准化快照
        {trade_date}_17-30/          # 盘后快照
          {dataset}.json             # 标准化快照

src/
  providers/
    kaipan_provider.py      # 抓取层
    kaipan_normalizer.py    # 转换层
    kaipan_scheduler.py     # 调度层（CLI 入口）
    kaipan_schema/          # YAML 字段映射（代码资产）
      hot_topics.yaml
      topic_constituents.yaml
      strong_symbols.yaml
```

**约定**：
- `dataset`：接口名，如 `hot_topics`、`topic_constituents`、`strong_symbols`
- `trade_date`：格式 `YYYY-MM-DD`，如 `2026-04-20`
- `slot`：时间槽，`09-25`（盘前）或 `17-30`（盘后），两次数据完全独立，不相互覆盖
- 目录按 `dataset` 分层，不按 baseURL 分层（baseURL 已在 meta.request.endpoint 中记录）
- 目录结构为 `{base_dir}/{dataset}/{trade_date}_{slot}/{dataset}.json`

---

## 4. Schema 映射设计

### 4.1 文件位置

`src/providers/kaipan_schema/` 下，每个 snapshot dataset 一个 YAML 文件：

```
kaipan_schema/
  hot_topics.yaml         # 板块强度、行业涨幅、概念风口 → hot_topics
  topic_constituents.yaml # 股票所属板块 V2、题材详情、涨停原因、涨停信息、龙虎榜列表 → topic_constituents
  strong_symbols.yaml     # 最强风口、区间统计-按股票、竞价列表 → strong_symbols
  market_context.yaml    # 竞价总体信息、竞价数量统计 → market_context
```

### 4.2 映射格式（YAML）

以 `hot_topics.yaml` 为例：

```yaml
# hot_topics 快照的字段映射
# raw_path: 原始 JSON 中的字段路径，支持数组索引占位 [i]
# snapshot_path: 快照 JSON 中的输出路径

dataset: hot_topics
raw_endpoint: https://apphis.longhuvip.com/w1/api/index.php

mappings:
  # 概念板块强度
  concept:
    source_api: RealRankingInfo
    source_controller: ZhiShuRanking
    source_params:
      Type: "1"
      ZSType: "7"
    fields:
      topic_id:
        raw_path: "list.[i].[0]"
        type: string
      topic_name:
        raw_path: "list.[i].[1]"
        type: string
      score:
        raw_path: "list.[i].[2]"
        type: number
      increase_pct:
        raw_path: "list.[i].[3]"
        type: number

  # 行业涨幅
  industry:
    source_api: RealRankingInfo
    source_controller: ZhiShuRanking
    source_params:
      Type: "2"
      ZSType: "4"
    fields:
      topic_id:
        raw_path: "list.[i].[0]"
        type: string
      topic_name:
        raw_path: "list.[i].[1]"
        type: string
      increase_pct:
        raw_path: "list.[i].[3]"
        type: number

  # 概念风口
  concept_feng Kou:
    source_api: GetFengKYDPlate
    source_controller: StockFengKData
    fields:
      topic_name:
        raw_path: "List.[i].[0]"
        type: string
      score:
        raw_path: "List.[i].[1]"
        type: number
```

---

## 5. Normalizer 转换逻辑

### 5.1 接口设计

```python
class KaipanNormalizer:
    """读取 YAML 映射，执行字段转换"""

    def normalize(self, dataset: str, raw_path: Path, slot: str) -> dict:
        """通用转换接口，根据 dataset 路由到对应映射规则"""

    def normalize_hot_topics(self, raw_path: Path, slot: str) -> dict:
        """转换 hot_topics 快照（板块强度 + 行业涨幅 + 概念风口）"""

    def normalize_topic_constituents(self, raw_path: Path, slot: str) -> dict:
        """转换 topic_constituents 快照（股票所属板块 V2 + 题材详情 + 涨停原因 + 涨停信息 + 龙虎榜列表）"""

    def normalize_strong_symbols(self, raw_path: Path, slot: str) -> dict:
        """转换 strong_symbols 快照（最强风口 + 区间统计-按股票 + 竞价列表）"""

    def normalize_market_context(self, raw_path: Path, slot: str) -> dict:
        """转换 market_context 快照（竞价总体信息 + 竞价数量统计）"""

    def normalize_date(self, trade_date: date) -> dict[str, dict[str, dict]]:
        """批量转换某交易日全部时间槽的 snapshots（便利封装）"""
        # 返回 {"09-25": {dataset: snapshot, ...}, "17-30": {dataset: snapshot, ...}}
```

### 5.2 转换流程

1. 读取 `src/providers/kaipan_schema/{dataset}.yaml`
2. 根据 `source_api` 和 `source_controller` 找到对应的 raw 文件
3. 按 `fields` 定义执行字段映射（支持数组索引遍历）
4. 输出标准化快照 JSON 到 `data/kaipan/snapshots/{dataset}/{trade_date}_{slot}/`

### 5.3 Snapshot Dataset 分类

| Snapshot Dataset | 来源接口 |
|-----------------|---------|
| `hot_topics` | 板块强度、行业涨幅、概念风口 |
| `topic_constituents` | 股票所属板块 V2、题材详情、涨停原因、涨停信息、龙虎榜列表 |
| `strong_symbols` | 最强风口、区间统计-按股票、竞价列表 |
| `market_context` | 竞价总体信息、竞价数量统计 |

---

## 6. 调度设计

### 6.1 双轨模式

| 模式 | 用途 | 入口 |
|------|------|------|
| 手动触发 | 调试、回补历史数据、指定日期抓取 | CLI: `python -m src.providers.kaipan_scheduler fetch --date 2026-04-18 --slot 09-25` 或 `--slot all` |
| 自动调度 | 交易日 9:25 和 17:30 自动运行 | APScheduler |

### 6.2 配置项

```yaml
# config/app.yaml
kaipan:
  fetch_schedule:
    pre_market: "9:25"      # 盘前：竞价相关数据
    post_close: "17:30"    # 盘后：收盘相关数据
  trading_calendar:
    source: akshare         # akshare 为主
    fallback_source: kaipan # kaipan 节假日接口作为补充验证
```

### 6.3 数据集分配

| 时间 | 抓取数据集 | 说明 |
|------|-----------|------|
| 9:25（盘前） | 竞价总体信息、竞价数量统计、竞价列表、涨停信息、涨停原因、板块强度、行业涨幅、最强风口、区间统计-按股票/板块、题材详情、股票所属板块 V2 | 开盘前全量数据，用于盘前预测 |
| 17:30（盘后） | 涨停信息、涨停原因、板块强度、行业涨幅、龙虎榜列表、最强风口、区间统计-按股票/板块、题材详情、股票所属板块 V2 | 收盘归档数据，用于盘后归因（无竞价数据，因已收盘） |

**核心区别**：
- 9:25 有**竞价数据**（竞价总体/数量统计/列表），无**龙虎榜**
- 17:30 有**龙虎榜列表**，无竞价数据（竞价数据本质是盘前快照，盘后不再更新）
- 两次数据独立存储在 `09-25` 和 `17-30` 两个时间槽，不相互覆盖

### 6.4 交易日判断

- 优先使用 `akshare.trade_cal()` 获取 A 股完整交易日历
- `kaipan` 节假日接口（`NTL-S7-006`）落地后用于补充验证特殊调休
- 非交易日（周末、法定节假日）自动跳过调度，不报错

---

## 7. 首批接口清单（13 个）

| # | 接口 | dataset | baseURL | 9:25 | 17:30 |
|---|------|---------|---------|-------|-------|
| 1 | 板块强度 | `hot_topics` | `apphis` | ✅ | ✅ |
| 2 | 行业涨幅 | `hot_topics` | `apphis` | ✅ | ✅ |
| 3 | 概念风口 | `hot_topics` | `apphis` | ✅ | ✅ |
| 4 | 题材详情 | `topic_constituents` | `applhb` | ✅ | ✅ |
| 5 | 股票所属板块 V2 | `topic_constituents` | `apphwshhq` | ✅ | ✅ |
| 6 | 最强风口 | `strong_symbols` | `apphis` | ✅ | ✅ |
| 7 | 区间统计-按股票 | `strong_symbols` | `apphis` | ✅ | ✅ |
| 8 | 竞价列表 | `strong_symbols` | `apphis` | ✅ | ❌ |
| 9 | 涨停原因 | `topic_constituents` | `apphis` | ✅ | ✅ |
| 10 | 竞价总体信息 | `pre_market_bid` | `apphis` | ✅ | ❌ |
| 11 | 竞价数量统计 | `pre_market_stats` | `apphis` | ✅ | ❌ |
| 12 | 涨停信息 | `limit_up_info` | `apphis` | ✅ | ✅ |
| 13 | 龙虎榜列表 | `lhb_list` | `applhb` | ❌ | ✅ |

---

## 8. 任务分解与依赖

| 任务 | 内容 | 前置依赖 |
|------|------|---------|
| `NTL-S0-007` | 定义 `raw / snapshots` 目录规范 | — |
| `NTL-S0-008` | 实现 `KaipanProvider` 的多域名 HTTP 请求和 raw JSON 保存 | `NTL-S0-007` |
| `NTL-S0-009` | 创建 `kaipan_schema/*.yaml` 字段映射文件 + 实现 `KaipanNormalizer` | `NTL-S0-008` |
| `NTL-S0-010` | 元信息嵌入 raw JSON（meta 字段） | `NTL-S0-007` |
| `NTL-S0-014` | 离线验证脚本（抓取 + 转换 + 读取全链路断言） | `NTL-S0-009`、`NTL-S0-010` |

---

## 9. 文件变更清单

| 操作 | 文件路径 |
|------|---------|
| 新增 | `src/providers/kaipan_provider.py`（改造：多域名支持） |
| 新增 | `src/providers/kaipan_normalizer.py` |
| 新增 | `src/providers/kaipan_scheduler.py` |
| 新增 | `src/providers/kaipan_schema/hot_topics.yaml` |
| 新增 | `src/providers/kaipan_schema/topic_constituents.yaml` |
| 新增 | `src/providers/kaipan_schema/strong_symbols.yaml` |
| 新增 | `src/providers/kaipan_schema/market_context.yaml` |
| 新增 | `data/kaipan/raw/`（目录结构，含 `09-25` 和 `17-30` 两个时间槽） |
| 新增 | `data/kaipan/snapshots/`（目录结构，含 `09-25` 和 `17-30` 两个时间槽） |
| 修改 | `config/app.yaml`（添加 `kaipan.fetch_schedule` 配置） |

---

## 10. 验收标准

1. `KaipanProvider` 可以向 3 个不同 baseURL 发起请求并存 raw JSON
2. raw JSON 顶部内嵌 `meta` 字段，包含 `dataset`、`trade_date`、`slot`（`09-25` 或 `17-30`）、来源接口、请求参数、抓取时间
3. `KaipanNormalizer` 可以从 YAML 映射文件读取规则并执行字段转换
4. 标准化快照 JSON 包含 `hot_topics`、`topic_constituents`、`strong_symbols`、`market_context` 四个数据集
5. CLI 命令 `kaipan_scheduler.py fetch --date YYYY-MM-DD --slot 09-25` 或 `--slot all` 可以手动触发指定日期和时间槽抓取
6. 自动调度在每个交易日 9:25 和 17:30 运行（可配置）
7. 非交易日自动跳过，不报错
8. 全链路可离线验证：有样例 raw JSON 文件时，normalizer 可以独立完成转换
9. 13 个接口全部可抓取，raw 文件和 snapshot 文件正确存放在对应 `slot` 目录
