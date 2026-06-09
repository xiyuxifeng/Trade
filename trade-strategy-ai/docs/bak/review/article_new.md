# article_new.md：文章工作台与 Article Pipeline 改造说明

## 1. 背景与目标

当前 sidebar 中保留一级入口“文章”，但文章页面实际更接近 `Article Pipeline` 技术入口，主要展示 Pipeline 概览、schema、config_path/Profile 表单、最近 pipeline jobs 和失败定位说明。

后续目标是：

- sidebar 入口仍然叫“文章”。
- 用户进入 `/articles` 后先看到“文章工作台”。
- 工作台提供各个文章子功能入口。
- 子功能页面均可返回工作台。
- 移除 Web 对 `config_path` 的输入依赖，统一使用 Profile。
- DuckDB 导出相关代码保留，但页面不提供入口，仅为后续预留。
- 高级维护放到文章模块内，其中Bool类型使用 Checkbox 表达。
- 最终移除sidebar 工作流中的`数据 Pipeline`入口，避免重复和混淆。

本改造只覆盖文章数据 Pipeline 相关功能，不处理其他 workflow 功能。

---

## 2. 明确保留与移除边界

### 2.1 保留

- sidebar 一级菜单：`文章`。
- 后端已有文章 Pipeline 能力：
  - crawl
  - clean
  - validate
  - store
  - process
  - export 代码
- 现有 Job Detail 作为任务执行状态查看入口。
- PipelineService / Job Runner 相关服务层能力。
- DuckDB export 代码与底层函数，为后续分析导出能力预留。

### 2.2 页面上移除或隐藏

- 普通页面不再显示 `config_path` 输入。
- 普通页面不再显示 DuckDB 导出入口。
- 普通用户入口不直接暴露底层 Pipeline schema。
- 不再把文章入口设计成单一“大 Pipeline 表单”。

### 2.3 不在本阶段处理

- 不删除 DuckDB 导出代码。
- 不删除其他 workflow 功能。
- 不做市场数据 Pipeline 的迁移。
- 不重构所有任务执行底层，只围绕文章入口和参数模型进行整理。

---

## 3. 目标信息架构

sidebar 仍然保持：

```text
业务工作台
└─ 文章 -> /articles
```

`/articles` 进入后是文章工作台，不直接进入具体 Pipeline 表单。

推荐结构：

```text
/articles
└─ 文章工作台
   ├─ 抓取与处理
   ├─ 文章列表
   ├─ 数据质量
   ├─ 最近任务
   ├─ 处理结果
   └─ 高级维护
```

子功能推荐路由：

```text
/articles                    文章工作台
/articles/run                抓取与处理
/articles/list               文章列表
/articles/quality            数据质量
/articles/jobs               最近文章任务
/articles/results            处理结果
/articles/maintenance        高级维护
```

每个子功能页面顶部需要提供：

```text
返回文章工作台
```

---

## 4. 文章工作台页面设计

### 4.1 工作台首页

首页目标是让用户选择“我要做什么”，不是直接填写底层 Pipeline 参数。

建议卡片：

```text
文章工作台
├─ 抓取与处理
│  └─ 抓取新文章、抓取并处理、处理已有文章
├─ 文章列表
│  └─ 查看已抓取文章、筛选作者/来源/处理状态
├─ 数据质量
│  └─ 查看 clean / validate 结果、不可抽取文章、错误和警告
├─ 最近任务
│  └─ 查看 article pipeline 相关 Job
├─ 处理结果
│  └─ 查看 metadata、概念、股票标的、规则抽取结果
└─ 高级维护
   └─ 从指定步骤重跑、force、skip crawl、use db、失败任务修复
```

首页顶部建议展示摘要：

```text
文章总数
待处理文章数
最近抓取时间
最近处理时间
失败任务数
metadata 覆盖率
```

如果当前没有对应统计 API，可以先保留占位或从最近 Job 中展示有限状态，不阻塞页面结构改造。

---

## 5. 子功能设计

### 5.1 抓取与处理

这是普通用户最常用入口。

推荐操作：

```text
抓取新文章
抓取并处理
处理已有文章
```

默认推荐主按钮：

