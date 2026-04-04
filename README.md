# Trade（多交易员 Agent 交易系统）

本 workspace 包含一个面向“多交易员文章 + 交易记录”的多 Agent 交易研究与复盘系统。核心目标是先跑通日常闭环：

- 每个交易员对应一个独立 `TraderAgent`
- `DataAgent` 通过可插拔 skills 提供数据能力（接口可持续增加）
- `ManagerAgent` 负责盘前/盘后编排、汇总日报、盘后考核与复盘反馈写回
- 盘前/盘后时间、收益阈值等关键参数全部通过 config 配置

当前阶段不做自动下单，优先交付“建议/报告/复盘闭环”；在无 GPU 前提下使用第三方大语言模型 API（OpenAI/Anthropic 等）增强画像与总结。

## 目录

- `doc/`：需求、计划、任务清单（以此为准）
- `trade-strategy-ai/`：主要代码仓（FastAPI/CLI/agents/models）

## 文档入口

- `doc/需求.md`
- `doc/Plan.md`
- `doc/Project.md`
- `doc/TaskList.md`

## Phase 0 快速开始（闭环 MVP）

前置：需要 Python 3.11+（该仓库与代码语法要求）。

1）进入项目并生成配置：

```bash
cd trade-strategy-ai
python -m cli.main init-config
```

2）编辑配置（核心键）：

- `schedule.pre_market_time`
- `schedule.after_close_time`
- `evaluation.min_expected_return`
- `traders[].watchlist`
- `data.mock_prices`（Phase 0 使用 mock price 让闭环可跑）

可选（Phase 0.5：Persona Router MVP）：

```bash
python -m cli.main persona-init-sample --config config/app.yaml
```

然后把 `persona.enable` 改为 `true`（并确认 `persona.clusters_path` 指向生成的 clusters 文件）。

3）手动跑盘前与盘后：

```bash
python -m cli.main run-pre-market --config config/app.yaml
python -m cli.main run-after-close --config config/app.yaml
```

输出默认落在 `trade-strategy-ai/data/processed/phase0/`（由 `storage.output_dir` 配置）。
