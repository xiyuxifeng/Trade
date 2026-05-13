# Web-only 重构与 CLI 拆分优化 TaskList

> 目标：把当前项目从“CLI + Web 双入口”收敛为“Web/API/Worker 为正式入口，CLI 仅作为开发调试薄包装”。
>
> 核心原则：CLI 不拥有业务逻辑；Web 不拥有业务逻辑；Job 不拥有业务逻辑；Workflow 只编排；Step 执行业务；Domain Module 提供能力；DB / Artifact / Snapshot 保存结果。
>
> 
---

## 0. 总目标

将当前项目调整为：

```text
Web UI / API
  -> Workflow
  -> Job Center
  -> Service Step
  -> Domain Module
  -> DB / Artifact / Snapshot
```

最终状态：

1. Web/API/Worker 是正式产品入口。
2. CLI 只作为开发调试入口，不能承载业务编排。
3. 所有长链路拆成可复用 Service Step。
4. 所有用户可见操作都能通过 Web 触发、查看状态、查看日志和查看产物。
5. CLI、Web、调度器不得各自复制业务逻辑。
6. 主要功能迁移通过覆盖矩阵和验收测试保证。

---

## 1. 核心约束

### 1.1 入口约束

禁止继续新增复杂 CLI 命令。

允许的 CLI 形态只有两种：

```text
dev run-step <step_name>
dev run-workflow <workflow_name>
```

CLI 只能调用 Service Step 或 Workflow，不能直接操作 DB、文件路径、Agent、Provider 或 Pipeline 内部细节。

### 1.2 Service Step 约束

每个业务步骤必须是独立 Service Step，具备统一结构：

```python
class StepInput:
    ...

class StepOutput:
    ...

async def run(input: StepInput, context: RunContext) -> StepOutput:
    ...
```

每个 Step 必须满足：

```text
可单独运行
可被 Workflow 编排
可记录输入参数
可记录输出产物
失败时返回结构化错误
不能直接依赖 Typer/CLI
不能直接 print 作为业务输出
```

### 1.3 Workflow 约束

Workflow 只负责编排，不写业务细节。

例如：

```text
article_pipeline:
  - crawl_articles
  - clean_articles
  - validate_articles
  - store_articles
  - extract_article_metadata

pre_market_pipeline:
  - build_market_snapshot
  - build_strategy_version
  - run_pre_market

after_close_pipeline:
  - run_after_close
  - build_evidence_pack
  - update_ranking
  - write_trader_memory
```

### 1.4 Job 约束

所有超过 3 秒、会写库、会写文件、会调用外部接口、或需要追踪状态的操作，都必须进入 Job Center。

Job 必须记录：

```text
job_id
job_type
workflow_name / step_name
input_params
status
started_at
finished_at
logs
error
artifacts
created_by
retry_count
cancel_requested
```

### 1.5 Web UI 约束

只要 Service Contract / Job Type / Workflow / Artifact / 权限发生变化，就必须同步检查 Web UI。

必须同步检查：

```text
web/ 页面
api/routers/ui/*
src/services/*
src/services/job_registry.py
docs/WebUserManual.md
docs/Web-UserManual-Coverage.md
docs/APIReference.md
```

---

## 2. 阶段规划

## Stage 0：冻结现状与建立迁移矩阵

### 目标

建立“旧 CLI 功能 -> 新 Web/API/Workflow/Step”的完整映射，避免功能遗漏。

### 任务

#### [ ] WRF-S0-001 建立 Web-only 迁移矩阵

输出文件：

```text
docs/WebOnly-Migration-Matrix.md
```

矩阵字段：

```text
旧 CLI 命令
当前 Service
新 Step
新 Workflow
新 Job Type
Web 页面
API 路由
产物路径
权限
风险等级
迁移状态
验收方式
```

初始覆盖范围：

```text
init-config
db-check
db-migrate
init-project
seed-data
backup-data
restore-data
scheduler-start
crawl
pipeline-run
pipeline-step
import-trade-logs
migrate-crawl-state
extract-articles
clusters-build
e2e-regression
snapshot build
ohlcv crawl
strategy build/list
run-pre-market
run-after-close
list-signals
market-state-build
kaipan fetch/normalize/status/run
dashboard report
backtest run/report/validate-rules
optimize filter/advise/create-candidate
rule-pool show/list/review/review-batch
```

