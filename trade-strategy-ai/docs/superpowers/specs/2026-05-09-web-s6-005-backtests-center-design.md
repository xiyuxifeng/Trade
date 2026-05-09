# WEB-S6-005 Backtests Center Design

> 目标：把 Web 回测中心从占位页升级为一个可执行、可追踪、可验证的分析工作台，支持回测结果浏览、回测任务发起、规则验真、可复现性检查入口和关键指标查看。

## 1. 设计目标

### 1.1 核心目标

- 提供一个面向分析场景的回测工作台，而不是简单的结果列表页。
- 复用现有 `backtest_results` 查询接口和 `jobs` 任务中心，不新增一套重复的后端结果体系。
- 让用户在同一个页面完成三类动作：
  - 发起回测任务
  - 查看回测结果、报告和规则验真内容
  - 追踪回测复现检查的 Job 结果
- 提供关键指标摘要和轻量图表，便于快速判断某次回测是否值得继续深入。

### 1.2 设计边界

- 不在本任务中新增后端回测 API。
- 不在页面内直接执行长任务，所有运行类动作必须提交为 Job。
- 不把回测中心做成通用报表中心，也不把所有回测能力塞进一个超长单页。
- 可复现性检查只负责任务提交与结果追踪，不新增独立算法实现。

## 2. 功能范围

### 2.1 必须支持

- 回测结果列表查询
- 回测结果详情查看
- 回测 Markdown 报告查看
- 规则验真报告查看
- 回测任务提交
- 规则验真任务提交
- 可复现性检查任务提交
- 关键指标摘要
- 轻量趋势图或条形图

### 2.2 暂不支持

- 回测结果编辑
- 回测结果删除
- 回测结果批量重算
- 服务端图表渲染
- 自定义回测引擎参数扩展
- 规则池回测独立页面

## 3. 数据与接口契约

### 3.1 结果查询接口

页面读取现有 `api/routers/backtest_results.py` 提供的文件型接口：

- `GET /backtest_results/`
- `GET /backtest_results/{result_id}`
- `GET /backtest_results/{result_id}/report`
- `GET /backtest_results/{result_id}/validate_rules`

结果列表按文件读取，页面只负责展示和筛选，不负责重写结果存储策略。
由于这组接口当前并未挂在 `/api/ui/v1` 下，前端需要使用独立的请求封装直接访问根路径，并在请求头中保持与现有 UI 请求一致的 `X-API-Key` 传递规则。

### 3.2 任务提交接口

页面通过现有 Job API 提交三类任务：

- `backtest-run`
- `backtest-validate-rules`
- `backtest-reproducibility-check`

提交内容必须显式包含：

- `trader_id`
- `date_from`
- `date_to`
- `strategy_version_id`（可选）
- `mode`
- `config_path`

### 3.3 前端契约类型

回测中心前端需要新增独立的 API 封装与类型定义，用于隔离页面逻辑：

- `web/src/lib/api/backtests.ts`
- `web/src/types/backtests.ts`

前端类型至少覆盖：

- 回测列表条目
- 回测详情
- 回测总结
- 回测记录
- 规则验真报告摘要
- 回测 Job 提交参数

## 4. 页面架构

### 4.1 总体布局

页面采用“主从分栏工作台”布局：

- 左侧：任务提交区 + 结果筛选区 + 回测结果列表
- 右侧：选中结果详情 + 指标摘要 + 报告 / 验真 / JSON 详情切换

该布局优先服务分析任务，因为用户通常会先筛选某次回测，再深入看指标和报告。

### 4.2 顶部任务提交区

顶部区域放在左侧栏最上方，包含三个独立提交卡片或分组表单：

- `Run backtest`
- `Validate rules`
- `Reproducibility check`

三个入口共享基础字段，但按钮和 Job type 不同。
提交后页面只显示 Job ID 和跳转 Jobs Center 的入口，不在本页阻塞等待长任务完成。

### 4.3 左侧结果列表

左侧结果列表按以下条件过滤：

- `trader_id`
- `date_from`
- `date_to`
- `skip / limit`

列表项至少展示：

- `result_id`
- `trader_id`
- 日期范围
- 胜率或总交易数
- 最近更新时间或文件名

### 4.4 右侧详情区

右侧详情区采用标签页：

