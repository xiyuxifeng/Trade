# 2026-05-09 WEB-S8-006 E2E Acceptance Plan

> 目标：把 Web 后台的端到端验收测试拆成可落地、可追踪、可回放的浏览器主链路，避免 Stage 8 只停留在构建和单测层。

## 背景

`WEB-S8-006` 的目标不是再验证一次组件单测，而是验证浏览器视角下的完整交互链路。它应覆盖真实用户最关心的操作，而不是追求把所有页面都写成 E2E。

## E2E 主链路

### 1. Jobs 主链路

- 从 `/jobs?jobId=<id>` 进入详情抽屉。
- 查看参数、日志和产物引用。
- 发起 rerun 并确认新的 Job 已创建。
- 取消一个可取消的运行中 Job。

### 2. Workflows 主链路

- 从 `/workflows/:workflowId` 打开向导。
- 填写参数并触发 Job 创建。
- 高风险工作流必须看到确认弹窗。
- 提交后跳转到 Jobs 详情。

### 3. Artifacts 主链路

- 从 Jobs 详情跳转到 Artifacts Center。
- 使用 `jobId` 过滤查看产物。
- 打开可预览产物并执行下载。

### 4. Settings 主链路

- 打开配置中心。
- 查看脱敏配置。
- 提交配置校验。
- 保存前必须经过二次确认，保存失败要保留原值。

### 5. Auth / Permission 主链路

- viewer 只能查看。
- operator 不能执行高风险配置动作。
- admin 可以执行高风险动作并看到审计结果。

## 执行清单

### Phase 1: E2E 基线

- [ ] 选择并安装浏览器测试工具链。
- [ ] 固化 mock/snapshot 数据入口。
- [ ] 建立 E2E 公共登录、跳转和断言辅助。

### Phase 2: Jobs / Workflows

- [ ] 覆盖 Jobs 深链、详情抽屉、rerun 和取消。
- [ ] 覆盖 Workflows 提交、确认弹窗和跳转 Jobs。
- [ ] 补齐失败路径：Job 创建失败和高风险拒绝。

### Phase 3: Artifacts / Settings

- [ ] 覆盖 Jobs 到 Artifacts 的联动跳转。
- [ ] 覆盖 Artifacts 过滤、预览和下载。
- [ ] 覆盖 Settings 的脱敏显示、校验、保存和回滚。

### Phase 4: 权限与审计

- [ ] 覆盖 viewer / operator / admin 的权限边界。
- [ ] 覆盖高风险操作拒绝和审计可见性。
- [ ] 记录最终验收结论和残余风险。

## 验收标准

- 至少覆盖以上五条主链路中的核心 happy path。
- 至少覆盖失败路径：
  - Job 创建失败
  - 高风险确认拒绝
  - 权限拒绝
  - 产物不可预览
  - 配置校验失败
- E2E 数据优先使用 mock/snapshot，不依赖真实外网。

## 追踪方式

- 在 `docs/Web-TaskList.md` 里继续保留 `WEB-S8-006` 作为总入口。
- 具体实现时，可在本计划下再拆子任务或分批验收。
- 完成后把验证结论写回 `daily-sessions` 和 `daily-report`。

## 备注

- 这份计划不要求现在就引入所有页面的端到端测试，只追踪 Stage 8 必要主链路。
- 若后续决定引入 Playwright 或类似工具，再单独补安装和脚本任务，不和本计划混在一起。
