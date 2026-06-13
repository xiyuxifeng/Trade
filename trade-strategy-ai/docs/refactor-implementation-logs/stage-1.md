# Stage 1 实施记录

## Stage 摘要

- Stage：`Stage 1 产品信息架构与统一页面框架`
- 当前状态：`[x] 已完成`
- Task：`RT-S1-001`、`RT-S1-002`、`RT-S1-003`
- 代码与机械验收：已完成 Parent Review，未发现剩余代码 BLOCKER 或 required HIGH。
- UI 验收：用户已完成检查并确认当前 UI 可接受。
- 最终结论：Stage 1 已满足当前以功能实现和基本可用性为主的出口条件，允许进入 Stage 2。

## RT-S1-001 重构导航和路由

- 状态：`[x] 已完成并接受`。
- 修改范围：
  - 新增集中路由配置及测试。
  - Router、Sidebar、导航导出和 Route Registry 从集中配置派生。
  - 增加认证返回路径和路由级权限测试。
  - 共享导航改为普通用户可理解的业务中文。
- 关键契约：
  - 七个正式一级入口：首页、研究中心、规则与回测、作者画像、策略中心、每日交易、系统管理。
  - 49 条 Stage 0 路径统一标记为 `canonical` 或 `compat`。
  - `route-config.tsx` 是路由、导航、权限、元数据和兼容信息的唯一事实源。
  - `/dashboard`、`/articles` 等旧入口按迁移矩阵保留兼容，不进入普通用户主导航。
- 验证摘要：
  - 受影响测试 9 个文件、46 个测试通过。
  - 完整前端测试 77 个文件、218 个测试通过。
  - typecheck、lint、build、`git diff --check` 通过。

## RT-S1-002 建立统一页面体验

### Session A：共享框架和布局

- 状态：完成实现。
- 新增：`BusinessPageShell`、`SectionNav`、`CompatibilityNotice`、`ProductPageAdapter` 及测试。
- `DashboardLayout` 使用集中路由元数据和二级导航。
- `StatusStrip` 删除无业务价值的路径参数。
- 权限不足时显示真实原因、影响和返回动作。
- `PageAvailability` 固定为：`ready`、`loading`、`empty`、`error`、`partial`、`permission_denied`、`unavailable`。
- 验证摘要：
  - 共享组件 6 个文件、22 个测试通过。
  - 权限和布局组合 8 个文件、46 个测试通过。
  - 完整前端测试 82 个文件、239 个测试通过。
  - typecheck、lint、build、`git diff --check` 通过。

### Session B：正式领域页面装配

- 状态：完成初始装配，但 Parent Review 发现阻断问题。
- 使用 2 个边界独立的 Executor mini：研究领域和每日交易领域；Parent 保留共享契约、路由和跨域 Review。
- 17 个 canonical 子页面由迁移说明替换为正式页面组件。
- 研究、规则与回测、作者、策略、每日交易和适用系统页面接入统一页面契约。
- 正式路径不要求用户访问 `/jobs`、`/workflows`、`/artifacts` 或 `/market/*`。
- 兼容路径和旧页面默认行为保留。
- 初始验证摘要：
  - 指定测试 9 个文件、45 个测试通过。
  - 完整前端测试 87 个文件、268 个测试通过。
  - typecheck、lint、build、`git diff --check` 通过。

### Parent 严格复审与有限修复

- 委派：零子代理。
- 主要发现：
  - `HIGH`：管理员技术详情没有角色门槛，普通用户可看到工程信息。
  - `HIGH`：空基准、无记录和缺失统计被错误显示为默认、等待或零。
  - `HIGH`：`/rules/results` 未接回现有分市场状态结果组件。
  - `BLOCKER`：多个正式页面的真实旧能力只存在于管理员技术区，普通用户无法完成真实业务操作。
  - `HIGH`：状态矩阵没有从集中路由配置逐页派生。
  - `MEDIUM`：盘后状态和降级原因仍显示内部英文值。
- 有限修复：
  - 管理员技术区增加 `admin` 权限门槛。
  - 修正空值、无记录和缺失统计语义。
  - 受控接入现有分市场状态结果组件。
  - 非 `ready`/`partial` 状态不再显示主要业务动作。
- 验证摘要：19 个文件、109 个测试通过；typecheck 和 `git diff --check` 通过。
- 结论：当时仍有 BLOCKER 和 required HIGH，不允许进入 `RT-S1-003`。

### Parent 复审问题修复

- 委派：零子代理。
- 修改范围：
  - 为规则、回测结果、作者、策略和系统页面增加普通用户安全的 `productMode`。
  - 正式页面直接复用真实查询、动作和结果，不复制领域逻辑。
  - 系统配置、数据新鲜度、失败处理和告警摘要接入现有真实接口。
  - 盘后内部状态、部分数据和降级原因映射为业务中文。
  - `route-config.tsx` 增加统一页面渲染分类和状态投影，状态矩阵从集中配置派生。
