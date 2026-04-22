"""Kaipan 调度器 CLI。

提供 fetch / normalize / status / run 四个命令。
"""

from __future__ import annotations

import argparse
import sys
import yaml
from datetime import date
from pathlib import Path

# 动态导入：直接从 trade-strategy-ai/src/providers/ 导入子模块（避免 providers 包名冲突）
import importlib.util
import sys as _sys

_tai_src = Path(__file__).parent.parent.parent / "trade-strategy-ai" / "src"
if str(_tai_src) not in _sys.path:
    _sys.path.insert(0, str(_tai_src))

# 动态加载 kaipan_provider（注册到 sys.modules 避免 dataclass 装饰器失败）
_provider_spec = importlib.util.spec_from_file_location(
    "providers.kaipan_provider", _tai_src / "providers" / "kaipan_provider.py"
)
_provider_module = importlib.util.module_from_spec(_provider_spec)
_sys.modules["providers.kaipan_provider"] = _provider_module
_provider_spec.loader.exec_module(_provider_module)  # type: ignore
KaipanAuth = _provider_module.KaipanAuth
KaipanProvider = _provider_module.KaipanProvider

# 动态加载 kaipan_normalizer
_normalizer_spec = importlib.util.spec_from_file_location(
    "providers.kaipan_normalizer", _tai_src / "providers" / "kaipan_normalizer.py"
)
_normalizer_module = importlib.util.module_from_spec(_normalizer_spec)
_sys.modules["providers.kaipan_normalizer"] = _normalizer_module
_normalizer_spec.loader.exec_module(_normalizer_module)  # type: ignore
KaipanNormalizer = _normalizer_module.KaipanNormalizer

del _tai_src, _provider_spec, _provider_module, _normalizer_spec, _normalizer_module, _sys
from providers.kaipan_provider import KaipanAuth, KaipanProvider
from providers.kaipan_normalizer import KaipanNormalizer


def load_kaipan_config() -> dict:
    """从 config/app.yaml 加载 kaipan 配置。"""
    config_path = Path("trade-strategy-ai/config/app.yaml")
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
        slot = args.slot

        # 解析时间槽对应的接口集合
        if slot == "all":
            slots_to_fetch = ["09-25", "17-30"]
        else:
            slots_to_fetch = [slot]

        # 实例化 provider（使用 worktree 路径结构）
        auth_dict = get_auth()
        auth = KaipanAuth(device_id=auth_dict.get("device_id", ""))
        provider = KaipanProvider(
            auth=auth,
            raw_dir="trade-strategy-ai/data/kaipan/raw",
            normalized_dir="trade-strategy-ai/data/kaipan/normalized",
            snapshots_dir="trade-strategy-ai/data/kaipan/snapshots",
        )

        # 9:25 有 12 个接口（含竞价数据，无龙虎榜）
        fetchors_0925 = [
            provider.fetch_board_strength,
            provider.fetch_industry_ranking,
            provider.fetch_concept_fengkou,
            provider.fetch_theme_detail,
            provider.fetch_stock_sector_v2,
            provider.fetch_strong_fengkou,
            provider.fetch_interval_stats_stock,
            provider.fetch_morning_bidding_list,
            provider.fetch_limit_up_reason,
            provider.fetch_pre_market_bid,
            provider.fetch_pre_market_stats,
            provider.fetch_limit_up_info,
        ]
        # 17:30 有 10 个接口（含龙虎榜，无竞价数据）
        fetchors_1730 = [
            provider.fetch_board_strength,
            provider.fetch_industry_ranking,
            provider.fetch_concept_fengkou,
            provider.fetch_theme_detail,
            provider.fetch_stock_sector_v2,
            provider.fetch_strong_fengkou,
            provider.fetch_interval_stats_stock,
            provider.fetch_limit_up_reason,
            provider.fetch_limit_up_info,
            provider.fetch_lhb_list,
        ]

        for s in slots_to_fetch:
            if s == "09-25":
                fetchors = fetchors_0925
            elif s == "17-30":
                fetchors = fetchors_1730
            else:
                print(f"[WARN] 未知时间槽 {s}，跳过")
                continue

            print(f"[fetch] 开始抓取 {trade_date} {s}，共 {len(fetchors)} 个接口")
            for i, fetcher in enumerate(fetchors, 1):
                try:
                    fetcher(trade_date=trade_date, slot=s)
                    print(f"[fetch] [{i}/{len(fetchors)}] {fetcher.__name__} 成功")
                except Exception as e:
                    print(f"[WARN] [{i}/{len(fetchors)}] {fetcher.__name__} 失败: {e}，继续其余接口")

        # 抓取完成后调用 normalize_date 转换
        normalizer = KaipanNormalizer(
            schema_dir="trade-strategy-ai/src/providers/kaipan_schema",
            snapshots_dir="trade-strategy-ai/data/kaipan/snapshots",
        )
        slots_tuple = tuple(slots_to_fetch)
        norm_results = normalizer.normalize_date(trade_date.isoformat(), slots_tuple)
        print(f"[fetch] normalize 完成，结果: {norm_results}")
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
    elif args.command == "run":
        print("scheduler started")


if __name__ == "__main__":
    main()