验收标准：

```text
所有旧 CLI 功能都有去向
未迁移项明确标记 blocked / deprecated / web-only later
没有“未知功能”
```

#### [ ] WRF-S0-002 冻结 CLI 新增规则

输出文件：

```text
docs/Development-Constraints.md
```

规则：

```text
不得新增面向用户的 CLI 命令
不得在 CLI 中新增业务逻辑
不得在 CLI 中直接写库
不得在 CLI 中直接拼产物路径
CLI 只能调用 Service Step 或 Workflow
```

验收标准：

```text
开发约束写入文档
PR Review checklist 增加 CLI 检查项
```

---

## Stage 1：拆分 Service Step

### 目标

把现有长链路拆成可单独运行、可组合、可测试的 Step。

### 任务

#### [ ] WRF-S1-001 定义 Step 基础协议

新增：

```text
src/workflows/step.py
src/workflows/context.py
src/workflows/result.py
```

建议结构：

```python
@dataclass
class RunContext:
    run_id: str
    job_id: str | None
    actor: str | None
    config_profile_id: str
    config_path: str
    config_hash: str | None
    project_root: Path
    dry_run: bool = False

@dataclass
class StepResult:
    status: Literal["success", "failed", "skipped"]
    message: str
    payload: dict
    artifacts: list[ArtifactRef]
    warnings: list[str]
```

验收标准：

```text
StepResult 统一
RunContext 统一
不依赖 CLI
有单元测试
```

#### [ ] WRF-S1-002 拆分文章 Pipeline Step

拆成：

```text
crawl_articles
clean_articles
validate_articles
store_articles
extract_article_metadata
export_article_dataset
cleanup_pipeline_files
```

验收标准：

```text
每个 Step 可单独测试
article_pipeline 可组合执行
旧 pipeline-run 不再直接编排内部步骤
```

#### [ ] WRF-S1-003 拆分快照与行情 Step

拆成：

```text
build_market_snapshot
fetch_kaipan_raw
normalize_kaipan_snapshot
crawl_ohlcv
compute_indicators
```

验收标准：

```text
快照构建可单独运行
Kaipan fetch/normalize 不依赖 CLI
OHLCV 入库可通过 Job 运行
Artifact 中能看到 raw/snapshot 输出
```

#### [ ] WRF-S1-004 拆分策略与盘前盘后 Step

拆成：

```text
build_strategy_version
run_pre_market
run_after_close
build_evidence_pack
update_ranking
write_trader_memory
```

验收标准：

```text
盘前 Workflow 可重放
盘后 Workflow 可重放
TradeIdea / Evaluation / Evidence Pack 可追溯到 snapshot 和 strategy_version
```

#### [ ] WRF-S1-005 拆分回测与优化 Step

拆成：

```text
run_backtest
load_backtest_report
validate_rules
run_rule_pool_backtest
optimize_filter_traders
optimize_advise_strategy
create_candidate_strategy_version
```

验收标准：

```text
回测与线上评分口径一致
规则验真可单独运行
候选策略版本不会直接覆盖 released 版本
```

---

## Stage 2：建立 Workflow 层

### 目标

把 Step 组合成稳定 Workflow，让 Web 和 Job 只认 Workflow，不关心内部步骤细节。

### 任务

#### [ ] WRF-S2-001 定义 Workflow Registry

新增：

```text
src/workflows/registry.py
src/workflows/definitions.py
```

首批 Workflow：

```text
article_pipeline
snapshot_pipeline
pre_market_pipeline
after_close_pipeline
backtest_pipeline
optimization_pipeline
data_health_pipeline
backup_pipeline
restore_pipeline
```

Workflow Definition 建议结构：

```python
@dataclass
class WorkflowDefinition:
    name: str
    title: str
    description: str
    steps: list[str]
    input_schema: type[BaseModel]
    risk_level: RiskLevel
    required_role: Role
    artifact_kinds: list[str]
```

验收标准：

```text
Workflow 可枚举
Workflow 有参数 schema
Workflow 有权限和风险等级
Web 可以读取 Workflow Definition 渲染表单
```

#### [ ] WRF-S2-002 重构 pipeline-run / pipeline-step 为 Workflow 调用

旧行为：

```text
CLI -> pipeline-run -> 内部编排
```

