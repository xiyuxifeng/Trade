# New-Web-V2-TaskList

> V2 目标：在 V1 的产品化运行底座和 article_pipeline 切片之上，完成 Config/Profile 正式迁移、正式 Web 信息架构、市场数据与策略运行核心链路，使系统从“可交付骨架”进入“可持续使用版本”。

## 0. V2 范围

### V2 必须交付

- Config 从 `config_path` 兼容输入迁移到正式 Profile 模型。
- Web UI 从临时验收入口升级为正式用户工作台。
- 市场数据纵向切片：Kaipan、OHLCV、MarketState、Snapshot。
- 策略运行纵向切片：策略版本、盘前、盘后、证据包、结果查看。
- Job / Workflow / Step / Artifact / ConfigSnapshot 在所有 V2 链路中统一使用。
- CLI 正式业务命令降级为 dev 入口，不再出现在用户文档主流程中。

### V2 不强制交付

- 完整回测优化平台。
- 规则池完整审核闭环。
- 多租户复杂权限。
- 高级告警、分布式 Worker、高级调度。

## 1. AI Implementation Rules

每个 AI Agent 任务必须遵守：

- 每次只执行一个 Task ID。
- 先阅读 V1 产物、迁移矩阵、当前代码，再实现。
- 不允许新增第二套 Job / Workflow / Profile / Artifact 事实源。
- 不允许把业务逻辑写入 Web Router 或 React 页面。
- 不允许删除 `config_path` 兼容能力，除非任务明确进入最终清理阶段。
- 新增用户可见能力必须包含 API、Job/Workflow、Artifact、错误处理、测试、文档。
- 修改 UI 时必须依赖 API contract，不允许写死业务规则。

## 2. Stage V2-0：V1 验收回归与边界冻结（P0）

#### [ ] NWV2-S0-001 P0 回归 V1 article_pipeline 闭环

目标：确认 V1 运行契约、Job Center、Step Timeline、ConfigSnapshot、ArtifactMetadata 在 article_pipeline 上稳定。

允许修改：
- tests/
- docs/New-Web-V2-Current-State.md

禁止修改：
- 不在本任务中重构业务代码。
- 不跳过失败测试。

验收标准：
- article_pipeline 可通过 Web/API 运行。
- Job detail 能看到状态、日志、错误、Step Timeline、Artifact、ConfigSnapshot。
- 失败、空数据、重复执行至少有一条可验证路径。

#### [ ] NWV2-S0-002 P0 更新 V2 迁移矩阵

目标：补充市场数据、策略运行、正式 Profile、正式 Web UI 的迁移矩阵。

输出：
- docs/New-Web-V2-Migration-Matrix.md

矩阵字段：
- 旧入口
- 现有 Job Type
- 新 PipelineSpec
- 新 Workflow
- Step 列表
- Profile 依赖
- Artifact 输出
- Web 页面
- API
- 权限
- 测试
- 验收
- 迁移状态

## 3. Stage V2-1：Config/Profile 正式迁移（P0）

#### [ ] NWV2-S1-001 P0 定义 Profile 领域模型

目标：把 V1 的 ConfigSnapshot 升级为正式 Profile 体系，但保留 `config_path` 兼容入口。

允许修改：
- src/services/config_profile_service.py
- src/services/config_snapshot_service.py
- src/models/
- migrations/
- tests/services/test_config_profile_service.py

禁止修改：
- 不删除现有 config_path。
- 不把 secret 原文写入 DB、日志、Artifact 或 API 响应。
- 不让 Web Router 直接读取配置文件。

实现要求：
- ProfileDefinition：可复用配置。
- ProfileVersion：版本化配置。
- ProfileSnapshot：Job 运行时快照。
- EffectiveConfig：合并后的运行配置。
- SensitiveFieldPolicy：敏感字段脱敏规则。
- config_path import：从旧配置导入 Profile。

验收标准：
- 可以从旧 config 文件导入默认 Profile。
- Job 运行时保存 ProfileSnapshot 和 config_hash。
- API 返回只展示脱敏配置。
- 旧 config_path 仍能运行 V1 article_pipeline。

#### [ ] NWV2-S1-002 P0 实现 Profile Resolver

目标：统一 Web、API、CLI dev 入口的配置解析逻辑。

允许修改：
- src/services/profile_resolver.py
- src/services/application_service.py
- tests/services/test_profile_resolver.py

禁止修改：
- 不允许各业务 Service 自行读取不同配置来源。

实现要求：
- 输入 profile_id、profile_version、config_path、runtime_overrides。
- 输出 EffectiveConfig + ProfileSnapshot。
- 支持默认值、环境变量、安全脱敏、校验错误。

验收标准：
- Web 创建 Job 和 CLI dev 创建 Job 得到一致 EffectiveConfig。
- 缺失必填配置时返回用户可理解错误。

#### [ ] NWV2-S1-003 P0 建立 Profile API

目标：提供正式配置管理 API。

允许修改：
- api/routers/ui/settings.py
- api/schemas/
- tests/api/test_settings_profiles.py

实现要求：
- list profiles
- get profile detail
- create/update profile draft
- validate profile
- import from config_path
- activate profile version
- get masked effective config

验收标准：
- API 不返回 secret 原文。
- 非 admin 不能修改高风险配置。
- Profile 修改有审计记录。

## 4. Stage V2-2：正式 Web UI 信息架构（P0）

#### [ ] NWV2-S2-001 P0 设计正式 Web IA 与路由结构

目标：把临时 Web UI 收敛为正式工作台结构。

输出：
- docs/New-Web-UI-IA.md

