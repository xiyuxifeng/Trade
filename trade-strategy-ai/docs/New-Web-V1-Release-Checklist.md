# New-Web V1 Release Checklist

> V1 发布前内部检查清单。
> 这份清单用于确认 Web、E2E、TaskList 和用户文档已经收口。

## 1. 发布前提

- `NW-V1-S4-001` 已完成。
- `NW-V1-S4-002` 已完成。
- `UI-V1-011` 已完成。
- `article_pipeline` 已收口到 canonical Web/API 入口。
- `Job Detail` 已接入步骤时间线、产物面和配置快照面。

## 2. 自动化检查

按以下顺序执行：

```bash
python -m pytest tests/e2e/test_e2e_runner.py tests/e2e/test_web_acceptance.py tests/e2e/test_article_pipeline_v1.py -q
PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH ./node_modules/.bin/vitest run src/pages/jobs/JobDetailPage.test.tsx src/pages/jobs/index.test.tsx src/features/workflows/workflow-parameter-form.test.tsx src/pages/articles/index.test.tsx src/components/profiles/config-snapshot-panel.test.tsx src/components/artifacts/artifact-panel.test.tsx src/pages/reports/index.test.tsx src/features/reports/report-center.test.tsx src/app/route-registry.test.ts
git diff --check
```

检查点：

- `test_article_pipeline_v1` 默认跳过真实 CLI 回归，不应因此误判失败。
- 如果需要验证真实 CLI gate，必须显式设置 `RUN_V1_E2E=1`。

## 3. 手工验收

### 3.1 `article_pipeline`

- 打开 `/articles`。
- 提交 `article_pipeline`。
- 确认能跳转到 `任务详情`。

### 3.2 `任务`

- 打开 `/jobs`。
- 确认能看到 loading、empty、error 和 permission denied 的可解释状态。
- 打开一个成功任务和一个失败任务，确认详情页内容一致。

### 3.3 `任务详情`

- 确认能看到步骤时间线。
- 确认能看到产物面板。
- 确认能看到配置快照面板。
- 确认失败任务有错误信息和回退提示。

### 3.4 `产物`

- 打开 `/artifacts`。
- 确认能看到产物详情和下载入口。
- 确认缺失产物不会暴露服务器绝对路径。

### 3.5 `设置`

- 打开 `/settings`。
- 确认配置预览、保存和备份/恢复路径正常。
- 确认敏感配置保持脱敏。

## 4. 文档一致性检查

- 文档中的页面名称必须与当前 UI 一致：
  - `任务`
  - `任务详情`
  - `引导式操作`
  - `产物中心`
  - `报告中心`
  - `配置中心`
- 文档中的按钮名称必须与当前 UI 一致：
  - `运行 article_pipeline`
  - `查看详情`
  - `重新运行任务`
  - `取消任务`
  - `下载`
  - `保存配置`

## 5. 发布判定

满足以下条件时，V1 可以对外交付：

- 自动化检查通过。
- 手工验收路径可走通。
- TaskList 状态一致。
- 用户手册和 release checklist 已更新。
- 没有把 V2/V3 能力写成 V1 阻断项。

如果以上任一项不满足，不能把 V1 标成发布完成。