新行为：

```text
CLI/Web/API -> WorkflowRunner -> StepRunner
```

验收标准：

```text
pipeline-run 只调用 article_pipeline
pipeline-step 只调用单个 Step
CLI 不再发现前置文件、不再做复杂恢复逻辑
```

#### [ ] WRF-S2-003 增加 Workflow 运行审计

每次 Workflow 运行记录：

```text
workflow_run_id
workflow_name
job_id
input_params
step_results
artifact_refs
status
duration
error_summary
```

验收标准：

```text
任务详情页可看到 Workflow 步骤状态
失败时知道失败在哪个 Step
支持从失败 Step 重跑
```

---

## Stage 3：Job Center 收敛

### 目标

让所有长任务通过统一 Job 执行，不再出现 Web 直调长任务或 CLI 私自跑长任务。

### 任务

#### [ ] WRF-S3-001 收敛 Job Type

建议只保留两类 Job：

```text
workflow.run
step.run
```

或者保留业务型 Job，但必须映射到 Workflow：

```text
pipeline-run -> workflow: article_pipeline
run-pre-market -> workflow: pre_market_pipeline
run-after-close -> workflow: after_close_pipeline
backtest-run -> workflow: backtest_pipeline
```

验收标准：

```text
job_registry 中没有孤立 job type
每个 job type 都能找到 workflow 或 step
```

#### [ ] WRF-S3-002 扩展 Job 详情返回 Step 状态

API 返回示例：

```json
{
  "job_id": "...",
  "workflow_name": "article_pipeline",
  "status": "running",
  "steps": [
    {"name": "crawl_articles", "status": "success"},
    {"name": "clean_articles", "status": "running"},
    {"name": "validate_articles", "status": "pending"}
  ]
}
```

验收标准：

```text
Web 任务详情可以展示步骤进度
日志能按 step 过滤
产物能按 step 归类
```

#### [ ] WRF-S3-003 统一取消、重试和重跑语义

规则：

```text
pending job: 可直接取消
running job: 标记 cancel_requested
failed job: 可从失败 step 重跑
success job: 可 clone params 重新运行
high/critical risk job: 重跑需要二次确认
```

验收标准：

```text
Web UI 行为和后端状态一致
文档写明取消不是强杀进程
```

---

## Stage 4：Web UI 同步改造

### 目标

让 Web 页面以 Workflow/Step/Job 为中心，而不是以 CLI 命令为中心。

### 任务

#### [ ] WRF-S4-001 工作流页面改造

页面展示：

```text
Workflow 列表
Workflow 说明
步骤列表
参数表单
配置 Profile 选择
风险等级
运行按钮
最近运行记录
```

验收标准：

```text
用户不需要知道 CLI 命令
用户可以理解每个 Workflow 会执行哪些步骤
用户可以选择允许范围内的配置 Profile
```

#### [ ] WRF-S4-002 任务详情页改造

增加：

```text
Step Timeline
Step 日志过滤
Step 产物分组
失败 Step 重跑按钮
参数快照
配置快照
审计记录
```

验收标准：

```text
长任务失败时，用户能定位失败步骤
不用查服务器日志
能看到本次任务使用的配置 Profile / hash / snapshot
```

#### [ ] WRF-S4-003 产物中心改造

Artifact 增加字段：

```text
artifact_id
job_id
workflow_name
step_name
kind
path
previewable
created_at
source
```

验收标准：

```text
产物可按 Workflow / Step / Job 过滤
HTML / JSON / Markdown 可预览
大文件可下载
```

#### [ ] WRF-S4-004 页面与功能矩阵同步

每次 Web 页面变化，同步：

```text
docs/WebUserManual.md
docs/Web-UserManual-Coverage.md
docs/APIReference.md
```

验收标准：

```text
Web 页面名称和文档一致
按钮行为和文档一致
功能矩阵无 stale 项
```

---

## Stage 5：CLI 降级为开发工具

### 目标

移除 CLI 的产品入口地位，防止再次变复杂。

### 任务

#### [ ] WRF-S5-001 新增 dev CLI

新增：

```text
tools/dev_cli.py
```

只支持：

```bash
python -m tools.dev_cli run-step crawl_articles --params params.json
python -m tools.dev_cli run-workflow article_pipeline --params params.json
python -m tools.dev_cli list-steps
python -m tools.dev_cli list-workflows
```

