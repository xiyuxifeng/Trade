# Config Path to Profile Migration

本文件说明 `NW-V2-S1-002` 的迁移工具边界。

## 目标

- 将现有 `config_path` 迁移为正式 `Profile` 记录。
- 提供脱敏预览，便于用户在保存前确认配置内容。
- 提供缺失项检查，帮助识别旧配置中仍依赖默认值的部分。
- 保留 `config_path` 兼容入口，但不再把它当作长期事实源。

## 入口

当前迁移入口为内部脚本：

```bash
python -m scripts.profile_migration --config config/app.yaml --profile-id app
```

可选参数：

- `--dry-run`：仅预览，不保存。
- `--profile-id`：目标 Profile ID，默认使用配置文件名。
- `--name`：目标 Profile 显示名称。
- `--environment`：目标 Profile 环境标识。
- `--created-by`：迁移创建者。

## 迁移流程

1. 读取原始 `config_path`。
2. 生成脱敏预览。
3. 检查核心分区是否缺失。
4. 保存为正式 `Profile`。
5. 生成 Profile snapshot，供后续 Job / 审计回溯。

## 缺失项检查

工具会检查以下核心分区是否出现在原始配置中：

- `database`
- `storage`
- `llm`
- `crawl`
- `data`
- `traders`

如果某些分区缺失，迁移仍可继续，但结果会标记为 `draft`，提示需要后续补齐。

## 兼容边界

`config_path` 仍然保留，原因只有一个：

- 旧配置文件的导入和迁移需要它。

它不应再作为新的正式运行事实源。后续正式运行入口应逐步转向 `Profile`。

## 退役条件

当以下条件同时满足时，可以考虑停用 `config_path` 的正式入口：

- 所有主要 UI 流程都已改为 `Profile`。
- Job / Workflow / UI 运行都以 `Profile` 作为 canonical 输入。
- 兼容迁移脚本仍保留，但仅作为历史导入入口。
