# UI-V2-002 用户视角信息架构与浅色工作台设计

## 目标

将 `trade-strategy-ai` 的 V2 Web UI 从 Demo 风格收敛为面向最终交付用户的正式工作台。

这份 IA 的核心目标不是“展示所有能力”，而是让用户能够稳定地完成以下任务：

1. 快速判断系统是否可用。
2. 快速找到并管理 Profile。
3. 通过 Profile 或兼容的 `config_path` 完成导入。
4. 查看 Job、Snapshot、Artifact 的运行结果。
5. 以低认知成本理解当前工作流状态。

## 设计原则

### 0. UI 文案中文优先

面向用户展示的界面文案尽量使用中文，优先保证业务含义清楚、操作指向明确。

允许保留英文原词的场景：

- API 字段名或技术标识必须和后端对齐时。
- 详情页中必须展示的系统字段名，例如 `profile_id`、`config_hash`。
- 用户已广泛认知且不宜翻译歧义的产品名，例如 `Job`、`Profile`、`Snapshot`。

主导航、按钮、空状态、错误提示、导入说明、校验提示应优先使用中文表达。

### 1. 先任务，后功能

导航和首屏不按技术模块堆叠，而按用户实际任务组织。

用户进入系统后，首先应该知道：

- 现在系统是否健康。
- 我应该先看什么。
- 我应该去哪里创建、导入或复盘。

### 2. 单一正式入口

每个业务概念只保留一个 canonical 入口。

- `Profile` 是正式对象。
- `Job` 是执行记录。
- `Snapshot` 是只读历史记录。
- `legacy` 入口只保留兼容层，不进入主导航。

### 3. 术语稳定

主界面优先使用最终交付语义：

- `Profile`
- `Job`
- `Workflow`
- `Artifact`
- `Market`
- `Strategy`

避免在主导航和首屏暴露过多实现词：

- `config_path`
- `snapshot`
- `migration`
- `masked_snapshot`

这些词只允许出现在详情页、高级信息区或导入流程中。

### 4. 安全默认

所有可能影响运行结果的操作都必须先预览、再校验、再提交。

- Secret 永远不展示原文。
- 导入必须先展示脱敏预览。
- Profile 编辑必须先通过基本校验。
- Snapshot 只能只读查看，不允许回写。

### 5. 状态完整

每个用户可见页面都必须考虑以下状态：

- Loading
- Empty
- Error
- Retry
- Permission denied

用户不应该进入一个“空白但看不出原因”的页面。

## 信息架构

### 顶层导航

建议的主导航顺序如下：

1. Dashboard
2. Jobs
3. Profiles
4. Workflows
5. Artifacts
6. Market Data
7. Strategy
8. Backtest
9. Admin
10. Settings

#### 说明

- `Dashboard` 放在最前面，用来回答“系统现在是否正常”。
- `Jobs` 放在前列，因为用户最常做的是查看运行记录和结果。
- `Profiles` 必须是正式一级入口，因为它是 V2 的核心业务对象。
- `Workflows` 负责承接流程化触发。
- `Artifacts` 用于复盘和结果下载。
- `Market Data`、`Strategy`、`Backtest` 属于业务工作台能力。
- `Admin` 放在靠后位置，避免打断业务用户的日常路径。
- `Settings` 只承载系统配置、账号和连接信息，不承载业务主对象。

### 次级入口

以下内容不进入主导航：

- legacy 路由
- 迁移工具
- 调试页
- 旧 Demo 页面

它们只允许出现在：

- 兼容层
- 详情页高级区
- 文档说明

## 页面结构

### 1. Dashboard

Dashboard 是用户进入系统后的第一站，只回答三个问题：

1. 系统是否正常。
2. 最近的任务是否成功。
3. 下一步应该去哪里。

首屏建议包含：

- 关键状态摘要
- 最近 Job
- 最近 Artifact
- Profile 快捷入口
- 兼容入口提示

不建议在首页堆叠太多图表或技术配置。

### 2. Profiles

Profiles 是 V2 的核心正式入口，采用“列表 -> 详情 -> 导入 -> 只读快照”的结构。

#### Profile List

列表只展示对用户决策最重要的字段：

- name
- environment
- status
- updated_at
- validation_status

用户进入列表页后，应该能快速判断：

- 哪个 Profile 是默认或常用的。
- 哪个 Profile 校验通过。
- 哪个 Profile 最近更新。

#### Profile Detail

详情页按信息分组，不直接暴露完整原始配置。

建议分区：

- 基础信息
- 配置 sections
- 脱敏字段
- 校验结果
- 关联 Job
- 只读 snapshot 入口

用户在详情页里应该先理解“这个 Profile 是什么”，再看“它能不能用”，最后才看“它被哪些 Job 用过”。