验收标准：

```text
dev CLI 只调用 StepRunner / WorkflowRunner
无业务逻辑
无复杂参数树
```

#### [ ] WRF-S5-002 标记旧 CLI deprecated

在旧 CLI 帮助和文档顶部标记：

```text
Deprecated: CLI 仅保留兼容，正式操作请使用 Web/API。
```

验收标准：

```text
UserManual 不再作为主用户手册
WebUserManual 成为主用户手册
旧 CLI 文档进入 docs/Deprecated
```

#### [ ] WRF-S5-003 删除或冻结旧 CLI 编排逻辑

冻结范围：

```text
cli/main.py 中复杂命令
cli/snapshot.py
cli/ohlcv.py
cli/backtest.py
cli/optimize.py
src.providers.kaipan_scheduler CLI wrapper
```

处理方式：

```text
保留薄包装
或迁移到 tools/dev_cli.py
或标记 deprecated
```

验收标准：

```text
旧 CLI 不再新增功能
业务变更不要求优先改 CLI
```

---

## Stage 6：功能覆盖与回归验收

### 目标

证明主要功能都已经迁移，且 Web/API/Job 能跑通。

### 任务

#### [ ] WRF-S6-001 建立功能覆盖验收表

输出：

```text
docs/WebOnly-Acceptance.md
```

字段：

```text
功能
Workflow
Job Type
Web 页面
API
测试用例
手工验收步骤
迁移状态
负责人
```

最低必须覆盖：

```text
配置检查
数据库检查
数据库迁移
文章抓取
文章处理
市场快照
OHLCV
策略版本
盘前日报
盘后考核
Evidence Pack
Ranking
回测
规则验真
优化
规则池审核
产物查看
任务日志
备份恢复
用户权限
告警
```

#### [ ] WRF-S6-002 建立 E2E 主链路测试

E2E 场景：

```text
1. 初始化测试数据库
2. 导入样例文章/交易记录
3. 运行 article_pipeline
4. 运行 snapshot_pipeline
5. 运行 pre_market_pipeline
6. 运行 after_close_pipeline
7. 运行 backtest_pipeline
8. 检查产物中心
9. 检查报告页
10. 检查任务日志和审计
```

验收标准：

```text
一条命令或一个测试脚本可重复执行
失败时能定位具体 Step
```

#### [ ] WRF-S6-003 建立 Contract Test

覆盖：

```text
Step Input Schema
Step Output Schema
Workflow Definition
Job Definition
Artifact Schema
Web API Response
Config Profile Schema
```

验收标准：

```text
Service 改参数时测试会失败
Web 不会静默失配
配置 Profile 变化不会导致 Job 不可追溯
```

---

## Stage 7：文档收敛

### 目标

把文档从“CLI + Web 双入口”收敛成“Web 为主，CLI 为开发调试”。

### 任务

#### [ ] WRF-S7-001 更新 Project.md

修改为：

```text
正式运行形态：FastAPI + Web + Worker + PostgreSQL
开发调试入口：dev CLI
旧 CLI：deprecated
```

#### [ ] WRF-S7-002 更新 需求.md

将：

```text
运行支持 CLI 手动触发和服务化定时触发
```

改为：

```text
运行支持 Web/API 手动触发、服务化定时触发和开发调试 CLI。
正式用户操作以 Web/API 为准。
```

#### [ ] WRF-S7-003 更新 WebUserManual.md

确保它成为主用户手册。

新增章节：

```text
工作流与步骤
配置 Profile
任务失败后如何从失败步骤重跑
为什么不再使用 CLI
开发调试 CLI 与用户 Web 操作的区别
```

#### [ ] WRF-S7-004 归档 UserManual.md

处理方式：

```text
docs/Deprecated/UserManual-CLI.md
```

顶部加说明：

```text
本文件为历史 CLI 手册，仅供调试和迁移参考。
正式使用请看 WebUserManual.md。
```

---

## 8. Config Profile 管理方案

### 8.1 结论

`--config config/app.yaml` 不应该在 Web UI 中继续表现为“用户输入配置文件路径”。

Web 中应该抽象成：

```text
配置 Profile（Configuration Profile）
```

例如：

```text
default
staging
production
research
```

后端负责把 Profile 解析到具体配置文件：

