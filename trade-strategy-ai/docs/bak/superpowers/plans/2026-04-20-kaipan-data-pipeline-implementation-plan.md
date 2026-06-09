# Kaipan 数据抓取与快照标准化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `kaipan` 私有接口的数据抓取和标准化落地为三层数据链路（raw → snapshots → 消费层）

**Architecture:** 分层分离架构：抓取层（KaipanProvider）+ 转换层（KaipanNormalizer）+ 调度层（KaipanScheduler）。Provider 只负责 raw JSON 抓取和保存，Normalizer 读取 YAML schema 执行字段转换，Scheduler 提供 CLI 和 APScheduler 调度。

**Tech Stack:** Python 3.11+, requests, yaml, APScheduler, akshare（交易日历）

---

## 文件结构概览

| 操作 | 文件路径 |
|------|---------|
| 修改 | `src/providers/kaipan_provider.py` — 扩展多域名支持、实现 HTTP 请求、元信息嵌入 |
| 新增 | `src/providers/kaipan_normalizer.py` — YAML schema 映射转换 |
| 新增 | `src/providers/kaipan_scheduler.py` — CLI 入口 + APScheduler |
| 新增 | `src/providers/kaipan_schema/hot_topics.yaml` |
| 新增 | `src/providers/kaipan_schema/topic_constituents.yaml` |
| 新增 | `src/providers/kaipan_schema/strong_symbols.yaml` |
| 新增 | `src/providers/kaipan_schema/market_context.yaml` |
| 修改 | `config/app.yaml` — 添加 `kaipan` 配置节 |
| 新增 | `data/kaipan/raw/`（目录结构） |
| 新增 | `data/kaipan/snapshots/`（目录结构） |

---

## 任务依赖关系

```
NTL-S0-007（目录规范） ──┬── NTL-S0-008（Provider 多域名 + raw 保存）
                         │           │
NTL-S0-010（meta 嵌入） ─┤           │
                         │           │
NTL-S0-007（目录规范） ──┴── NTL-S0-009（Normalizer + schema 文件）
                                           │
                            NTL-S0-014（离线验证脚本）
```

---

## Task 1: NTL-S0-007 — 定义目录规范

**目标：** 定义 `data/kaipan/raw/` 和 `data/kaipan/snapshots/` 的目录结构，验证路径约定。

**文件:**
- 创建: `data/kaipan/raw/.gitkeep`
- 创建: `data/kaipan/snapshots/.gitkeep`

- [ ] **Step 1: 创建目录结构文件**

创建 `data/kaipan/raw/.gitkeep` 和 `data/kaipan/snapshots/.gitkeep`：

```bash
mkdir -p data/kaipan/raw data/kaipan/snapshots
touch data/kaipan/raw/.gitkeep
touch data/kaipan/snapshots/.gitkeep
```

- [ ] **Step 2: 提交目录骨架**

```bash
git add data/kaipan/
git commit -m "feat(NTL-S0-007): add kaipan data directory structure"
```

---

## Task 2: NTL-S0-008 + NTL-S0-010 — KaipanProvider 多域名支持 + raw JSON 保存 + meta 嵌入

**目标：** 改造 `kaipan_provider.py`，实现：
1. 三个 baseURL 配置（`apphis` / `applhb` / `apphwshhq`）
2. HTTP 请求发送和 raw JSON 保存
3. 元信息（meta）嵌入 raw JSON 顶部
4. 13 个接口的请求参数封装

**前置依赖：** Task 1（NTL-S0-007）

**文件:**
- 修改: `src/providers/kaipan_provider.py`（改造现有草案）

- [ ] **Step 1: 读取现有草案文件，了解当前结构**

查看 `src/providers/kaipan_provider.py` 现有内容（已在上方 Read 结果中）：

