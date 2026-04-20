"""开盘啦私有接口 Provider 草案。

说明：
- 当前文件是接口设计草案，不直接接入主链路。
- 目标是把 App 私有接口与上层 DataAgent / market_universe 隔离。
- 第一阶段优先支持 raw JSON 抓取、标准化快照输出、字段映射。
"""

from __future__ import annotations

import json
import requests
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
        self.base_urls = {
            "apphis": "https://apphis.longhuvip.com/w1/api/index.php",
            "apphwshhq": "https://apphwshhq.longhuvip.com/w1/api/index.php",
            "applhb": "https://applhb.longhuvip.com/w1/api/index.php",
        }
        self._trade_date: date | None = None
        self._slot: str | None = None

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

    def build_request(
        self,
        *,
        api_name: str,
        controller: str,
        base_url_key: str = "apphis",
        method: str = "GET",
        **params: Any,
    ) -> KaipanRequest:
        """生成规范化请求对象。"""
        merged = self.build_common_params()
        merged.update(params)
        return KaipanRequest(
            endpoint=self.base_urls[base_url_key],
            method=method,
            controller=controller,
            action=api_name,
            params=merged,
        )

    def _fetch_single(self, request: KaipanRequest) -> dict[str, Any]:
        """发起单次 HTTP 请求，返回解析后的 JSON 响应。"""
        resp = requests.get(request.endpoint, params=request.params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _save_raw(self, raw_path: Path, request: KaipanRequest, response_data: Any) -> None:
        """将 raw JSON 保存到文件，顶部嵌入 meta 元信息。"""
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "dataset": raw_path.stem,
                "trade_date": self._trade_date.isoformat() if self._trade_date else None,
                "slot": self._slot,
                "fetched_at": datetime.now().isoformat(),
                "source": "kaipan",
                "request": {
                    "endpoint": request.endpoint,
                    "controller": request.controller,
                    "action": request.action,
                    "params": request.params,
                },
            },
            "data": response_data,
        }
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

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

    # ================================
    # 13 个具体接口实现
    # ================================

    def fetch_board_strength(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """板块强度 - RealRankingInfo (ZSType=7)。

        Args:
            trade_date: 交易日期
            slot: 时段标识，如 "09-30"

        Returns:
            板块强度排名原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="RealRankingInfo",
            controller="ZhiShuRanking",
            base_url_key="apphis",
            method="POST",
            Date=trade_date.strftime("%Y-%m-%d"),
            Type="1",
            Order="1",
            ZSType="7",
            Index=0,
            st=20,
        )
        raw_path = self.raw_dir / "board_strength" / f"{trade_date.isoformat()}_{slot}" / "board_strength.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_industry_ranking(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """行业排名 - RealRankingInfo (ZSType=4)。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            行业排名原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="RealRankingInfo",
            controller="ZhiShuRanking",
            base_url_key="apphis",
            method="POST",
            Date=trade_date.strftime("%Y-%m-%d"),
            Type="2",
            Order="1",
            ZSType="4",
            Index=0,
            st=20,
        )
        raw_path = self.raw_dir / "industry_ranking" / f"{trade_date.isoformat()}_{slot}" / "industry_ranking.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_concept_fengkou(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """概念风口 - GetFengKYDPlate。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            概念风口原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="GetFengKYDPlate",
            controller="StockFengKData",
            base_url_key="apphis",
            method="POST",
        )
        raw_path = self.raw_dir / "concept_fengkou" / f"{trade_date.isoformat()}_{slot}" / "concept_fengkou.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_theme_detail(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """主题详情 - InfoGet。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            主题详情原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="InfoGet",
            controller="Theme",
            base_url_key="applhb",
            method="POST",
        )
        raw_path = self.raw_dir / "theme_detail" / f"{trade_date.isoformat()}_{slot}" / "theme_detail.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_stock_sector_v2(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """股票板块 v2 - GetFeaturedSection。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            股票板块 v2 原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="GetFeaturedSection",
            controller="StockL2Data",
            base_url_key="apphwshhq",
            method="POST",
        )
        raw_path = self.raw_dir / "stock_sector_v2" / f"{trade_date.isoformat()}_{slot}" / "stock_sector_v2.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_strong_fengkou(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """强势风口 - GetFengKListBest。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            强势风口原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="GetFengKListBest",
            controller="StockFengKData",
            base_url_key="apphis",
            method="POST",
        )
        raw_path = self.raw_dir / "strong_fengkou" / f"{trade_date.isoformat()}_{slot}" / "strong_fengkou.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_interval_stats_stock(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """区间统计股票 - GetInterviewsByDateStock。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            区间统计股票原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="GetInterviewsByDateStock",
            controller="StockLineData",
            base_url_key="apphis",
            method="POST",
            Type="2",
            FilterBJS="1",
        )
        raw_path = self.raw_dir / "interval_stats_stock" / f"{trade_date.isoformat()}_{slot}" / "interval_stats_stock.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_morning_bidding_list(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """早盘竞价列表 - MorningBiddingList。

        Args:
            trade_date: 交易日期
            slot: 09-25 时段

        Returns:
            早盘竞价列表原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="MorningBiddingList",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="POST",
        )
        raw_path = self.raw_dir / "morning_bidding_list" / f"{trade_date.isoformat()}_{slot}" / "morning_bidding_list.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_limit_up_reason(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """涨停原因 - GetPlateInfo_w38。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            涨停原因原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="GetPlateInfo_w38",
            controller="HisLimitResumption",
            base_url_key="apphis",
            method="POST",
        )
        raw_path = self.raw_dir / "limit_up_reason" / f"{trade_date.isoformat()}_{slot}" / "limit_up_reason.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_pre_market_bid(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """盘前竞价 - MorningBidding。

        Args:
            trade_date: 交易日期
            slot: 09-25 时段

        Returns:
            盘前竞价原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="MorningBidding",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="POST",
        )
        raw_path = self.raw_dir / "pre_market_bid" / f"{trade_date.isoformat()}_{slot}" / "pre_market_bid.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_pre_market_stats(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """盘前统计 - MorningBiddingNum。

        Args:
            trade_date: 交易日期
            slot: 09-25 时段

        Returns:
            盘前统计原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="MorningBiddingNum",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="POST",
        )
        raw_path = self.raw_dir / "pre_market_stats" / f"{trade_date.isoformat()}_{slot}" / "pre_market_stats.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_limit_up_info(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """涨停信息 - GetZhangTingTianTi。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            涨停信息原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="GetZhangTingTianTi",
            controller="FuPanLa",
            base_url_key="apphis",
            method="POST",
        )
        raw_path = self.raw_dir / "limit_up_info" / f"{trade_date.isoformat()}_{slot}" / "limit_up_info.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

    def fetch_lhb_list(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """龙虎榜列表 - GetStockList。

        Args:
            trade_date: 交易日期
            slot: 17-30 时段

        Returns:
            龙虎榜列表原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        request = self.build_request(
            api_name="GetStockList",
            controller="LongHuBang",
            base_url_key="applhb",
            method="POST",
        )
        raw_path = self.raw_dir / "lhb_list" / f"{trade_date.isoformat()}_{slot}" / "lhb_list.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response)
        return response

