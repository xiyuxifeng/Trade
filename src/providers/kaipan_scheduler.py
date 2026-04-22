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