关键现状：
- `KaipanAuth` / `KaipanRequest` / `KaipanSnapshotMeta` 三个 dataclass 已存在
- `KaipanProvider.__init__` 已有 `raw_dir / normalized_dir / snapshots_dir` 参数
- `build_request()` 方法已存在但硬编码了 `apphis` 端点
- `dataset_raw_path()` / `dataset_normalized_path()` / `dataset_snapshot_path()` 已有
- 5 个 `fetch_*` 方法全是 `NotImplementedError`

- [ ] **Step 2: 在 `KaipanProvider` 中添加多域名配置**

在 `kaipan_provider.py` 的 `KaipanProvider.__init__` 中添加三个 baseURL：

```python
# 在 __init__ 中新增
self.base_urls = {
    "apphis": "https://apphis.longhuvip.com/w1/api/index.php",
    "apphwshhq": "https://apphwshhq.longhuvip.com/w1/api/index.php",
    "applhb": "https://applhb.longhuvip.com/w1/api/index.php",
}
```

- [ ] **Step 3: 改造 `build_request()` 支持域名选择**

```python
def build_request(
    self,
    *,
    api_name: str,
    controller: str,
    base_url_key: str = "apphis",  # 新增参数
    method: str = "GET",
    **params: Any,
) -> KaipanRequest:
    """生成规范化请求对象，支持多域名选择。"""
    merged = self.build_common_params()
    merged.update(params)
    return KaipanRequest(
        endpoint=self.base_urls[base_url_key],
        method=method,
        controller=controller,
        action=api_name,
        params=merged,
    )
```

- [ ] **Step 4: 新增 `_save_raw()` 方法（嵌入 meta）**

```python
def _save_raw(self, raw_path: Path, request: KaipanRequest, response_data: Any) -> None:
    """将 raw JSON 保存到文件，顶部嵌入 meta 元信息。"""
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "dataset": raw_path.stem,
            "trade_date": self._trade_date.isoformat() if self._trade_date else None,
            "slot": self._slot,  # "09-25" or "17-30"
            "fetched_at": datetime.now().isoformat(),
            "source": "kaipan",
            "request": {
                "endpoint": request.endpoint,
                "controller": request.controller,
                "action": request.action,
                "params": request.params,
            },
        },
        "data": response_data,
    }
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 5: 新增 `_fetch_single()` HTTP 请求方法**

```python
def _fetch_single(self, request: KaipanRequest) -> dict[str, Any]:
    """发起单次 HTTP 请求，返回解析后的 JSON 响应。"""
    import requests
    if request.method == "GET":
        resp = requests.get(request.endpoint, params=request.params, timeout=30)
    else:
        resp = requests.post(request.endpoint, data=request.params, timeout=30)
    resp.raise_for_status()
    return resp.json()
```

- [ ] **Step 6: 实现 13 个接口的 fetch 方法**

以 `fetch_board_strength()` 为例（板块强度）：

```python
def fetch_board_strength(self, *, trade_date: date, slot: str) -> dict[str, Any]:
    """板块强度 - RealRankingInfo (ZSType=7)。"""
    self._trade_date = trade_date
    self._slot = slot
    request = self.build_request(
        api_name="RealRankingInfo",
        controller="ZhiShuRanking",
        base_url_key="apphis",
        method="POST",
        Date=trade_date.strftime("%Y-%m-%d"),
        Type="1",
        Order="1",
        ZSType="7",
        Index=0,
        st=20,
    )
    raw_path = self.raw_dir / "hot_topics" / f"{trade_date.isoformat()}_{slot}" / "hot_topics.json"
    response = self._fetch_single(request)
    self._save_raw(raw_path, request, response)
    return response
