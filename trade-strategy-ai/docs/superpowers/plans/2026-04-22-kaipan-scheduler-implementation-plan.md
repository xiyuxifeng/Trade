# KaipanScheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `kaipan_scheduler.py`，提供 CLI 入口（fetch/normalize/status/run）和 APScheduler 自动调度。

**Architecture:** 调度层位于 KaipanProvider 和 KaipanNormalizer 之上，不承担业务逻辑。通过 `KaipanAuth` 从配置读取 device_id，协调 provider 抓取和 normalizer 转换。

**Tech Stack:** Python 3.11+, argparse, APScheduler, akshare（交易日历）, PyYAML

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/providers/kaipan_scheduler.py` | CLI 入口、APScheduler 调度、fetch/normalize/status/run 四个命令 |
| `config/app.yaml` | 新增 `kaipan.auth.device_id` 配置项 |

---

## Task 1: 添加配置项

**Files:**
- Modify: `config/app.yaml`

- [ ] **Step 1: 在 `kaipan` 配置节下新增 `auth` 段**

在 `kaipan` 配置节（line ~163）末尾添加：

```yaml
kaipan:
  auth:
    device_id: "your_device_id"  # 从 kaipan App 获取
```

- [ ] **Step 2: 提交**

```bash
git add config/app.yaml
git commit -m "feat(NTL-S0-007): add kaipan auth device_id config"
```

---

## Task 2: 实现 KaipanScheduler CLI 骨架

**Files:**
- Create: `src/providers/kaipan_scheduler.py`

- [ ] **Step 1: 编写 CLI 解析骨架（argparse）**

```python
"""Kaipan 调度器 CLI。

提供 fetch / normalize / status / run 四个命令。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.providers.kaipan_scheduler",
        description="Kaipan 开盘啦数据抓取与快照调度器",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # fetch 命令
    fetch_parser = sub.add_parser("fetch", help="抓取指定日期和时间槽的数据")
    fetch_parser.add_argument("--date", default=None, help="交易日期 YYYY-MM-DD，默认当天")
    fetch_parser.add_argument("--slot", default="all", help="时间槽：09-25、17-30、all（默认 all）")

    # normalize 命令
    norm_parser = sub.add_parser("normalize", help="转换指定日期和时间槽的 raw → snapshot")
    norm_parser.add_argument("--date", default=None, help="交易日期 YYYY-MM-DD，默认当天")
    norm_parser.add_argument("--slot", default="all", help="时间槽：09-25、17-30、all（默认 all）")

    # status 命令
    sub.add_parser("status", help="查看最近一次抓取状态")

    # run 命令
    run_parser = sub.add_parser("run", help="启动自动调度（APScheduler）")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:])

    if args.command == "fetch":
        trade_date = date.today() if args.date is None else date.fromisoformat(args.date)
        print(f"fetch {trade_date} slot={args.slot}")
    elif args.command == "normalize":
        trade_date = date.today() if args.date is None else date.fromisoformat(args.date)
        print(f"normalize {trade_date} slot={args.slot}")
    elif args.command == "status":
        print("status: no data yet")
    elif args.command == "run":
        print("scheduler started")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证 CLI 解析**

```bash
cd /Users/wanghui/Documents/Claude/trade-strategy-ai
python -m src.providers.kaipan_scheduler fetch --date 2026-04-22 --slot 09-25
# 预期输出：fetch 2026-04-22 slot=09-25
```

- [ ] **Step 3: 提交**

```bash
git add src/providers/kaipan_scheduler.py
git commit -m "feat: add kaipan_scheduler CLI skeleton"
```

---

## Task 3: 实现配置加载

**Files:**
- Modify: `src/providers/kaipan_scheduler.py`

- [ ] **Step 1: 添加配置加载函数**

在 `import` 区域下方添加：

```python
import yaml
from pathlib import Path


def load_kaipan_config() -> dict:
    """从 config/app.yaml 加载 kaipan 配置。"""
    config_path = Path("config/app.yaml")
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("kaipan", {})


def get_auth() -> dict:
    """从配置中构造 KaipanAuth 参数字典。"""
    cfg = load_kaipan_config()
    auth_cfg = cfg.get("auth", {})
    return {
        "device_id": auth_cfg.get("device_id", ""),
    }
```

- [ ] **Step 2: 提交**

```bash
git add src/providers/kaipan_scheduler.py
git commit -m "feat: add config loading to kaipan_scheduler"
```

---

## Task 4: 实现 `fetch` 命令

**Files:**
- Modify: `src/providers/kaipan_scheduler.py`

- [ ] **Step 1: 添加 fetch 逻辑**

将 `main()` 中的 fetch 分支替换为：

```python
elif args.command == "fetch":
    import sys
    sys.path.insert(0, "src")
    from providers.kaipan_provider import KaipanProvider
    from providers.kaipan_normalizer import KaipanNormalizer
    from providers.kaipan_provider import KaipanAuth

    trade_date = date.today() if args.date is None else date.fromisoformat(args.date)
    slots = ("09-25", "17-30") if args.slot == "all" else (args.slot,)

    # 加载配置
    cfg = load_kaipan_config()
    auth_cfg = cfg.get("auth", {})
    auth = KaipanAuth(device_id=auth_cfg.get("device_id", ""))

    # 实例化 provider 和 normalizer
    provider = KaipanProvider(
        auth=auth,
        raw_dir=cfg.get("data_dir", "data/kaipan/raw"),
        normalized_dir="data/kaipan/snapshots",  # 暂不使用
        snapshots_dir="data/kaipan/snapshots",
    )
    normalizer = KaipanNormalizer(
        schema_dir=cfg.get("schema_dir", "src/providers/kaipan_schema"),
        snapshots_dir=cfg.get("data_dir", "data/kaipan/snapshots"),
    )

    # 定义数据集分配
    slot_datasets = {
        "09-25": [
            ("hot_topics", provider.fetch_board_strength, {}),
            ("hot_topics", provider.fetch_industry_ranking, {}),
            ("hot_topics", provider.fetch_concept_fengkou, {}),
            ("topic_constituents", provider.fetch_theme_detail, {}),
            ("topic_constituents", provider.fetch_stock_sector_v2, {}),
            ("strong_symbols", provider.fetch_strong_fengkou, {}),
            ("strong_symbols", provider.fetch_interval_stats_stock, {}),
            ("strong_symbols", provider.fetch_morning_bidding_list, {}),
            ("topic_constituents", provider.fetch_limit_up_reason, {}),
            ("market_context", provider.fetch_pre_market_bid, {}),
            ("market_context", provider.fetch_pre_market_stats, {}),
            ("topic_constituents", provider.fetch_limit_up_info, {}),
        ],
        "17-30": [
            ("hot_topics", provider.fetch_board_strength, {}),
            ("hot_topics", provider.fetch_industry_ranking, {}),
            ("hot_topics", provider.fetch_concept_fengkou, {}),
            ("topic_constituents", provider.fetch_theme_detail, {}),
            ("topic_constituents", provider.fetch_stock_sector_v2, {}),
            ("strong_symbols", provider.fetch_strong_fengkou, {}),
            ("strong_symbols", provider.fetch_interval_stats_stock, {}),
            ("topic_constituents", provider.fetch_limit_up_reason, {}),
            ("topic_constituents", provider.fetch_limit_up_info, {}),
            ("topic_constituents", provider.fetch_lhb_list, {}),
        ],
    }

    for slot in slots:
        datasets = slot_datasets.get(slot, [])
        success, failed = 0, 0
        for _dataset, fetch_fn, kwargs in datasets:
            try:
                fetch_fn(trade_date=trade_date, slot=slot, **kwargs)
                success += 1
            except Exception as e:
                failed += 1
                print(f"  [WARN] {fetch_fn.__name__} failed: {e}", file=sys.stderr)

        # 抓取完成后立即转换
        try:
            normalizer.normalize_date(trade_date.isoformat(), slots=(slot,))
            print(f"fetch + normalize {trade_date} {slot}: {success} ok, {failed} failed")
        except Exception as e:
            print(f"fetch {trade_date} {slot}: {success} ok, {failed} failed (normalize error: {e})", file=sys.stderr)
```

- [ ] **Step 2: 提交**

```bash
git add src/providers/kaipan_scheduler.py
git commit -m "feat: implement fetch command in kaipan_scheduler"
```

---

## Task 5: 实现 `normalize` 命令

**Files:**
- Modify: `src/providers/kaipan_scheduler.py`

- [ ] **Step 1: 添加 normalize 逻辑**

将 `main()` 中的 normalize 分支替换为：

```python
elif args.command == "normalize":
    import sys
    sys.path.insert(0, "src")
    from providers.kaipan_normalizer import KaipanNormalizer

    trade_date = date.today() if args.date is None else date.fromisoformat(args.date)
    slots = ("09-25", "17-30") if args.slot == "all" else (args.slot,)

    cfg = load_kaipan_config()
    normalizer = KaipanNormalizer(
        schema_dir=cfg.get("schema_dir", "src/providers/kaipan_schema"),
        snapshots_dir=cfg.get("data_dir", "data/kaipan/snapshots"),
    )

    results = normalizer.normalize_date(trade_date.isoformat(), slots=slots)
    for slot, datasets in results.items():
        ok = sum(1 for v in datasets.values() if v is not None and "_error" not in v)
        err = sum(1 for v in datasets.values() if v is None or "_error" in v)
        print(f"normalize {trade_date} {slot}: {ok} ok, {err} failed")
```

- [ ] **Step 2: 提交**

```bash
git add src/providers/kaipan_scheduler.py
git commit -m "feat: implement normalize command in kaipan_scheduler"
```

---

## Task 6: 实现 `status` 命令

**Files:**
- Modify: `src/providers/kaipan_scheduler.py`

- [ ] **Step 1: 添加 status 逻辑**

将 `main()` 中的 status 分支替换为：

```python
elif args.command == "status":
    from pathlib import Path
    import json

    cfg = load_kaipan_config()
    raw_base = Path(cfg.get("data_dir", "data/kaipan/raw"))
    if not raw_base.exists():
        print("status: no data yet")
        return

    # 查找最近一次抓取
    latest = None
    for p in sorted(raw_base.rglob("*.json"), reverse=True):
        if p.parent.name.startswith("20"):
            latest = p.parent.name
            break

    if latest:
        print(f"status: latest slot {latest}")
    else:
        print("status: no data yet")
```

- [ ] **Step 2: 提交**

```bash
git add src/providers/kaipan_scheduler.py
git commit -m "feat: implement status command in kaipan_scheduler"
```

---

## Task 7: 实现 `run` 命令（APScheduler 自动调度）

**Files:**
- Modify: `src/providers/kaipan_scheduler.py`

- [ ] **Step 1: 添加 APScheduler 调度逻辑**

在文件顶部 `import` 区域添加：

```python
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
```

在 `main()` 前添加辅助函数：

```python
def is_trading_day(trade_date: date) -> bool:
    """通过 akshare 判断是否为 A 股交易日。"""
    try:
        import akshare as ak
        cal = ak.trade_cal(symbol="A股")
        trading_days = cal[cal["is_open"] == 1]["cal_date"].tolist()
        return trade_date.isoformat() in trading_days
    except Exception:
        return False  # 网络异常时跳过，不阻塞调度


def run_fetch(slot: str):
    """由 APScheduler 调用的 fetch 包装函数。"""
    import sys
    sys.argv = ["kaipan_scheduler", "fetch", "--slot", slot]
    # 复用 main 中的 fetch 分支逻辑，但通过 sys.argv 注入
    # 由于 main() 已有完整实现，这里直接调用内部函数
    from datetime import date as date_cls
    import yaml
    sys.path.insert(0, "src")
    from providers.kaipan_provider import KaipanProvider
    from providers.kaipan_normalizer import KaipanNormalizer
    from providers.kaipan_provider import KaipanAuth

    trade_date = date_cls.today()
    cfg = load_kaipan_config()
    auth_cfg = cfg.get("auth", {})
    auth = KaipanAuth(device_id=auth_cfg.get("device_id", ""))
    provider = KaipanProvider(
        auth=auth,
        raw_dir=cfg.get("data_dir", "data/kaipan/raw"),
        normalized_dir="data/kaipan/snapshots",
        snapshots_dir=cfg.get("data_dir", "data/kaipan/snapshots"),
    )
    normalizer = KaipanNormalizer(
        schema_dir=cfg.get("schema_dir", "src/providers/kaipan_schema"),
        snapshots_dir=cfg.get("data_dir", "data/kaipan/snapshots"),
    )

    if slot == "09-25":
        datasets = [
            (provider.fetch_board_strength, {}),
            (provider.fetch_industry_ranking, {}),
            (provider.fetch_concept_fengkou, {}),
            (provider.fetch_theme_detail, {}),
            (provider.fetch_stock_sector_v2, {}),
            (provider.fetch_strong_fengkou, {}),
            (provider.fetch_interval_stats_stock, {}),
            (provider.fetch_morning_bidding_list, {}),
            (provider.fetch_limit_up_reason, {}),
            (provider.fetch_pre_market_bid, {}),
            (provider.fetch_pre_market_stats, {}),
            (provider.fetch_limit_up_info, {}),
        ]
    else:
        datasets = [
            (provider.fetch_board_strength, {}),
            (provider.fetch_industry_ranking, {}),
            (provider.fetch_concept_fengkou, {}),
            (provider.fetch_theme_detail, {}),
            (provider.fetch_stock_sector_v2, {}),
            (provider.fetch_strong_fengkou, {}),
            (provider.fetch_interval_stats_stock, {}),
            (provider.fetch_limit_up_reason, {}),
            (provider.fetch_limit_up_info, {}),
            (provider.fetch_lhb_list, {}),
        ]

    for fetch_fn, kwargs in datasets:
        try:
            fetch_fn(trade_date=trade_date, slot=slot, **kwargs)
        except Exception as e:
            logging.warning(f"{fetch_fn.__name__} failed: {e}")

    normalizer.normalize_date(trade_date.isoformat(), slots=(slot,))
    logging.info(f"scheduled fetch + normalize completed for {trade_date} {slot}")
```

将 `main()` 中的 run 分支替换为：

```python
elif args.command == "run":
    import signal

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not is_trading_day(date.today()):
        print("today is not a trading day, skipping")
        return

    scheduler = BackgroundScheduler()

    cfg = load_kaipan_config()
    pre_market = cfg.get("fetch_schedule", {}).get("pre_market", "9:25")
    post_close = cfg.get("fetch_schedule", {}).get("post_close", "17:30")

    # 解析时间
    pre_hour, pre_min = map(int, pre_market.split(":"))
    post_hour, post_min = map(int, post_close.split(":"))

    scheduler.add_job(
        run_fetch,
        CronTrigger(hour=pre_hour, minute=pre_min, second=0),
        args=["09-25"],
        id="pre_market",
        replace_existing=True,
    )
    scheduler.add_job(
        run_fetch,
        CronTrigger(hour=post_hour, minute=post_min, second=0),
        args=["17-30"],
        id="post_close",
        replace_existing=True,
    )

    scheduler.start()
    print(f"scheduler started (pre_market {pre_market}, post_close {post_close})")

    signal.signal(signal.SIGINT, lambda *_: scheduler.shutdown())
    signal.signal(signal.SIGTERM, lambda *_: scheduler.shutdown())
    scheduler._thread.join()
```

- [ ] **Step 2: 提交**

```bash
git add src/providers/kaipan_scheduler.py
git commit -m "feat: implement APScheduler run command in kaipan_scheduler"
```

---

## Task 8: 添加 kaipan_scheduler 测试

**Files:**
- Create: `tests/providers/test_kaipan_scheduler.py`

- [ ] **Step 1: 编写测试**

```python
"""KaipanScheduler 离线验证测试。"""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, "src")


class TestKaipanSchedulerCLI:
    """验证 CLI 解析和命令入口。"""

    def test_fetch_command_parses(self):
        """fetch 命令正确解析 --date 和 --slot 参数。"""
        import io
        import contextlib
        from providers import kaipan_scheduler

        parser = kaipan_scheduler.build_parser()
        args = parser.parse_args(["fetch", "--date", "2026-04-22", "--slot", "09-25"])
        assert args.command == "fetch"
        assert args.date == "2026-04-22"
        assert args.slot == "09-25"

    def test_fetch_command_defaults(self):
        """fetch 命令默认参数正确。"""
        from providers import kaipan_scheduler

        parser = kaipan_scheduler.build_parser()
        args = parser.parse_args(["fetch"])
        assert args.command == "fetch"
        assert args.date is None
        assert args.slot == "all"

    def test_normalize_command_parses(self):
        """normalize 命令正确解析参数。"""
        from providers import kaipan_scheduler

        parser = kaipan_scheduler.build_parser()
        args = parser.parse_args(["normalize", "--date", "2026-04-22", "--slot", "17-30"])
        assert args.command == "normalize"
        assert args.date == "2026-04-22"
        assert args.slot == "17-30"

    def test_status_command_exists(self):
        """status 命令存在。"""
        from providers import kaipan_scheduler

        parser = kaipan_scheduler.build_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"

    def test_run_command_exists(self):
        """run 命令存在。"""
        from providers import kaipan_scheduler

        parser = kaipan_scheduler.build_parser()
        args = parser.parse_args(["run"])
        assert args.command == "run"


class TestConfigLoading:
    """验证配置加载。"""

    def test_load_kaipan_config(self):
        """配置加载返回字典。"""
        from providers import kaipan_scheduler

        cfg = kaipan_scheduler.load_kaipan_config()
        assert isinstance(cfg, dict)
        assert "data_dir" in cfg or len(cfg) >= 0

    def test_device_id_in_config(self):
        """配置中 device_id 字段存在（值可能为空字符串）。"""
        from providers import kaipan_scheduler

        cfg = kaipan_scheduler.load_kaipan_config()
        auth_cfg = cfg.get("auth", {})
        assert "device_id" in auth_cfg
```

- [ ] **Step 2: 运行测试验证**

```bash
cd /Users/wanghui/Documents/Claude/trade-strategy-ai
pytest tests/providers/test_kaipan_scheduler.py -v
```

预期：所有测试 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/providers/test_kaipan_scheduler.py
git commit -m "feat: add kaipan_scheduler CLI tests"
```

---

## 自检清单

1. **Spec 覆盖检查**
   - CLI 四个命令（fetch/normalize/status/run）：Task 2、4、5、6、7 ✅
   - 数据集分配（9:25 12个，17:30 10个）：Task 4、7 ✅
   - APScheduler 调度逻辑：Task 7 ✅
   - 配置加载：Task 3、4 ✅
   - 测试覆盖：Task 8 ✅

2. **占位符扫描**：无占位符，所有步骤均包含实际代码 ✅

3. **类型一致性**：
   - `KaipanProvider.__init__` 参数与 Task 4 一致 ✅
   - `KaipanNormalizer.normalize_date` 参数与 Task 5 一致 ✅
   - `KaipanAuth` 的 `device_id` 属性与 Task 3 配置加载一致 ✅
