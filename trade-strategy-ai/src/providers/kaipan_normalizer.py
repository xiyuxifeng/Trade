"""Kaipan 数据标准化转换器。

读取 src/providers/kaipan_schema/*.yaml，执行字段映射，输出标准化快照 JSON。
"""

from __future__ import annotations

import json
import re
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
        """根据路径从嵌套结构中获取值。

        支持 "." 分隔键，"[i]" 遍历数组。
        示例：_get_nested(data, "list.[i].[0]") 遍历 list，取每个元素的 [0]。
        """
        if not path:
            return data
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
        fields = mapping.get("fields", {})
        if not fields:
            return []

        # 找到带 [i] 的字段，确定 list 路径
        list_field = None
        list_base = None
        for field_name, field_spec in fields.items():
            raw_path = field_spec["raw_path"]
            if "[i]" in raw_path:
                list_field = field_name
                idx = raw_path.index("[i]")
                list_base = raw_path[:idx].rstrip(".")
                break

        if not list_base:
            # 无数组遍历，单条记录
            result = {}
            for field_name, field_spec in fields.items():
                result[field_name] = self._get_nested(raw_data, field_spec["raw_path"])
            return [result] if any(v is not None for v in result.values()) else []

        raw_list = self._get_nested(raw_data, list_base)
        if not isinstance(raw_list, list):
            return []

        results = []
        for idx in range(len(raw_list)):
            record = {}
            for field_name, field_spec in fields.items():
                indexed_path = field_spec["raw_path"].replace("[i]", f"[{idx}]")
                record[field_name] = self._get_nested(raw_data, indexed_path)
            results.append(record)
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
                raw_file = (
                    Path("data/kaipan/raw")
                    / dataset
                    / f"{trade_date}_{slot}"
                    / f"{dataset}.json"
                )
                if raw_file.exists():
                    results[slot][dataset] = self.normalize(dataset, raw_file, slot)
        return results
