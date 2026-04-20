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
        if request.method == "POST":
            resp = requests.post(request.endpoint, data=request.params, timeout=30)
        else:
            resp = requests.get(request.endpoint, params=request.params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _save_raw(self, raw_path: Path, request: KaipanRequest, response_data: Any, dataset: str) -> None:
        """将 raw JSON 保存到文件，顶部嵌入 meta 元信息。

        Args:
            raw_path: 原始文件存储路径
            request: 请求对象
            response_data: 响应数据
            dataset: 标准 dataset 名称（从设计文档规定，不是方法名）
        """
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "dataset": dataset,
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

    def _fetch_and_save(
        self,
        *,
        dataset: str,
        api_name: str,
        controller: str,
        base_url_key: str = "apphis",
        method: str = "GET",
        **params: Any,
    ) -> dict[str, Any]:
        """通用抓取保存方法。

        统一处理请求构造、HTTP抓取和原始文件存储。

        Args:
            dataset: 标准 dataset 名称（必须与设计文档一致）
            api_name: API 接口名
            controller: 控制器名
            base_url_key: Base URL key（默认 apphis）
            method: HTTP 方法（默认 GET）
            **params: 传递给 build_request 的额外参数

        Returns:
            API 响应原始数据
        """
        request = self.build_request(
            api_name=api_name,
            controller=controller,
            base_url_key=base_url_key,
            method=method,
            **params,
        )
        # 根据 api_name 和关键参数区分文件名，避免同 dataset 下数据互相覆盖
        filename_parts = [dataset, api_name]
        if api_name == "RealRankingInfo":
            filename_parts.append(f"ZSType{params.get('ZSType', '')}")
        elif api_name == "GetInterviewsByDateStock":
            filename_parts.append(f"Type{params.get('Type', '')}")
        elif api_name == "MorningBiddingList":
            filename_parts.append(f"PidType{params.get('PidType', '')}")
        elif api_name == "GetPlateInfo_w38":
            filename_parts.append(f"Index{params.get('Index', '')}")
        elif api_name == "GetZhangTingTianTi":
            filename_parts.append(f"Index{params.get('Index', '')}")
        elif api_name == "GetFengKListBest":
            filename_parts.append(f"Time{params.get('Time', '')}")
        elif api_name == "GetFengKList":
            filename_parts.append(f"Time{params.get('Time', '')}")
        elif api_name == "GetInterviewsByDateZS":
            filename_parts.append(f"Type{params.get('Type', '')}")
        raw_filename = "_".join(filter(None, filename_parts))
        raw_path = self.raw_dir / dataset / f"{self._trade_date.isoformat()}_{self._slot}" / f"{raw_filename}.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response, dataset)
        return response

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
        return self._fetch_and_save(
            dataset="hot_topics",
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
        return self._fetch_and_save(
            dataset="hot_topics",
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
        return self._fetch_and_save(
            dataset="hot_topics",
            api_name="GetFengKYDPlate",
            controller="StockFengKData",
            base_url_key="apphis",
            method="POST",
        )

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
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="InfoGet",
            controller="Theme",
            base_url_key="applhb",
            method="POST",
        )

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
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="GetFeaturedSection",
            controller="StockL2Data",
            base_url_key="apphwshhq",
            method="POST",
        )

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
        return self._fetch_and_save(
            dataset="strong_symbols",
            api_name="GetFengKListBest",
            controller="StockFengKData",
            base_url_key="apphis",
            method="POST",
        )

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
        return self._fetch_and_save(
            dataset="strong_symbols",
            api_name="GetInterviewsByDateStock",
            controller="StockLineData",
            base_url_key="apphis",
            method="POST",
            Type="2",
            FilterBJS="1",
        )

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
        return self._fetch_and_save(
            dataset="strong_symbols",
            api_name="MorningBiddingList",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="POST",
        )

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
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="GetPlateInfo_w38",
            controller="HisLimitResumption",
            base_url_key="apphis",
            method="POST",
        )

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
        return self._fetch_and_save(
            dataset="market_context",
            api_name="MorningBidding",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="POST",
        )

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
        return self._fetch_and_save(
            dataset="market_context",
            api_name="MorningBiddingNum",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="POST",
        )

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
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="GetZhangTingTianTi",
            controller="FuPanLa",
            base_url_key="apphis",
            method="POST",
        )

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
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="GetStockList",
            controller="LongHuBang",
            base_url_key="applhb",
            method="POST",
        )