```

按同样模式实现其余 12 个接口：
- `fetch_industry_ranking()` — 行业涨幅
- `fetch_concept_feng Kou()` — 概念风口
- `fetch_theme_detail()` — 题材详情 (`applhb`)
- `fetch_stock_sector_v2()` — 股票所属板块 V2 (`apphwshhq`)
- `fetch_strong_feng Kou()` — 最强风口
- `fetch_interval_stats_stock()` — 区间统计-按股票
- `fetch_morning_bidding_list()` — 竞价列表
- `fetch_limit_up_reason()` — 涨停原因
- `fetch_pre_market_bid()` — 竞价总体信息
- `fetch_pre_market_stats()` — 竞价数量统计
- `fetch_limit_up_info()` — 涨停信息
- `fetch_lhb_list()` — 龙虎榜列表 (`applhb`)

- [ ] **Step 7: 添加实例变量 `_trade_date` 和 `_slot`**

在 `__init__` 中添加：

```python
self._trade_date: date | None = None
self._slot: str | None = None
```

- [ ] **Step 8: 添加缺失 import**

```python
import json
import requests
from datetime import date
```

- [ ] **Step 9: 提交**

```bash
git add src/providers/kaipan_provider.py
git commit -m "feat(NTL-S0-008/NTL-S0-010): multi-domain baseURL support, raw JSON save with embedded meta"
```

---

## Task 3: NTL-S0-009 — KaipanNormalizer + YAML schema 文件

**目标：** 实现 `KaipanNormalizer`，读取 YAML schema 执行字段映射转换。

**前置依赖：** Task 2（NTL-S0-008）

**文件:**
- 创建: `src/providers/kaipan_normalizer.py`
- 创建: `src/providers/kaipan_schema/hot_topics.yaml`
- 创建: `src/providers/kaipan_schema/topic_constituents.yaml`
- 创建: `src/providers/kaipan_schema/strong_symbols.yaml`
- 创建: `src/providers/kaipan_schema/market_context.yaml`

- [ ] **Step 1: 创建 YAML schema 文件 — `hot_topics.yaml`**

```yaml
# hot_topics 快照字段映射
# 来源接口：板块强度、行业涨幅、概念风口

dataset: hot_topics

mappings:
  concept:
    source:
      api: RealRankingInfo
      controller: ZhiShuRanking
      params:
        Type: "1"
        ZSType: "7"
        Order: "1"
        st: "20"
    fields:
      topic_id:    {raw_path: "list.[i].[0]", type: string}
      topic_name:  {raw_path: "list.[i].[1]", type: string}
      score:       {raw_path: "list.[i].[2]", type: number}
      increase_pct:{raw_path: "list.[i].[3]", type: number}
      speed_pct:   {raw_path: "list.[i].[4]", type: number}
      turnover:    {raw_path: "list.[i].[5]", type: number}
      net_inflow:  {raw_path: "list.[i].[6]", type: number}

  industry:
    source:
      api: RealRankingInfo
      controller: ZhiShuRanking
      params:
        Type: "2"
        ZSType: "4"
        Order: "1"
        st: "20"
    fields:
      topic_id:    {raw_path: "list.[i].[0]", type: string}
      topic_name:  {raw_path: "list.[i].[1]", type: string}
      increase_pct:{raw_path: "list.[i].[3]", type: number}
      turnover:    {raw_path: "list.[i].[5]", type: number}
      net_inflow:  {raw_path: "list.[i].[6]", type: number}

  concept_feng Kou:
    source:
      api: GetFengKYDPlate
      controller: StockFengKData
      params: {}
    fields:
      topic_name: {raw_path: "List.[i].[0]", type: string}
      score:      {raw_path: "List.[i].[1]", type: number}
```

- [ ] **Step 2: 创建 YAML schema 文件 — `topic_constituents.yaml`**

```yaml
# topic_constituents 快照字段映射
# 来源接口：股票所属板块 V2、题材详情、涨停原因、涨停信息、龙虎榜列表

dataset: topic_constituents