- `Summary`
- `Records`
- `Report`
- `Validation`
- `JSON`

其中：

- `Summary` 展示总天数、交易数、有效交易数、跳过交易数、胜率、平均收益率
- `Records` 展示交易记录表或列表
- `Report` 展示 Markdown 渲染结果或下载入口
- `Validation` 展示规则验真摘要和 Markdown 渲染结果或下载入口
- `JSON` 展示原始回测 JSON

## 5. 视觉与交互

### 5.1 视觉方向

沿用 Web 控制台的深色数据面板风格，并与现有页面保持一致：

- 深色背景
- 高信息密度
- 绿色表示正收益或通过
- 红色表示失败或负收益
- 中性灰表示空状态和未选中状态

### 5.2 关键交互

- 结果列表支持点击选中。
- 任务提交按钮必须有 pending 状态。
- 选中结果变化后，详情区自动刷新。
- 报告和验真内容使用只读预览，不允许直接执行脚本。
- 回测结果无内容时显示空状态，而不是空白区域。

### 5.3 图表策略

为了避免引入额外依赖，回测中心使用轻量 SVG 图表：

- 一条收益率折线，按交易记录顺序展示 `return_pct`
- 一个胜负/跳过状态的简易计数条

图表只作为“快速判断”工具，不替代完整分析报表。

## 6. 组件拆分

### 6.1 新增组件

- `web/src/features/backtests/backtests-center.tsx`
  - 页面主体
  - 查询状态组合
  - 结果选择
  - 任务提交
- `web/src/lib/api/backtests.ts`
  - 回测结果查询封装
  - 报告下载封装
  - 规则验真报告下载封装
- `web/src/types/backtests.ts`
  - 后端契约类型
- `web/src/pages/backtests/index.tsx`
  - 页面路由出口
- `web/src/pages/backtests/index.test.tsx`
  - 页面行为测试

### 6.2 复用组件

优先复用现有组件：

- `PageHeader`
- `Card`
- `Tabs`
- `Badge`
- `Button`
- `Input`
- `Select`
- `Skeleton`

如需下载或跳转提示，沿用 Jobs / Snapshots / Reports 页面已验证的交互模式。

## 7. 错误处理与空状态

### 7.1 错误处理

- API 失败时显示明确错误信息。
- Job 提交失败时保留当前表单输入，便于用户修正后重试。
- 某条回测结果 JSON 解析失败时，只屏蔽该条详情，不影响列表。
- 报告文件不存在时提供“无报告文件”的明确提示。

### 7.2 空状态

- 列表为空时显示“当前筛选范围内暂无回测结果”。
- 详情未选中时显示引导态。
- 报告或规则验真内容缺失时显示占位文本，而不是空白面板。

## 8. 测试策略

### 8.1 必须新增的测试

- 页面能渲染结果列表和详情壳子
- 页面能调用 `backtest-run` Job 提交
- 页面能调用 `backtest-validate-rules` Job 提交
- 页面能调用 `backtest-reproducibility-check` Job 提交
- 页面能加载回测详情并展示 summary / records / json
- 页面能展示回测报告和规则验真入口

### 8.2 测试文件

- `web/src/pages/backtests/index.test.tsx`

### 8.3 验证命令

- `corepack pnpm test src/pages/backtests/index.test.tsx`
- `corepack pnpm typecheck`
- `corepack pnpm lint`
- `corepack pnpm build`

## 9. 验收标准

### 9.1 功能验收

- 能在 Web 上提交回测、规则验真和可复现性检查 Job。
- 能浏览回测结果列表并打开详情。
- 能查看回测结果摘要、记录、JSON 和报告。
- 能查看规则验真结果和对应报告。
- 能看到关键指标摘要和轻量图表。

### 9.2 工程验收

- 页面逻辑不直接依赖临时 mock 数据。
- 前端类型和 API 封装与后端契约一致。
- 新增测试能稳定覆盖主要交互路径。
- 现有 `Jobs`、`Reports`、`Snapshots` 页面不被回归破坏。

## 10. 不在本任务内的内容

- 不实现规则池回测专页。
- 不调整后端 `backtest_results` 存储格式。
- 不引入新的图表库。
- 不重构 Jobs Center。
- 不把回测中心拆成多个独立路由页，先保持单页工作台。
