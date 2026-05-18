"""Kaipan 数据标准化转换器。

读取 src/providers/kaipan_schema/*.yaml，执行字段映射，输出标准化快照 JSON。
"""

from __future__ import annotations

import json
import re
import yaml
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.common.paths import resolve_project_path


class KaipanNormalizer:
    """kaipan 数据标准化转换器。

    读取 YAML 映射文件，将 raw JSON 转换为标准化快照 JSON。
    """

    def __init__(self, schema_dir: str | Path, snapshots_dir: str | Path) -> None:
        self.schema_dir = resolve_project_path(schema_dir)
        self.snapshots_dir = resolve_project_path(snapshots_dir)

    def _load_schema(self, dataset: str) -> dict[str, Any]:
        """加载指定 dataset 的 YAML schema。"""
        schema_path = self.schema_dir / f"{dataset}.yaml"
        with open(schema_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _canonicalize_raw_data(self, raw_data: Any, meta: dict[str, Any]) -> Any:
        """按请求 URL/action 统一历史/今日响应差异。

        这一步只处理同一接口在历史 URL 与今日 URL 下返回字段不一致的问题，
        不改变原始业务含义，只补齐别名或缺失字段，便于后续 schema 映射和上层消费。
        """
        if not isinstance(raw_data, dict):
            return raw_data

        normalized = dict(raw_data)
        request = meta.get("request", {}) if isinstance(meta, dict) else {}
        endpoint = str(request.get("endpoint", ""))
        action = str(request.get("action", ""))
        host = urlparse(endpoint).netloc

        # 今日接口在 apphwhq 域名下会缺少 MinDay，历史接口通常有该字段。
        if action == "RealRankingInfo" and host == "apphwhq.longhuvip.com" and "MinDay" not in normalized:
            normalized["MinDay"] = None

        # 历史/今日返回的提示字段存在 Tip/Tips 命名差异。
        if action == "GetFengKListBest":
            tip = normalized.get("Tip")
            tips = normalized.get("Tips")
            if tips is None and tip is not None:
                normalized["Tips"] = tip
            elif tip is None and tips is not None:
                normalized["Tip"] = tips

        # 历史接口可能不返回 Count，按 List 长度补齐，避免下游分支。
        if action == "GetInterviewsByDateStock" and normalized.get("Count") is None:
            list_value = normalized.get("List")
            if isinstance(list_value, list):
                normalized["Count"] = len(list_value)

        # 历史/今日返回的日期字段存在 Date/date 大小写差异。
        if action == "GetZhangTingTianTi":
            if normalized.get("Date") is None and normalized.get("date") is not None:
                normalized["Date"] = normalized["date"]
            if normalized.get("date") is None and normalized.get("Date") is not None:
                normalized["date"] = normalized["Date"]

        if action == "GetPlateInfo_w38" and normalized.get("summary") is None and normalized.get("nums") is not None:
            normalized["summary"] = normalized.get("nums")

        if action in {"GetZsReal", "RefreshStockList"} and normalized.get("StockList") is None and normalized.get("list") is not None:
            normalized["StockList"] = normalized.get("list")

        return normalized

    def _get_nested(self, data: Any, path: str) -> Any:
        """根据路径从嵌套结构中获取值。

        支持 "." 分隔键和 "[N]" 数组索引（数字）。
        示例：
        - "info.[0].[1]" -> data["info"][0][1]
        - "list.[0].name" -> data["list"][0]["name"]
        注意：不处理 "[i]" 符号，[i] 的展开由 _transform() 在调用前完成。
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
        raw_data = self._canonicalize_raw_data(raw.get("data", {}), raw.get("meta", {}))
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

    def normalize_market_sentiment(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("market_sentiment", raw_path, slot)

    def normalize_market_index(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("market_index", raw_path, slot)

    def normalize_sharp_withdrawal(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("sharp_withdrawal", raw_path, slot)

    def normalize_sector_ranking(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("sector_ranking", raw_path, slot)

    def normalize_market_context(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("market_context", raw_path, slot)

    def normalize_market_stock_zd_num(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("market_stock_zd_num", raw_path, slot)

    def normalize_zhang_ting_expression(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("zhang_ting_expression", raw_path, slot)

    def normalize_daily_limit_index(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("daily_limit_index", raw_path, slot)

    def normalize_weight_performance(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("weight_performance", raw_path, slot)

    def normalize_get_feng_k_list(self, raw_path: Path, slot: str) -> dict[str, Any]:
        return self.normalize("get_feng_k_list", raw_path, slot)

    def normalize_date(self, trade_date: str, slots: tuple[str, ...] = ("09-25", "17-30")) -> dict[str, dict[str, Any]]:
        """批量转换某交易日全部时间槽的 snapshots。

        Args:
            trade_date: 交易日期，格式 YYYY-MM-DD
            slots: 时间槽列表，默认为 ("09-25", "17-30")
        """
        results = {}
        for slot in slots:
            results[slot] = {}
            for dataset in (
                "hot_topics",
                "topic_constituents",
                "strong_symbols",
                "market_sentiment",
                "market_index",
                "sharp_withdrawal",
                "sector_ranking",
                "market_context",
                "market_stock_zd_num",
                "zhang_ting_expression",
                "daily_limit_index",
                "weight_performance",
                "get_feng_k_list",
            ):
                raw_file = (
                    resolve_project_path("data/kaipan/raw")
                    / dataset
                    / f"{trade_date}_{slot}"
                    / f"{dataset}.json"
                )
                if raw_file.exists():
                    try:
                        results[slot][dataset] = self.normalize(dataset, raw_file, slot)
                    except Exception as e:
                        results[slot][dataset] = {"_error": str(e)}
                else:
                    results[slot][dataset] = None  # 明确标记为不存在
        return results
