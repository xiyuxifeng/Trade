# WEB-S6-007 Strategy Studio Design

> 目标：把策略版本、优化建议和规则池审核整合进一个高密度的 `Strategy Studio` 工作台，支持版本浏览、优化预览、候选版本生成和规则池审核，不再让用户在多个割裂页面之间切换。

## 1. 设计目标

### 1.1 核心目标

- 提供一个单页工作台，让用户围绕同一批策略上下文完成「看版本 -> 做优化 -> 审规则」的闭环。
- 复用现有的 `StrategyLibraryService`、`OptimizeService` 和 `RulePoolService`，避免重复建设一套新的策略数据体系。
- 把前端和内部 service 层隔离开，前端只调用 UI BFF，不直接依赖文件路径或服务内部实现细节。
- 支持高密度信息展示，方便分析型用户快速对比版本、识别风险、推进候选版本和规则审核。

### 1.2 设计边界

- 不把策略管理拆成多个独立路由页，本任务先保持一个主工作台。
- 不让前端直接传 `adjustments_path`、`parent_path` 这类文件系统参数。
- 不在本任务中重构底层策略建模逻辑，只做 UI 和 UI BFF 收口。
- 不新增新的优化算法；优化结果只做展示、整理和候选版本生成。

## 2. 功能范围

### 2.1 必须支持

- 策略版本列表查询
- 策略版本详情查看
- 版本推荐、证据引用和规则快照查看
- 优化建议摘要查看
- 候选版本生成
- 规则池列表查询
- 规则详情查看
- 单条审核
- 批量审核
- 规则映射与审核状态筛选

### 2.2 暂不支持

- 策略版本编辑
- 策略版本删除
- 候选版本自动发布
- 规则池数据回写之外的复杂编辑
- 独立的优化算法页面
- 独立的规则池专页

## 3. 数据与接口契约

### 3.1 UI BFF 设计

为了避免前端直连 service 层，新增一个策略工作台 UI BFF：

- `api/routers/ui/strategy_studio.py`
- 路由前缀：`/api/ui/v1/strategy-studio`

这一层负责把前端请求转换为现有 service 调用，并统一返回结构。
前端只依赖 BFF，不依赖文件路径，也不直接依赖 `src/services/*` 的内部签名。

### 3.2 版本接口

BFF 需要提供以下版本接口：

- `GET /api/ui/v1/strategy-studio/versions`
- `GET /api/ui/v1/strategy-studio/versions/{version_id}`

列表返回的摘要至少包含：

- `version_id`
- `trader_id`
- `strategy_date`
- `status`
- `version_type`
- `parent_version_id`
- `recommendations_count`
- `source_article_ids_count`
- `released_at`
- `has_rules_snapshot`

详情返回的完整内容至少包含：

- `version_id`
- `trader_id`
- `strategy_date`
- `status`
- `version_type`
- `parent_version_id`
- `recommendations`
- `source_article_ids`
- `evidence_refs`
- `notes`
- `released_at`
- `rules_snapshot`

### 3.3 优化接口

BFF 需要提供以下优化接口：

- `POST /api/ui/v1/strategy-studio/optimize/advise-rule-validations`
- `POST /api/ui/v1/strategy-studio/optimize/filter-active-traders`
- `POST /api/ui/v1/strategy-studio/optimize/create-candidate`

前端请求体必须是 UI 友好的 JSON，不暴露文件路径。
候选版本生成的请求体至少包含：

- `parent_version_id`
- `trader_id`
- `strategy_date`
- `adjustments`
- `recommendations`
- `notes`

其中 `adjustments` 由 UI BFF 直接转换为 `StrategyAdjustment` 所需字段，前端不能知道 `依据` 这种内部字段名。
如果底层 `OptimizeService` 仍保留文件路径签名，BFF 负责在服务端临时落盘并清理，不能把这个实现细节泄漏到前端。

### 3.4 规则池接口

BFF 需要提供以下规则池接口：

- `GET /api/ui/v1/strategy-studio/rule-pool`
- `GET /api/ui/v1/strategy-studio/rule-pool/{rule_id}`
- `POST /api/ui/v1/strategy-studio/rule-pool/{rule_id}/review`
- `POST /api/ui/v1/strategy-studio/rule-pool/review-batch`

规则池列表支持以下筛选项：