页面结构建议：
- Dashboard
- Jobs
- Workflows
- Articles
- Market Data
- Strategy Runs
- Artifacts
- Settings / Profiles
- Admin / Health

禁止事项：
- 不在本任务中大量重写页面。
- 不让 UI 直接表达业务规则。

验收标准：
- 每个页面都有 API 依赖、用户目标、空状态、错误状态、权限说明。

#### [ ] NWV2-S2-002 P0 重构 API Client 与类型层

目标：让 Web UI 依赖稳定 API contract。

允许修改：
- web/src/api/
- web/src/types/
- web/src/hooks/
- web/src/pages/
- tests 或前端测试目录

实现要求：
- 统一 API error handling。
- 统一 Job / Workflow / Artifact / Profile 类型。
- 统一 loading / empty / error 状态。

验收标准：
- 页面不直接拼接后端文件路径。
- 页面不硬编码 secret 或 config 结构。

#### [ ] NWV2-S2-003 P0 实现正式 Job Detail 页面

目标：Job Detail 成为所有异步任务的统一解释页。

必须展示：
- 基础信息
- 状态与时间线
- Step Timeline
- 参数摘要
- ConfigSnapshot
- 日志
- 错误解释
- Artifacts
- Retry / Cancel 权限动作

验收标准：
- article_pipeline、market、strategy 三类 Job 都能使用同一详情页。

## 5. Stage V2-3：市场数据纵向切片（P0）

#### [ ] NWV2-S3-001 P0 定义 MarketData PipelineSpec

目标：为 Kaipan、OHLCV、MarketState、Snapshot 建立统一业务规格。

输出：
- src/pipelines/market_data/spec.py
- tests/pipelines/test_market_data_spec.py

必须包含：
- 输入参数
- Profile 依赖
- Step 列表
- Artifact 输出
- 风险等级
- 权限
- 验收数据

#### [ ] NWV2-S3-002 P0 接入 Kaipan Workflow

目标：Web/API 可运行 Kaipan fetch / normalize / run。

要求：
- 使用 ProfileResolver。
- 使用 Job Center。
- 产物进入 ArtifactService。
- 错误有用户可读说明。

验收标准：
- 可触发指定 trade_date / slot。
- 可查看原始数据、归一化结果、日志、失败原因。

#### [ ] NWV2-S3-003 P0 接入 OHLCV Workflow

目标：Web/API 可运行 OHLCV crawl。

验收标准：
- 支持 symbols、start_date、end_date、mode、limit。
- 产物包含抓取摘要、失败标的、数据范围。

#### [ ] NWV2-S3-004 P0 接入 MarketState 与 Snapshot Workflow

目标：Web/API 可构建市场状态和候选池快照。

验收标准：
- MarketState 和 Snapshot 输出 Artifact 可解释。
- Job Detail 能展示数据日期、数量、缺失项。

#### [ ] NWV2-S3-005 P0 实现 Market Data Web 页面

目标：提供正式市场数据工作台。

页面能力：
- 触发抓取/归一化/快照构建。
- 查看最近 Job。
- 查看数据健康摘要。
- 打开 Artifact。

## 6. Stage V2-4：策略运行纵向切片（P0）

#### [ ] NWV2-S4-001 P0 定义 StrategyRun PipelineSpec

目标：统一策略版本、盘前、盘后、证据包、排名等能力。

输出：
- src/pipelines/strategy_run/spec.py
- tests/pipelines/test_strategy_run_spec.py

#### [ ] NWV2-S4-002 P0 接入策略版本构建 Workflow

目标：Web/API 可按 trader_id + strategy_date 构建策略版本。

验收标准：
- 生成版本 Artifact。
- 可查看输入、配置快照、生成摘要、错误原因。

#### [ ] NWV2-S4-003 P0 接入盘前 Workflow

目标：Web/API 可执行盘前流程。

验收标准：
- 支持 as_of_date、force、export_html。
- 产物包含日报、候选、证据摘要。

#### [ ] NWV2-S4-004 P0 接入盘后 Workflow

目标：Web/API 可执行盘后考核流程。

验收标准：
- 支持 as_of_date、force、export_html。
- 产物包含考核摘要、归因、错误说明。

#### [ ] NWV2-S4-005 P0 实现 Strategy Runs Web 页面

目标：提供策略运行工作台。

页面能力：
- 创建策略版本。
- 运行盘前/盘后。
- 查看最近结果。
- 打开证据包和报告。

## 7. Stage V2-5：CLI 正式降级（P1）

#### [ ] NWV2-S5-001 P1 标记旧 CLI 正式入口 deprecated

目标：用户文档不再以 CLI 作为正式主流程。

#### [ ] NWV2-S5-002 P1 CLI dev 命令调用 Application Service

目标：CLI 保留调试能力，但不复制业务逻辑。

保留命令：
- dev run-step
- dev run-workflow
- dev list-workflows
- dev inspect-job

## 8. Stage V2-6：V2 发布验收（P0）

#### [ ] NWV2-S6-001 P0 V2 E2E 回归

覆盖：
- article_pipeline
- profile import / validate / snapshot
- market_data workflow
- strategy_run workflow
- job detail
- artifact download

#### [ ] NWV2-S6-002 P0 更新用户文档

输出：
- docs/UserManual.md
- docs/WebUserManual.md
- docs/APIReference.md
- docs/ProfileMigrationGuide.md

#### [ ] NWV2-S6-003 P0 V2 Release Checklist

发布阻断项：
- secret 泄露
- Job 不可追踪
- Artifact 不可解释
- Profile 无法回滚
- Web 主流程无法完成
- CLI 与 Web 运行结果不一致且无说明
