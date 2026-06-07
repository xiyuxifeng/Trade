# 一级入口与子入口对照表

> 这份文档用于把重构后的一级入口进一步下钻，明确每个入口下面哪些子入口保留、替换、废弃。
>
> 目标不是保留所有历史页面，而是只保留真正服务最终用户目标的子入口。

---

## 1. 口径说明

- **保留**：继续作为正式用户入口或正式子入口存在。
- **替换**：路径可能保留，但页面名称、导航位置、文案或职责需要改。
- **废弃**：不再作为正式入口出现，可保留短期兼容跳转，但不能进入主导航。

---

## 1.1 入口去向总表

| 一级入口 | 路径保留 / 能力保留 | 对外替换 | 废弃为主入口 |
|---|---|---|---|
| 文章与规则 | `/articles`, `/articles/list`, `/articles/quality`, `/articles/results` | `/articles/run` 的页面表达 | `/articles/jobs`, `/articles/maintenance` |
| 回测与画像 | `/backtest`, `/backtest/regime`, `/rule-pool`, `/rule-pool/:ruleId`, `/persona` | `/strategies/regime-selection` 的页面表达 | `/strategies` |
| 盘前分析 | `/strategies/pre-market` | 无 | `/strategies`, `/workflows/pre-market`, `/workflows/pre-market/run` |
| 盘后复盘 | `/strategies/after-close` | 无 | `/workflows/after-close`, `/workflows/after-close/run` |
| 市场上下文 | `/market`, `/market/snapshots`, `/market/datasets`, `/market/kaipan`, `/market/ohlcv` | `/market` 及其子页的对外表达 | 无 |
| Job List | `/jobs`, `/jobs/:jobId` | 无 | `/articles/jobs` |
| Dashboard | `/dashboard` | 无 | 无 |
| 配置与管理 | `/profiles`, `/profiles/import`, `/profiles/:profileId`, `/profiles/:profileId/edit`, `/profiles/:profileId/snapshots/:snapshotId`, `/system`, `/system/audit`, `/system/users`, `/system/health`, `/system/db-migrate`, `/system/backup` | `/profiles`、`/system` 的对外表达 | `/system/restore`, `/admin`, `/admin/audit`, `/settings` |
| 告警 | 无 | 无 | `/alerts` |

---

## 2. 文章与规则

一级入口目标：

- 导入文章
- 提取规则
- 查看规则结果
- 进入后续验证流程

核心子入口：

- 文章导入 / 处理
- 文章列表
- 规则抽取结果
- 规则详情
- 处理质量
- 任务列表
- 结果中心

处理建议：

| 子入口 | 处理 |
|---|---|
| `/articles` | 保留，替换为 `文章与规则` 的主入口 |
| `/articles/run` | 保留，替换为 `文章导入 / 处理` |
| `/articles/list` | 保留 |
| `/articles/quality` | 保留 |
| `/articles/results` | 保留，作为结果查看页 |
| `/articles/jobs` | 废弃为主入口，改为跳转 `/jobs` |
| `/articles/maintenance` | 废弃为主入口，必要时仅作为高级维护兼容页 |

结论：

- 文章与规则是用户主链路起点，必须保留。
- 任务查看不要再在文章下单独形成一套任务中心。

---

## 3. 回测与画像

一级入口目标：

- 验证规则可信度
- 形成交易员风格画像
- 判断规则适用市场阶段

核心子入口：

- 回测工作台
- Regime 回测
- 规则池审核
- Persona / 画像详情

处理建议：

| 子入口 | 处理 |
|---|---|
| `/backtest` | 保留，替换为 `回测与画像` 主入口 |
| `/backtest/regime` | 保留，作为高级回测视图 |
| `/rule-pool` | 保留或并入回测结果页，若保留则替换为 `规则审核` |
| `/rule-pool/:ruleId` | 保留，作为规则审核详情 |
| `/persona` | 保留，替换为 `交易员画像` |
| `/strategies/regime-selection` | 替换或并入回测/画像流程，不作为独立一级入口 |

结论：

- 回测与画像是一条主链路，规则审核可以作为辅助子入口。
- 不要让 `策略` 作为一级入口再出现。

---

## 4. 盘前分析

一级入口目标：

- 结合规则、画像和当天市场上下文生成盘前建议
- 输出当天可执行的关注对象和判断依据

核心子入口：

- 盘前分析首页
- 候选关注对象
- 今日市场上下文
- 盘前建议
- 规则解释

处理建议：

| 子入口 | 处理 |
|---|---|
| `/strategies/pre-market` | 保留，替换为 `盘前分析` |
| `/strategies` | 替换为盘前分析概览或废弃为主入口 |
| `/workflows/pre-market` | 废弃为主入口，仅保留兼容跳转 |
| `/workflows/pre-market/run` | 废弃为主入口，仅保留兼容跳转 |

结论：

- 盘前分析必须是独立的一等入口。
- 不再使用 `workflows` 作为用户主入口名。

---

## 5. 盘后复盘

一级入口目标：

