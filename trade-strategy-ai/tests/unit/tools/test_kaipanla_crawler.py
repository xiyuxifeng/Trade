"""
KaipanlaCrawler 单元测试

测试开盘啦数据爬虫的工具函数和类方法。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))

from kaipanla_crawler import KaipanlaCrawler, is_weekend, get_trading_dates


class TestIsWeekend:
    """测试 is_weekend 函数"""

    def test_saturday_returns_true(self) -> None:
        """周六应返回 True"""
        assert is_weekend("2026-04-11") is True

    def test_sunday_returns_true(self) -> None:
        """周日应返回 True"""
        assert is_weekend("2026-04-12") is True

    def test_monday_returns_false(self) -> None:
        """周一应返回 False"""
        assert is_weekend("2026-04-13") is False

    def test_tuesday_returns_false(self) -> None:
        """周二应返回 False"""
        assert is_weekend("2026-04-14") is False

    def test_wednesday_returns_false(self) -> None:
        """周三应返回 False"""
        assert is_weekend("2026-04-15") is False

    def test_thursday_returns_false(self) -> None:
        """周四应返回 False"""
        assert is_weekend("2026-04-16") is False

    def test_friday_returns_false(self) -> None:
        """周五应返回 False"""
        assert is_weekend("2026-04-17") is False

    def test_invalid_date_returns_false(self) -> None:
        """无效日期格式应返回 False"""
        assert is_weekend("invalid-date") is False
        assert is_weekend("2026-13-45") is False
        assert is_weekend("") is False


class TestGetTradingDates:
    """测试 get_trading_dates 函数"""

    def test_single_weekday_returns_one_date(self) -> None:
        """单个工作日应返回该日期"""
        # 2026-04-13 是周一
        result = get_trading_dates("2026-04-13", "2026-04-13")
        assert result == ["2026-04-13"]

    def test_single_weekend_returns_empty(self) -> None:
        """单个周末日期应返回空列表"""
        # 2026-04-11 是周六
        result = get_trading_dates("2026-04-11", "2026-04-11")
        assert result == []

    def test_weekdays_only(self) -> None:
        """工作日应被包含"""
        # 2026-04-13 (周一) 到 2026-04-17 (周五)
        result = get_trading_dates("2026-04-13", "2026-04-17")
        assert result == [
            "2026-04-13", "2026-04-14", "2026-04-15", "2026-04-16", "2026-04-17"
        ]

    def test_includes_weekend_skips_weekend(self) -> None:
        """包含周末时应跳过周末"""
        # 2026-04-11 (周六) 到 2026-04-14 (周二)
        result = get_trading_dates("2026-04-11", "2026-04-14")
        assert result == ["2026-04-13", "2026-04-14"]

    def test_start_after_end_swaps(self) -> None:
        """开始日期晚于结束日期时应交换"""
        result = get_trading_dates("2026-04-17", "2026-04-13")
        assert result == [
            "2026-04-13", "2026-04-14", "2026-04-15", "2026-04-16", "2026-04-17"
        ]

    def test_full_week_includes_5_days(self) -> None:
        """完整一周应返回5个工作日"""
        # 2026-04-13 (周一) 到 2026-04-19 (周日) 包含周六周日
        result = get_trading_dates("2026-04-13", "2026-04-19")
        assert result == [
            "2026-04-13", "2026-04-14", "2026-04-15", "2026-04-16", "2026-04-17"
        ]

    def test_two_weeks(self) -> None:
        """两周应返回10个工作日"""
        result = get_trading_dates("2026-04-13", "2026-04-24")
        assert len(result) == 10
        assert result[0] == "2026-04-13"
        assert result[-1] == "2026-04-24"


class TestKaipanlaCrawlerInit:
    """测试 KaipanlaCrawler 类初始化"""

    def test_init_sets_base_urls(self) -> None:
        """初始化应设置正确的 base_url"""
        crawler = KaipanlaCrawler()
        assert crawler.base_url == "https://apphis.longhuvip.com/w1/api/index.php"
        assert crawler.sector_base_url == "https://apphwhq.longhuvip.com/w1/api/index.php"

    def test_init_sets_headers(self) -> None:
        """初始化应设置正确的 headers"""
        crawler = KaipanlaCrawler()
        assert "User-Agent" in crawler.headers
        assert "Dalvik/2.1.0" in crawler.headers["User-Agent"]
        assert crawler.headers["Host"] == "apphis.longhuvip.com"

    def test_init_sets_sector_headers(self) -> None:
        """初始化应设置正确的 sector_headers"""
        crawler = KaipanlaCrawler()
        assert "User-Agent" in crawler.sector_headers
        assert crawler.sector_headers["Host"] == "apphwhq.longhuvip.com"


class TestKaipanlaCrawlerRequest:
    """测试 KaipanlaCrawler _request 方法"""

    def test_request_returns_empty_on_exception(self) -> None:
        """请求异常时应返回空字典"""
        crawler = KaipanlaCrawler()

        with patch("kaipanla_crawler.requests.post") as mock_post:
            mock_post.side_effect = Exception("Network error")
            result = crawler._request({"a": "Test"}, "2026-04-13")
            assert result == {}

    def test_request_returns_json_on_success(self) -> None:
        """请求成功时应返回 JSON"""
        crawler = KaipanlaCrawler()
        expected = {"code": 0, "data": "test"}

        with patch("kaipanla_crawler.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = expected
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = crawler._request({"a": "Test"}, "2026-04-13")
            assert result == expected

    def test_request_includes_date_in_params(self) -> None:
        """请求应包含日期参数"""
        crawler = KaipanlaCrawler()

        with patch("kaipanla_crawler.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            crawler._request({"a": "Test"}, "2026-04-13")
            call_args = mock_post.call_args
            # 检查 data 中包含 Day 参数
            assert "Day" in call_args.kwargs["data"]
            assert call_args.kwargs["data"]["Day"] == "2026-04-13"


class TestGetMarketSentiment:
    """测试 get_market_sentiment 方法"""

    def test_returns_empty_df_when_no_result(self) -> None:
        """无数据时返回空 DataFrame"""
        crawler = KaipanlaCrawler()
        crawler._request = MagicMock(return_value={})

        result = crawler.get_market_sentiment("2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_df_with_correct_columns(self) -> None:
        """返回包含正确列的 DataFrame"""
        crawler = KaipanlaCrawler()
        crawler._request = MagicMock(return_value={
            "date": "2026-04-13",
            "info": {
                "ZT": "100",
                "SJZT": "90",
                "DT": "20",
                "SJDT": "15",
                "SZJS": "1500",
                "XDJS": "3000",
                "0": "500"
            }
        })

        result = crawler.get_market_sentiment("2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert "涨停数" in result.columns
        assert "跌停数" in result.columns
        assert "上涨家数" in result.columns
        assert "下跌家数" in result.columns
        assert result["涨停数"].iloc[0] == 100
        assert result["实际涨停"].iloc[0] == 90


class TestGetMarketIndex:
    """测试 get_market_index 方法"""

    def test_returns_empty_df_when_no_result(self) -> None:
        """无数据时返回空 DataFrame"""
        crawler = KaipanlaCrawler()
        crawler._request = MagicMock(return_value={})

        result = crawler.get_market_index("2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_df_with_correct_columns(self) -> None:
        """返回包含正确列的 DataFrame"""
        crawler = KaipanlaCrawler()
        crawler._request = MagicMock(return_value={
            "StockList": [
                {
                    "StockID": "000001",
                    "prod_name": "上证指数",
                    "last_px": 3200.5,
                    "increase_amount": 20.3,
                    "increase_rate": "0.64%",
                    "turnover": 3000000000
                }
            ]
        })

        result = crawler.get_market_index("2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert "指数代码" in result.columns
        assert "指数名称" in result.columns
        assert "最新价" in result.columns
        assert result["最新价"].iloc[0] == 3200.5


class TestGetLimitUpLadder:
    """测试 get_limit_up_ladder 方法"""

    def test_returns_empty_df_when_no_result(self) -> None:
        """无数据时返回空 DataFrame"""
        crawler = KaipanlaCrawler()
        crawler._request = MagicMock(return_value={})

        result = crawler.get_limit_up_ladder("2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_empty_df_when_info_too_short(self) -> None:
        """info 长度不足12时返回空 DataFrame"""
        crawler = KaipanlaCrawler()
        crawler._request = MagicMock(return_value={
            "info": [1, 2, 3]  # 不足12个元素
        })

        result = crawler.get_limit_up_ladder("2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_df_with_correct_data(self) -> None:
        """返回包含正确数据的 DataFrame"""
        crawler = KaipanlaCrawler()
        crawler._request = MagicMock(return_value={
            "info": [50, 20, 10, 5, 65.5, 30, 10, 15.2, 3.5, -2.1, -5.3, "市场强势"]
        })

        result = crawler.get_limit_up_ladder("2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert "一板" in result.columns
        assert result["一板"].iloc[0] == 50
        assert result["二板"].iloc[0] == 20
        assert result["三板"].iloc[0] == 10
        assert result["连板率(%)"].iloc[0] == 65.5  # round(65.5, 2) = 65.5


class TestGetSharpWithdrawal:
    """测试 get_sharp_withdrawal 方法"""

    def test_returns_empty_df_when_no_result(self) -> None:
        """无数据时返回空 DataFrame"""
        crawler = KaipanlaCrawler()
        crawler._request = MagicMock(return_value={})

        result = crawler.get_sharp_withdrawal("2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_returns_df_with_correct_columns(self) -> None:
        """返回包含正确列的 DataFrame"""
        crawler = KaipanlaCrawler()
        crawler._request = MagicMock(return_value={
            "date": "2026-04-13",
            "num": 100,
            "info": [
                ["000001", "平安银行", -8.5, 15.2, 10.5],
                ["000002", "万科A", -6.3, 12.1, 8.9]
            ]
        })

        result = crawler.get_sharp_withdrawal("2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert "股票代码" in result.columns
        assert "股票名称" in result.columns
        assert "当日涨跌幅(%)" in result.columns
        assert "回撤幅度(%)" in result.columns
        assert len(result) == 2
        assert result["股票代码"].iloc[0] == "000001"
        assert result["回撤幅度(%)"].iloc[0] == 15.2


class TestGetDailyData:
    """测试 get_daily_data 方法"""

    def test_returns_series_for_single_date(self) -> None:
        """单日数据返回 Series"""
        crawler = KaipanlaCrawler()
        crawler._get_single_day_data = MagicMock(return_value={
            "涨停数": 100,
            "跌停数": 20,
            "上涨家数": 1500
        })

        result = crawler.get_daily_data("2026-04-13")
        assert isinstance(result, pd.Series)
        assert result["涨停数"] == 100

    def test_returns_df_for_date_range(self) -> None:
        """日期范围返回 DataFrame"""
        crawler = KaipanlaCrawler()
        # 2026-04-13 和 2026-04-14 都是工作日
        crawler._get_single_day_data = MagicMock(side_effect=[
            {"涨停数": 100, "跌停数": 20},
            {"涨停数": 80, "跌停数": 15}
        ])

        result = crawler.get_daily_data("2026-04-14", "2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_filters_out_empty_data(self) -> None:
        """过滤掉没有数据的日期"""
        crawler = KaipanlaCrawler()
        # 2026-04-13 和 2026-04-14 都是工作日
        crawler._get_single_day_data = MagicMock(side_effect=[
            {"涨停数": 100, "跌停数": 20},  # 有效
            {"涨停数": 0, "跌停数": 0}       # 无效（节假日）
        ])

        result = crawler.get_daily_data("2026-04-14", "2026-04-13")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # 只保留有效数据


class TestGetNewHighData:
    """测试 get_new_high_data 方法"""

    def test_returns_series_for_single_date(self) -> None:
        """单日数据返回标量值"""
        crawler = KaipanlaCrawler()

        with patch("kaipanla_crawler.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "errcode": "0",
                "x": ["20260413_478_127_0"]
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = crawler.get_new_high_data("2026-04-13")
            # 单日查询时返回标量值（pd.Series 的单个元素）
            assert result == 127

    def test_returns_empty_series_on_error(self) -> None:
        """错误时返回空 Series"""
        crawler = KaipanlaCrawler()

        with patch("kaipanla_crawler.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"errcode": "1", "message": "error"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = crawler.get_new_high_data("2026-04-13")
            assert isinstance(result, pd.Series)
            assert result.empty