#### Profile Import

导入页是从旧 `config_path` 走向正式 Profile 的迁移入口。

导入流程建议分三步：

1. 输入 `config_path`。
2. 显示脱敏预览。
3. 校验后保存。

导入页必须明确告诉用户：

- 仍兼容旧配置路径。
- 新建的是正式 Profile。
- Secret 不会暴露原文。

#### Snapshot Viewer

Snapshot Viewer 只读，目标是帮助用户复盘历史 Job。

建议展示：

- linked job
- config_hash
- source
- captured_at
- validation_status
- masked sections

Snapshot 页面不允许编辑，不允许写回 Profile。

### 3. Jobs

Jobs 页是执行中心，不是配置中心。

用户在 Jobs 页最关心的是：

- 当前状态
- 是否完成
- 结果是否可复盘
- 是否能跳到对应 Snapshot 或 Artifact

Job Detail 要把配置快照、执行结果、日志和 Artifact 放在同一条复盘链路里，但主视觉优先级仍然是“任务状态”和“结果摘要”。

### 4. Workflows

Workflows 页面负责承接引导式流程。

要求：

- 清晰的入口说明。
- 清晰的运行态。
- 不把流程细节混成大段文字。

### 5. Artifacts

Artifacts 页面负责展示任务产物。

用户应该能快速回答：

- 这个产物是什么。
- 谁生成的。
- 能不能下载。
- 跟哪个 Job 相关。

### 6. Settings

Settings 只放系统级配置：

- API 连接
- 认证信息
- 显示偏好
- 兼容入口说明

不建议把业务主对象放在 Settings 中。

## 浅色视觉方向

### 视觉基调

整体风格采用浅色调的企业极简工作台，强调：

- 白色或近白背景
- 低饱和灰蓝中性色
- 轻量边框
- 细腻层次
- 较高留白

### 推荐色彩策略

建议使用以下方向，而不是强紫或高饱和色：

- Background: `#F8FAFC`
- Surface: `#FFFFFF`
- Surface soft: `#F1F5F9`
- Border: `#E2E8F0`
- Text primary: `#0F172A`
- Text secondary: `#475569`
- Accent: `#2563EB`
- Success: `#16A34A`
- Warning: `#D97706`
- Danger: `#DC2626`

### 字体建议

推荐使用更适合企业工作台的无衬线字体组合：

- Heading: `Poppins`
- Body: `Open Sans`

如果项目希望更偏阅读友好和稳定，也可以切换为：

- Heading: `Lexend`
- Body: `Source Sans 3`

不建议在正式工作台里继续使用偏代码感太强的标题字体作为主视觉。

### 卡片与层次

- 卡片使用白底和轻边框，不用重阴影。
- 主要信息与次要信息分层展示。
- Hover 只做轻微颜色和边框变化。
- 不使用夸张动效。

## 用户路径

### 路径 1：先看系统，再进入 Profile

1. 用户打开 Dashboard。
2. 用户看到系统健康和最近 Job。
3. 用户点击 Profiles。
4. 用户查看列表和校验状态。
5. 用户进入详情或导入。

### 路径 2：从旧配置迁移到正式 Profile

1. 用户进入 Profiles。
2. 用户选择 Import。
3. 用户输入 `config_path`。
4. 页面展示脱敏预览和校验结果。
5. 用户确认保存为正式 Profile。

### 路径 3：复盘历史 Job

1. 用户进入 Jobs。
2. 用户打开 Job Detail。
3. 用户查看配置快照和 Artifact。
4. 用户跳转只读 Snapshot。
5. 用户理解这次运行对应的 Profile 状态。

## 兼容策略

### legacy 入口

legacy 入口必须满足以下要求：

- 不进入主导航。
- 不作为正式业务入口宣传。
- 只用于历史书签和过渡跳转。
- 有明确退役阶段。

### config_path

`config_path` 仍可作为导入入口，但不再作为正式长期对象的首选呈现方式。

用户层面的表达应为：

- 可从旧配置导入
- 推荐转为 Profile
- 迁移后以 Profile 为正式对象

## 验收口径

这套 IA 的验收重点不在“页面数量”，而在以下结果：

1. 用户是否能快速找到 Profile。
2. 用户是否能区分 Profile、Job、Snapshot 的角色。
3. 用户是否能安全导入旧配置。
4. 用户是否能从 Job 顺畅跳到复盘信息。
5. 页面是否符合浅色、正式、克制的工作台风格。

## 建议的实现顺序

1. 先完成导航和 Dashboard 的正式入口组织。
2. 再完成 `Profiles` 的列表、详情和导入。
3. 然后补齐 Snapshot Viewer 与 Job 的跳转链路。
4. 最后收口 legacy 入口和 Settings 的系统化表达。