- 关键契约：
  - `route-config.tsx` 继续是路由、导航、权限、元数据、兼容信息和状态矩阵页面清单的唯一事实源。
  - 兼容组件默认行为不变；只有显式 `productMode` 才隐藏工程参数。
  - 不可用数据不得转换为零、空集合或成功。
- 验证摘要：
  - 最终聚焦测试 19 个文件、113 个测试通过。
  - typecheck 和 `git diff --check` 通过。
- 结论：原 BLOCKER、required HIGH 和 MEDIUM 已修复；允许进入 `RT-S1-003`。

## RT-S1-003 首页改造

- 状态：`[x] 已完成并接受`。
- 委派：零子代理。首页聚合事实、API 契约和状态优先级相互依赖，由 Parent 直接实现。
- 修改范围：
  - 新增只读 `HomeDashboardService`，聚合已保存市场快照、盘前盘后运行、规则池、已发布策略、市场状态和失败运行。
  - 复用 `/api/ui/v1/system/dashboard`，增量加入业务日期、交易上下文、九项业务状态和下一步主操作。
  - 新增首页 Query Hook、组件和正式首页，替换旧快捷入口和产物工作台。
  - 缺失画像建议和策略建议时明确标记 `unavailable`，不返回零。
  - 聚合失败时返回 `unavailable` 和影响说明，不转换为空集合、false、零或成功。
  - 交易日历只读取已保存文件，不调用实时 Provider。
  - 清理集中兼容配置之外的 `/dashboard` 生产返回路径。
- 关键契约：
  - 首页不建立第二个 API 或前端缓存事实源。
  - 主操作优先级：补齐数据、今日盘前、最近盘后、规则审核、失败处理、查看今日状态。
  - 不创建 Stage 2 领域对象、数据库迁移或 Prompt。
- 验证摘要：
  - 后端聚焦测试 `10 passed`。
  - 前端 11 个文件、31 个测试通过。
  - typecheck 和 `git diff --check` 通过。
- 结论：代码范围、增量 API 契约、真实首页状态和聚焦回归通过。

## Stage 1 Parent 总验收

- 状态：`[x] 已完成并接受`
- 委派：零子代理；最终接受判断由 Parent 完成。
- Parent 修复：
  - 失败运行查询失败不再转换为空列表，首页改为真实 `unavailable`。
  - 新增 Web 验收入口，覆盖七个业务导航、正式业务旅程、技术工作台兼容隔离和 49 条历史路径。
  - 注册既有 `settings_router`，恢复 `/api/ui/v1/settings/*` OpenAPI 兼容合同。
  - 注册既有 `/run/pre_market` 和 `/run/after_close` 兼容 Router。
  - 系统状态在运行配置缺失时返回结构化 `partial`，不直接返回 400，也不暴露具体密钥名称。
- 关键契约复核：
  - `route-config.tsx` 仍是唯一集中事实源。
  - 正式旅程：研究中心 → 待审核规则 → 回测实验 → 作者画像 → 策略中心 → 今日盘前 → 今日盘后。
  - 首页继续复用既有 Dashboard API 和真实事实源。
  - 未新增数据库表、迁移、Prompt、第二套 Schema 或 Stage 2 对象。
- 最终验证摘要：
  - 前端全量：90 个文件、283 个测试通过。
  - typecheck、lint、build 通过；构建转换 1794 个模块。
  - 后端受影响套件：25 passed，2 条既有异步连接清理 warning。
  - 系统状态定向：4 passed。
  - app factory、唯一入口和 OpenAPI：5 passed。
  - Web 静态/API 路由优先级：3 passed。
  - Web E2E：1 passed。
  - `git diff --check` 通过。
  - 静态门禁确认 `/dashboard` 生产引用仅存在于集中兼容配置；无迁移、Prompt 或 Stage 2 文件变更。
- 用户 UI 验收：
  - 用户已完成 Stage 1 UI 检查，并明确确认当前 UI 可接受。
  - 当前重构以功能实现和基本可用性为主；视觉一致性和非关键响应式细节转入 UI backlog。
  - 未发现会阻止页面或核心流程使用的 UI 问题。
- 残余风险：
  - React Router v7 future flag warning，非阻塞。
  - 后端存在既有异步数据库连接清理 RuntimeWarning，非阻塞。
  - 仓库级后端全量测试曾在 11 分钟后中止；定向修复后的相关套件已通过，不能声称仓库后端全量通过。
  - 工作区存在用户已有的 `.codex/config.toml`、AI 模板和运行时文件差异。
- 最终验收结论：
  - 已清除代码 BLOCKER 和 required HIGH。
  - 功能、契约、自动验证、基本可用性和用户 UI 检查满足 Stage 1 当前出口条件。
  - `RT-S1-001`、`RT-S1-002`、`RT-S1-003` 标记为 `[x]`。
  - Stage 1 标记为 `[x]`。
  - 允许进入 Stage 2。