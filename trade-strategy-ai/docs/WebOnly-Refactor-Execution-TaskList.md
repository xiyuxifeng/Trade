# WebOnly-Refactor-Execution-TaskList

> 本文件是 `trade-strategy-ai` Web-only 重构的可执行追踪清单。  
>  
> 目标不是替代 `WebOnly-Refactor.md` 总纲，而是把重构拆成可实施、可验收、可并行、可回滚的小任务。  
>  
> 当前只细化 Stage 0 ~ Stage 2 的 P0 任务；Stage 3 及之后先保留占位，等 `article_pipeline` 样板跑通后再继续细化。

---

## 1. 文档用途

本清单承担 4 个作用：

1. 把 Web-only 重构拆成可执行任务。  
2. 防止 CLI / Web / Job / Service 行为分叉。  
3. 保证 Config Profile、Step、Workflow、Job、Web UI、文档和测试同步推进。  
4. 作为后续 PR、验收和回归测试的依据。

---

## 2. 执行原则

### 2.1 总原则

```text  
CLI 不拥有业务逻辑。  
Web 不拥有业务逻辑。  
Job 不拥有业务逻辑。  
Workflow 只负责编排。  
Step 执行业务动作。  
Domain Module 提供底层能力。  
DB / Artifact / Snapshot 保存结果。  
```

### 2.2 当前阶段边界

当前只推进到：

```text  
Stage 0：现状冻结与迁移矩阵  
Stage 1：Config Profile 与运行上下文  
Stage 2：Step 协议与 article_pipeline 样板  
```

后续阶段暂不展开细化，等 `article_pipeline` 样板完整跑通后再补：

```text  
Stage 3：Workflow Registry / Runner 完整化  
Stage 4：Job Center 收敛  
Stage 5：Web UI 改造  
Stage 6：CLI 降级与退役  
Stage 7：Provider / 市场数据扩展规范落地  
Stage 8：E2E、Contract Test 与最终验收  
Stage 9：文档收敛  
```

### 2.3 任务状态规则

- `[ ]` 未开始  
- `[-]` 进行中  
- `[x]` 已完成  
- `[!]` 阻塞  
- `[~]` 等待后续阶段细化

### 2.4 优先级规则

- `P0`：阻塞 Web-only 重构主链路，不完成不能进入下一阶段。  
- `P1`：主链路增强能力，P0 样板跑通后推进。  
- `P2`：体验、运维、可视化增强。

---

## 3. Stage 0：现状冻结与迁移矩阵（P0）

### Stage 目标

- 明确当前 CLI / Web / API / Service / Job 的现状。  
- 建立“旧 CLI 功能 -> 新 Web/API/Workflow/Step”的迁移矩阵。  
- 冻结 CLI 新增规则，避免重构过程中继续扩散。  
- 形成后续拆分 article_pipeline 的输入依据。

### 阶段完成标准

- 存在完整迁移矩阵。  
- 所有旧 CLI 功能都有状态：`keep-thin-wrapper` / `migrate-to-workflow` / `migrate-to-step` / `deprecated` / `remove-later`。  
- 开发约束写入文档。  
- 后续 PR 能按 checklist 判断是否违反 Web-only 约束。

---

### [ ] WRF-S0-001 P0 建立 Web-only 迁移矩阵

目标：

建立旧 CLI 功能到新 Web/API/Workflow/Step/Job 的完整映射，避免迁移遗漏。

输入：

- `docs/UserManual.md`  
- `docs/Web-UserManual-Coverage.md`  
- `docs/WebOnly-Refactor.md`  
- `cli/main.py`  
- `cli/*.py`  
- `src/services/*`  
- `api/routers/ui/*`

输出：

```text  
docs/WebOnly-Migration-Matrix.md  
```

矩阵字段：

```text  
旧 CLI 命令  
当前 Service  
当前 API  
新 Step  
新 Workflow  
新 Job Type  
Web 页面  
产物类型  
权限  
风险等级  
迁移策略  
迁移状态  
验收方式  
备注  
```

