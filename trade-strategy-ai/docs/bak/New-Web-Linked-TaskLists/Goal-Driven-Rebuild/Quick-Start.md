# Goal-Driven Rebuild 快速入口

这是一页式入口，用来在新 session 或重新进入任务时快速恢复上下文。

## 1. 先看什么

按下面顺序阅读：

1. [README.md](./README.md)
2. [TaskList.md](./TaskList.md)
3. [Implementation-Plan.md](./Implementation-Plan.md)
4. [Entry-Subentry-Matrix.md](./Entry-Subentry-Matrix.md)
5. 对应任务的必读文档

## 2. 这组文档分别负责什么

- `README.md`
  - 目录索引
- `TaskList.md`
  - 执行任务、顺序、约束、协作模板
- `Implementation-Plan.md`
  - 按 GD-R1 -> GD-R5 的实施顺序计划
- `Entry-Subentry-Matrix.md`
  - 一级入口与子入口的保留 / 替换 / 废弃对照表
- `Product-Usage-Flow.md`
  - 用户如何使用 Web
- `Market-Data-Contract.md`
  - 市场数据与 Job 的技术契约
- `Web-Navigation-and-Copy.md`
  - 页面和文案清单

## 3. 统一主线

```text
博客文章 -> 规则提取 -> 回测验证 -> 交易员画像 -> 盘前预测 -> 盘后复盘
```

任何任务、页面、Job、数据流、文案都必须服务于这条主线。

## 4. 标准协作方式

### 标准指令格式

```text
执行 <Task 编号>。
目标：<这一步要达成什么用户结果>。
允许范围：<允许修改哪些页面 / 路由 / 数据 / 逻辑 / 文案>。
约束：<必须围绕哪条主线，不能引入什么新概念>。
方式：<先 review 再实施，或直接实施>。
参考：Implementation-Plan.md、TaskList.md、Entry-Subentry-Matrix.md。
```

### 首次启动示例 / 高风险任务示例

```text
执行 GD-R1。
目标：统一 Web 主入口和入口分层。
允许范围：允许修改 / 删除 / 合并页面、路由、文案和必要逻辑。
约束：必须围绕“文章 -> 规则 -> 回测 -> 画像 -> 盘前 -> 盘后”主线，不要新增新的对外主概念。
方式：先给实施计划，再开始。
参考：Implementation-Plan.md、TaskList.md、Entry-Subentry-Matrix.md。
```

```text
执行 GD-R3。
目标：重构 Job 中心，让状态、统计、详情、操作清晰可见。
允许范围：允许修改 API、页面和必要的状态流转逻辑。
约束：Job 只做调度和状态记录，不要把业务转换塞进 Job。
方式：先 review 再实施。
参考：Implementation-Plan.md、TaskList.md、Entry-Subentry-Matrix.md。
```

### 最短版

```text
开始执行 GD-Rx。
目标：<一句话目标>
方式：<先 review 再实施 / 直接实施>
参考：Quick-Start.md
```

### 新 Session 恢复模板

```text
恢复 Goal-Driven-Rebuild。
当前任务：GD-Rx。
请先读取 README.md、TaskList.md、Implementation-Plan.md、Entry-Subentry-Matrix.md、对应必读文档，再继续。
目标：<一句话目标>。
允许范围：<允许改动范围>。
约束：<不能偏离什么>。
方式：<先 review 再实施，或直接实施>。
```

### 完成后 Review 模板

```text
review GD-Rx 的实现。
目标：<这一步想达成什么用户结果>。
重点：<检查哪些地方>。
范围：<只看代码 / 文档 / 前端 / 后端 / 全部>。
```

### 使用规则

- 开始任务时，优先用“开始执行 Task”或“最短版”模板。
- 任务完成后，优先用“完成后 Review Task”模板。
- 如果要强调检查严格程度，可以加上“按 code review 标准来，先列问题，按严重程度排序”。
- 如果要强调文档一致性，可以加上“对照 TaskList 和 Implementation-Plan”。
- 如果要强调主线一致性，可以加上“重点看是否偏离文章 -> 规则 -> 回测 -> 画像 -> 盘前 -> 盘后”。
