"""Kaipan 数据管线离线验证测试。"""

from datetime import date
from pathlib import Path

import pytest
import yaml


class TestKaipanSchemaFiles:
    """验证 schema 文件存在性和合法性。"""

    def test_schema_dir_exists(self):
        """schema 目录存在。"""
        schema_dir = Path("src/providers/kaipan_schema")
        assert schema_dir.exists(), f"{schema_dir} 不存在"

    def test_all_schema_files_exist(self):
        """4 个 schema 文件都存在。"""
        schema_dir = Path("src/providers/kaipan_schema")
        for name in ("hot_topics", "topic_constituents", "strong_symbols", "market_context"):
            path = schema_dir / f"{name}.yaml"
            assert path.exists(), f"{name}.yaml 不存在"

    def test_schema_files_valid_yaml(self):
        """所有 schema 文件是合法 YAML。"""
        schema_dir = Path("src/providers/kaipan_schema")
        for yaml_file in schema_dir.glob("*.yaml"):
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert isinstance(data, dict), f"{yaml_file.name} 不是有效字典"
            assert "dataset" in data, f"{yaml_file.name} 缺少 dataset 字段"
            assert "mappings" in data, f"{yaml_file.name} 缺少 mappings 字段"

    def test_schema_has_required_datasets(self):
        """schema dataset 名称正确。"""
        schema_dir = Path("src/providers/kaipan_schema")
        datasets = {f.stem for f in schema_dir.glob("*.yaml")}
        assert datasets == {
            "hot_topics",
            "topic_constituents",
            "strong_symbols",
            "market_context",
        }