- `status`
- `rule_type`
- `mapping_status`
- `source_type`
- `instrument_focus`
- `skip_no_mapped`
- `skip`
- `limit`

如果现有 `RulePoolService.list_rules()` 的筛选能力不够，实施时需要先补齐 service 或 repository 级别的查询参数，再由 BFF 暴露给前端。

列表返回至少包含：

- `rule_id`
- `source_type`
- `rule_type`
- `instrument_focus`
- `mapping_status`
- `review_status`
- `initial_confidence`
- `validated_confidence`
- `backtest_result`
- `backtest_hits`
- `backtest_misses`
- `backtest_samples`

### 3.5 前端契约类型

新增前端独立类型与 API 封装：

- `web/src/lib/api/strategyStudio.ts`
- `web/src/types/strategyStudio.ts`

前端类型至少覆盖：

- 策略版本摘要
- 策略版本详情
- 优化建议摘要
- 候选版本生成请求和结果
- 规则池条目摘要
- 规则池详情
- 单条审核请求
- 批量审核请求

## 4. 页面架构

### 4.1 总体布局

页面采用 `Strategy Studio` 主从三栏工作台：

- 左侧：策略版本列表与筛选
- 中间：当前选中版本详情与优化面板
- 右侧：规则池列表与审核面板

这个布局的目标是把同一条上下文链路放在同一屏里，减少用户在页面之间跳转的成本。

### 4.2 顶部信息条

页面顶部放一个摘要条，用来快速展示：

- 当前选中的 `trader_id`
- 当前日期或版本日期
- 当前版本状态
- 候选版本数量
- 待审核规则数量
- 已通过规则数量

顶部还放三个全局动作：

- 刷新数据
- 切换 trader 或日期
- 快速回到最近一次选中的版本

### 4.3 左侧版本列表

左侧面板负责版本查询和选择，支持：

- `trader_id`
- `strategy_date`
- `status`
- `version_type`
- `skip / limit`

列表项至少展示：

- `version_id`
- `status`
- `version_type`
- `strategy_date`
- `recommendations_count`
- `released_at`

点击版本后：

- 中间面板刷新版本详情
- 优化面板以该版本作为上下文
- 规则池面板根据该版本的规则快照或 trader/date 维度刷新

### 4.4 中间版本详情与优化面板

中间区域分两段：

1. 版本详情
2. 优化建议与候选版本生成

版本详情至少展示：

- 推荐列表
- 证据引用
- 规则快照
- 备注
- 发布状态

优化面板至少展示：

- 规则验真摘要
- 版本对比摘要
- 候选版本预览
- 调整建议列表

候选版本生成按钮的行为：

- 只对当前选中的版本生效
- 生成成功后返回候选版本摘要
- 页面保留当前版本选择，不自动跳转

### 4.5 右侧规则池面板

右侧面板负责规则池检视与审核，支持：

- 规则列表筛选
- 单条规则详情查看
- 单条审核
- 批量审核

列表项至少展示：

- `rule_id`
- `rule_type`
- `source_type`
- `mapping_status`
- `review_status`
- `confidence`
- `mapped`

规则详情至少展示：

- 来源文章 ID
- 提取层原始条件
- 映射后的条件
- 置信度变化
- 回测结果
- 使用次数

### 4.6 窄屏行为

移动端或窄屏下，三栏折叠为标签页：

- `Versions`
- `Optimize`
- `Rule Pool`

当前选中项和筛选条件在切换标签后保持不丢失。

## 5. 视觉与交互

### 5.1 视觉方向

沿用项目当前控制台语言，基于 `ui-ux-pro-max` 的数据密度建议，采用：

- 深色控制台底色
- 蓝色作为主要信息色
- 琥珀色表示风险、待审核或需注意状态
- 绿色表示通过、有效或可发布状态
- 灰色表示空状态和未选中状态

文字风格保持克制，不引入花哨装饰，重点放在信息层次和密度。

### 5.2 关键交互

- 选择版本后，其余两个面板立即切换到对应上下文。
- 规则审核必须明确显示当前决策，避免误点。
- 候选版本生成按钮需要 pending 状态和成功反馈。
- 批量审核必须先显示命中数量，再允许提交。
- 空列表和空详情必须显示明确引导，不允许出现空白区域。

### 5.3 摘要展示策略

