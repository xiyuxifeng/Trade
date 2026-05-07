# `docs/bak/kaipan.md` 接口 -> Proposed-Plan 任务号 -> 建议字段映射

> 本表只保留与当前主线直接相关或中高价值的接口。  
> 优先服务三类能力：`hot_topics`、`topic_constituents`、`strong_symbols`，其次是盘后评估与解释层。

| 接口 | 主要用途 | 对应任务号 | 建议映射字段 |
|---|---|---|---|
| 市场情绪 | 市场状态与风险提示 | `NTL-S5-009` `NTL-S5-010` | `market_context.sentiment_score` `market_context.limit_up_count` `market_context.max_board_height` `market_context.drawdown_count` |
| 市场量能 | 市场状态与盘后解释 | `NTL-S5-009` `NTL-S5-010` | `market_context.turnover_estimate` `market_context.turnover_delta_pct` `market_context.turnover_3d_avg` |
| 指数数据 | 市场摘要与 regime 辅助 | `NTL-S2-016` `NTL-S5-009` | `market_context.indexes[]` `symbol` `name` `last_px` `increase_rate` `turnover` |
| 涨跌停数 | 市场广度与盘后总结 | `NTL-S5-009` `NTL-S5-010` | `market_context.limit_up_count` `market_context.limit_down_count` |
| 涨停表现 | 涨停生态强弱 | `NTL-S2-009` `NTL-S5-010` | `hot_topic_features.limit_up_total` `promotion_rate_2b` `break_rate` `yesterday_limit_up_return` |
| 涨停信息 | 题材证据、热点成分、强势标签 | `NTL-S2-009` `NTL-S2-010` `NTL-S2-011` | `topic_evidence[]` `topic_id` `topic_name` `stocks[]` `board_count` `turnover` |
| 涨停原因 | 热点分类与解释因子 | `NTL-S2-009` `NTL-S2-010` `NTL-S5-003` | `hot_topics[]` `reason` `stock_list[]` `topic_tags[]` `main_force_buy/sell` |
| 盘面亮点 | 强势标签、事件证据 | `NTL-S2-011` `NTL-S5-001` | `symbol_tags[]` `tag_name` `detail` `topic_id` `time` |
| 大幅回撤 | 风险过滤、盘后归因 | `NTL-S2-011` `NTL-S5-001` `NTL-S5-010` | `risk_flags[]` `symbol` `drawdown_pct` `topic_tags` |
| 板块涨停历史 | 主题强持续性分析 | `NTL-S2-009` `NTL-S6-009` | `topic_history[]` `topic_id` `date` `limit_up_num` `stocks[]` |
| 板块强度 | 概念/主题热点排序 | `NTL-S2-009` `NTL-S2-013` | `hot_topics.concept[]` `topic_id` `topic_name` `score` `increase_pct` `speed_pct` `turnover` `net_inflow` |
| 行业涨幅 | 行业热点排序 | `NTL-S2-009` `NTL-S2-013` | `hot_topics.industry[]` `topic_id` `topic_name` `score` `increase_pct` `turnover` |
| 权重表现 | 市场解释层 | `NTL-S5-009` | `market_context.weighted_sector_up[]` `weighted_sector_down[]` |
| 板块竞价 | 盘前热点异动 | `NTL-S2-009` `NTL-S4-007` | `pre_market_topics[]` `topic_id` `topic_name` `bid_volume_ratio` `abnormal_amount` `main_force_net` |
| 板块内股票竞价 | 盘前强势标的候选 | `NTL-S2-011` `NTL-S4-007` | `strong_symbols[]` `symbol` `bid_ratio` `bid_amount` `bid_change_pct` `bid_turnover` `topic_tags` |
| 龙虎榜列表 | 盘后风格证据、解释层 | `NTL-S5-001` `NTL-S5-003` | `postmarket_flow[]` `symbol` `net_buy` `join_num` `turnover` `amplitude` `lhb_count` |
| 龙虎榜详细信息 | 单票复盘证据 | `NTL-S5-001` `NTL-S5-003` | `evidence_refs.lhb_detail` `buy_seats[]` `sell_seats[]` `up_reasons[]` |
| 游资动向 | 风格/席位解释层 | `NTL-S5-003` `NTL-S7-001` | `capital_actor_flows[]` `actor_id` `actor_name` `symbols[]` `money` |
| 游资席位信息 | 解释层知识库 | `NTL-S5-003` | `capital_actor_profile` `short_name` `info` `business_list[]` |
| 竞价总体信息 | 盘前市场态 | `NTL-S4-007` `NTL-S5-009` | `pre_market_context.bid_amount_today` `bid_up_count` `bid_down_count` |
| 竞价数量统计 | 盘前广度特征 | `NTL-S4-007` | `pre_market_stats.limit_buy_count` `hot_count` `main_force_positive_count` `smash_count` |
| 竞价列表 | 盘前强势池候选 | `NTL-S2-011` `NTL-S4-007` | `strong_symbols[]` `symbol` `rt_change_pct` `bid_net` `bid_turnover` `topic_tags` `float_market_cap` |
| 尾盘抢筹 | 盘后补充证据 | `NTL-S5-001` `NTL-S5-003` | `late_session_accumulation[]` `symbol` `grab_amount` `grab_ratio` `main_force_net` |
| 股票所属板块 | 成分映射与解释层 | `NTL-S2-010` | `topic_constituents.by_symbol[]` `topic_id` `topic_name` `topic_change_pct` |
| 股票所属板块（V2） | 成分映射与龙头信息 | `NTL-S2-010` `NTL-S4-008` | `topic_constituents.by_symbol[]` `topic_id` `topic_name` `leader_symbol` `leader_name` `leader_change_pct` |
| 百日新高 | 趋势型候选池 | `NTL-S2-011` `NTL-S6-010` | `strong_symbols[]` `symbol` `group_id` `group_name` `trend_tag=new_high_100d` |
| 区间统计-按板块 | 热点历史评分与回测特征 | `NTL-S2-009` `NTL-S6-009` | `topic_interval_stats[]` `topic_id` `return_pct` `net_inflow_days` `strength_score` |
| 区间统计-按股票 | 强势股筛选与回测特征 | `NTL-S2-011` `NTL-S6-010` | `strong_symbols[]` `symbol` `return_pct` `net_inflow` `turnover_ratio` `topic_tags` `net_inflow_days` |
| 复盘榜 | fallback 强势候选源 | `NTL-S2-011` | `strong_symbols.seed_symbols[]` |
| 最强风口 | 直接强势池上游 | `NTL-S2-011` `NTL-S2-015` | `strong_symbols[]` `symbol` `strength_score` `change_pct` `turnover` `main_force_buy` `main_force_sell` `topic_tags` |
| 股票风口 | 单票题材标签与解释 | `NTL-S2-010` `NTL-S5-001` | `symbol_topic_features[]` `fengkou_concepts` `actor_tag` `topic_tags` |
| 概念风口 | 概念热点强度 | `NTL-S2-009` `NTL-S2-013` | `hot_topics.concept[]` `topic_name` `score` |
| 题材详情 | 主题成分与题材知识库 | `NTL-S2-010` `NTL-S3-005` | `topic_constituents[]` `theme_id` `theme_name` `brief_intro` `stocks[]` `tags[]` `hot_num` |
| 题材库搜索 | 题材检索辅助 | `NTL-S2-010` | `theme_search_results[]` `theme_id` `theme_name` `sub_theme_ids[]` |
| 大盘直播 | 盘后解释与事件证据 | `NTL-S5-001` `NTL-S5-003` | `market_live_events[]` `time` `comment` `stock_refs[]` |
| 新高趋势 | 趋势环境统计 | `NTL-S6-009` | `market_trend_context.new_high_series[]` |
| 节假日 | 交易日历辅助 | `NTL-S7-006` | `trading_calendar.holidays[]` |
| 最新消息 | 事件驱动证据层 | `NTL-S5-001` `NTL-S5-003` | `news_events[]` `time` `content` `stock_id` `stock_name` |

## 首批推荐接入接口

1. `板块强度`
2. `行业涨幅`
3. `概念风口`
4. `题材详情`
5. `股票所属板块（V2）`
6. `最强风口`
7. `区间统计-按股票`
8. `竞价列表`
9. `涨停原因`

## 首批建议落地字段族

- `hot_topics.concept`
- `hot_topics.industry`
- `topic_constituents`
- `strong_symbols`
- `market_context`
- `evidence_refs`