```python
config_path = ConfigProfileService.resolve("default")
```

### 8.2 是否修改 app.yaml 格式

不建议把原来的 `app.yaml` 改成：

```yaml
profiles:
  default:
    database: ...
  staging:
    database: ...
```

推荐保持每个 YAML 的原有结构：

```text
config/app.yaml
config/app.staging.yaml
config/app.prod.yaml
```

然后用 Profile 管理这些 YAML 文件。

也就是说：

```text
底层配置格式不大改
Web/数据库层增加 ConfigProfile 管理
Web UI 上用 Profile 选择和编辑
```

### 8.3 推荐数据模型

新增表或配置文件维护：

```text
config_profiles
```

字段：

```text
id
profile_id
display_name
config_path
environment
is_default
is_active
editable
created_by
created_at
updated_at
last_validated_at
last_config_hash
```

示例：

```json
{
  "profile_id": "default",
  "display_name": "默认配置",
  "config_path": "config/app.yaml",
  "environment": "local",
  "is_default": true,
  "is_active": true,
  "editable": true
}
```

### 8.4 Web Settings 页面设计

设置页展示：

```text
当前配置 Profile
配置文件路径
配置摘要
敏感项脱敏
最后校验时间
最后备份时间
配置 hash
```

操作：

```text
查看配置
校验配置
保存配置
创建备份
恢复配置
切换默认 Profile
创建 Profile
停用 Profile
```

配置页签建议：

```text
基础配置：timezone, run_mode, storage
数据库：database
调度：schedule, kaipan.fetch_schedule
数据源：data, akshare
爬虫：crawl
LLM：llm
交易员：traders
Persona：persona
Kaipan：kaipan
告警：alerting, dashboard.alerts
风控/评估：evaluation, data_quality
高级 YAML：完整 YAML 只读/高级编辑
```

### 8.5 Workflow 页面设计

Workflow 运行页默认显示：

```text
使用配置：default
```

高级选项允许 operator/admin 选择：

```text
配置 Profile：default / staging / test
```

不允许普通用户输入任意路径。

### 8.6 后端实现建议

所有 Service / Step / Workflow 接收：

```python
config_profile_id: str = "default"
```

由后端解析为真实路径：

```python
config_path = ConfigProfileService.resolve(config_profile_id)
config = load_app_config(config_path)
```

禁止前端直接传：

```text
../../some/path.yaml
/Users/xxx/secret.yaml
```

如果需要临时配置，使用“配置草稿”机制：

```text
创建配置草稿
校验草稿
保存并生成备份
成为新的 Profile
```

### 8.7 敏感字段处理

以下字段不要在 Web 明文展示：

```text
database.url 里的密码
crawl.auth.tgb.cn.cookie
llm.api_key
kaipan.token
kaipan.user_id
api.auth.api_keys
alerting.dingtalk.webhook_url
alerting.dingtalk.secret
alerting.feishu.webhook_url
alerting.wecom.webhook_url
```

Web UI 里显示：

```text
已配置 / 未配置
******后四位
来源：环境变量 / YAML / Secret Store
```

保存时建议优先写环境变量引用，不要把真实密钥写回 YAML。

例如：

```yaml
llm:
  api_key: "${DASHSCOPE_API_KEY}"

crawl:
  auth:
    tgb.cn:
      cookie: "${TGB_COOKIE}"
```

### 8.8 Job 配置追溯

每次 Job 必须记录：

```json
{
  "config_profile_id": "default",
  "config_path": "config/app.yaml",
  "config_hash": "sha256:xxxx",
  "config_snapshot_artifact_id": "artifact_xxx"
}
```

这样可以保证之后配置变了，旧 Job 还能追溯。

### 8.9 权限设计

```text
viewer：只能查看当前 Profile 名称和脱敏摘要
operator：可以在允许运行的 Profile 中选择，但不能编辑配置
admin：可以创建、编辑、校验、保存、恢复、切换默认 Profile
```

### 8.10 分阶段实现

第一阶段：

```text
config/app.yaml 继续存在
Web 默认使用 default profile
default profile 指向 config/app.yaml
Settings 页面读取 app.yaml
页面分区展示配置
保存前校验
保存前自动备份
Job 记录 config hash
```

第二阶段：

