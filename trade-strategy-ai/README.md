# trade-strategy-ai

## 系统介绍

trade-strategy-ai 是一个面向“多交易员文章 + 交易记录”的多 Agent 交易研究与复盘系统。

## 项目目标

1. 支持多交易员独立分析与复盘。
2. 通过多智能体协作，实现自动化数据处理、策略分析与报告生成。
3. 强化盘前/盘后总结、考核与反馈闭环。
4. 兼容第三方大模型 API，提升智能分析能力。

## 配置键（节选）

- `schedule.enable`
- `schedule.pre_market_time`
- `schedule.after_close_time`
- `evaluation.min_expected_return`
- `evaluation.loss_trigger`
- `traders[].watchlist`
- `data.mock_prices`（Phase 0 演示用，后续可接入 akshare/tushare 等）

文档入口：workspace 根目录 `doc/`。
