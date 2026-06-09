# Architecture Boundary Rules

## 1. Architecture Freeze Rules

以下模块属于架构冻结层，修改前必须先分析影响范围，并获得用户确认：

- strategy schema
- workflow DAG
- provider interface
- article pipeline
- profile / config system
- backtest result schema
- task orchestration
- API contract
- database schema
- Web / CLI 边界

---

## 2. 修改前必须输出

涉及架构冻结层时，必须先输出：

```md
## 计划修改的内容

## 影响范围

## 风险

## 替代方案

## 推荐方案

## 是否需要用户确认
```

用户确认前不得修改。

---

## 3. Web / CLI 收敛约束

涉及 CLI -> Web 演进时：

- 不允许无计划删除 CLI 能力
- 不允许生成第二套 schema
- 不允许 UI 与后端 contract 脱节
- 不允许临时兼容层没有收口任务
- 不允许绕过现有 Job / Workflow / Web 体系重新造一套

推荐原则：

- 优先收敛
- 优先复用现有 Workflow / Job
- 新旧 schema 若需要并存，必须有迁移和收口计划
- 临时桥接必须有 TaskList 追踪

---

## 4. Config / Profile 约束

涉及 config / profile system 时：

- 不允许隐式改变配置语义
- 不允许把用户级配置和系统级配置混在一起
- 不允许硬编码 Provider / Market / Strategy 参数
- 不允许引入无法迁移的临时配置格式

如果要引入 Profile：

必须说明：

- Profile 的边界
- 与旧 config 的兼容关系
- 迁移路径
- UI 管理方式
- 默认值策略
- 后续收口任务

---

## 5. API Contract 约束

修改 API contract 前必须确认：

- 请求字段
- 响应字段
- 错误结构
- 兼容性
- UI 使用点
- 测试覆盖
- 文档更新

禁止：

- 后端字段改变但 UI 不更新
- UI 依赖不存在字段
- mock contract 与真实 API 不一致
- 错误态没有统一处理

---

## 6. Database / Migration 约束

修改 database schema 或 migration 前必须确认：

- 影响表
- 数据迁移方案
- 回滚方案
- 兼容性
- 是否影响已有数据
- 是否需要备份

未经确认，不得执行不可逆 migration。
