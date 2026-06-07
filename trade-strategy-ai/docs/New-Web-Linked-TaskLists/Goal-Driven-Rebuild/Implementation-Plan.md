# Goal-Driven Rebuild 实施顺序计划

> 本计划对应 [TaskList.md](./TaskList.md)。
>
> 目标只有一个：把项目重构成用户打开 Web 后就能清楚知道怎么用、每一步做什么、最后得到什么结果的产品。
>
> 执行顺序必须严格遵循：
>
> `GD-R1 -> GD-R2 -> GD-R3 -> GD-R4 -> GD-R5`

---

## 1. 总体执行原则

1. 先收口入口，再收口数据，再收口 Job，再收口页面，最后清理旧东西。
2. 每一步都必须能独立验证，不要等所有步骤都做完再看结果。
3. 任何新改动都必须服务于主链路：

```text
博客文章 -> 规则提取 -> 回测验证 -> 交易员画像 -> 盘前预测 -> 盘后复盘
```

4. 允许删除、合并、替换旧页面、旧逻辑、旧入口，但不得新增新的对外主概念。
5. 所有任务都要优先保留用户可理解性，而不是优先保留现有实现形态。

---

## 2. GD-R1 统一用户主流程和 Web 入口

### 2.1 目标

- 收口首页和主导航。
- 确定一级入口和核心子入口。
- 保留 `Job List`、`Dashboard`、`配置与管理`，但明确分层。
- 让用户一进入 Web 就知道从哪里开始。

### 2.2 主要要改的文件

#### 导航与路由定义

- `web/src/app/route-registry.ts`
- `web/src/app/navigation.ts`
- `web/src/app/router.tsx`
- `web/src/components/layout/sidebar.tsx`
- `web/src/layouts/dashboard-layout.tsx`

#### 首页和概览

- `web/src/routes/overview.tsx`
- `web/src/components/dashboard/dashboard-status-summary.tsx`
- `web/src/components/dashboard/dashboard-recent-jobs.tsx`
- `web/src/components/dashboard/dashboard-recent-artifacts.tsx`
- `web/src/components/dashboard/dashboard-alert-strip.tsx`

#### 一级入口页面

- `web/src/pages/articles/*`
- `web/src/pages/backtest/*`
- `web/src/pages/market/*`
- `web/src/pages/jobs/*`
- `web/src/pages/profiles/*`
- `web/src/pages/system/*`
- `web/src/pages/artifacts/*`

#### 兼容入口和重定向

- `web/src/app/router.tsx`

### 2.3 先后顺序

1. 先改 `route-registry.ts` 和 `navigation.ts`，把可见入口顺序和名称先定下来。
2. 再改 `router.tsx`，把 `dashboard`、`jobs`、`articles`、`market`、`backtest`、`profiles`、`system`、`artifacts` 的主路径明确下来。
3. 再改 `sidebar.tsx` 和 `dashboard-layout.tsx`，保证侧边栏和布局呈现一致。
4. 最后改 `overview.tsx` 和 dashboard 相关组件，把首页变成清晰的概览，而不是旧技术入口集合。

### 2.4 验收点

- 用户打开首页后，能明确看到主流程入口。
- `Job List`、`Dashboard`、`配置与管理` 的层级关系清楚。
- `workflows/*`、`admin/*`、`settings`、`alerts` 不再作为主导航入口出现。
- 一级入口命名和文案符合产品叙事，不再要求用户先懂内部实现名词。

---

## 3. GD-R2 收口市场数据链路，建立单一市场上下文快照

### 3.1 目标

- 统一市场数据流向。
- 让盘前、盘后、回测消费同一套市场上下文。
- 消除 `kaipan-fetch` / `kaipan-normalize` / `snapshot-build` 的重复职责。

### 3.2 主要要改的文件

#### Kaipan / 市场数据链路

- `src/services/kaipan_service.py`
- `api/routers/ui/kaipan.py`
- `src/providers/kaipan_normalizer.py`
- `src/services/snapshot_service.py`
- `src/services/market_snapshot_service.py`
- `src/services/market_snapshot_builders.py`
- `src/services/market_data_storage_service.py`
- `src/market_universe/snapshot_service.py`
- `src/pipeline/tasks/snapshot_tasks.py`
- `src/pipelines/market_data_pipeline_spec.py`
- `src/pipeline/completion.py`

#### 市场上下文与回放消费

- `src/backtest/snapshot_loader.py`
- `src/services/market_snapshot_query_service.py`
- `src/services/market_regime_feature_service.py`
- `src/services/market_regime_service.py`
- `src/services/backtest_service.py`

#### 市场页面

- `web/src/pages/market/*`
- `web/src/features/market-browser/*`
- `web/src/features/market-datasets/*`
- `web/src/features/market-workspace/*`

### 3.3 先后顺序

1. 先收口市场上下文快照的数据契约，明确唯一事实源。
2. 再拆分 `kaipan-fetch` 和 `kaipan-normalize` 的职责，去掉重复抓取和重复标准化。
3. 再让 `snapshot-build` 明确只消费标准化产物，不再绕回 raw/provider。
4. 再统一 `MarketUniverse` 和 `Market Snapshot` 的对外叙事，收口成“市场上下文快照”。
5. 最后让盘前、盘后、回测只消费这套统一上下文。

### 3.4 验收点

