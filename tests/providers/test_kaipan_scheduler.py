"""KaipanScheduler 离线验证测试。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, "src")


class TestKaipanSchedulerCLI:
    """验证 CLI 解析和命令入口。"""

    def test_fetch_command_parses(self):
        """fetch 命令正确解析 --date 和 --slot 参数。"""
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

    def test_device_id_in_auth_dict(self):
        """get_auth() 返回的字典中 device_id 键存在（有可能为空字符串）。"""
        from providers import kaipan_scheduler

        auth = kaipan_scheduler.get_auth()
        assert "device_id" in auth