class TestKaipanProvider:
    """验证 KaipanProvider 的配置。"""

    def setup_method(self):
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_provider import KaipanProvider, KaipanAuth
        self.auth = KaipanAuth()
        self.provider = KaipanProvider(
            auth=self.auth,
            raw_dir=Path("data/kaipan/raw"),
            normalized_dir=Path("data/kaipan/snapshots"),
            snapshots_dir=Path("data/kaipan/snapshots"),
        )

    def test_base_urls_defined(self):
        """验证三个 baseURL 已配置。"""
        assert hasattr(self.provider, "base_urls"), "缺少 base_urls 属性"
        assert "apphis" in self.provider.base_urls
        assert "apphwhq" in self.provider.base_urls
        assert "apphwshhq" in self.provider.base_urls
        assert "applhb" in self.provider.base_urls
        assert "longhuvip.com" in self.provider.base_urls["apphis"]
        assert "longhuvip.com" in self.provider.base_urls["apphwhq"]
        assert "longhuvip.com" in self.provider.base_urls["apphwshhq"]
        assert "longhuvip.com" in self.provider.base_urls["applhb"]

    def test_default_headers_defined(self):
        """验证模拟客户端请求头已配置。"""
        assert hasattr(self.provider, "default_headers"), "缺少 default_headers"
        headers = self.provider.default_headers
        assert headers["Content-Type"] == "application/x-www-form-urlencoded; charset=UTF-8"
        assert "Dalvik/2.1.0" in headers["User-Agent"]
        assert headers["Connection"] == "Keep-Alive"
        assert headers["Accept-Encoding"] == "gzip"
        for key, value in headers.items():
            assert self.provider.session.headers.get(key) == value

    def test_provider_uses_kaipan_config_values(self):
        """验证 provider 可以从 kaipan 配置中读取反爬参数。"""
        import sys
        sys.path.insert(0, "src")
        from common.config import KaipanConfig
        from providers.kaipan_provider import KaipanProvider, KaipanAuth

        kaipan_config = KaipanConfig(
            min_request_interval_seconds=1.5,
            max_retries=5,
            retry_backoff_seconds=[2.0, 4.0, 8.0],
            retry_status_codes=[403, 429],
        )
        provider = KaipanProvider(
            auth=KaipanAuth(),
            raw_dir=Path("data/kaipan/raw"),
            normalized_dir=Path("data/kaipan/snapshots"),
            snapshots_dir=Path("data/kaipan/snapshots"),
            kaipan_config=kaipan_config,
        )

        assert provider.min_request_interval_seconds == 1.5
        assert provider.max_retries == 5
        assert provider.retry_backoff_seconds == (2.0, 4.0, 8.0)
        assert provider.retry_status_codes == {403, 429}

    def test_provider_uses_kaipan_config_token_and_user_id(self):
        """验证 provider 优先使用配置中的 Token/UserID。"""
        import sys
        sys.path.insert(0, "src")
        from common.config import KaipanConfig
        from providers.kaipan_provider import KaipanProvider, KaipanAuth

        provider = KaipanProvider(
            auth=KaipanAuth(token="auth-token", user_id="auth-user"),
            raw_dir=Path("data/kaipan/raw"),
            normalized_dir=Path("data/kaipan/snapshots"),
            snapshots_dir=Path("data/kaipan/snapshots"),
            kaipan_config=KaipanConfig(token="config-token", user_id="config-user"),
        )

        params = provider.build_common_params()
        assert params["Token"] == "config-token"
        assert params["UserID"] == "config-user"

    def test_fetch_single_retries_on_retryable_status(self, monkeypatch):
        """验证遇到可重试状态码时会重试。"""
        calls = []

        class FakeResponse:
            def __init__(self, status_code, payload):
                self.status_code = status_code
                self._payload = payload

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError(f"status={self.status_code}")

            def json(self):
                return self._payload

        def fake_request(*, method, url, params=None, data=None, timeout=None, headers=None):
            calls.append(
                {
                    "method": method,
                    "url": url,
                    "params": params,
                    "data": data,
                    "timeout": timeout,
                    "headers": headers,
                }
            )
            if len(calls) == 1:
                return FakeResponse(429, {"error": "rate limited"})
            return FakeResponse(200, {"ok": True})

        monkeypatch.setattr(self.provider.session, "request", fake_request)
        monkeypatch.setattr(self.provider, "_throttle", lambda: None)
        monkeypatch.setattr(self.provider, "_sleep_with_backoff", lambda attempt: None)
        self.provider.max_retries = 2

        request = self.provider.build_request(api_name="MorningBidding", controller="HisHomeDingPan", method="POST")
        result = self.provider._fetch_single(request)

        assert result == {"ok": True}
        assert len(calls) == 2
        assert calls[0]["method"] == "POST"
        assert calls[0]["data"] == request.params
        assert calls[0]["params"] is None
        assert calls[0]["headers"]["User-Agent"].startswith("Dalvik/2.1.0")
        assert calls[1]["headers"]["Accept-Encoding"] == "gzip"

    def test_auth_defaults_generate_device_id_and_phone_os(self):
        """验证 KaipanAuth 默认生成 device_id，并将 PhoneOSNew 设为 1。"""
        from providers.kaipan_provider import KaipanAuth

        auth = KaipanAuth()
        assert isinstance(auth.device_id, str)
        assert auth.device_id
        assert auth.phone_os_new == "1"

    def test_modified_methods_pass_expected_params(self, monkeypatch):
        """验证按新版文档更新后的接口参数。"""
        captured = []

        def fake_fetch_and_save(**kwargs):
            captured.append(kwargs)
            return {"ok": True}

        monkeypatch.setattr(self.provider, "_fetch_and_save", fake_fetch_and_save)
        import providers.kaipan_provider as kaipan_module

        class FakeDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 4, 16)

        monkeypatch.setattr(kaipan_module, "date", FakeDate)

        self.provider.fetch_board_strength(trade_date=date(2026, 4, 16), slot="09-25")
        self.provider.fetch_board_strength(trade_date=date(2026, 4, 15), slot="09-25")
        self.provider.fetch_stock_sector_v2(trade_date=date(2026, 4, 16), slot="09-25", stock_id="002726")
        self.provider.fetch_theme_detail(trade_date=date(2026, 4, 16), slot="09-25", theme_id="261")

        assert captured[0]["base_url_key"] == "apphwhq"
        assert captured[0]["Date"] == "2026-04-16"
        assert captured[0]["ZSType"] == "7"
        assert captured[1]["base_url_key"] == "apphis"
        assert captured[1]["Date"] == "2026-04-15"
        assert captured[2]["method"] == "GET"
        assert captured[2]["StockID"] == "002726"
        assert captured[2]["base_url_key"] == "apphwshhq"
        assert captured[3]["ID"] == "261"
        assert captured[3]["base_url_key"] == "applhb"

    def test_all_implemented_methods_use_expected_urls(self, monkeypatch):
        """验证已实现接口的 URL 选择与文档一致。"""
        captured = []

        def fake_fetch_and_save(**kwargs):
            captured.append(kwargs)
            return {"ok": True}

        monkeypatch.setattr(self.provider, "_fetch_and_save", fake_fetch_and_save)
        import providers.kaipan_provider as kaipan_module

        class FakeDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 4, 16)

        monkeypatch.setattr(kaipan_module, "date", FakeDate)

        self.provider.fetch_board_strength(trade_date=date(2026, 4, 16), slot="09-25")
        self.provider.fetch_board_strength(trade_date=date(2026, 4, 15), slot="09-25")
        self.provider.fetch_industry_ranking(trade_date=date(2026, 4, 16), slot="09-25")
        self.provider.fetch_concept_fengkou(trade_date=date(2026, 4, 16), slot="09-25")
        self.provider.fetch_theme_detail(trade_date=date(2026, 4, 16), slot="09-25", theme_id="261")
        self.provider.fetch_stock_sector_v2(trade_date=date(2026, 4, 16), slot="09-25", stock_id="002726")
        self.provider.fetch_strong_fengkou(trade_date=date(2026, 4, 16), slot="09-25")
        self.provider.fetch_interval_stats_stock(
            trade_date=date(2026, 4, 16),
            slot="09-25",
            start_date=date(2026, 4, 8),
            end_date=date(2026, 4, 16),
        )
        self.provider.fetch_morning_bidding_list(trade_date=date(2026, 4, 16), slot="09-25", pid_type=0, data_type=4)
        self.provider.fetch_limit_up_reason(trade_date=date(2026, 4, 16), slot="09-25")
        self.provider.fetch_pre_market_bid(trade_date=date(2026, 4, 16), slot="09-25")
        self.provider.fetch_pre_market_stats(trade_date=date(2026, 4, 16), slot="09-25")
        self.provider.fetch_limit_up_info(trade_date=date(2026, 4, 16), slot="09-25")
        self.provider.fetch_lhb_list(trade_date=date(2026, 4, 16), slot="17-30")

        assert captured[0]["base_url_key"] == "apphwhq"
        assert captured[1]["base_url_key"] == "apphis"
        assert captured[2]["base_url_key"] == "apphwhq"
        assert captured[3]["base_url_key"] == "apphis"
        assert captured[4]["base_url_key"] == "applhb"
        assert captured[5]["base_url_key"] == "apphwshhq"
        assert captured[6]["base_url_key"] == "apphwhq"
        assert captured[7]["base_url_key"] == "apphwhq"
        assert captured[8]["base_url_key"] == "apphis"
        assert captured[9]["base_url_key"] == "apphis"
        assert captured[10]["base_url_key"] == "apphis"
        assert captured[11]["base_url_key"] == "apphis"
        assert captured[12]["base_url_key"] == "apphwhq"
        assert captured[13]["base_url_key"] == "applhb"

    def test_fetch_and_save_method_exists(self):
        """验证 _fetch_and_save 方法存在且可调用。"""
        import inspect
        assert hasattr(self.provider, "_fetch_and_save"), "缺少 _fetch_and_save 方法"
        sig = inspect.signature(self.provider._fetch_and_save)
        params = list(sig.parameters.keys())
        required = ["dataset", "api_name", "controller"]
        for p in required:
            assert p in params, f"_fetch_and_save 缺少必需参数 {p}，当前参数: {params}"

    def test_save_raw_method_has_dataset_param(self):
        """验证 _save_raw 方法接受 dataset 参数。"""
        import inspect
        sig = inspect.signature(self.provider._save_raw)
        params = list(sig.parameters.keys())
        assert "dataset" in params, f"_save_raw 缺少 dataset 参数，当前参数: {params}"