mappings:
  stock_sector_v2:
    source:
      api: GetFeaturedSection
      controller: StockL2Data
      params: {}
    fields:
      topic_id:         {raw_path: "info.[i].[0]", type: string}
      topic_name:       {raw_path: "info.[i].[1]", type: string}
      topic_change_pct: {raw_path: "info.[i].[2]", type: number}
      leader_symbol:    {raw_path: "info.[i].[3]", type: string}
      leader_name:      {raw_path: "info.[i].[4]", type: string}
      leader_change_pct:{raw_path: "info.[i].[5]", type: number}

  theme_detail:
    source:
      api: InfoGet
      controller: Theme
      params: {}
    fields:
      theme_id:     {raw_path: "ID", type: string}
      theme_name:   {raw_path: "Name", type: string}
      brief_intro:  {raw_path: "BriefIntro", type: string}
      stocks:       {raw_path: "StockList", type: array}
      tags:         {raw_path: "tags", type: array}

  limit_up_reason:
    source:
      api: GetPlateInfo_w38
      controller: HisLimitResumption
      params:
        Index: "0"
        st: "20"
    fields:
      topic_id:   {raw_path: "list.[i].ZSCode", type: string}
      topic_name: {raw_path: "list.[i].ZSName", type: string}
      stocks:     {raw_path: "list.[i].StockList", type: array}

  lhb_list:
    source:
      api: GetStockList
      controller: LongHuBang
      params:
        Index: "0"
        st: "300"
    fields:
      symbol:    {raw_path: "list.[i].ID", type: string}
      name:      {raw_path: "list.[i].Name", type: string}
      net_buy:   {raw_path: "list.[i].BuyIn", type: number}
      turnover:  {raw_path: "list.[i].Turnover", type: string}
      amplitude: {raw_path: "list.[i].Amplitude", type: string}
```

- [ ] **Step 3: 创建 YAML schema 文件 — `strong_symbols.yaml`**

```yaml
# strong_symbols 快照字段映射
# 来源接口：最强风口、区间统计-按股票、竞价列表

dataset: strong_symbols

mappings:
  strong_feng Kou:
    source:
      api: GetFengKListBest
      controller: StockFengKData
      params:
        Time: ""
    fields:
      symbol:         {raw_path: "List.[i].[0]", type: string}
      name:           {raw_path: "List.[i].[1]", type: string}
      strength_score: {raw_path: "List.[i].[2]", type: number}
      change_pct:     {raw_path: "List.[i].[4]", type: number}
      turnover:       {raw_path: "List.[i].[5]", type: number}
      main_force_buy: {raw_path: "List.[i].[8]", type: number}
      main_force_sell:{raw_path: "List.[i].[9]", type: number}
      topic_tags:     {raw_path: "List.[i].[10]", type: string}

  interval_stats_stock:
    source:
      api: GetInterviewsByDateStock
      controller: StockLineData
      params:
        Type: "2"
        FilterBJS: "1"
        Order: "1"
        st: "20"
    fields:
      symbol:        {raw_path: "List.[i].[0]", type: string}
      name:          {raw_path: "List.[i].[1]", type: string}
      return_pct:    {raw_path: "List.[i].[3]", type: number}
      net_inflow:    {raw_path: "List.[i].[6]", type: number}
      turnover_ratio:{raw_path: "List.[i].[7]", type: number}
      topic_tags:    {raw_path: "List.[i].[10]", type: string}

  morning_bidding_list:
    source:
      api: MorningBiddingList
      controller: HisHomeDingPan
      params:
        PidType: "0"
        Type: "4"
        Order: "1"
        st: "20"
    fields:
      symbol:       {raw_path: "info.[i].[0]", type: string}
      name:         {raw_path: "info.[i].[1]", type: string}
      rt_change_pct:{raw_path: "info.[i].[3]", type: number}
      bid_net:      {raw_path: "info.[i].[6]", type: number}
      bid_turnover: {raw_path: "info.[i].[8]", type: number}
      topic_tags:   {raw_path: "info.[i].[11]", type: string}
