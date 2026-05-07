"""MFE / MAE / return_pct 计算器（NTL-S5-010）。

职责：
- 从 ohlcv_1d bars 计算持仓期间的 MFE（最大有利偏移）和 MAE（最大不利偏移）
- 计算入场到出场的收益率
- 判定止盈/止损触发
- 支持 A 股交易规则约束（T+1、涨跌停限制）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from src.common.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class TradeConstraint:
    """A股交易规则约束配置（NTL-S6-003 扩展版）。

    用于在 MFE/MAE/exit 判定中体现真实交易限制，避免回测高估止盈/止损触发概率。

    属性：
        t_plus_one: 是否启用 T+1 约束（买入当日不能卖出）
        limit_up_pct: 涨停幅度比例（主板 0.10，创业板/科创板 0.20，ST 0.05）
            - None 表示无涨跌幅限制（如新股上市前 5 日）
        limit_down_pct: 跌停幅度比例（主板 0.10，创业板/科创板 0.20，ST 0.05）
            - None 表示无涨跌幅限制
        board_type: 板块类型，用于自动推断涨跌停幅度
            - "auto": 根据 symbol 自动推断（6 开头上海主板/科创板，0/3 开头深圳主板/创业板）
            - "main": 主板（10%）
            - "chinext": 创业板（20%）
            - "star": 科创板（20%）
            - "st": ST 股票（5%，2026-07-06 起沪市调整为 10%）
            - "bse": 北交所（30%，预留）
        market: 市场（"SH"=上海，"SZ"=深圳），用于区分沪市/深市 ST 规则
        trade_date: 交易日期，用于判断 ST 规则切换时间点（2026-07-06 沪市 ST 调整为 10%）
        is_new_stock: 是否为新股（上市前 5 日无涨跌幅限制）
        listing_date: 上市日期（用于自动判断 is_new_stock）
    """

    t_plus_one: bool = True
    limit_up_pct: float | None = None
    limit_down_pct: float | None = None
    board_type: str = "auto"
    market: str | None = None  # "SH" / "SZ"
    trade_date: date | None = None  # 用于 ST 规则日期切换
    is_new_stock: bool = False  # 新股上市前 5 日无涨跌幅限制
    listing_date: date | None = None  # 上市日期


def _infer_board_type(symbol: str) -> str:
    """根据股票代码推断板块类型。

    A股代码规则：
    - 600/601/603/605 开头：上海主板（10%）
    - 688 开头：科创板（20%）
    - 000/001/002/003 开头：深圳主板（10%）
    - 300/301 开头：创业板（20%）
    - 8/4 开头或含 "ST"：北交所/ST（预留，默认 5%）

    对于非标准代码（如 ETF、指数），默认按主板 10% 处理。
    """
    s = symbol.strip().upper()
    # 去掉后缀（如 .SH, .SZ）
    code = s.split(".")[0] if "." in s else s

    # ST 股票识别（代码中包含 ST 字样，且不是以数字开头——如 "ST0001"）
    if "ST" in s and not s[0].isdigit():
        return "st"

    if not code or not code[0].isdigit():
        return "main"  # 非数字代码（如 ETF）默认主板

    # 科创板
    if code.startswith("688"):
        return "star"

    # 创业板
    if code.startswith("300") or code.startswith("301"):
        return "chinext"

    # 北交所（预留）
    if code.startswith("8") or code.startswith("4"):
        return "bse"

    # 上海主板 / 深圳主板
    return "main"


# 沪市 ST 规则变更生效日（2026-07-06 起涨跌幅从 5% 调整为 10%）
ST_SH_RULE_EFFECTIVE_DATE = date(2026, 7, 6)


def _get_limit_pct(
    board_type: str,
    trade_date: date | None = None,
    market: str | None = None,
) -> tuple[float, float]:
    """根据板块类型返回涨跌停幅度（limit_up_pct, limit_down_pct）。

    ST 规则日期切换（NTL-S6-003 Step 6）：
    - 沪市 ST（market="SH"）：2026-07-06 前为 5%，之后为 10%
    - 深市 ST（market="SZ"）：维持 5%（截至 2026-04-26 无变化）

    Args:
        board_type: 板块类型
        trade_date: 交易日期（用于判断 ST 规则切换）
        market: 市场（"SH" / "SZ"，用于区分 ST 规则适用市场）

    Returns:
        (limit_up_pct, limit_down_pct) 比例值
    """
    if board_type == "st":
        # ST 规则需要区分市场 + 日期
        if market == "SH" and trade_date is not None and trade_date >= ST_SH_RULE_EFFECTIVE_DATE:
            # 2026-07-06 起沪市 ST 调整为 10%
            return (0.10, 0.10)
        # 其余情况默认 5%（深市 ST / 沪市 2026-07-06 前）
        return (0.05, 0.05)

    pct_map = {
        "main": (0.10, 0.10),
        "chinext": (0.20, 0.20),
        "star": (0.20, 0.20),
        "bse": (0.30, 0.30),  # 北交所预留
    }
    return pct_map.get(board_type, (0.10, 0.10))


def _get_price_cage_pct(board_type: str) -> tuple[float, float]:
    """根据板块类型返回价格笼子幅度（上限, 下限）。

    A 股常见限价申报规则：
    - 沪深主板 / 创业板 / 科创板 / ST：102% / 98%
    - 北交所：105% / 95%

    这里仅做约束校验和记录，不改变当前回测的成交口径。
    """
    if board_type == "bse":
        return (0.05, 0.05)
    return (0.02, 0.02)


def _resolve_constraint(
    constraint: TradeConstraint | None,
    symbol: str,
) -> TradeConstraint:
    """解析并补全交易约束配置。

    如果 constraint 为 None，返回默认配置。
    如果 board_type="auto"，根据 symbol 自动推断。
    如果 limit_up_pct/limit_down_pct 未设置，根据 board_type 补全。
    market 未设置且 symbol 已知时，自动从 symbol 推断（6xx/688 → "SH"，0xx/3xx → "SZ"）。
    trade_date 用于 ST 规则日期切换。
    listing_date + trade_date 用于判断新股（上市前 5 日无涨跌幅限制）。
    """
    if constraint is None:
        constraint = TradeConstraint()

    board = constraint.board_type
    if board == "auto":
        board = _infer_board_type(symbol)

    market = constraint.market
    if market is None:
        # 从 symbol 推断市场
        code = symbol.split(".")[0] if "." in symbol else symbol
        if code.startswith("6") or code.startswith("688"):
            market = "SH"
        elif code.startswith("0") or code.startswith("3"):
            market = "SZ"

    # 新股判断：上市日期存在且当前日期在上市后 5 日内（含上市当日）
    is_new_stock = constraint.is_new_stock
    if not is_new_stock and constraint.listing_date is not None and constraint.trade_date is not None:
        days_since_listing = (constraint.trade_date - constraint.listing_date).days
        if 0 <= days_since_listing < 5:
            is_new_stock = True

    limit_up = constraint.limit_up_pct
    limit_down = constraint.limit_down_pct

    # 新股上市前 5 日无涨跌幅限制
    if is_new_stock:
        limit_up = None
        limit_down = None
    elif limit_up is None or limit_down is None:
        default_up, default_down = _get_limit_pct(board, constraint.trade_date, market)
        limit_up = limit_up if limit_up is not None else default_up
        limit_down = limit_down if limit_down is not None else default_down

    return TradeConstraint(
        t_plus_one=constraint.t_plus_one,
        limit_up_pct=limit_up,
        limit_down_pct=limit_down,
        board_type=board,
        market=market,
        trade_date=constraint.trade_date,
        is_new_stock=is_new_stock,
        listing_date=constraint.listing_date,
    )


def compute_return_pct(entry_price: float, exit_price: float) -> float:
    """计算收益率（比例口径，0.01=1%）。

    统一供盘前、盘后、fallback 路径复用，避免不同入口出现口径漂移。
    """
    if entry_price <= 0:
        return 0.0
    return exit_price / entry_price - 1


def _normalize_bar(bar: dict[str, Any]) -> dict[str, Any]:
    """统一 bar 数据格式，兼容不同 key 命名（lowercase / uppercase）。

    同时归一化 volume 字段（仅当原始数据提供时），用于后续停牌/无成交识别。
    volume 字段缺失时不默认填充 0，避免正常数据被误判为停牌。
    """
    result: dict[str, Any] = {
        "date": bar.get("date") or bar.get("Date") or "",
        "open": float(bar.get("open") or bar.get("Open") or 0),
        "high": float(bar.get("high") or bar.get("High") or 0),
        "low": float(bar.get("low") or bar.get("Low") or 0),
        "close": float(bar.get("close") or bar.get("Close") or 0),
    }
    raw_volume = bar.get("volume") if "volume" in bar else bar.get("Volume") if "Volume" in bar else None
    if raw_volume is not None:
        result["volume"] = float(raw_volume)
    return result


def _is_bar_halted(bar: dict[str, Any]) -> bool:
    """判断单个 bar 是否表示停牌。

    仅识别真实停牌（交易暂停），不包括一字板。
    如需区分一字板，请使用 _classify_bar_status。

    识别规则：
    1. 显式 is_halted=True
    2. volume == 0 且价格完全无波动，且不在涨跌停价格上
    """
    if bar.get("is_halted") is True:
        return True

    if "volume" in bar:
        volume = float(bar.get("volume") or 0)
        high = float(bar.get("high") or 0)
        low = float(bar.get("low") or 0)
        open_price = float(bar.get("open") or 0)
        close = float(bar.get("close") or 0)
        if volume == 0 and high == low == open_price == close and close > 0:
            return True

    return False


def _is_bar_limit_locked(
    bar: dict[str, Any],
    prev_close: float | None = None,
    limit_up_pct: float | None = None,
    limit_down_pct: float | None = None,
) -> tuple[bool, str]:
    """判断单个 bar 是否为涨跌停一字板。

    一字板特征：
    - 开盘价 = 涨停价/跌停价
    - 成交量极低（无法买入/卖出）
    - 价格全天无波动（high == low == close）

    与停牌的区别：
    - 停牌：无价格、无成交、原因是不交易
    - 一字板：有价格（涨跌停价）、可能有极少成交、原因是买卖力量极端

    Args:
        bar: OHLCV bar 数据
        prev_close: 前一日收盘价（用于计算涨跌停价格）
        limit_up_pct: 涨停比例（None 表示无限制）
        limit_down_pct: 跌停比例（None 表示无限制）

    Returns:
        (is_locked, direction) — direction 为 "up"/"down"/""
    """
    if prev_close is None or prev_close <= 0:
        return False, ""

    open_price = float(bar.get("open") or 0)
    high = float(bar.get("high") or 0)
    low = float(bar.get("low") or 0)
    close = float(bar.get("close") or 0)
    volume = float(bar.get("volume") or 0)

    if open_price <= 0:
        return False, ""

    # 检查是否在涨停价上且价格无波动
    if limit_up_pct is not None:
        limit_up_price = prev_close * (1 + limit_up_pct)
        if (abs(open_price - limit_up_price) < 0.01
                and high == low == open_price == close
                and volume < 100):  # 极低成交量
            return True, "up"

    # 检查是否在跌停价上且价格无波动
    if limit_down_pct is not None:
        limit_down_price = prev_close * (1 - limit_down_pct)
        if (abs(open_price - limit_down_price) < 0.01
                and high == low == open_price == close
                and volume < 100):
            return True, "down"

    return False, ""


def classify_bar_status(
    bar: dict[str, Any],
    prev_close: float | None = None,
    limit_up_pct: float | None = None,
    limit_down_pct: float | None = None,
) -> str:
    """分类 bar 的交易状态。

    检查顺序：一字板 > 停牌 > 低流动性 > 正常
    一字板优先于停牌判断（一字板是极端市场行为，不是暂停交易）。

    Returns:
        "normal" — 正常交易
        "halted" — 停牌（无交易）
        "limit_up_locked" — 涨停一字板
        "limit_down_locked" — 跌停一字板
        "low_liquidity" — 低流动性（有价格但成交量极小）
    """
    # 1. 优先检查一字板（涨跌停锁死），避免与停牌混淆
    is_locked, direction = _is_bar_limit_locked(
        bar, prev_close, limit_up_pct, limit_down_pct
    )
    if is_locked:
        return f"limit_{direction}_locked"

    # 2. 停牌检查
    if _is_bar_halted(bar):
        return "halted"

    # 3. 流动性检查
    volume = float(bar.get("volume") or 0)
    if 0 < volume < 100:
        return "low_liquidity"

    return "normal"


def _find_bar_index(bars: list[dict[str, Any]], target_date: str) -> int | None:
    """在 bars 中查找指定日期的 index，不存在则返回 None。"""
    for i, bar in enumerate(bars):
        normalized = _normalize_bar(bar)
        if normalized["date"] == target_date:
            return i
    return None


def _extract_rules_hit(signal_context_rules_snapshot: list[dict[str, Any]]) -> list[str]:
    """从 SignalContext.rules_snapshot 提取 rules_hit。

    当前简化实现：rules_snapshot 中的每条 rule 都视为参与了决策，
    将其 rule_id 收集为 rules_hit。
    后续可扩展：增加 matched=True 过滤，或从 Signal.triggered_rules 获取。
    """
    return [rule.get("rule_id") for rule in signal_context_rules_snapshot if rule.get("rule_id")]


def compute_mfe_mae_return(
    bars: list[dict[str, Any]],
    entry_price: float,
    entry_date: str,
    target_price: float | None = None,
    stop_loss_price: float | None = None,
    symbol: str = "",
    constraint: TradeConstraint | None = None,
) -> tuple[float, float, float, str | None, str | None, list[str], str | None]:
    """计算 MFE / MAE / return_pct（比例口径，0.01=1%）。

    做多（buy）场景：
    - MFE = max(high_i) - entry_price（持仓期间最大盈利）
    - MAE = entry_price - min(low_i)（持仓期间最大亏损）

    exit 判定：从 entry_date bar 起遍历，遇到 high >= target_price
    则止盈触发（exit_triggered="target"）；遇到 low <= stop_loss_price
    则止损触发（exit_triggered="stop_loss"）。未触发则用最后 bar close。

    A股交易规则约束（可选）：
    - T+1：买入当日（entry_date）不能卖出，当日不检查止盈/止损触发
    - 涨跌停：止盈/止损价格受涨停价/跌停价限制，不能超出当日涨跌停范围

    停牌/无成交识别：遍历过程中跳过 is_halted 或 volume==0 且价格无波动的 bar，
    避免停牌日价格对 MFE/MAE 产生误判，并在返回结果中记录被跳过的日期。

    Args:
        bars: ohlcv_1d 日线数据 list
        entry_price: 入场价格（元）
        entry_date: 入场日期（YYYY-MM-DD）
        target_price: 止盈价（可选）
        stop_loss_price: 止损价（可选）
        symbol: 股票代码（用于自动推断板块类型和涨跌停幅度）
        constraint: 交易规则约束配置（None 时使用默认 A 股规则）

    Returns:
        (mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, limit_locked_dates, eval_date)
        exit_triggered: "target" | "stop_loss" | None（实际触发出场的类型）
        exit_date: 触发 exit 的日期或 None（None 表示未实际出场）
        halted_dates: 被识别为停牌的日期列表
        limit_locked_dates: 被识别为一字板（涨跌停锁死）的日期列表
        eval_date: 评估截止日（最后一条 bar 的日期，无论是否停牌）
    """
    if not bars or entry_price <= 0:
        # entry_price 非法或 bars 为空：eval_date 仍取最后一条 bar 日期（如有）
        eval_date_fallback = None
        if bars:
            eval_date_fallback = _normalize_bar(bars[-1]).get("date")
        return (0.0, 0.0, 0.0, None, None, [], [], eval_date_fallback)

    # 解析交易约束
    resolved = _resolve_constraint(constraint, symbol)

    # 评估截止日：始终取最后一条 bar 的日期
    last_bar = _normalize_bar(bars[-1])
    eval_date = last_bar["date"]

    # 找 entry bar index
    entry_idx = _find_bar_index(bars, entry_date)
    if entry_idx is None:
        # entry_date 不在 bars 中，从第一条开始（保守处理）
        entry_idx = 0

    mfe = 0.0
    mae = 0.0
    exit_triggered: str | None = None
    exit_date: str | None = None
    exit_price = entry_price  # 默认用 entry_price
    halted_dates: list[str] = []
    limit_locked_dates: list[str] = []  # 一字板日期（区分于停牌）

    for i in range(entry_idx, len(bars)):
        bar = _normalize_bar(bars[i])
        bar_date = bar["date"]

        # 计算前收价（用于涨跌停约束和一字板判断）
        prev_close_for_limit = bar["open"]
        if i > 0:
            prev_close_for_limit = _normalize_bar(bars[i - 1])["close"]

        # 分类 bar 状态：停牌 / 一字板 / 低流动性 / 正常
        bar_status = classify_bar_status(
            bar,
            prev_close=prev_close_for_limit,
            limit_up_pct=resolved.limit_up_pct,
            limit_down_pct=resolved.limit_down_pct,
        )

        # 停牌：跳过
        if bar_status == "halted":
            logger.debug("停牌跳过: symbol=%s, date=%s", symbol, bar_date)
            halted_dates.append(bar_date)
            continue

        # 一字板：记录但使用涨跌停价格参与 MFE 计算（理论极值）
        if bar_status in ("limit_up_locked", "limit_down_locked"):
            logger.debug("一字板: symbol=%s, date=%s, direction=%s", symbol, bar_date, bar_status)
            limit_locked_dates.append(bar_date)
            # 一字板日不跳过，但成交量极低，MFE/MAE 使用涨跌停价作为极值参考

        high = bar["high"]
        low = bar["low"]
        close = bar["close"]
        open_price = bar["open"]

        # 涨跌停价格约束
        prev_close = prev_close_for_limit

        # 有效 high/low：受涨跌停限制（None 表示无限制，如新股上市前 5 日）
        if resolved.limit_up_pct is not None:
            limit_up_price = prev_close * (1 + resolved.limit_up_pct)
            effective_high = min(high, limit_up_price)
        else:
            effective_high = high

        if resolved.limit_down_pct is not None:
            limit_down_price = prev_close * (1 - resolved.limit_down_pct)
            effective_low = max(low, limit_down_price)
        else:
            effective_low = low

        # T+1 约束：entry_date 当日不能卖出，仅累计 MFE/MAE，不检查止盈/止损
        is_entry_day = (bar_date == entry_date)
        if resolved.t_plus_one and is_entry_day:
            mfe = max(mfe, effective_high - entry_price)
            mae = max(mae, entry_price - effective_low)
            exit_price = close
            exit_date = bar_date
            continue

        # 累计 MFE / MAE（使用有效价格）
        mfe = max(mfe, effective_high - entry_price)
        mae = max(mae, entry_price - effective_low)

        # 检查止盈（使用 effective_high）
        if target_price is not None and effective_high >= target_price:
            logger.debug(
                "止盈触发: symbol=%s, date=%s, entry=%.2f, target=%.2f, exit=%.2f",
                symbol,
                bar_date,
                entry_price,
                target_price,
                close,
            )
            exit_triggered = "target"
            # exit_price 用当日收盘价（实际交易中以收盘价成交）
            exit_price = close
            exit_date = bar_date
            break

        # 检查止损（使用 effective_low）
        if stop_loss_price is not None and effective_low <= stop_loss_price:
            logger.debug(
                "止损触发: symbol=%s, date=%s, entry=%.2f, stop_loss=%.2f, exit=%.2f",
                symbol,
                bar_date,
                entry_price,
                stop_loss_price,
                close,
            )
            exit_triggered = "stop_loss"
            # exit_price 用当日收盘价
            exit_price = close
            exit_date = bar_date
            break

        # 未触发：持续更新 exit_price 为当前 bar close（仍持仓）
        exit_price = close
        exit_date = bar_date

    # 计算收益率（比例口径：0.01 = 1%）
    return_pct = compute_return_pct(entry_price, exit_price)

    return (mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, limit_locked_dates, eval_date)
