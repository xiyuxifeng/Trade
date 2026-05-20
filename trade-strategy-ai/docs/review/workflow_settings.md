# workflow_settings.md

## 目标

把当前关于配置入口、系统管理和 `config_path` 迁移的讨论，整理成一份后续可直接执行的修改清单。

这份清单的原则是：

- Web 端以 `Profile / Profile Snapshot` 作为正式配置模型。
- CLI 继续保留 `config_path` 兼容能力。
- `/settings` 不再作为正式 Web 配置入口。
- 系统管理页面按最新需求文档实现。
- `backup_dir` 必须限制为白名单目录，不允许任意服务端绝对路径输入。

---

## TaskList

### Task 1: 路由与入口收敛

- [x] 保留 Sidebar 中的 `配置管理 -> /profiles`。
- [x] 新增或保留 `系统管理 -> /system`。
- [x] 从 Sidebar 和路由注册中移除 `安装与配置`、`数据库维护` 和正式 `/settings` 入口。
- [x] 明确 `/settings` 的过渡策略：短期兼容跳转或直接移除。

### Task 2: Profile 作为 Web 唯一配置模型

- [x] 保留 `/profiles` 作为 Web 唯一正式配置入口。
- [x] 支持 Profile 列表、详情、导入、编辑、校验、保存新版本、归档、Snapshot 查看。
- [x] Web 表单和提交参数移除 `config_path` 的直接输入，改为 `profile_id` / `profile_snapshot_id`。
- [x] 保证历史 Job 仍然引用创建时的 Snapshot，不受后续 Profile 修改影响。

### Task 3: 系统管理页面实现

- [x] 按最新需求文档实现 `/system` 页面。
- [x] 系统管理页面保留高风险操作的确认流程和结构化错误展示。
- [x] 数据库迁移、数据备份、数据恢复以 Job 方式创建并跳转 Job Detail。
- [x] 权限与审计、用户管理、系统健康检查不创建 Job，直接走页面内查询 / 提交。
- [x] 系统管理页面包含 `数据库迁移`、`数据备份`、`数据恢复` `权限与审计`、`用户管理`、`系统健康检查` 三个功能。

### Task 4: 数据库迁移、备份、恢复与白名单

- [x] 数据库迁移、数据备份、数据恢复从工作流页迁移到系统管理页。
- [x] 数据备份和数据恢复都使用 `profile_id` 作为必填项。
- [x] `include_processed` 和 `force` 改为 checkbox。
- [x] `backup_dir` 只能从后端白名单目录中选择，不允许任意绝对路径输入。
- [x] 恢复优先使用 `backup_id`，仅在短期兼容场景下保留受限的 `backup_dir`。

### Task 5: 后端兼容层与工作流清理

- [x] Job 参数模型同时支持 Web 的 Profile 参数和 CLI 的 `config_path` 兼容参数。
- [x] 后端新增或复用 `resolve_runtime_config(params)` 一类解析层。
- [x] 审计记录中包含 actor、job_type、profile_id、profile_snapshot_id、operation、confirmed、risk、created_at。
- [x] 权限与审计、用户管理、系统健康检查使用独立管理 API，不依赖 Job 参数模型。
- [x] 从默认工作流列表中移除 `install-config` 和 `database`，并删除旧 Settings 页面相关实现。

---

## 落地顺序

### 第一优先级

1. 确认最新系统管理页面需求边界。
2. 收敛路由与 Sidebar。
3. 确认 `/settings` 的下线策略。

### 第二优先级

1. 完成 Profile 作为 Web 唯一配置模型的收口。
2. 完成系统管理页面的基础结构。
3. 把数据库迁移、备份、恢复迁移到系统管理。

### 第三优先级

1. 把 `backup_dir` 收敛为白名单选择。
2. 清理工作流页中旧的系统管理能力。
3. 删除旧 Settings 页面和相关 API。

### 第四优先级

1. 整理后端兼容层和审计。
2. 补齐测试。
3. 回收文档与 TaskList。

---

## 验收标准

- [x] Web 正式入口只保留 `/profiles` 和 `/system`。
- [x] Web 页面不再要求用户输入 `config_path`。
- [x] CLI 仍可使用 `--config-path`。
- [x] 系统管理页面按最新需求文档完成。
- [x] 数据库迁移、备份、恢复均通过 Profile 运行。
- [x] 权限与审计页面可查询并展示系统审计信息。
- [x] 用户管理支持添加用户、删除用户、修改用户权限、修改用户密码。
- [x] 系统健康检查可直接查看结果，不需要创建 Job。
- [x] `backup_dir` 只能从白名单目录中选择。
- [x] `include_processed` 和 `force` 都是 checkbox。
- [x] 所有高风险操作都有确认弹窗。
- [x] 数据库迁移、数据备份、数据恢复提交后创建 Job，并可跳转 Job Detail。
- [x] 权限与审计、用户管理、系统健康检查不创建 Job。
- [x] 旧 `/settings` 不再出现在正式导航中。
- [x] 工作流页不再包含 `install-config` 和 `database`。
- [x] 历史 Job 仍可追溯到原始 Snapshot。

---

## 不在本次直接修改的项

- [ ] 不移除 CLI 的 `config_path` 兼容能力。
- [ ] 不在 Web 中保留任意绝对路径输入框。
- [ ] 不把系统管理功能继续放回工作流页。
- [ ] 不把 `Profile` 编辑做成覆盖历史版本的行为。