页面顶部和卡片摘要只显示最重要的聚合字段：

- 版本数量
- 待审核数量
- 已通过数量
- 关键置信度
- 回测命中率

完整细节放到详情面板，不在摘要区堆满原始 JSON。

## 6. 组件拆分

### 6.1 新增组件

- `web/src/features/strategy-studio/strategy-studio.tsx`
  - 页面主体
  - 三栏布局
  - 版本选择
  - 优化动作
  - 规则审核联动
- `web/src/lib/api/strategyStudio.ts`
  - 版本、优化、规则池的前端请求封装
- `web/src/types/strategyStudio.ts`
  - 前端数据类型定义
- `web/src/pages/strategy-studio/index.tsx`
  - 路由出口
- `web/src/pages/strategy-studio/index.test.tsx`
  - 页面行为测试

### 6.2 后端新增或修改

- `api/routers/ui/strategy_studio.py`
  - 策略工作台 UI BFF
- `api/routers/ui/__init__.py`
  - 注册新的 UI 路由
- `api/routers/__init__.py`
  - 如需按现有模式导出 UI router，则补充导入

### 6.3 复用组件

优先复用现有组件：

- `PageHeader`
- `Card`
- `Tabs`
- `Badge`
- `Button`
- `Input`
- `Select`
- `Textarea`
- `Dialog`
- `Skeleton`

## 7. 错误处理与空状态

### 7.1 错误处理

- 版本列表加载失败时展示明确错误，并保留筛选项。
- 版本详情不存在时显示「版本未找到」，不影响列表和规则池。
- 候选版本生成失败时保留当前输入和当前版本选择。
- 单条审核失败时只刷新当前规则，不影响整个列表。
- 批量审核失败时保留已选规则和筛选条件。

### 7.2 空状态

- 版本列表为空时显示当前筛选条件下没有匹配版本。
- 版本详情未选中时显示引导态，提示先在左侧选择一个版本。
- 规则池列表为空时显示当前筛选条件下没有规则。
- 优化面板未获得上下文时显示「请选择一个版本后再查看优化建议」。

## 8. 测试策略

### 8.1 必须新增的测试

- 页面能渲染三栏工作台壳子
- 页面能在选择版本后刷新详情和规则池上下文
- 页面能提交候选版本生成请求
- 页面能发起单条规则审核
- 页面能发起批量规则审核
- 页面在空版本列表、空规则列表和错误状态下有明确文案

### 8.2 测试文件

- `web/src/pages/strategy-studio/index.test.tsx`
- `web/src/lib/api/strategyStudio.test.ts`
- `tests/api/routers/ui/test_strategy_studio.py`

### 8.3 验证命令

- `pnpm test src/pages/strategy-studio/index.test.tsx src/lib/api/strategyStudio.test.ts`
- `pnpm typecheck`
- `pnpm lint`
- `pnpm build`

## 9. 验收标准

### 9.1 功能验收

- 能在 Web 上浏览策略版本列表和版本详情。
- 能看到版本推荐、证据引用和规则快照。
- 能提交优化请求并生成候选版本预览。
- 能浏览规则池列表和规则详情。
- 能单条和批量审核规则。
- 能在同一个页面完成版本、优化和规则池三类操作。

### 9.2 工程验收

- 前端不直接依赖文件路径参数。
- 前端类型与 UI BFF 契约一致。
- 版本、优化和规则池的接口边界清晰。
- 新增测试覆盖主要交互路径。
- 现有 Jobs、Reports、Snapshots、Backtests、Alerts 页面不被回归破坏。

## 10. 不在本任务内的内容

- 不新增独立的策略版本详情页。
- 不新增独立的优化页。
- 不新增独立的规则池页。
- 不实现新的优化算法。
- 不重构底层 repository 或数据库模型。

## 11. 未来扩展

以下能力保留给后续 Stage 10 或后续独立任务，不计入 `WEB-S6-007` 的主验收：

- `策略版本编辑`
  - 适合后续单独做成受审计保护的编辑流程。
- `策略版本删除`
  - 更推荐演进为归档、隐藏或软删除，不建议直接物理删除。
- `候选版本自动发布`
  - 作为设置项 `auto_release_candidate` 保留，默认关闭。
  - 如果启用，也必须先经过候选版本完整校验和人工确认条件。
