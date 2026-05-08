"""Kaipan 调度器 CLI。

提供 fetch / normalize / status / run 四个命令。
"""

from __future__ import annotations

import argparse
import sys
import yaml
import logging
from datetime import date
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 确保项目根目录在 sys.path 中
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.providers.kaipan_provider import KaipanAuth, KaipanProvider
from src.providers.kaipan_normalizer import KaipanNormalizer


def load_kaipan_config() -> dict:
    """从 config/app.yaml 加载 kaipan 配置。"""
    config_path = _root / "config" / "app.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("kaipan", {})


def get_auth() -> dict[str, str]:
    """返回 Kaipan 认证信息字典，兼容旧测试与脚本。"""
    cfg = load_kaipan_config()
    return {
        "device_id": str(cfg.get("device_id", "")),
        "token": str(cfg.get("token", "")),
        "user_id": str(cfg.get("user_id", "")),
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
    from src.services.kaipan_service import KaipanService

    result = KaipanService().fetch(config_path=_root / "config" / "app.yaml", trade_date=date.today(), slot=slot)
    summary = result.payload.get("slot_results", {}).get(slot, {})
    logging.info(
        "scheduled fetch + normalize completed for %s %s: success=%s failed=%s",
        result.payload.get("trade_date"),
        slot,
        len(summary.get("success", [])),
        len(summary.get("failed", [])),
    )


def main():
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:])

    if args.command == "fetch":
        from src.services.kaipan_service import KaipanService

        trade_date = date.today() if args.date is None else date.fromisoformat(args.date)
        result = KaipanService().fetch(config_path=_root / "config" / "app.yaml", trade_date=trade_date, slot=args.slot)
        slots = result.payload.get("slots", [])
        for s in slots:
            slot_result = result.payload.get("slot_results", {}).get(s, {})
            print(
                f"[fetch] {trade_date} {s}: {len(slot_result.get('success', []))} success, "
                f"{len(slot_result.get('failed', []))} failed"
            )
        print(f"[fetch] normalize 完成，结果: {result.payload.get('normalize_results', {})}")
    elif args.command == "normalize":
        from src.services.kaipan_service import KaipanService

        trade_date = date.today() if args.date is None else date.fromisoformat(args.date)
        result = KaipanService().normalize(config_path=_root / "config" / "app.yaml", trade_date=trade_date, slot=args.slot)
        for slot, datasets in result.payload.get("results", {}).items():
            ok = sum(1 for v in datasets.values() if v is not None and "_error" not in v)
            err = sum(1 for v in datasets.values() if v is None or "_error" in v)
            print(f"normalize {trade_date} {slot}: {ok} ok, {err} failed")
    elif args.command == "status":
        from src.services.kaipan_service import KaipanService

        result = KaipanService().status(config_path=_root / "config" / "app.yaml")
        if result.payload.get("latest_slot"):
            print(f"status: latest slot {result.payload['latest_slot']}")
        else:
            print("status: no data yet")
    elif args.command == "run":
        from src.services.kaipan_service import KaipanService

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

        if not is_trading_day(date.today()):
            print("today is not a trading day, skipping")
            return

        result = KaipanService().run(config_path=_root / "config" / "app.yaml", start_scheduler=True, block=True)
        print(f"scheduler started (pre_market {result.payload['pre_market']}, post_close {result.payload['post_close']})")


if __name__ == "__main__":
    main()
