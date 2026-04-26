"""NTL-S6-013: 回测复现验证

提供 fingerprint 生成用于比对两次回测结果是否一致。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime

from src.backtest.schemas import BacktestResult


def _json_safe(obj):
    """将对象转换为 JSON 安全类型（处理 date/datetime）。"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(item) for item in obj]
    return obj


def fingerprint_result(result: BacktestResult) -> str:
    """对 BacktestResult 生成稳定 fingerprint（供复现比对）。

    Args:
        result: BacktestResult

    Returns:
        SHA256 hex digest
    """
    # dataclass 使用 asdict 序列化，sort_keys 保证顺序稳定
    d = asdict(result)
    d = _json_safe(d)
    payload = json.dumps(d, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