```text
抓取并处理
```

它对应：

```text
crawl -> clean -> validate -> store -> process
```

DuckDB export 不包含在默认流程中。

参数统一使用 Profile：

```text
Profile               必选
source / trader        可选
max_articles           可选
mode                   可选：测试 / 增量 / 处理已有
```

不再提供 `config_path` 输入框。

### 5.2 文章列表

用于查看 Pipeline 的业务结果，而不是技术日志。

建议字段：

```text
标题
作者 / trader
来源 source
发布时间
抓取时间
是否可抽取
是否已入库
是否已抽取 metadata
关联股票 / 概念
处理状态
```

建议筛选：

```text
Profile
作者 / trader
source
日期范围
是否已抽取 metadata
是否可抽取
是否失败
是否包含交易标的
```

### 5.3 数据质量

对应 clean / validate 输出。

展示内容：

```text
抓取文章数
清洗文章数
评论总数
保留评论数
过滤评论数
重复文章数
校验 errors
校验 warnings
不可抽取文章数
```

可从 Job result / artifacts / validation_report 中读取。

### 5.4 最近任务

展示文章相关任务，而不是所有系统任务。

建议过滤任务类型：

```text
article-crawl
article-pipeline
article-process
article-maintenance
```

如果后端暂时仍只有 `pipeline-run`，页面可先过滤 article_pipeline 相关参数或 workflow id。

每条任务展示：

```text
任务 ID
操作类型
Profile
状态
当前阶段
创建时间
耗时
打开 Job Detail
```

### 5.5 处理结果

展示文章处理后的结构化结果。

建议内容：

```text
metadata 抽取结果
extracted_concepts
trading_symbols
strategy_rules
preconditions
comment_insights
sentiment_score
confidence_score
```

该页面用于验收文章是否已成为策略/规则/画像可消费的数据。

### 5.6 高级维护

高级维护可以放在文章模块内，但需要与普通操作明显分离。

入口建议放在工作台底部，并标记：

```text
高级维护
仅用于失败恢复、重跑、任务修复和数据修复。
```

权限建议：

```text
viewer：不可见或只读
operator：可执行非危险维护
admin：可执行危险维护
```

---

## 6. 高级维护参数设计

### 6.1 重跑选项使用 Checkbox

用户明确要求“重跑选项做成 Checkbox”。建议如下：

```text
重跑选项
[ ] 强制重跑 force
[ ] 跳过抓取 skip_crawl
[ ] 使用数据库原始文章 use_db
[ ] 重建 pending tasks
[ ] 重试 failed tasks
```

说明：

- `force`：忽略已有中间结果，重新执行相关步骤。
- `skip_crawl`：不重新抓取，只处理已有文章。
- `use_db`：从 raw_articles / DB 模式读取原始文章。
- `rebuild pending tasks`：从数据库重建待处理任务。
- `retry failed tasks`：重试失败任务。

### 6.2 从指定步骤恢复

`from_step` 更适合用下拉选择，而不是 Checkbox，因为它是互斥值。

建议：

```text
从指定步骤开始
- 不指定，完整执行
- crawl
- clean
- validate
- store
- process
```

不在页面提供 `export` 选项，因为 DuckDB 导出本阶段不提供页面入口。

### 6.3 危险操作

危险操作必须单独分组，并二次确认。

```text
危险操作
[ ] 清理中间文件 cleanup
```

执行前必须提示会影响：

```text
articles.jsonl
*.articles.cleaned.jsonl
*.validated.jsonl
pending_tasks.jsonl
failed_tasks.jsonl
llm_checkpoint.jsonl
```

建议 admin 权限才可操作。

---

## 7. DuckDB 导出处理策略

### 7.1 本阶段要求

- 保留 DuckDB 导出代码。
- 保留 `run_export_task` 等底层能力。
- 不在文章页面提供 DuckDB 导出按钮。
- 不把 DuckDB export 放入普通用户默认流程。
- 不在高级维护页面暴露 DuckDB export 入口。

### 7.2 Pipeline 执行策略

推荐将默认文章 Pipeline 视为：

```text
crawl -> clean -> validate -> store -> process
```

DuckDB export 作为预留能力：