class TestKaipanNormalizer:
    """验证 KaipanNormalizer 的 schema 加载和字段转换。"""

    def test_normalizer_has_required_methods(self):
        """验证 normalizer 有所有必需方法。"""
        import sys
        import inspect
        sys.path.insert(0, "src")
        from providers.kaipan_normalizer import KaipanNormalizer

        normalizer = KaipanNormalizer(
            schema_dir="src/providers/kaipan_schema",
            snapshots_dir="data/kaipan/snapshots",
        )
        methods_with_params = {
            "normalize": ["dataset", "raw_path", "slot"],
            "normalize_date": ["trade_date"],
        }
        for method_name, required_params in methods_with_params.items():
            assert hasattr(normalizer, method_name), f"缺少方法: {method_name}"
            sig = inspect.signature(getattr(normalizer, method_name))
            params = list(sig.parameters.keys())
            for p in required_params:
                assert p in params, f"{method_name} 缺少必需参数 {p}，当前参数: {params}"

    def test_normalizer_loads_schema(self):
        """验证 normalizer 可以加载 schema。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_normalizer import KaipanNormalizer

        normalizer = KaipanNormalizer(
            schema_dir="src/providers/kaipan_schema",
            snapshots_dir="data/kaipan/snapshots",
        )
        schema = normalizer._load_schema("hot_topics")
        assert schema["dataset"] == "hot_topics"
        assert "mappings" in schema

    def test_canonicalize_real_ranking_adds_minday_for_today_url(self, tmp_path):
        """验证今日 URL 的 RealRankingInfo 会补齐 MinDay。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_normalizer import KaipanNormalizer

        normalizer = KaipanNormalizer(
            schema_dir="src/providers/kaipan_schema",
            snapshots_dir=tmp_path / "snapshots",
        )
        raw = {"Count": 1, "list": [[1, 2, 3]]}
        meta = {"request": {"endpoint": "https://apphwhq.longhuvip.com/w1/api/index.php", "action": "RealRankingInfo"}}

        normalized = normalizer._canonicalize_raw_data(raw, meta)

        assert normalized["MinDay"] is None
        assert normalized["Count"] == 1
        assert normalized["list"] == [[1, 2, 3]]

    def test_canonicalize_fengkou_tip_alias(self, tmp_path):
        """验证 Tip/Tips 别名会被统一补齐。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_normalizer import KaipanNormalizer

        normalizer = KaipanNormalizer(
            schema_dir="src/providers/kaipan_schema",
            snapshots_dir=tmp_path / "snapshots",
        )
        raw_today = {"List": [["000001", "测试", 1]], "Tip": "today-tip"}
        raw_history = {"List": [["000001", "测试", 1]], "Tips": "history-tips"}
        meta = {"request": {"endpoint": "https://apphwhq.longhuvip.com/w1/api/index.php", "action": "GetFengKListBest"}}

        normalized_today = normalizer._canonicalize_raw_data(raw_today, meta)
        normalized_history = normalizer._canonicalize_raw_data(raw_history, meta)

        assert normalized_today["Tips"] == "today-tip"
        assert normalized_today["Tip"] == "today-tip"
        assert normalized_history["Tips"] == "history-tips"
        assert normalized_history["Tip"] == "history-tips"

    def test_canonicalize_interval_stats_stock_infers_count(self, tmp_path):
        """验证区间统计接口会在缺失 Count 时按 List 长度补齐。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_normalizer import KaipanNormalizer

        normalizer = KaipanNormalizer(
            schema_dir="src/providers/kaipan_schema",
            snapshots_dir=tmp_path / "snapshots",
        )
        raw = {"List": [[1], [2], [3]]}
        meta = {"request": {"endpoint": "https://apphis.longhuvip.com/w1/api/index.php", "action": "GetInterviewsByDateStock"}}

        normalized = normalizer._canonicalize_raw_data(raw, meta)

        assert normalized["Count"] == 3
        assert normalized["List"] == [[1], [2], [3]]

    def test_canonicalize_limit_up_info_uses_date_alias(self, tmp_path):
        """验证涨停信息会统一 Date/date 字段。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_normalizer import KaipanNormalizer

        normalizer = KaipanNormalizer(
            schema_dir="src/providers/kaipan_schema",
            snapshots_dir=tmp_path / "snapshots",
        )
        raw = {"StockList": [], "date": "2026-04-22"}
        meta = {"request": {"endpoint": "https://apphwhq.longhuvip.com/w1/api/index.php", "action": "GetZhangTingTianTi"}}

        normalized = normalizer._canonicalize_raw_data(raw, meta)

        assert normalized["Date"] == "2026-04-22"
        assert normalized["date"] == "2026-04-22"


class TestDirectoryStructure:
    """验证目录结构符合规范。"""

    def test_data_dirs_exist(self):
        """data/kaipan/raw 和 data/kaipan/snapshots 目录存在。"""
        assert Path("data/kaipan/raw").exists(), "data/kaipan/raw 不存在"
        assert Path("data/kaipan/snapshots").exists(), "data/kaipan/snapshots 不存在"


class TestConfig:
    """验证 config/app.yaml 中的 kaipan 配置。"""

    def test_kaipan_config_exists(self):
        """验证 app.yaml 包含 kaipan 配置节。"""
        with open("config/app.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert "kaipan" in config, "app.yaml 缺少 kaipan 配置节"
        kaipan = config["kaipan"]
        assert "data_dir" in kaipan, "kaipan 配置缺少 data_dir"
        assert "schema_dir" in kaipan, "kaipan 配置缺少 schema_dir"
        assert "fetch_schedule" in kaipan, "kaipan 配置缺少 fetch_schedule"
        assert "pre_market" in kaipan["fetch_schedule"], "fetch_schedule 缺少 pre_market"
        assert "post_close" in kaipan["fetch_schedule"], "fetch_schedule 缺少 post_close"
        assert kaipan["fetch_schedule"]["pre_market"] == "9:25"
        assert kaipan["fetch_schedule"]["post_close"] == "17:30"
