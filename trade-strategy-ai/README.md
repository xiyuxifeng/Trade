# trade-strategy-ai

面向“多交易员文章 + 交易记录”的多 Agent 交易研究与复盘系统。

Phase 0-3 的核心闭环：
- 每个交易员对应一个独立 `TraderAgent`
- `DataAgent` 通过可插拔 skills 提供数据能力（接口可持续增加）
- `ManagerAgent` 负责盘前/盘后编排、汇总日报、盘后考核与复盘反馈写回
- 盘前/盘后时间、收益阈值等关键参数全部通过 config 配置

当前优先：不做自动下单，只做建议/报告/复盘闭环；无 GPU 场景通过第三方大模型 API（OpenAI/Anthropic 等）增强画像与总结。

## Phase 0 快速开始

前置：Python 3.11+。

1）生成配置：

```bash
python -m cli.main init-config
```

2）手动触发盘前/盘后：

```bash
python -m cli.main run-pre-market --config config/app.yaml
python -m cli.main run-after-close --config config/app.yaml
```

输出默认目录：`data/processed/phase0/`（由 `storage.output_dir` 配置）。

## 配置键（节选）

- `schedule.enable`
- `schedule.pre_market_time`
- `schedule.after_close_time`
- `evaluation.min_expected_return`
- `evaluation.loss_trigger`
- `traders[].watchlist`
- `data.mock_prices`（Phase 0 演示用，后续可接入 akshare/tushare 等）

文档入口：workspace 根目录 `doc/`。