```text
export_to_duckdb：reserved / future
```

如果当前后端 `run_pipeline` 固定包含 export，需要实现时评估两种方案：

1. 短期兼容：后端仍执行 export，但页面不显示、不强调、不提供单独入口。
2. 推荐方案：新增参数或新 job type，使 Web 默认不执行 export。

推荐最终方案是第二种，但需要小心不破坏 CLI 或已有测试。

---

## 8. config_path 移除与 Profile 统一

### 8.1 页面层

移除：

```text
config_path / Profile 参数类型切换
config_path 输入框
config_path 相关表单错误展示
```

改为：

```text
Profile 选择器
```

Profile 应支持：

```text
选择已有 Profile
显示 Profile 当前状态
显示 Profile 是否可用
链接到配置管理编辑 Profile
```

### 8.2 API 请求层

当前请求参数应从：

```json
{
  "config_path": "config/articles.yaml"
}
```

调整为：

```json
{
  "profile": "default-profile"
}
```

或更明确：

```json
{
  "profile_id": "default-profile"
}
```

建议统一使用 `profile_id`，如果现有后端只接受 `profile`，可以先兼容，然后逐步收敛。

### 8.3 后端服务层

后端需要通过 Profile 解析运行配置，不再要求 Web 传入 config_path。

建议职责：

```text
Web：只传 profile_id 和运行参数
API：校验权限与 Profile 是否存在
Service：把 Profile 解析成 AppConfig / 运行上下文
Pipeline：只消费已解析配置
```

---

## 9. 修改范围

### 9.1 Web 路由

涉及：

```text
web/src/app/route-registry.ts
web/src/app/navigation.ts
web/src/pages/articles/*
```

修改内容：

- sidebar 仍保留 `文章 -> /articles`。
- `/articles` 调整为文章工作台。
- 新增或规划子路由。
- 保证子功能页面可返回 `/articles`。
- route registry 中补充文章子路由。

### 9.2 文章页面组件

涉及：

```text
web/src/pages/articles/ArticlePipelinePage.tsx
```

建议处理：

- 重命名或重构为 `ArticleWorkspacePage`。
- 原 Pipeline 技术信息下沉到高级信息区或移除。
- 移除 config_path/Profile 切换。
- 改为 Profile-only 表单。
- 新增工作台卡片入口。
- 新增高级维护区域。
- 重跑选项使用 Checkbox。
- DuckDB export 不显示入口。

### 9.3 API client

涉及：

```text
web/src/lib/api/pipelines.ts
web/src/lib/api/jobs.ts
web/src/types/pipeline.ts
```

修改内容：

- run article pipeline 请求改为 Profile-only。
- 类型中移除或弱化 config_path。
- 新增高级维护请求参数类型。
- 如需支持子功能，补充 article stats / article quality / article jobs API client。

### 9.4 后端 API

可能涉及：

```text
api routers / workflows / pipelines / jobs
src/services/pipeline_service.py
src/services/workflow_service.py
src/services/job_runner.py
```

修改内容：

- Web 请求不再接受 config_path 作为正式参数。
- 使用 profile_id 解析配置。
- Job params 记录 Profile 与操作类型。
- 支持高级维护参数：force、skip_crawl、use_db、from_step、rebuild_pending、retry_failed。
- DuckDB export 代码保留但不暴露 Web 入口。

### 9.5 测试

涉及：

```text
web/src/components/layout/sidebar.test.tsx
web/src/app/navigation.test.ts
web/src/pages/articles/*.test.tsx
backend pipeline/job/service tests
```

测试重点：

- sidebar 仍显示“文章”。
- `/articles` 能显示工作台入口。
- config_path 输入不再出现。
- Profile 是必选输入。
- 高级维护 Checkbox 能正确组成请求参数。
- DuckDB 导出按钮/入口不出现在页面。
- 子功能页面有返回工作台入口。
- 提交任务后仍跳转 Job Detail。

---

## 10. 推荐实现步骤

### Step 1：改造文章入口为工作台

- 保留 sidebar `文章`。
- `/articles` 页面展示工作台卡片。
- 原有运行表单先迁移为“抓取与处理”卡片入口。
- 添加“返回文章工作台”组件。