```text
支持多个 profile
每个 profile 指向一个 YAML
operator 运行任务时可选择 profile
admin 可编辑/切换默认 profile
```

第三阶段：

```text
配置拆分 base + overlay
敏感值进入 Secret Store
Job 保存完整配置快照
```

### 8.11 验收标准

```text
Web 运行任何 Workflow 不需要用户输入 config/app.yaml
Job 记录 config_profile_id、config_path、config_hash
Settings 页面可查看和校验当前配置
敏感字段脱敏
普通用户不能输入任意配置路径
admin 修改配置前自动备份
配置变化后旧 Job 仍可追溯原配置版本
```

---

## 9. 实现注意事项

### 9.1 不要把复杂度从 CLI 搬到 Web 或 Job 里

这次重构真正要达成的是：

```text
CLI 不拥有业务逻辑
Web 不拥有业务逻辑
Job 不拥有业务逻辑
Workflow 只编排
Step 执行业务
Domain Module 提供底层能力
```

### 9.2 不要一次性删除 CLI

建议先降级，不要直接删。先做到：

```text
旧 CLI -> 调用 Workflow / Step
Web -> 调用 Workflow / Step
Job -> 执行 Workflow / Step
```

等 Web 主链路稳定后，再把旧 CLI 标记 deprecated。

### 9.3 Step 拆分不要过细，也不要过粗

建议粒度是：

```text
一个 Step = 一个明确业务动作 + 一个明确产物
```

合理示例：

```text
crawl_articles
clean_articles
validate_articles
store_articles
```

不合理示例：

```text
parse_one_field       太细
run_whole_pipeline    太粗
```

### 9.4 每个 Step 必须有输入、输出、产物、错误

否则 Web 任务详情页无法展示清楚。

每个 Step 至少返回：

```json
{
  "status": "success",
  "message": "...",
  "payload": {},
  "artifacts": [],
  "warnings": []
}
```

### 9.5 配置必须可追溯

引入 Config Profile 后，每个 Job 要记录：

```json
{
  "config_profile_id": "default",
  "config_path": "config/app.yaml",
  "config_hash": "sha256:...",
  "config_snapshot_artifact_id": "..."
}
```

否则以后看历史 Job 时不知道当时用的是哪版配置。

### 9.6 不要让前端传任意路径

Web 不应该传：

```text
config_path = ../../secret.yaml
```

只能传：

```text
config_profile_id = default
```

后端负责解析白名单 Profile。

### 9.7 API / Worker / Scheduler 必须共用同一套 Workflow

不要出现：

```text
Web 有一套逻辑
Worker 有一套逻辑
Scheduler 有一套逻辑
CLI 有一套逻辑
```

正确方式：

```text
Web/API/Scheduler/CLI -> WorkflowRunner -> StepRunner
```

### 9.8 文档和代码要同步

每次改以下内容，都要更新文档和测试：

```text
Step Input / Output
Workflow Definition
Job Type
Artifact Schema
Config Profile
权限 / 风险等级
Web 页面按钮和表单
```

---

## 10. 新增 Provider、市场数据和功能的扩展规范

### 10.1 总原则

以后新增能力时，不要直接把新能力塞进 Agent、CLI 或页面里。

统一走：

```text
Provider / Domain Module
  -> Step
  -> Workflow
  -> Job
  -> API
  -> Web
  -> Docs
  -> Tests
```

禁止：

```text
直接写 CLI
直接写 Web 调 Provider
直接在 Agent 里调外部接口
直接在页面里拼参数
直接把结果散落到文件夹
```

### 10.2 新增 Provider 的标准流程

例如新增：

```text
akshare provider
tushare provider
同花顺 provider
新的 kaipan 接口
```

应该按这个流程：

```text
1. 新增 Provider 实现
2. 新增 Normalizer
3. 新增 Snapshot Schema
4. 注册 Capability
5. 暴露为 Step
6. 必要时加入 Workflow
7. 加入 Web 页面或查询 API
8. 加入测试和文档
```

推荐结构：

```text
src/providers/
  base.py
  registry.py
  kaipan/
  akshare/
  tushare/

src/market_data/
  normalizers/
  schemas/
  snapshots/

src/workflows/steps/
  market_data/
  snapshots/
```

新增 Provider 不应该直接被 Web 调用，而是：

```text
Provider -> Step -> Workflow -> Job -> Web
```

