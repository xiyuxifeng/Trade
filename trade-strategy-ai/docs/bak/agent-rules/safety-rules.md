# Safety Rules

## 1. Forbidden Actions

未经用户明确确认，禁止执行以下操作。

### 文件与数据

- 删除文件
- 覆盖重要文档
- 清空目录
- 清理 cookie / key / token / secret
- 修改数据库内容
- 删除数据库表
- 执行不可逆 migration

### 架构与依赖

- 大规模重构
- 修改数据库 schema
- 修改 provider interface
- 修改 workflow DAG
- 修改 orchestration layer
- 引入新 framework
- 主动升级依赖
- 修改 deployment 配置
- 修改 CI/CD

### Task 与文档

- 创建重复 Task 编号
- 修改 `ACTIVE_TASK_LIST` 但不记录原因
- 将未验收任务标记为 `DONE`
- 在 `daily-report` 中夸大完成度
- 把临时结论写成最终结论
- 重复写入 session/report 造成状态漂移

### UI / API

- 隐式修改 API contract
- UI 与 API contract 不同步
- 使用 mock 数据但不标注
- 新增页面但不补 Loading / Error / Empty / Retry 状态

---

## 2. 敏感信息与安全规范

敏感信息包括：

- cookie
- token
- API key
- secret
- database password
- private key
- 个人账号信息
- 未脱敏日志

要求：

- 不在输出中暴露敏感信息
- 不将敏感信息写入 `daily-report`
- 必要时仅在 `daily-sessions` 中写“已清理 / 待清理”，不要写具体值
- 清理敏感信息前必须获得用户确认
- 如果发现敏感信息已写入文档，必须提醒用户处理

---

## 3. 数据库停止规则

会话结束时如用户要求停止数据库，使用：

```bash
brew services stop postgresql@15
```

不得未经确认主动停止数据库。

---

## 4. 资源与成本意识

执行高成本操作前必须确认范围和影响。

高成本操作包括：

- 全量数据回测
- 大规模数据爬取
- 大模型批量生成
- 长时间 benchmark
- 大规模测试矩阵
- 大量文件批量重写
- 数据库批量写入或清理

优先使用：

- cache
- snapshot
- fixture
- 小样本验证
- 增量执行

执行前应说明：

```md
## 操作范围

## 预计影响

## 可替代方案

## 推荐执行方式
```