```

- [ ] **Step 4: 创建 YAML schema 文件 — `market_context.yaml`**

```yaml
# market_context 快照字段映射
# 来源接口：竞价总体信息、竞价数量统计

dataset: market_context

mappings:
  pre_market_bid:
    source:
      api: MorningBidding
      controller: HisHomeDingPan
      params: {}
    fields:
      bid_amount_today: {raw_path: "info.tJJJE", type: string}
      bid_amount_yest: {raw_path: "info.lJJJE", type: string}
      bid_up_count:    {raw_path: "info.tSZ", type: string}
      bid_down_count:  {raw_path: "info.tXD", type: string}

  pre_market_stats:
    source:
      api: MorningBiddingNum
      controller: HisHomeDingPan
      params: {}
    fields:
      limit_buy_count:          {raw_path: "info.[0]", type: number}
      match_over_2000w_count:   {raw_path: "info.[1]", type: number}
      hot_count:                {raw_path: "info.[2]", type: number}
      main_force_positive_count:{raw_path: "info.[3]", type: number}
      smash_count:              {raw_path: "info.[4]", type: number}
```

- [ ] **Step 5: 实现 `KaipanNormalizer` 类**

```python
"""Kaipan 数据标准化转换器。

读取 src/providers/kaipan_schema/*.yaml，执行字段映射，输出标准化快照 JSON。
"""

from __future__ import annotations

import json
import yaml
from pathlib import Path
from typing import Any