- `kaipan-fetch` 不再承担标准化职责。
- `kaipan-normalize` 不再重新抓取。
- `snapshot-build` 不再绕回 raw/provider。
- 市场上下文快照成为盘前、盘后、回测的统一输入。
- Web 端不再要求用户同时理解 `MarketUniverse` 和 `Market Snapshot`。

---

## 4. GD-R3 重构 Job 语义和进度展示

### 4.1 目标

- 让 Job 只做调度、状态记录和结果记录。
- 让进度条和终态明确分离。
- 让用户能提交、查看、暂停、恢复、取消和重试 Job。
- 让用户能看到成功、失败、进行中等统计信息。

### 4.2 主要要改的文件

#### Job 后端

- `src/services/job_service.py`
- `src/services/job_runner.py`
- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/artifact_service.py`
- `src/services/audit_service.py`

#### Job API

- `api/routers/ui/jobs.py`
- `api/routers/ui/artifacts.py`

#### Job 页面

- `web/src/pages/jobs/*`
- `web/src/features/jobs/*`
- `web/src/features/artifacts/*`

#### 相关提交入口

- `web/src/features/market-workspace/*`
- `web/src/features/strategy-workspace/*`
- `web/src/features/articles/*`

### 4.3 先后顺序

1. 先统一 Job 状态机和统计口径。
2. 再实现 Job 详情页需要的状态、日志、结果、统计信息。
3. 再实现暂停 / 恢复 / 取消 / 重新执行的操作语义。
4. 再补 Job 提交时的 loading / success / failure 反馈。
5. 最后让所有相关提交入口跳转到统一的 Job 中心。

### 4.4 验收点

- 100% 进度不等于成功。
- Job 详情页能展示当前状态、步骤进度、成功数、失败数、进行中数。
- Job 支持暂停、恢复、取消、重新执行，并且状态流转可追踪。
- 用户在提交任务后能看到明确 loading 和成功/失败提示。

---

## 5. GD-R4 重构 Web 页面与文案

### 5.1 目标

- 让 Web 端像一个可直接使用的产品，而不是技术入口集合。
- 页面文案、按钮文案、空状态、错误状态统一表达。
- 让用户看到每一步的作用和结果，而不是内部实现名词。

### 5.2 主要要改的文件

#### 页面与路由

- `web/src/routes/overview.tsx`
- `web/src/pages/articles/*`
- `web/src/pages/backtest/*`
- `web/src/pages/market/*`
- `web/src/pages/jobs/*`
- `web/src/pages/profiles/*`
- `web/src/pages/system/*`
- `web/src/pages/artifacts/*`

#### 页面组件与空状态 / 状态文案

- `web/src/features/dashboard/*`
- `web/src/features/market-browser/*`
- `web/src/features/market-datasets/*`
- `web/src/features/market-workspace/*`
- `web/src/features/articles/*`
- `web/src/features/jobs/*`
- `web/src/features/reports/*`

#### 文案和导航文档

- `docs/New-Web-Linked-TaskLists/Goal-Driven-Rebuild/Product-Usage-Flow.md`
- `docs/New-Web-Linked-TaskLists/Goal-Driven-Rebuild/Web-Navigation-and-Copy.md`

### 5.3 先后顺序

1. 先改首页和导航文案，让用户进入后知道先看什么。
2. 再改主业务页面标题、说明、按钮、空状态、错误状态。
3. 再改 Job 页面和市场上下文页面的状态表达。
4. 最后统一所有入口的术语，去掉内部实现名词。

### 5.4 验收点

- 用户能直接通过页面文案理解每一步做什么。
- 页面不再默认暴露内部实现名词。
- 首页、任务中心、主业务页、市场页的文案风格统一。
- 空状态和错误状态能告诉用户下一步怎么做。

---

## 6. GD-R5 清理冗余实现并完成最终验收

### 6.1 目标

- 清理不再服务主目标的冗余页面、冗余数据路径、冗余概念。
- 验证最终用户链路完整可用。
- 确认重构后的实现不会再次漂移。

### 6.2 主要要改的文件

#### 兼容入口和重定向

- `web/src/app/router.tsx`
- `web/src/app/navigation.ts`
- `web/src/app/route-registry.ts`

#### 冗余页面和旧入口

- `web/src/pages/workflows/*`
- `web/src/pages/alerts/*`
- `web/src/pages/dashboard/*` 中不再需要的旧块
- `web/src/pages/market/*` 中不再需要的旧块
- `web/src/pages/articles/*` 中不再需要的维护页

#### 文档和 TaskList

- `docs/New-Web-Linked-TaskLists/Goal-Driven-Rebuild/*`
- 需要同步更新所有会引用旧入口的文档

### 6.3 先后顺序

1. 先确认新主入口和新流程已经完全可用。
2. 再关闭或重定向旧兼容入口。
3. 再清理不再服务主目标的旧页面和旧导航。
4. 最后做一次端到端验收和文档同步。

### 6.4 验收点

- 用户从 Web 可以完整走通主链路。
- 所有入口和说明都围绕最终目标。
- 不再保留会持续制造混淆的并行主概念。
- 文档、TaskList、页面入口和数据契约一致。

---

## 7. 收尾规则

执行完 `GD-R5` 后，必须检查以下内容：

1. 主入口是否只剩一套。
2. 市场数据是否只剩一套事实源。
3. Job 是否已经变成统一的任务中心语义。
4. 页面是否已经完全按用户目标组织。
5. 旧兼容入口是否已经退役或明确下沉。

如果其中任意一项没有满足，就不能视为重构完成。
