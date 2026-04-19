"""开盘啦私有接口 Provider 草案。

说明：
- 当前文件是接口设计草案，不直接接入主链路。
- 目标是把 App 私有接口与上层 DataAgent / market_universe 隔离。
- 第一阶段优先支持 raw JSON 抓取、标准化快照输出、字段映射。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KaipanAuth:
    """开盘啦私有接口鉴权参数。"""

    device_id: str
    phone_os_new: str = "2"
    version: str = "5.23.0.1"
    apiv: str = "w44"
    token: str | None = None
    user_id: str | None = None


@dataclass(frozen=True)
class KaipanRequest:
    """单次接口请求的规范化描述。"""

    endpoint: str
    method: str
    controller: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KaipanSnapshotMeta:
    """抓取快照元信息。

    该结构用于 raw/normalized/snapshot 三层存储时写入元数据。
    """

    dataset: str
    trade_date: date | None
    fetched_at: datetime
    request: KaipanRequest
    page_key: str | None = None
    source: str = "kaipan"


class KaipanProvider:
    """开盘啦数据提供者草案。

    职责：
    - 组装私有接口请求参数
    - 统一保存 raw JSON
    - 输出标准化热点 / 成分 / 强势池快照

    非职责：
    - 不直接给 DataAgent 暴露所有私有接口细节
    - 不在本文件中承担 ranking / backtest / manager 编排逻辑
    """

    def __init__(
        self,
        *,
        auth: KaipanAuth,
        raw_dir: str | Path,
        normalized_dir: str | Path,
        snapshots_dir: str | Path,
    ) -> None:
        self.auth = auth
        self.raw_dir = Path(raw_dir)
        self.normalized_dir = Path(normalized_dir)
        self.snapshots_dir = Path(snapshots_dir)

    def build_common_params(self) -> dict[str, Any]:
        """构造私有接口公共参数。"""
        params: dict[str, Any] = {
            "DeviceID": self.auth.device_id,
            "PhoneOSNew": self.auth.phone_os_new,
            "VerSion": self.auth.version,
            "apiv": self.auth.apiv,
        }
        if self.auth.token:
            params["Token"] = self.auth.token
        if self.auth.user_id:
            params["UserID"] = self.auth.user_id
        return params

    def build_request(self, *, controller: str, action: str, method: str = "GET", **params: Any) -> KaipanRequest:
        """生成规范化请求对象。"""
        merged = self.build_common_params()
        merged.update(params)
        return KaipanRequest(
            endpoint="https://apphis.longhuvip.com/w1/api/index.php",
            method=method,
            controller=controller,
            action=action,
            params=merged,
        )

    def dataset_raw_path(self, *, trade_date: date, dataset: str, page_key: str | None = None) -> Path:
        """返回原始 JSON 存储路径。"""
        suffix = f"_{page_key}" if page_key else ""
        return self.raw_dir / trade_date.isoformat() / f"{dataset}{suffix}.json"

    def dataset_normalized_path(self, *, trade_date: date, dataset: str) -> Path:
        """返回标准化 JSON 存储路径。"""
        return self.normalized_dir / trade_date.isoformat() / f"{dataset}.json"

    def dataset_snapshot_path(self, *, trade_date: date, dataset: str) -> Path:
        """返回快照 JSON 存储路径。"""
        return self.snapshots_dir / trade_date.isoformat() / f"{dataset}.json"

    # -----------------------------
    # 下列方法是后续推荐实现的接口
    # -----------------------------

    def fetch_hot_topics(self, *, trade_date: date, kind: str) -> dict[str, Any]:
        """获取热点主题。

        kind:
        - `concept`
        - `industry`

        预期输出：
        - `topics`: 标准化主题列表
        - `evidence`: 原始接口摘要
        """
        raise NotImplementedError

    def fetch_topic_constituents(self, *, trade_date: date, topic_ids: list[str], kind: str) -> dict[str, Any]:
        """获取主题成分股映射。"""
        raise NotImplementedError

    def fetch_strong_symbols(self, *, trade_date: date, universe: list[str] | None = None) -> dict[str, Any]:
        """获取强势股候选池。"""
        raise NotImplementedError

    def fetch_market_context(self, *, trade_date: date) -> dict[str, Any]:
        """获取市场状态上下文。

        适合聚合：
        - 市场情绪
        - 市场量能
        - 指数数据
        - 涨跌停数
        """
        raise NotImplementedError

    def fetch_postmarket_evidence(self, *, trade_date: date, symbols: list[str]) -> dict[str, Any]:
        """获取盘后解释型证据。

        适合聚合：
        - 龙虎榜
        - 涨停原因
        - 大盘直播
        - 最新消息
        """
        raise NotImplementedError