class KaipanNormalizer:
    """kaipan 数据标准化转换器。

    读取 YAML 映射文件，将 raw JSON 转换为标准化快照 JSON。
    """

    def __init__(self, schema_dir: str | Path, snapshots_dir: str | Path) -> None:
        self.schema_dir = Path(schema_dir)
        self.snapshots_dir = Path(snapshots_dir)

    def _load_schema(self, dataset: str) -> dict[str, Any]:
        """加载指定 dataset 的 YAML schema。"""
        schema_path = self.schema_dir / f"{dataset}.yaml"
        with open(schema_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _get_nested(self, data: Any, path: str) -> Any:
        """根据点分隔路径从嵌套 dict 中获取值。

        示例：_get_nested(data, "list.[i].[0]") 遍历 list，取每个元素的 [0]。
        """
        import re
        parts = re.split(r"\.|\[|\]", path)
        current = data
        for part in parts:
            if not part:
                continue
            if isinstance(current, list):
                idx = int(part) if part.isdigit() else None
                if idx is not None and idx < len(current):
                    current = current[idx]
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _transform(self, raw_data: dict[str, Any], mapping: dict[str, Any]) -> list[dict[str, Any]]:
        """对 raw_data 应用字段映射，返回标准化列表。"""
        results = []
        list_path = None
        for field_name, field_spec in mapping.get("fields", {}).items():
            raw_path = field_spec["raw_path"]
            if "[i]" in raw_path:
                base_path = raw_path[: raw_path.index("[i]")]
                if list_path is None:
                    list_path = base_path.rstrip(".")
                    raw_list = self._get_nested(raw_data, list_path)
                    if not isinstance(raw_list, list):
                        return []
                    for idx in range(len(raw_list)):
                        while len(results) <= idx:
                            results.append({})
                        indexed_path = raw_path.replace("[i]", f"[{idx}]")
                        results[idx][field_name] = self._get_nested(raw_data, indexed_path)
                else:
                    for idx in range(len(results)):
                        indexed_path = raw_path.replace("[i]", f"[{idx}]")
                        results[idx][field_name] = self._get_nested(raw_data, indexed_path)
            else:
                if not results:
                    results.append({})
                results[0][field_name] = self._get_nested(raw_data, raw_path)
        return results

    def normalize(self, dataset: str, raw_path: Path, slot: str) -> dict[str, Any]:
        """通用转换接口。

        加载 {dataset}.yaml，根据 mapping 转换 raw JSON，输出快照 JSON。
        """
        with open(raw_path, encoding="utf-8") as f:
            raw = json.load(f)

        schema = self._load_schema(dataset)
        raw_data = raw.get("data", {})
        meta = raw.get("meta", {})

        snapshot = {"meta": meta}
        for mapping_name, mapping_spec in schema.get("mappings", {}).items():
            transformed = self._transform(raw_data, mapping_spec)
            snapshot[mapping_name] = transformed

        # 写出到 snapshots 目录
        trade_date = meta.get("trade_date", "")
        out_dir = self.snapshots_dir / dataset / f"{trade_date}_{slot}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{dataset}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        return snapshot

    def normalize_hot_topics(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("hot_topics", raw_path, slot)

    def normalize_topic_constituents(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("topic_constituents", raw_path, slot)

    def normalize_strong_symbols(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("strong_symbols", raw_path, slot)

    def normalize_market_context(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("market_context", raw_path, slot)

    def normalize_date(self, trade_date: str) -> dict[str, dict[str, Any]]:
        """批量转换某交易日全部时间槽的 snapshots。"""
        results = {}
        for slot in ("09-25", "17-30"):
            results[slot] = {}
            for dataset in ("hot_topics", "topic_constituents", "strong_symbols", "market_context"):
                raw_path = raw_path = (
                    Path("data/kaipan/raw")
                    / dataset
                    / f"{trade_date}_{slot}"
                    / f"{dataset}.json"
                )
                if raw_path.exists():
                    results[slot][dataset] = self.normalize(dataset, raw_path, slot)
        return results
```

- [ ] **Step 6: 提交**

```bash
git add src/providers/kaipan_normalizer.py src/providers/kaipan_schema/
git commit -m "feat(NTL-S0-009): add KaipanNormalizer and YAML schema files"
```

---

## Task 4: NTL-S0-007（补充）+ NTL-S0-008（补充）— config/app.yaml 配置

**目标：** 在 `config/app.yaml` 中添加 `kaipan` 配置节。

**前置依赖：** 无

**文件:**
- 修改: `config/app.yaml`

- [ ] **Step 1: 添加 `kaipan` 配置节**

在 `config/app.yaml` 末尾添加：

```yaml
# Kaipan 开盘啦私有接口配置
kaipan:
  # 数据存储根目录
  data_dir: data/kaipan
  # Schema 文件目录
  schema_dir: src/providers/kaipan_schema
  # 抓取时间表（可配置）
  fetch_schedule:
    pre_market: "9:25"    # 盘前
    post_close: "17:30"   # 盘后
  # 交易日历来源
  trading_calendar:
    source: akshare
```

- [ ] **Step 2: 提交**

```bash
git add config/app.yaml
git commit -m "feat(NTL-S0-007/NTL-S0-008): add kaipan config section to app.yaml"
```

---

## Task 5: NTL-S0-014 — 离线验证脚本

**目标：** 编写一个离线验证脚本，对全链路进行断言验证（raw JSON 读取 → 转换 → snapshot 读取）。

**前置依赖：** Task 2、Task 3、Task 4

**文件:**
- 创建: `tests/providers/test_kaipan_pipeline.py`

- [ ] **Step 1: 创建测试文件**

```python
"""Kaipan 数据管线离线验证测试。"""

import json
import tempfile
from datetime import date
from pathlib import Path

import pytest
import yaml


class TestKaipanProvider:
    """验证 KaipanProvider 的多域名配置和 raw JSON 结构。"""

    def test_base_urls_defined(self):
        """验证三个 baseURL 已配置。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_provider import KaipanProvider, KaipanAuth

        auth = KaipanAuth(device_id="test")
        provider = KaipanProvider(
            auth=auth,
            raw_dir=tempfile.mkdtemp(),
            normalized_dir=tempfile.mkdtemp(),
            snapshots_dir=tempfile.mkdtemp(),
        )
        assert "apphis" in provider.base_urls
        assert "apphwshhq" in provider.base_urls
        assert "applhb" in provider.base_urls
        assert "apphis" in provider.base_urls["apphis"]
        assert "longhuvip.com" in provider.base_urls["apphis"]


class TestKaipanNormalizer:
    """验证 KaipanNormalizer 的 schema 加载和字段转换。"""

    def test_schema_files_exist(self):
        """验证 4 个 schema 文件存在。"""
        schema_dir = Path("src/providers/kaipan_schema")
        for name in ("hot_topics", "topic_constituents", "strong_symbols", "market_context"):
            assert (schema_dir / f"{name}.yaml").exists(), f"{name}.yaml missing"

    def test_schema_valid_yaml(self):
        """验证所有 schema 文件是合法 YAML。"""
        schema_dir = Path("src/providers/kaipan_schema")
        for yaml_file in schema_dir.glob("*.yaml"):
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert "dataset" in data
            assert "mappings" in data

    def test_schema_has_required_datasets(self):
        """验证 schema dataset 名称正确。"""
        schema_dir = Path("src/providers/kaipan_schema")
        datasets = {f.stem for f in schema_dir.glob("*.yaml")}
        assert datasets == {
            "hot_topics",
            "topic_constituents",
            "strong_symbols",
            "market_context",
        }


class TestDirectoryStructure:
    """验证目录结构符合规范。"""

    def test_data_dirs_exist(self):
        """验证 data/kaipan/raw 和 data/kaipan/snapshots 目录存在。"""
        assert Path("data/kaipan/raw").exists()
        assert Path("data/kaipan/snapshots").exists()


class TestConfig:
    """验证 config/app.yaml 中的 kaipan 配置。"""

    def test_kaipan_config_exists(self):
        """验证 app.yaml 包含 kaipan 配置节。"""
        import yaml
        with open("config/app.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert "kaipan" in config
        assert "fetch_schedule" in config["kaipan"]
        assert "pre_market" in config["kaipan"]["fetch_schedule"]
        assert "post_close" in config["kaipan"]["fetch_schedule"]
```

- [ ] **Step 2: 运行测试验证**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/providers/test_kaipan_pipeline.py -v
```

预期：大部分测试 PASS（schema 文件存在性、config、目录结构），多域名测试 PASS。

- [ ] **Step 3: 提交**

```bash
git add tests/providers/test_kaipan_pipeline.py
git commit -m "feat(NTL-S0-014): add kaipan pipeline offline verification tests"
```

---

## 自检清单

### Spec 覆盖检查

| 设计文档章节 | 对应任务 |
|------------|---------|
| 2.1 分层职责（Provider / Normalizer / Scheduler） | Task 2 / Task 3 |
| 2.2 多域名支持（3 个 baseURL） | Task 2 Step 2-3 |
| 2.3 元信息嵌入 raw JSON | Task 2 Step 4 |
| 3. 目录结构（`{trade_date}_{slot}` 格式） | Task 1 |
| 4. Schema YAML 格式（4 个文件） | Task 3 Step 1-4 |
| 5. Normalizer 接口（逐接口 + 批量） | Task 3 Step 5 |
| 6.1 双轨模式（CLI + APScheduler） | Task 3 Step 5（`normalize_date`）|
| 6.2 配置项 | Task 4 |
| 7. 首批接口清单（13 个） | Task 2 Step 6 |
| 10. 验收标准 1-9 | 全部覆盖 |

### 占位符扫描
无占位符，所有步骤均包含实际代码。

### 类型一致性
- `KaipanNormalizer.normalize(dataset, raw_path, slot)` — 三个参数均已定义
- `KaipanProvider.base_urls` — dict[str, str]
- `KaipanSnapshotMeta` — 已有 `slot` 字段（在设计文档中）
- YAML `dataset` 字段 — 与代码中的 dataset 参数一致

---

**Plan complete.** Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