### 10.3 新增市场数据的标准流程

例如新增：

```text
龙虎榜详情
游资席位
竞价异动
指数分钟线
行业资金流
涨停原因
```

先判断它属于哪一类：

```text
raw data       原始数据
snapshot       可回放快照
feature        特征
report         报告展示
decision input 决策输入
```

推荐流程：

```text
1. 定义数据契约
2. 定义 raw 保存格式
3. 定义 snapshot / normalized 格式
4. 定义 DB 表是否必要
5. 定义 Artifact 类型
6. 定义 Step
7. 定义查询 API
8. 定义 Web 展示方式
```

不要一上来就直接建页面。先保证：

```text
可抓取
可标准化
可落盘
可回放
可测试
```

再考虑 UI。

### 10.4 新增功能的标准流程

任何新功能都先问 6 个问题：

```text
1. 是查询类，还是长任务类？
2. 是否会写库 / 写文件 / 调外部接口？
3. 是否需要 Job？
4. 是否需要 Workflow？
5. 是否产生 Artifact？
6. 是否需要权限和审计？
```

判断标准：

| 新功能类型 | 推荐处理 |
|---|---|
| 纯查询 | API + Web 页面 |
| 会写库 | Step + Job |
| 会调外部接口 | Step + Job |
| 多步骤链路 | Workflow + Job |
| 产生文件 | Artifact |
| 高风险操作 | 权限 + 二次确认 + 审计 |
| 可定时执行 | Scheduler -> WorkflowRunner |

### 10.5 新 Provider / 新功能必须补的注册点

以后新增能力时，不要只写代码文件。至少要同步这些地方：

```text
Provider Registry
Capability Registry
Step Registry
Workflow Registry
Job Registry
Artifact Registry
API Router
Web 页面或菜单
权限表
文档
测试
```

硬性规则：

```text
没有注册到 Registry 的能力，不算完成。
没有测试和文档的能力，不算完成。
没有 Artifact/日志/错误追踪的长任务，不允许上线。
```

### 10.6 新增 Provider 示例：Tushare

如果新增 `tushare`：

```text
[ ] 定义 tushare 配置项
[ ] 新增 TushareProvider
[ ] 新增 tushare normalizer
[ ] 新增 snapshot schema
[ ] 新增 fetch_tushare_xxx Step
[ ] 注册 capability: market.ohlcv / market.index / market.fund_flow
[ ] 注册 workflow: market_data_sync
[ ] 注册 job: workflow.run market_data_sync
[ ] Web 市场页增加数据源筛选
[ ] Job 详情展示数据源、参数、产物
[ ] Artifact 中可查看 raw/normalized/snapshot
[ ] 补测试
[ ] 更新 WebUserManual / APIReference
```

---

## 11. 推荐实施顺序

不要一口气删 CLI。建议这样做：

```text
第一步：建迁移矩阵
第二步：定义 Step 协议
第三步：引入 Config Profile default
第四步：拆 article_pipeline
第五步：接入 WorkflowRunner
第六步：让 Job 跑 Workflow
第七步：改 Web 任务详情展示 Step
第八步：拆快照/盘前/盘后/回测
第九步：旧 CLI 改成薄包装
第十步：文档收敛
第十一步：删除或冻结旧 CLI
```

---

## 12. 每次改动的 Checklist

每个 PR 必须回答：

```text
[ ] 是否新增/修改了 Service Step？
[ ] 是否修改了 Step Input/Output？
[ ] 是否修改了 Workflow？
[ ] 是否修改了 Job Type？
[ ] 是否修改了 Artifact？
[ ] 是否修改了 Config Profile？
[ ] 是否修改了权限或风险等级？
[ ] 是否需要同步 Web UI？
[ ] 是否需要同步 WebUserManual？
[ ] 是否需要同步 APIReference？
[ ] 是否需要更新迁移矩阵？
[ ] 是否保留了旧 CLI 兼容？
[ ] 如果不保留，是否写了 deprecated 说明？
```

---

## 13. 最关键的判断标准

后续所有设计都用这句话校验：

```text
CLI 不拥有业务逻辑。
Web 不拥有业务逻辑。
Job 不拥有业务逻辑。
Workflow 只编排。
Step 执行业务。
Domain Module 提供能力。
DB / Artifact / Snapshot 保存结果。
```