- 对照盘前判断验证当天是否命中
- 输出复盘结论和规则修正信号

核心子入口：

- 盘后复盘首页
- 盘前结论
- 盘后结果
- 复盘结论
- 偏差分析

处理建议：

| 子入口 | 处理 |
|---|---|
| `/strategies/after-close` | 保留，替换为 `盘后复盘` |
| `/workflows/after-close` | 废弃为主入口，仅保留兼容跳转 |
| `/workflows/after-close/run` | 废弃为主入口，仅保留兼容跳转 |

结论：

- 盘后复盘必须和盘前分析成对出现。
- `after-close` 只作为技术路径，不作为主叙事。

---

## 6. 市场上下文

一级入口目标：

- 浏览统一市场上下文快照
- 查看市场状态、质量、数据集和市场资产

核心子入口：

- 市场上下文总览
- 市场上下文快照
- 数据集浏览
- Kaipan 数据健康
- OHLCV 行情

处理建议：

| 子入口 | 处理 |
|---|---|
| `/market` | 保留，替换为 `市场上下文` |
| `/market/snapshots` | 保留，替换为 `市场上下文快照` |
| `/market/datasets` | 保留，替换为 `数据集浏览` 或 `市场数据资产` |
| `/market/kaipan` | 保留，替换为 `市场数据健康` |
| `/market/ohlcv` | 保留，替换为 `OHLCV 数据` |

结论：

- 市场上下文是主流程的输入层，但其中子页面偏数据浏览和运维，不能再被包装成主业务流程本身。

---

## 7. Job List

一级入口目标：

- 统一查看任务状态、进度、日志、结果和操作

核心子入口：

- Job 列表
- Job 详情
- Job 提交
- Job 暂停 / 恢复 / 取消 / 重试

处理建议：

| 子入口 | 处理 |
|---|---|
| `/jobs` | 保留，作为任务中心 |
| `/jobs/:jobId` | 保留，作为 Job 详情 |
| `/articles/jobs` | 废弃为主入口，统一跳转到 `/jobs` |

结论：

- Job 中心只能有一个。
- 不允许文章页再长出一套自己的任务中心。

---

## 8. Dashboard

一级入口目标：

- 提供全局概览和最近运行摘要

核心子入口：

- 全局状态摘要
- 最近 Job
- 最近产物
- 快速入口卡片

处理建议：

| 子入口 | 处理 |
|---|---|
| `/dashboard` | 保留，替换为概览页 |

结论：

- Dashboard 可以保留，但只能做概览，不承担主流程入口职责。

---

## 9. 配置与管理

一级入口目标：

- 管理 Profile、系统健康、审计和高风险运维动作

核心子入口：

- Profile 列表
- Profile 导入
- Profile 编辑
- Profile 快照
- 系统健康
- 审计
- 用户管理
- 数据库迁移
- 备份与恢复

处理建议：

| 子入口 | 处理 |
|---|---|
| `/profiles` | 保留，替换为 `配置与管理` |
| `/profiles/import` | 保留 |
| `/profiles/:profileId` | 保留 |
| `/profiles/:profileId/edit` | 保留 |
| `/profiles/:profileId/snapshots/:snapshotId` | 保留 |
| `/system` | 保留，作为系统管理总入口 |
| `/system/audit` | 保留 |
| `/system/users` | 保留 |
| `/system/health` | 保留 |
| `/system/db-migrate` | 保留，但应标为高风险 |
| `/system/backup` | 保留 |
| `/system/restore` | 废弃为主入口，统一并入备份与恢复 |
| `/admin` | 废弃为主入口，仅保留兼容跳转 |
| `/admin/audit` | 废弃为主入口，仅保留兼容跳转 |
| `/settings` | 废弃为主入口，仅保留兼容跳转 |

结论：

- 配置与管理保留，但必须下沉。
- 旧兼容入口不能继续出现在正式导航里。

---

## 10. Alert / 告警

一级入口目标：

- 当前不属于最终用户主链路

处理建议：

| 子入口 | 处理 |
|---|---|
| `/alerts` | 废弃为主入口，仅保留兼容或运维入口 |

结论：

- 告警不是当前主目标的一部分，不应出现在主导航。

---

## 11. 总结

从重构目标看，当前入口应分为三类：

### 必须保留

- `Job List`
- `文章与规则`
- `回测与画像`
- `盘前分析`
- `盘后复盘`
- `市场上下文`
- `Dashboard`（仅概览）
- `配置与管理`
- `系统管理`

### 必须替换

- `dashboard`
- `strategies`
- `market/snapshots`
- `market/datasets`
- `market/kaipan`
- `market/ohlcv`
- `rule-pool`
- `articles/run`
- `articles/jobs`
- `articles/maintenance`

### 必须废弃为主入口

- `workflows/*`
- `admin/*`
- `settings`
- `alerts`

这份对照表的目标，是让后续执行时一眼就能知道：

- 哪些入口是用户主流程的一部分
- 哪些入口只是辅助页面
- 哪些入口应该逐步退役