初始必须覆盖：

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
persona-init-sample  
market-state-build  
kaipan fetch  
kaipan normalize  
kaipan status  
kaipan run  
dashboard report  
backtest run  
backtest report  
backtest validate-rules  
backtest reproducibility-check  
backtest rule-pool-run  
optimize filter  
optimize advise  
optimize create-candidate  
rule-pool show  
rule-pool list  
rule-pool review  
rule-pool review-batch  
```

修改范围：

```text  
docs/WebOnly-Migration-Matrix.md  
```

前置依赖：无。

可并行：

- `WRF-S0-002`  
- `WRF-S0-003`

验收标准：

- 所有旧 CLI 命令都有迁移策略。  
- 所有保留能力都能映射到 Service / Step / Workflow / Web 页面中的至少一项。  
- 没有“待确认但未标记”的功能。  
- 矩阵中明确哪些功能先不迁移、哪些功能保留薄 CLI 包装。

完成情况：

- 待填写。

备注：

迁移矩阵是后续所有阶段的验收入口。没有进入矩阵的能力，不允许直接进入实现。

---

### [ ] WRF-S0-002 P0 建立 Web-only 开发约束文档

目标：

明确 Web-only 重构期间的开发约束，防止继续向 CLI、Web 页面或 Job Runner 中堆业务逻辑。

输入：

- `docs/WebOnly-Refactor.md`  
- 当前 `Web-TaskList.md` 中的 Web 不执行 shell、Service Layer、Job Center 原则

输出：

```text  
docs/Development-Constraints.md  
```

必须包含的约束：

```text  
不得新增面向用户的复杂 CLI 命令。  
不得在 CLI 中新增业务逻辑。  
不得在 Web 页面中直接拼业务参数调用 Provider。  
不得在 Job Runner 中写具体业务逻辑。  
不得让前端传任意 config_path。  
所有长任务必须进入 Job Center。  
所有业务动作必须落到 Step 或 Domain Module。  
所有 Workflow 只能编排 Step。  
所有新增能力必须注册到对应 Registry。  
所有配置变更必须可追溯。  
```

修改范围：

```text  
docs/Development-Constraints.md  
```

前置依赖：无。

可并行：

- `WRF-S0-001`  
- `WRF-S0-003`

验收标准：

- 文档中包含开发禁令、允许模式和 PR checklist。  
- PR checklist 至少覆盖：Step、Workflow、Job、Artifact、Config、Web UI、Docs、Tests。  
- 明确“CLI 只能作为薄包装”。

完成情况：

- 待填写。

备注：

建议把 checklist 后续复制到 PR 模板中。

---

### [ ] WRF-S0-003 P0 盘点当前 Service 与 CLI 耦合点

目标：

识别现有 CLI 中仍然直接承担业务编排、参数恢复、文件发现、DB 操作或产物路径拼接的位置，为 Stage 2 拆 Step 做准备。

输入：

```text  
cli/main.py  
cli/snapshot.py  
cli/ohlcv.py  
cli/backtest.py  
cli/optimize.py  
src/providers/kaipan_scheduler.py  
src/services/*  
```

输出：

```text  
docs/WebOnly-CLI-Coupling-Audit.md  
```

审计字段：

```text  
文件  
函数/命令  
当前职责  
是否直接操作 DB  
是否直接操作文件路径  
是否直接调用 Provider  
是否直接编排多步骤  
应迁移到 Step / Workflow / Service 的目标位置  
风险等级  
备注  
```

修改范围：

```text  
docs/WebOnly-CLI-Coupling-Audit.md  
```

前置依赖：无。

可并行：

- `WRF-S0-001`  
- `WRF-S0-002`

验收标准：

- 至少覆盖所有 `cli/*.py` 和 `src.providers.kaipan_scheduler`。  
- 明确 `pipeline-run`、`pipeline-step`、`snapshot build`、`ohlcv crawl`、`backtest`、`optimize` 的现状职责。  
- 为 Stage 2 的 article_pipeline 拆分给出明确迁移目标。

完成情况：

- 待填写。

备注：

这个任务不要求修改代码，只做现状审计。

---

### [ ] WRF-S0-004 P0 明确 article_pipeline 样板范围

目标：

选择 article_pipeline 作为 Web-only 重构的第一个样板，明确它的边界、输入、输出、Step 划分和验收口径。

输入：

- `docs/crawl.md`  
- `docs/UserManual.md` 中 pipeline-run / pipeline-step 部分  
- `WRF-S0-001` 迁移矩阵  
- `WRF-S0-003` CLI 耦合审计

输出：

```text  
docs/WebOnly-ArticlePipeline-Spec.md  
```

必须明确：

```text  
article_pipeline 包含哪些 Step  
article_pipeline 不包含哪些能力  
每个 Step 的输入输出  
每个 Step 的产物  
每个 Step 的失败语义  
是否支持从失败 Step 重跑  
是否支持 dry-run  
是否支持 force  
是否支持 max_articles  
```

建议 Step：

```text  
crawl_articles  
clean_articles  
validate_articles  
store_articles  
extract_article_metadata  
export_article_dataset  
cleanup_pipeline_files  
```

修改范围：

```text  
docs/WebOnly-ArticlePipeline-Spec.md  
```

前置依赖：

- `WRF-S0-001`  
- `WRF-S0-003`

可并行：无。

验收标准：

- article_pipeline 的边界清晰。  
- 不再把“所有 pipeline 相关能力”一次性塞进样板。  
- Stage 2 可以直接按此规格拆 Step。

完成情况：

- 待填写。

备注：

样板阶段优先保证闭环，不追求一次覆盖所有历史变体。

---

## 4. Stage 1：Config Profile 与运行上下文（P0）

### Stage 目标

- 将 CLI 的 `--config config/app.yaml` 转换为 Web/API/Job 可用的 Config Profile 模式。  
- 不改变现有 `app.yaml` 内部结构。  
- 禁止前端传任意配置路径。  
- 每次 Job 记录配置 hash 和配置快照，保证可追溯。

### 阶段完成标准

- 存在 ConfigProfileService。  
- 存在 default profile，指向 `config/app.yaml`。  
- Workflow / Step / Job 使用 `config_profile_id`，不直接要求用户输入 `config_path`。  
- Job 记录 `config_profile_id`、`config_path`、`config_hash`、`config_snapshot_artifact_id`。

---

### [ ] WRF-S1-001 P0 定义 Config Profile 数据结构

目标：

建立 Config Profile 概念，保留原有 `app.yaml` 格式，只在运行层和 Web UI 层抽象为 Profile。

输入：

- 当前 `config/app.yaml`  
- `src/common/config.py`  
- `src/services/config_service.py`  
- Web Settings 相关设计

输出：

```text  
src/services/config_profile_service.py  
src/schemas/config_profile.py  
```

建议数据结构：

```text  
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

第一版可以先不建 DB 表，允许使用内存/配置文件注册 default profile；但接口必须为后续落库预留。

修改范围：

```text  
src/services/config_profile_service.py  
src/schemas/config_profile.py  
tests/services/test_config_profile_service.py  
```

前置依赖：

- `WRF-S0-002`

可并行：

- `WRF-S1-002`

验收标准：

- 默认存在 `default -> config/app.yaml`。  
- 能通过 `config_profile_id` 解析到服务端白名单内的 config path。  
- 不允许解析任意前端传入路径。  
- 有最小单元测试覆盖 default profile、未知 profile、非法路径。

完成情况：

- 待填写。

备注：

不要把 YAML 改成 `profiles:` 大容器；保持现有 `app.yaml` 结构。

---

### [ ] WRF-S1-002 P0 新增配置 hash 与快照能力

目标：

为每次 Workflow/Job 运行记录配置版本，保证历史任务可追溯和可回放。

输入：

- `ConfigProfileService`  
- `ConfigService`  
- `JobService`  
- Artifact 目录规范

输出：

```text  
src/services/config_snapshot_service.py  
```

能力：

```text  
计算 config_hash  
生成脱敏 config summary  
保存 config snapshot artifact  
返回 config_snapshot_artifact_id  
```

Job 中应记录：

```json  
{  
  "config_profile_id": "default",  
  "config_path": "config/app.yaml",  
  "config_hash": "sha256:...",  
  "config_snapshot_artifact_id": "..."  
}  
```

修改范围：

```text  
src/services/config_snapshot_service.py  
src/services/job_service.py  
src/services/job_runner.py  
tests/services/test_config_snapshot_service.py  
tests/services/test_job_config_trace.py  
```

前置依赖：

- `WRF-S1-001`

可并行：

- `WRF-S1-003`

验收标准：

- 同一配置内容生成稳定 hash。  
- 配置修改后 hash 变化。  
- Job 创建或开始执行时能绑定配置快照。  
- 快照中敏感字段脱敏或以环境变量引用形式保存。  
- 历史 Job 能查看当时使用的 config hash。

完成情况：

- 待填写。

备注：

敏感字段不要明文写入 artifact，例如 cookie、api_key、password、token、secret、webhook。

---

### [ ] WRF-S1-003 P0 定义 RunContext

目标：

建立统一运行上下文，后续 Step / Workflow / Job / Dev CLI 都通过 RunContext 获取配置、actor、job_id、project_root 等信息。

输入：

- `ConfigProfileService`  
- `ConfigSnapshotService`  
- 现有 service 方法签名

输出：

```text  
src/workflows/context.py  
```

建议结构：

```python  
@dataclass  
class RunContext:  
    run_id: str  
    actor: str | None  
    config_profile_id: str  
    config_path: Path  
    config_hash: str  
    config_snapshot_artifact_id: str | None  
    project_root: Path  
    job_id: str | None = None  
    dry_run: bool = False  
```

修改范围：

```text  
src/workflows/context.py  
tests/workflows/test_run_context.py  
```

前置依赖：

- `WRF-S1-001`  
- `WRF-S1-002`

可并行：无。

验收标准：

- RunContext 可以从 `config_profile_id` 创建。  
- RunContext 不接受任意未校验的 `config_path`。  
- RunContext 包含 config hash 和 snapshot artifact id。  
- 单元测试覆盖 default profile 和非法 profile。

完成情况：

- 待填写。

备注：

后续 Step 不应再自己调用 `load_app_config("config/app.yaml")`，而应通过 RunContext 获取配置路径或配置对象。

---

### [ ] WRF-S1-004 P0 改造 Job 创建参数支持 config_profile_id

目标：

让 Web/API 创建 Job 时使用 `config_profile_id`，不再暴露 `config_path`。

输入：

- `api/routers/ui/jobs.py`  
- `src/services/job_registry.py`  
- `src/services/job_service.py`  
- `RunContext`

输出：

- Job create request 支持 `config_profile_id`。  
- Job detail response 返回配置追溯信息。

修改范围：

```text  
api/routers/ui/jobs.py  
src/services/job_registry.py  
src/services/job_service.py  
src/services/job_runner.py  
tests/api/test_ui_jobs_config_profile.py  
```

前置依赖：

- `WRF-S1-001`  
- `WRF-S1-002`  
- `WRF-S1-003`

可并行：无。

验收标准：

- 创建 Job 时可传 `config_profile_id=default`。  
- 不允许通过 API 传任意 `config_path`。  
- Job detail 返回 `config_profile_id`、`config_hash`、`config_snapshot_artifact_id`。  
- 旧 API 如仍兼容 `config_path`，必须只允许服务端白名单路径，并标记 deprecated。

完成情况：

- 待填写。

备注：

这个任务完成后，Web UI 只需要展示 Profile，不需要展示 YAML 路径输入框。

---

### [ ] WRF-S1-005 P0 Settings 页面配置摘要接口设计

目标：

为 Web Settings 页面提供 Profile 列表、当前 Profile、配置摘要、脱敏配置、校验状态。

输入：

- `ConfigProfileService`  
- `ConfigService`  
- `ConfigSnapshotService`  
- WebUserManual 中 Settings 页面说明

输出 API：

```text  
GET /api/ui/v1/settings/config-profiles  
GET /api/ui/v1/settings/config-profiles/{profile_id}  
POST /api/ui/v1/settings/config-profiles/{profile_id}/validate  
```

第一阶段只要求只读和校验，不要求编辑保存。

修改范围：

```text  
api/routers/ui/settings.py  
src/services/config_profile_service.py  
src/services/config_service.py  
tests/api/test_ui_settings_config_profiles.py  
```

前置依赖：

- `WRF-S1-001`  
- `WRF-S1-002`

可并行：无。

验收标准：

- viewer/operator/admin 均可查看脱敏摘要。  
- 只有 admin 可以看到更多诊断信息。  
- API 不返回明文 secret、token、cookie、password、api_key、webhook secret。  
- validate 能返回成功/失败、错误摘要和建议。

完成情况：

- 待填写。

备注：

编辑、保存、恢复配置可以放到后续 Stage 5 或 Stage 8，不阻塞 article_pipeline 样板。

---

## 5. Stage 2：Step 协议与 article_pipeline 样板（P0）

### Stage 目标

- 定义统一 Step 协议。  
- 以 article_pipeline 为样板，把当前 pipeline-run / pipeline-step 的核心链路拆成可组合 Step。  
- 让 article_pipeline 可以通过 WorkflowRunner 跑通，但先不要求所有 Web UI 完整改造。  
- 旧 CLI 只作为薄包装调用新 Step / Workflow。

### 阶段完成标准

- StepResult、StepInput、StepRunner 基础协议可用。  
- article_pipeline 的 Step 至少覆盖 crawl / clean / validate / store / extract。  
- article_pipeline 能通过 WorkflowRunner 跑通一次样例链路。  
- 旧 pipeline-run / pipeline-step 不再拥有主要编排逻辑。

---

### [ ] WRF-S2-001 P0 定义 Step 协议与 StepResult

目标：

统一所有 Step 的输入、输出、错误、产物和日志语义。

输入：

- `RunContext`  
- 当前 `ServiceResult`  
- Job artifact 目录规范

输出：

```text  
src/workflows/step.py  
src/workflows/result.py  
```

建议结构：

```python  
@dataclass  
class ArtifactRef:  
    kind: str  
    path: str  
    title: str | None = None  
    previewable: bool = False  
    metadata: dict = field(default_factory=dict)

@dataclass  
class StepResult:  
    status: Literal["success", "failed", "skipped"]  
    message: str  
    payload: dict = field(default_factory=dict)  
    artifacts: list[ArtifactRef] = field(default_factory=list)  
    warnings: list[str] = field(default_factory=list)  
    error: dict | None = None  
```

修改范围：

```text  
src/workflows/step.py  
src/workflows/result.py  
tests/workflows/test_step_result.py  
```

前置依赖：

- `WRF-S1-003`

可并行：

- `WRF-S2-002`

验收标准：

- StepResult 可序列化为 JSON。  
- StepResult 能表达 success / failed / skipped。  
- ArtifactRef 能被 Job / Artifact Center 后续消费。  
- 不依赖 Typer、FastAPI、具体 UI。

完成情况：

- 待填写。

备注：

StepResult 是后续 Web 任务详情页展示 Step Timeline 的基础。

---

### [ ] WRF-S2-002 P0 定义 Step Registry

目标：

建立 Step 注册机制，后续 Workflow 通过名称引用 Step。

输入：

- Step 协议  
- article_pipeline Step 规划

输出：

```text  
src/workflows/step_registry.py  
```

能力：

```text  
register_step(name, handler, input_schema, description)  
get_step(name)  
list_steps()  
validate_step_input(name, payload)  
```

修改范围：

```text  
src/workflows/step_registry.py  
tests/workflows/test_step_registry.py  
```

前置依赖：

- `WRF-S2-001`

可并行：

- `WRF-S2-003`

验收标准：

- 可以注册和查询 Step。  
- 未注册 Step 返回结构化错误。  
- Step input schema 可以校验参数。  
- article_pipeline 相关 Step 可注册。

完成情况：

- 待填写。

备注：

没有注册到 Step Registry 的业务动作，不允许被 Workflow 调用。

---

### [ ] WRF-S2-003 P0 定义 StepRunner

目标：

实现统一 Step 执行器，负责调用 Step、捕获错误、规范化结果、写入日志钩子。

输入：

- `RunContext`  
- `StepRegistry`  
- `StepResult`

输出：

```text  
src/workflows/step_runner.py  
```

能力：

```text  
run_step(step_name, input_payload, context)  
捕获异常并转为 StepResult failed  
记录开始/结束时间  
返回 artifacts / warnings / payload  
```

修改范围：

```text  
src/workflows/step_runner.py  
tests/workflows/test_step_runner.py  
```

前置依赖：

- `WRF-S2-001`  
- `WRF-S2-002`

可并行：无。

验收标准：

- StepRunner 可以执行已注册 Step。  
- Step 抛异常时不会导致进程无结构退出，而是返回 failed StepResult。  
- StepRunner 不依赖 CLI。  
- 有成功、失败、参数错误测试。

完成情况：

- 待填写。

备注：

JobRunner 后续应调用 WorkflowRunner / StepRunner，而不是直接调用具体业务 service。

---

### [ ] WRF-S2-004 P0 拆分 crawl_articles Step

目标：

将文章抓取动作从 CLI / pipeline-run 中拆成独立 Step。

输入：

- 现有 crawl 命令逻辑  
- `PipelineService`  
- `crawl.sources` 配置  
- `RunContext`

输出：

```text  
src/workflows/steps/articles/crawl_articles.py  
```

Step 输入建议：

```text  
source optional  
author_id optional  
max_articles optional  
use_db boolean  
force boolean optional  
```

Step 输出建议：

```text  
raw_count  
raw_file_artifact optional  
raw_table_written boolean  
crawl_state_summary  
```

修改范围：

```text  
src/workflows/steps/articles/crawl_articles.py  
src/workflows/steps/articles/__init__.py  
tests/workflows/steps/articles/test_crawl_articles.py  
```

前置依赖：

- `WRF-S2-001`  
- `WRF-S2-002`  
- `WRF-S2-003`

可并行：

- `WRF-S2-005`

验收标准：

- Step 可单独执行。  
- Step 使用 RunContext 中的配置。  
- Step 不直接依赖 Typer。  
- StepResult 中包含抓取数量和 artifact 引用。  
- 失败时返回结构化错误。

完成情况：

- 待填写。

备注：

如果当前抓取强依赖真实网络，可先用 mock provider / sample 数据完成测试。

---

### [ ] WRF-S2-005 P0 拆分 clean_articles Step

目标：

将文章清洗动作拆成独立 Step，支持从 raw file 或 raw_articles 表读取。

输入：

- 当前 clean pipeline 逻辑  
- crawl_articles 输出  
- `RunContext`

输出：

```text  
src/workflows/steps/articles/clean_articles.py  
```

Step 输入建议：

```text  
input_artifact_id optional  
use_db boolean  
max_articles optional  
force boolean optional  
```

Step 输出建议：

```text  
cleaned_count  
cleaned_file_artifact  
skipped_count  
warnings  
```

修改范围：

```text  
src/workflows/steps/articles/clean_articles.py  
tests/workflows/steps/articles/test_clean_articles.py  
```

前置依赖：

- `WRF-S2-001`  
- `WRF-S2-002`  
- `WRF-S2-003`

可并行：

- `WRF-S2-004`  
- `WRF-S2-006`

验收标准：

- Step 可单独执行。  
- 缺少输入时返回清晰错误。  
- 输出 cleaned artifact。  
- 支持 use_db 路径的最小测试或 mock 测试。

完成情况：

- 待填写。

备注：

不要把“自动查找前置文件”的复杂逻辑留在 CLI；应由 Workflow 上下文传递 artifact。

---

### [ ] WRF-S2-006 P0 拆分 validate_articles Step

目标：

将文章校验与富化动作拆成独立 Step。

输入：

- clean_articles 输出  
- 当前 validate pipeline 逻辑

输出：

```text  
src/workflows/steps/articles/validate_articles.py  
```

Step 输入建议：

```text  
cleaned_artifact_id  
max_articles optional  
force boolean optional  
```

Step 输出建议：

```text  
validated_count  
invalid_count  
validated_file_artifact  
warnings  
```

修改范围：

```text  
src/workflows/steps/articles/validate_articles.py  
tests/workflows/steps/articles/test_validate_articles.py  
```

前置依赖：

- `WRF-S2-005`

可并行：无。

验收标准：

- Step 可单独执行。  
- 输入缺失或格式错误时返回 failed StepResult。  
- 输出 validated artifact。  
- 有最小样例测试。

完成情况：

- 待填写。

备注：

校验失败的记录数量应进入 payload，不能只写日志。

---

### [ ] WRF-S2-007 P0 拆分 store_articles Step

目标：

将文章入库动作拆成独立 Step，负责写入 `blog_articles` / 生成 pending tasks。

输入：

- validate_articles 输出  
- 当前 store pipeline 逻辑  
- DB session

输出：

```text  
src/workflows/steps/articles/store_articles.py  
```

Step 输入建议：

```text  
validated_artifact_id  
max_articles optional  
force boolean optional  
```

Step 输出建议：

```text  
inserted_count  
updated_count  
skipped_count  
pending_tasks_artifact  
```

修改范围：

```text  
src/workflows/steps/articles/store_articles.py  
tests/workflows/steps/articles/test_store_articles.py  
```

前置依赖：

- `WRF-S2-006`

可并行：无。

验收标准：

- Step 可单独执行。  
- 成功写入测试数据库或 mock repository。  
- 输出 pending tasks artifact。  
- 幂等行为明确：重复运行不会产生不可控重复数据。

完成情况：

- 待填写。

备注：

这是 article_pipeline 的关键 Step，必须优先保证可测试性。

---

### [ ] WRF-S2-008 P0 拆分 extract_article_metadata Step

目标：

将文章元数据抽取动作拆成独立 Step，负责从 pending tasks 或数据库读取文章并写入 `article_metadata`。

输入：

- store_articles 输出  
- 当前 process/extract 逻辑  
- LLM 配置

输出：

```text  
src/workflows/steps/articles/extract_article_metadata.py  
```

Step 输入建议：

```text  
pending_tasks_artifact_id optional  
new_version optional  
limit optional  
force boolean optional  
```

Step 输出建议：

```text  
processed_count  
skipped_count  
failed_count  
metadata_count  
clusters_artifact optional  
```

修改范围：

```text  
src/workflows/steps/articles/extract_article_metadata.py  
tests/workflows/steps/articles/test_extract_article_metadata.py  
```

前置依赖：

- `WRF-S2-007`

可并行：无。

验收标准：

- Step 可单独执行。  
- 支持无真实 LLM 的 fallback/mock 测试。  
- 输出 processed/skipped/failed 数量。  
- 失败文章不导致整个 Step 无结构崩溃。

完成情况：

- 待填写。

备注：

LLM 相关错误必须脱敏，不应在日志中输出 API key。

---

### [ ] WRF-S2-009 P0 定义 article_pipeline Workflow 样板

目标：

将 article 相关 Step 编排成第一个可运行 Workflow 样板。

输入：

- `crawl_articles`  
- `clean_articles`  
- `validate_articles`  
- `store_articles`  
- `extract_article_metadata`  
- `StepRunner`

输出：

```text  
src/workflows/definitions/article_pipeline.py  
src/workflows/workflow_runner.py  
```

Workflow 输入建议：

```text  
config_profile_id  
max_articles optional  
use_db boolean  
force boolean  
new_version optional  
skip_crawl boolean optional  
from_step optional  
```

修改范围：

```text  
src/workflows/definitions/article_pipeline.py  
src/workflows/workflow_runner.py  
tests/workflows/test_article_pipeline_workflow.py  
```

前置依赖：

- `WRF-S2-004`  
- `WRF-S2-005`  
- `WRF-S2-006`  
- `WRF-S2-007`  
- `WRF-S2-008`

可并行：无。

验收标准：

- WorkflowRunner 可以执行 article_pipeline。  
- 每个 Step 的 StepResult 被记录。  
- 失败时能知道失败在哪个 Step。  
- 支持最小样例从 crawl/mock 到 metadata/mock 的完整运行。  
- 不依赖 CLI。

完成情况：

- 待填写。

备注：

这是进入后续 Stage 3 的门槛任务。

---

### [ ] WRF-S2-010 P0 改造旧 pipeline-run 为 article_pipeline 薄包装

目标：

让旧 CLI 的 `pipeline-run` 不再直接编排业务逻辑，而是调用 `article_pipeline` Workflow。

输入：

- `article_pipeline`  
- 当前 `cli/main.py pipeline-run`  
- `PipelineService`

输出：

- 旧 CLI pipeline-run 调用 WorkflowRunner。  
- CLI 输出只负责渲染 WorkflowResult。

修改范围：

```text  
cli/main.py  
src/services/pipeline_service.py  
tests/cli/test_pipeline_run_wrapper.py  
```

前置依赖：

- `WRF-S2-009`

可并行：

- `WRF-S2-011`

验收标准：

- CLI pipeline-run 仍可用。  
- CLI 中不再保留主要业务编排逻辑。  
- CLI 参数转换为 article_pipeline 输入。  
- CLI 标记为兼容/开发入口，不作为正式用户入口。

完成情况：

- 待填写。

备注：

不要在此任务中删除 CLI；只做薄包装改造。

---

### [ ] WRF-S2-011 P0 改造旧 pipeline-step 为 StepRunner 薄包装

目标：

让旧 CLI 的 `pipeline-step` 调用 StepRunner，而不是直接执行散落逻辑。

输入：

- StepRegistry  
- StepRunner  
- 当前 `pipeline-step` 命令

输出：

- CLI pipeline-step 调用注册 Step。

修改范围：

```text  
cli/main.py  
src/services/pipeline_service.py  
tests/cli/test_pipeline_step_wrapper.py  
```

前置依赖：

- `WRF-S2-002`  
- `WRF-S2-003`  
- `WRF-S2-004` ~ `WRF-S2-008`

可并行：

- `WRF-S2-010`

验收标准：

- CLI pipeline-step 仍可单步执行已注册 Step。  
- 未注册 step 返回清晰错误。  
- CLI 不再自己查找复杂前置文件；前置 artifact 由参数或 Workflow 上下文传递。  
- 保留必要的兼容提示。

完成情况：

- 待填写。

备注：

如果历史自动发现文件机制必须暂时保留，应标记为 deprecated，并放在兼容层，不进入 Step 内部。

---

### [ ] WRF-S2-012 P0 让 JobRunner 可执行 article_pipeline

目标：

让 Job Center 能执行 article_pipeline 样板，为 Web 工作流接入做准备。

输入：

- `article_pipeline`  
- `WorkflowRunner`  
- `JobRunner`  
- `JobService`  
- `RunContext`

输出：

- Job type 或 workflow job 支持 article_pipeline。  
- Job 结果包含 step_results。

修改范围：

```text  
src/services/job_registry.py  
src/services/job_runner.py  
src/services/job_service.py  
tests/services/test_job_runner_article_pipeline.py  
```

前置依赖：

- `WRF-S1-004`  
- `WRF-S2-009`

可并行：无。

验收标准：

- 可以创建 article_pipeline Job。  
- JobRunner 执行时创建 RunContext。  
- Job 记录 config_profile_id / config_hash / config_snapshot_artifact_id。  
- Job result 中包含每个 Step 的状态和产物。  
- 失败时 Job error 能指出失败 Step。

完成情况：

- 待填写。

备注：

如果当前 JobRegistry 只允许 `pipeline-run`，可以先让 `pipeline-run` 映射到 `article_pipeline`，后续再收敛为 `workflow.run`。

---

### [ ] WRF-S2-013 P0 增加 article_pipeline 最小验收测试

目标：

建立第一个 Web-only 重构样板的自动化验收，防止后续拆分破坏链路。

输入：

- `article_pipeline`  
- StepRunner  
- JobRunner  
- 测试数据库或 mock repository  
- sample article 数据

输出：

```text  
tests/e2e/test_article_pipeline_webonly.py  
```

测试场景：

```text  
1. 创建 RunContext(default profile)  
2. 运行 article_pipeline  
3. 检查 Step 状态  
4. 检查 artifact 输出  
5. 检查 blog_articles / article_metadata mock 或测试库写入  
6. 检查配置 hash 已记录  
7. 检查失败时可定位 Step  
```

修改范围：

```text  
tests/e2e/test_article_pipeline_webonly.py  
tests/fixtures/articles/*  
```

前置依赖：

- `WRF-S2-009`  
- `WRF-S2-012`

可并行：无。

验收标准：

- 一条测试能证明 article_pipeline 样板跑通。  
- 测试不依赖真实外部网络。  
- 测试不依赖真实 LLM API。  
- 失败时输出能定位到具体 Step。

完成情况：

- 待填写。

备注：

这个任务完成后，才允许细化 Stage 3 及之后任务。

---

## 6. 后续阶段占位：article_pipeline 样板跑通后再细化

### [~] Stage 3：Workflow Registry / Runner 完整化

暂不细化。

触发条件：

```text  
WRF-S2-013 完成，article_pipeline 样板通过 E2E 验收。  
```

预计内容：

```text  
Workflow Registry 完整化  
Workflow Definition API  
Workflow 参数 schema  
Workflow 权限/风险等级  
Workflow 审计  
失败 Step 重跑语义  
```

---

### [~] Stage 4：Job Center 收敛

暂不细化。

触发条件：

```text  
article_pipeline Job 可稳定执行并返回 step_results。  
```

预计内容：

```text  
Job type 收敛  
step_results 持久化  
Job 日志按 Step 分组  
Job artifacts 按 Step 分组  
取消/重试/重跑语义统一  
```

---

### [~] Stage 5：Web UI 改造

暂不细化。

触发条件：

```text  
后端能返回 workflow definition 和 step_results。  
```

预计内容：

```text  
工作流页面展示 Step 列表  
任务详情页展示 Step Timeline  
失败 Step 重跑按钮  
Artifact 按 workflow/step 过滤  
Settings 配置 Profile 页面  
```

---

### [~] Stage 6：CLI 降级与退役

暂不细化。

触发条件：

```text  
article_pipeline、snapshot_pipeline、pre_market_pipeline、after_close_pipeline 均可通过 Web/API/Job 运行。  
```

预计内容：

```text  
旧 CLI 标记 deprecated  
新增 tools/dev_cli.py  
UserManual CLI 归档  
WebUserManual 成为主用户手册  
```

---

### [~] Stage 7：Provider / 市场数据扩展规范落地

暂不细化。

触发条件：

```text  
Step / Workflow / Job / Artifact Registry 模式稳定。  
```

预计内容：

```text  
Provider Registry  
Capability Registry  
新增市场数据流程模板  
新增 Provider PR checklist  
raw / normalized / snapshot 标准  
```

---

### [~] Stage 8：E2E、Contract Test 与最终验收

暂不细化。

触发条件：

```text  
主要 Workflow 已迁移。  
```

预计内容：

```text  
主链路 E2E  
Step Contract Test  
Workflow Contract Test  
API Contract Test  
Artifact Schema Test  
权限与风险操作测试  
```

---

### [~] Stage 9：文档收敛

暂不细化。

触发条件：

```text  
Web-only 主链路稳定，旧 CLI 已降级。  
```

预计内容：

```text  
更新 Project.md  
更新 需求.md  
更新 WebUserManual.md  
归档 UserManual.md  
更新 APIReference.md  
更新 Web-UserManual-Coverage.md  
```

---

## 7. 当前推荐执行顺序

```text  
1. WRF-S0-001 建迁移矩阵  
2. WRF-S0-002 写开发约束  
3. WRF-S0-003 做 CLI 耦合审计  
4. WRF-S0-004 明确 article_pipeline 样板范围  
5. WRF-S1-001 定义 Config Profile  
6. WRF-S1-002 增加配置 hash / snapshot  
7. WRF-S1-003 定义 RunContext  
8. WRF-S1-004 改造 Job 创建参数  
9. WRF-S1-005 增加 Settings 配置摘要 API  
10. WRF-S2-001 ~ WRF-S2-003 定义 Step 基础设施  
11. WRF-S2-004 ~ WRF-S2-008 拆 article Step  
12. WRF-S2-009 定义 article_pipeline Workflow  
13. WRF-S2-010 / WRF-S2-011 降级旧 CLI 为薄包装  
14. WRF-S2-012 接入 JobRunner  
15. WRF-S2-013 完成样板 E2E 验收  
```

---

## 8. 每个 PR 必须检查

```text  
[ ] 是否新增/修改了 Service Step？  
[ ] 是否修改了 Step Input/Output？  
[ ] 是否修改了 Workflow？  
[ ] 是否修改了 Job Type？  
[ ] 是否修改了 Artifact？  
[ ] 是否修改了 Config Profile / RunContext？  
[ ] 是否修改了权限或风险等级？  
[ ] 是否需要同步 Web UI？  
[ ] 是否需要同步 WebUserManual？  
[ ] 是否需要同步 APIReference？  
[ ] 是否需要更新迁移矩阵？  
[ ] 是否保留了旧 CLI 兼容？  
[ ] 如果不保留，是否写了 deprecated 说明？  
[ ] 是否补了单元测试或 E2E 验收？  
```  