### Step 2：Profile-only 表单

- 移除 config_path/Profile 切换。
- 增加 Profile 选择器。
- 请求参数统一为 profile/profile_id。
- 表单校验只校验 Profile。

### Step 3：常用操作拆分

实现三个普通操作：

```text
抓取新文章
抓取并处理
处理已有文章
```

每个操作创建 Job，并跳转 Job Detail。

### Step 4：高级维护区域

- 增加高级维护页面或折叠区。
- 重跑选项使用 Checkbox。
- `from_step` 使用 Select。
- 危险操作增加二次确认。
- 按权限显示操作。

### Step 5：隐藏 DuckDB 导出入口

- 不显示 DuckDB export 按钮。
- 不在 from_step 里显示 export。
- 不在高级维护里显示 export。
- 底层代码保持不删。

### Step 6：补充文章状态与质量视图

- 增加文章概览统计。
- 增加数据质量报告入口。
- 增加最近文章任务列表。
- 增加处理结果入口。

---

## 11. 需求变更 TaskList（简版）

> 说明：本 TaskList 仅用于承接 `article_new.md` 这次 review 后的需求变更，不替代 `docs/New-Web-Linked-TaskLists/*` 主任务清单。

### [x] T1 文章工作台入口迁移

目标：把 `sidebar -> 文章` 对应的 `/articles` 从单一 Pipeline 页面升级为文章工作台。

范围：

- `/articles` 首屏改为工作台首页。
- 各子功能页面保留返回工作台入口。
- 不再把页面设计成单一“大 Pipeline 表单”。

### [x] T2 子功能页面实现

目标：把工作台下的核心文章子功能补齐为可用页面，而不是只有入口。

参照：`## 5. 子功能设计` 实现

范围：

- 抓取与处理页面，展示并提交现有文章处理动作。
- 文章列表页面，展示现有文章结果或空态。
- 数据质量页面，展示现有质量/校验信息或空态。
- 最近任务页面，展示现有文章相关 Job 列表。
- 处理结果页面，展示现有结构化处理结果或空态。
- 高级维护页面，展示维护操作并支持返回工作台。


### [x] T3 文章运行参数收敛

目标：移除 Web 对 `config_path` 的依赖，统一使用 Profile。

范围：

- 页面去掉 `config_path / Profile` 切换。
- 表单改为 Profile-only。
- API 请求和类型同步收敛到 `profile_id` 或现有统一字段。
- 相关测试更新为只覆盖 Profile 路径。

### [x] T4 高级维护与导出入口整理

目标：把文章的高级维护能力收口到工作台内，但不暴露 DuckDB 导出入口。

范围：

- 重跑选项使用 Checkbox。
- `from_step` 使用下拉选择，且仅包含 `crawl / clean / validate / store / process`，不包含 `export`。
- 高级维护支持 `force / skip_crawl / use_db / rebuild_pending / retry_failed`。
- 页面不显示 DuckDB export 按钮或入口。
- DuckDB 导出底层代码保留不删。

### [x] T5 导航、路由与测试收口

目标：清理 workflow 侧重复入口，保证文章入口改造后可验证、可回归。

范围：

- 移除 `sidebar -> 工作流 -> 数据 Pipeline` 入口。
- 路由注册、导航配置、文章页重定向逻辑同步更新。
- 补齐文章相关页面与 API client 测试。
- 验证提交后仍能跳转 Job Detail，并覆盖错误/空态/重试态。

---

## 12. 验收标准

完成后应满足：

- sidebar 仍显示“文章”。
- 进入 `/articles` 后看到的是“文章工作台”。
- 工作台能进入各子功能。
- 子功能能返回工作台。
- 页面不再要求用户填写 config_path。
- 页面统一使用 Profile。
- 高级维护在文章模块内，但与普通操作清晰分离。
- 重跑选项是 Checkbox。
- DuckDB 导出代码仍存在，但页面没有入口。
- 普通文章处理流程不依赖 DuckDB 导出。
- 执行类操作统一创建 Job，并通过 Job Detail 查看进度和日志。
- sidebar / 导航中不再出现 `工作流 -> 数据 Pipeline` 入口。
