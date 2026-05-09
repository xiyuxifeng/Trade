# 2026-05-09 WEB-S6-001 Job Center Enhancement Plan

> 目标：在现有 Jobs 页面基础上补齐 Stage 6 任务中心增强能力，并把剩余工作拆成可追踪、可验证、可交接的子步骤。

## 背景

当前 `WEB-S6-001` 已具备基础列表、过滤、详情抽屉、日志浏览和取消能力，但仍缺少两项 Stage 6 验收关键点：

- 产物关联需要从原始 JSON 变成可读、可跳转的引用视图。
- 重跑入口需要能以当前 Job 的参数重新创建同类任务。

## 范围

### 直接修改

- `web/src/pages/jobs/index.tsx`
- `web/src/lib/api/jobs.ts`
- `web/src/types/jobs.ts`

### 视情况联动

- `web/src/pages/artifacts/index.tsx`

## 追踪子项

- [ ] 补充 Job 创建 API，支持从 Jobs 页面触发重跑。
- [ ] 在 Job 详情抽屉里把 `artifacts` 渲染成可读引用。
- [ ] 给 Job 产物提供跳转到 Artifacts Center 的入口。
- [ ] 如需要，补充 `jobId` 过滤能力，让产物中心能直接定位某个 Job 的产物。
- [ ] 运行前端验证命令，确认改动不破坏现有 Jobs / Artifacts 页面。

## 验收标准

- Jobs 页面可以对当前 Job 重新发起同类任务。
- 任务详情抽屉里能够直接看见产物引用，不再只展示原始 JSON。
- 产物可以通过 UI 继续深入查看。
- 相关改动完成后，`docs/Web-TaskList.md`、`daily-sessions`、`daily-report` 的状态能继续顺着这一计划推进。

## 备注

- 这里的“重跑”仅限于复用当前 Job 的 `job_type` 和 `params`，不新增新的调度模型。
- 这份计划只追踪 `WEB-S6-001`，不扩展到其他 Stage。
