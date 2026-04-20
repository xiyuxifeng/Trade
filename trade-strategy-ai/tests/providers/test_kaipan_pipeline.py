"""Kaipan 数据管线离线验证测试。"""

import json
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

    def test_base_urls_defined(self):
        """验证三个 baseURL 已配置。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_provider import KaipanProvider, KaipanAuth

        auth = KaipanAuth(device_id="test")
        provider = KaipanProvider(
            auth=auth,
            raw_dir=Path("data/kaipan/raw"),
            normalized_dir=Path("data/kaipan/snapshots"),
            snapshots_dir=Path("data/kaipan/snapshots"),
        )
        assert hasattr(provider, "base_urls"), "缺少 base_urls 属性"
        assert "apphis" in provider.base_urls
        assert "apphwshhq" in provider.base_urls
        assert "applhb" in provider.base_urls
        assert "longhuvip.com" in provider.base_urls["apphis"]
        assert "longhuvip.com" in provider.base_urls["apphwshhq"]
        assert "longhuvip.com" in provider.base_urls["applhb"]

    def test_fetch_and_save_method_exists(self):
        """验证 _fetch_and_save 方法存在。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_provider import KaipanProvider, KaipanAuth

        auth = KaipanAuth(device_id="test")
        provider = KaipanProvider(
            auth=auth,
            raw_dir=Path("data/kaipan/raw"),
            normalized_dir=Path("data/kaipan/snapshots"),
            snapshots_dir=Path("data/kaipan/snapshots"),
        )
        assert hasattr(provider, "_fetch_and_save"), "缺少 _fetch_and_save 方法"

    def test_save_raw_method_has_dataset_param(self):
        """验证 _save_raw 方法接受 dataset 参数。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_provider import KaipanProvider, KaipanAuth
        import inspect

        auth = KaipanAuth(device_id="test")
        provider = KaipanProvider(
            auth=auth,
            raw_dir=Path("data/kaipan/raw"),
            normalized_dir=Path("data/kaipan/snapshots"),
            snapshots_dir=Path("data/kaipan/snapshots"),
        )
        sig = inspect.signature(provider._save_raw)
        params = list(sig.parameters.keys())
        assert "dataset" in params, f"_save_raw 缺少 dataset 参数，当前参数: {params}"


class TestKaipanNormalizer:
    """验证 KaipanNormalizer 的 schema 加载和字段转换。"""

    def test_normalizer_has_required_methods(self):
        """验证所有必需方法存在。"""
        import sys
        sys.path.insert(0, "src")
        from providers.kaipan_normalizer import KaipanNormalizer

        normalizer = KaipanNormalizer(
            schema_dir="src/providers/kaipan_schema",
            snapshots_dir="data/kaipan/snapshots",
        )
        required_methods = [
            "normalize",
            "normalize_hot_topics",
            "normalize_topic_constituents",
            "normalize_strong_symbols",
            "normalize_market_context",
            "normalize_date",
        ]
        for method in required_methods:
            assert hasattr(normalizer, method), f"缺少方法: {method}"

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