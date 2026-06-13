# Stage 1 Product Information Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 `RT-S1-001`、`RT-S1-002`、`RT-S1-003`，建立单一路由事实源、统一业务页面框架和接入真实状态的产品首页。

**Architecture:** 前端以一个集中路由配置派生 Router、Sidebar、二级导航、页面元数据和兼容入口；现有业务页面嵌入统一页面框架，不复制领域能力。后端新增单一职责的首页业务状态聚合 Service，并由现有 `/api/ui/v1/system/dashboard` 增量返回，保留原运维字段和事实源。

**Tech Stack:** React 18、React Router 6、TanStack Query、TypeScript、Vitest、Testing Library、FastAPI、SQLAlchemy Async、Pydantic、pytest。

---

## 1. 文件结构

### 1.1 新建文件

| 文件 | 职责 |
| --- | --- |
| `web/src/app/route-config.tsx` | 唯一路由、导航、权限、二级导航和兼容元数据 |
| `web/src/app/route-config.test.tsx` | 集中配置、49 条旧路由覆盖和开发术语门禁 |
| `web/src/components/layout/section-nav.tsx` | 横向二级导航 |
| `web/src/components/layout/section-nav.test.tsx` | 激活状态、移动滚动和权限测试 |
| `web/src/components/layout/business-page-shell.tsx` | 页面用途、步骤、前置条件、输入、进度、输出和下一步框架 |
| `web/src/components/layout/business-page-shell.test.tsx` | 页面区域和六类状态测试 |
| `web/src/components/layout/compatibility-notice.tsx` | 历史入口迁移说明 |
| `web/src/components/layout/compatibility-notice.test.tsx` | 新入口和退役条件展示测试 |
| `web/src/pages/home/index.tsx` | 新产品首页 |
| `web/src/pages/home/index.test.tsx` | 首页状态、主操作和错误状态测试 |
| `web/src/pages/research/index.tsx` | 研究中心正式入口及现有页面装配 |
| `web/src/pages/rules/index.tsx` | 规则与回测正式入口及现有页面装配 |
| `web/src/pages/authors/index.tsx` | 作者画像诚实状态页及现有画像入口 |
| `web/src/pages/strategies/StrategyOverviewPage.tsx` | 策略中心概览 |
| `web/src/pages/daily/index.tsx` | 每日交易总览及盘前盘后装配 |
| `web/src/pages/product-entry-pages.test.tsx` | 七个一级入口和真实页面装配测试 |
| `web/src/pages/product-page-state-matrix.test.tsx` | 所有实际渲染页面的五项信息和六类状态覆盖矩阵 |
| `web/src/app/product-journey.test.tsx` | 普通用户正式操作路径测试 |
| `web/src/components/layout/product-page-adapter.tsx` | 将真实查询、业务动作和结果接入统一页面框架，隔离工程表单 |
| `web/src/components/layout/product-page-adapter.test.tsx` | 验证正式入口不暴露内部参数 |
| `web/src/features/home/use-home-dashboard.ts` | 首页 Dashboard 查询和错误归一化 |
| `web/src/features/home/home-dashboard.tsx` | 首页三级信息结构 |
| `web/src/features/home/home-dashboard.test.tsx` | 主操作、状态卡和 partial/unavailable 测试 |
| `src/services/home_dashboard_service.py` | 首页业务日期和业务状态聚合 |
| `tests/unit/services/test_home_dashboard_service.py` | 聚合逻辑、事实源失败和优先级测试 |

### 1.2 主要修改文件

| 文件 | 修改 |
| --- | --- |
| `web/src/app/router.tsx` | 从集中配置注册正式和兼容路由 |
| `web/src/app/navigation.ts` | 改为从集中配置导出，删除独立事实源 |
| `web/src/app/route-registry.ts` | 改为兼容导出或删除，由集中配置替代 |
| `web/src/layouts/dashboard-layout.tsx` | 使用集中路由元数据和二级导航 |
| `web/src/components/layout/sidebar.tsx` | 七个中文一级入口和产品品牌 |
| `web/src/components/layout/status-strip.tsx` | 去除 Route/path 开发信息，改为业务上下文 |
| `web/src/routes/overview.tsx` | 退役旧工具首页实现，转出新首页 |
| `web/src/styles/globals.css` | 编辑型工作台视觉和响应式规则 |
| `web/src/types/system.ts` | Dashboard 业务状态类型 |
| `web/src/lib/api/system.ts` | 继续调用现有 Dashboard API |
| `web/src/lib/error-recovery.ts` | 正式返回路径改为 `/` 或对应业务入口 |
| `src/services/system_service.py` | 注入并合并首页业务状态聚合结果 |
| `api/routers/ui/system.py` | 保持原路径，更新接口说明 |
| `tests/api/routers/ui/test_ui_system_dashboard.py` | API 增量契约和旧字段兼容 |
| `docs/Refactor-Implementation-Log.md` | 记录三个任务实际完成情况 |

### 1.3 明确不修改

- 不新增数据库表或迁移。
- 不新增规则、画像、策略或回测 Schema。
- 不新增第二个首页 API。
- 不删除迁移矩阵尚未满足退役条件的历史路由。
- 不修改 Prompt。

## 2. Task 1：建立单一路由事实源

**Files:**
- Create: `web/src/app/route-config.tsx`
- Create: `web/src/app/route-config.test.tsx`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/navigation.ts`
- Modify: `web/src/app/route-registry.ts`
- Modify: `web/src/app/navigation.test.ts`
- Modify: `web/src/app/route-registry.test.ts`

- [ ] **Step 1: 写集中配置失败测试**

在 `route-config.test.tsx` 固定验证七个一级入口、默认路由和兼容映射：

```tsx
import { describe, expect, it } from 'vitest';
import {
  canonicalRoutes,
  compatibilityRoutes,
  primaryNavigation,
  resolveRoute,
} from './route-config';

describe('route config', () => {
  it('exposes exactly seven product navigation entries', () => {
    expect(primaryNavigation.map((item) => [item.label, item.path])).toEqual([
      ['首页', '/'],
      ['研究中心', '/research'],
      ['规则与回测', '/rules'],
      ['作者画像', '/authors'],
      ['策略中心', '/strategies'],
      ['每日交易', '/daily'],
      ['系统管理', '/system'],
    ]);
  });

  it('does not expose developer terms in primary navigation', () => {
    const text = JSON.stringify(primaryNavigation);
    for (const term of ['Job', 'Workflow', 'Pipeline', 'Artifact', 'Provider', 'Schema', 'CLI']) {
      expect(text).not.toContain(term);
    }
  });

  it('maps the immediate Stage 1 compatibility routes', () => {
    expect(compatibilityRoutes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ path: '/dashboard', targetPath: '/' }),
        expect.objectContaining({ path: '/articles', targetPath: '/research/articles' }),
      ]),
    );
    expect(resolveRoute('/strategies')?.label).toBe('策略中心');
  });

  it('keeps every audited legacy route classified', () => {
    const auditedPaths = [
      '/login', '/', '/dashboard', '/jobs', '/jobs/:jobId',
      '/profiles', '/profiles/import', '/profiles/:profileId',
      '/profiles/:profileId/edit', '/profiles/:profileId/snapshots/:snapshotId',
      '/workflows', '/workflows/pre-market', '/workflows/pre-market/run',
      '/workflows/after-close', '/workflows/after-close/run',
      '/workflows/:workflowId/run', '/articles', '/articles/run',
      '/articles/list', '/articles/quality', '/articles/results', '/alerts',
      '/backtest', '/backtest/regime', '/backtest/candidates', '/rule-pool',
      '/rule-pool/:ruleId', '/artifacts', '/artifacts/:artifactId', '/market',
      '/market/snapshots', '/market/datasets', '/market/kaipan', '/market/ohlcv',
      '/strategies', '/persona', '/strategies/pre-market',
      '/strategies/after-close', '/system', '/system/audit', '/system/users',
      '/system/health', '/system/db-migrate', '/system/backup', '/admin',
      '/admin/audit', '/system/restore', '/settings', '*',
    ];
    expect(auditedPaths.every((path) => canonicalRoutes.some((item) => item.path === path)
      || compatibilityRoutes.some((item) => item.path === path))).toBe(true);
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd web
pnpm test -- src/app/route-config.test.tsx
```

Expected: FAIL，原因是 `route-config.tsx` 尚不存在。

- [ ] **Step 3: 实现集中配置类型和派生函数**

`route-config.tsx` 使用如下核心契约：

```tsx
export type ProductRoute = {
  id: string;
  path: string;
  label: string;
  description: string;
  element: ReactNode;
  primary?: boolean;
  parentId?: string;
  minRole?: PrincipalRole;
  visibleInNavigation?: boolean;
  legacy?: {
    targetPath: string;
    retireStage: string;
    retireCondition: string;
    mode: 'redirect' | 'notice';
    retirementRequired: boolean;
  };
};

export const routeConfig: ProductRoute[] = [
  // 七个正式一级入口、正式子路由、历史深链和中文 404。
];

export const primaryNavigation = routeConfig
  .filter((route) => route.primary && route.visibleInNavigation !== false)
  .map(toNavigationItem);

export function getSectionNavigation(parentId: string) {
  return routeConfig.filter((route) => route.parentId === parentId && route.visibleInNavigation !== false);
}

export function resolveRoute(pathname: string) {
  return routeConfig.find((route) => matchPath({ path: route.path, end: true }, pathname));
}
```

兼容模式选择：

- `/dashboard`、`/articles`、`/admin*`、`/settings` 等无参数入口使用 redirect。
- 仍承载真实业务的历史页面使用 notice，不改变其当前组件和参数。
- `/strategies` 直接注册正式策略概览，不再兼容跳转首页。

对审计中的每条旧入口逐项断言：

```tsx
for (const route of auditedLegacyRoutes) {
  const configured = resolveLegacyRoute(route.path);
  expect(configured?.legacy?.targetPath).toBeTruthy();
  expect(['redirect', 'notice']).toContain(configured?.legacy?.mode);
  expect(configured?.legacy?.retireStage).toBeTruthy();
  expect(configured?.legacy?.retireCondition).toBeTruthy();
  expect(typeof configured?.legacy?.retirementRequired).toBe('boolean');
}
```

长期保留的详情入口使用 `retirementRequired: false`，`retireStage: '长期保留'`，并写明保留条件；不得用缺失字段表达长期保留。

- [ ] **Step 4: 让 Router、Navigation 和 Route Registry 从配置派生**

`router.tsx` 只保留认证外壳和配置映射：

```tsx
const authenticatedChildren = routeConfig
  .filter((route) => route.path !== '/login')
  .map(toReactRouterRoute);
```

`navigation.ts` 仅做兼容导出：

```ts
export { primaryNavigation as mainNavigation } from './route-config';
export const navigationGroups = [{ title: '主要功能', items: primaryNavigation }];
export const allNavigationItems = primaryNavigation;
```

`route-registry.ts` 仅从 `routeConfig` 派生 `routeRegistry` 和 `resolveRouteByPathname`，禁止再维护独立数组。

- [ ] **Step 5: 运行路由测试**

Run:

```bash
cd web
pnpm test -- src/app/route-config.test.tsx src/app/navigation.test.ts src/app/route-registry.test.ts
```

Expected: PASS。

## 3. Task 2：建立统一页面框架和二级导航

**Files:**
- Create: `web/src/components/layout/business-page-shell.tsx`
- Create: `web/src/components/layout/business-page-shell.test.tsx`
- Create: `web/src/components/layout/section-nav.tsx`
- Create: `web/src/components/layout/section-nav.test.tsx`
- Create: `web/src/components/layout/compatibility-notice.tsx`
- Create: `web/src/components/layout/compatibility-notice.test.tsx`
- Create: `web/src/components/layout/product-page-adapter.tsx`
- Create: `web/src/components/layout/product-page-adapter.test.tsx`
- Modify: `web/src/layouts/dashboard-layout.tsx`
- Modify: `web/src/components/layout/status-strip.tsx`

- [ ] **Step 1: 写页面框架失败测试**

```tsx
render(
  <BusinessPageShell
    title="待审核规则"
    purpose="确认文章提取出的候选规则是否可以进入正式规则库。"
    currentStep="人工审核"
    prerequisites={[{ label: '已有候选规则', status: 'ready' }]}
    nextAction={{ label: '审核下一条规则', to: '/rules/review' }}
  >
    <div>真实规则列表</div>
  </BusinessPageShell>,
);

expect(screen.getByRole('heading', { name: '待审核规则' })).toBeInTheDocument();
expect(screen.getByText('真实规则列表')).toBeInTheDocument();
expect(screen.getByRole('link', { name: '审核下一条规则' })).toHaveAttribute('href', '/rules/review');
```

分别测试 `loading`、`empty`、`error`、`partial`、`permission_denied`、`unavailable` 的中文说明和修复动作。

测试还必须断言默认页面结构不会省略五项必需信息：

```tsx
expect(screen.getByText('页面用途')).toBeInTheDocument();
expect(screen.getByText('输入')).toBeInTheDocument();
expect(screen.getByText('处理状态')).toBeInTheDocument();
expect(screen.getByText('输出')).toBeInTheDocument();
expect(screen.getByText('下一步')).toBeInTheDocument();
```

当页面无需输入或尚无输出时，组件必须要求调用方提供 `inputDescription="本页无需输入，数据来自候选规则库。"` 和 `outputDescription="审核后将在正式规则区域产生结果。"`，不得省略区域。

- [ ] **Step 2: 写二级导航和兼容提示失败测试**

验证：

- 当前子路由具有 `aria-current="page"`。
- 非管理员看不到高风险系统子入口。
- 兼容提示显示新入口、退役 Stage、退役条件和返回按钮。

- [ ] **Step 3: 运行测试确认失败**

Run:

```bash
cd web
pnpm test -- src/components/layout/business-page-shell.test.tsx src/components/layout/section-nav.test.tsx src/components/layout/compatibility-notice.test.tsx
```

Expected: FAIL，原因是组件尚不存在。

- [ ] **Step 4: 实现业务页面框架**

核心类型：

```tsx
type PageAvailability =
  | 'ready'
  | 'loading'
  | 'empty'
  | 'error'
  | 'partial'
  | 'permission_denied'
  | 'unavailable';

type PageAction = {
  label: string;
  to?: string;
  onClick?: () => void;
};

type BusinessPageShellProps = {
  title: string;
  purpose: string;
  inputDescription: string;
  processingDescription: string;
  outputDescription: string;
  currentStep?: string;
  prerequisites?: Array<{ label: string; status: PageAvailability; detail?: string }>;
  availability?: PageAvailability;
  stateTitle?: string;
  stateDescription?: string;
  impact?: string;
  recoveryAction?: PageAction;
  nextAction?: PageAction;
  input?: ReactNode;
  progress?: ReactNode;
  output?: ReactNode;
  help?: ReactNode;
  children?: ReactNode;
};
```

状态组件必须显示“发生了什么、影响了什么、应该怎么处理”；没有真实内容的区域不渲染空卡片。

`ProductPageAdapter` 负责把旧实现拆为：

```tsx
type ProductPageAdapterProps = {
  queryState: PageAvailability;
  purpose: string;
  inputDescription: string;
  processingDescription: string;
  outputDescription: string;
  businessAction: PageAction;
  result: ReactNode;
  advancedAdminDetails?: ReactNode;
};
```

正式页面只传入真实 Query 状态、业务动作和结果组件。旧页面中暴露 `job_type`、`workflow_id`、Pipeline Step、Artifact 路径、Provider、`force` 或内部配置对象的表单不得作为正式入口 children；管理员技术详情只能传入 `advancedAdminDetails`。

- [ ] **Step 5: 在 DashboardLayout 接入路由元数据和二级导航**

删除 Topbar/StatusStrip 中的 Route 和 path 展示。布局根据当前路由的 `parentId` 渲染 `SectionNav`，未知路径使用中文 404 元数据。

- [ ] **Step 6: 运行组件测试**

Run:

```bash
cd web
pnpm test -- src/components/layout/business-page-shell.test.tsx src/components/layout/section-nav.test.tsx src/components/layout/compatibility-notice.test.tsx src/components/layout/sidebar.test.tsx
```

Expected: PASS。

## 4. Task 3：装配七个正式入口和现有真实页面

**Files:**
- Create: `web/src/pages/research/index.tsx`
- Create: `web/src/pages/rules/index.tsx`
- Create: `web/src/pages/authors/index.tsx`
- Create: `web/src/pages/strategies/StrategyOverviewPage.tsx`
- Create: `web/src/pages/daily/index.tsx`
- Create: `web/src/pages/product-entry-pages.test.tsx`
- Create: `web/src/pages/product-page-state-matrix.test.tsx`
- Create: `web/src/app/product-journey.test.tsx`
- Modify: `web/src/pages/strategies/index.tsx`
- Modify: `web/src/pages/system/index.tsx`
- Modify: `web/src/app/route-config.tsx`

- [ ] **Step 1: 写正式入口失败测试**

测试每个正式子路由装配现有真实组件：

```tsx
vi.mock('@/pages/articles', () => ({
  ArticleListPage: () => <div data-testid="article-list" />,
  ArticleRunPage: () => <div data-testid="article-add" />,
  ArticleResultsPage: () => <div data-testid="article-results" />,
}));

render(<MemoryRouter><ResearchArticlesPage /></MemoryRouter>);
expect(screen.getByTestId('article-list')).toBeInTheDocument();

render(<MemoryRouter><ResearchAddPage /></MemoryRouter>);
expect(screen.getByTestId('article-add')).toBeInTheDocument();

render(<MemoryRouter><ResearchResultsPage /></MemoryRouter>);
expect(screen.getByTestId('article-results')).toBeInTheDocument();

it.each([
  [RulesReviewPage, 'rule-pool'],
  [RulesBacktestsPage, 'backtest'],
  [StrategyCandidatesPage, 'strategy-candidates'],
  [DailyPreMarketPage, 'pre-market'],
  [DailyAfterClosePage, 'after-close'],
])('mounts the existing real page in %s', (Page, testId) => {
  render(<MemoryRouter><Page /></MemoryRouter>);
  expect(screen.getByTestId(testId)).toBeInTheDocument();
});
```

该测试文件同时 mock `RulePoolPage`、`BacktestPage`、`BacktestCandidatesPage`、`PreMarketPage` 和 `AfterClosePage`，分别返回上面声明的 `data-testid`，避免依赖自定义 matcher。

作者画像和策略概览测试必须断言：

- 有真实现有数据入口。
- 明确说明正式三层画像或 StrategyVersion 尚未建立。
- 不显示虚构数量。
- 有正确的上一步入口。

- [ ] **Step 2: 写逐页状态矩阵和正式操作路径失败测试**

从集中路由配置派生所有实际渲染页面清单，不在测试中另写第二份路由事实源：

```tsx
const renderedPages = routeConfig.filter((route) => route.renderMode === 'page');
```

每个页面必须通过统一 Page Adapter 注入六类状态，并逐页断言：

```tsx
for (const route of renderedPages) {
  for (const availability of [
    'loading', 'empty', 'error', 'partial', 'permission_denied', 'unavailable',
  ] as const) {
    renderProductRoute(route.path, { availability });
    expect(screen.getByText('页面用途')).toBeInTheDocument();
    expect(screen.getByText('输入')).toBeInTheDocument();
    expect(screen.getByText('处理状态')).toBeInTheDocument();
    expect(screen.getByText('输出')).toBeInTheDocument();
    expect(screen.getByText('下一步')).toBeInTheDocument();
    expect(screen.getByTestId(`page-state-${availability}`)).toBeInTheDocument();
    cleanup();
  }
}
```

覆盖范围必须包括正式页面、兼容页面、参数化详情、运行详情、系统页面和中文 404。`renderMode: 'redirect'` 的纯重定向路由不进入矩阵。

正式操作路径测试从首页主操作开始，验证用户能沿业务链接访问：

```text
研究中心 → 待审核规则 → 回测实验 → 作者画像 → 策略中心 → 今日盘前 → 今日盘后
```

测试同时断言旅程中的链接不指向 `/jobs`、`/workflows`、`/artifacts` 或 `/market/*` 技术工作台。

业务入口适配测试对正式页面渲染结果执行：

```tsx
const visibleText = screen.getByTestId('product-page').textContent ?? '';
for (const term of ['job_type', 'workflow_id', 'Pipeline Step', 'Artifact path', 'Provider', 'force']) {
  expect(visibleText).not.toContain(term);
}
expect(screen.getByRole('button', { name: /添加文章|提取规则|开始回测|生成盘前计划|开始盘后复盘/ })).toBeInTheDocument();
```

- [ ] **Step 3: 运行测试确认失败**

Run:

```bash
cd web
pnpm test -- src/pages/product-entry-pages.test.tsx src/pages/product-page-state-matrix.test.tsx src/app/product-journey.test.tsx
```

Expected: FAIL。

- [ ] **Step 4: 实现领域入口包装页**

装配规则：

- `/research/articles` 使用现有 `ArticleListPage`。
- `/research/add` 使用现有 `ArticleRunPage`。
- `/research/results` 使用现有 `ArticleResultsPage`。
- `/rules/review` 使用现有 `RulePoolPage`。
- `/rules/library` 复用规则列表并按当前真实审核状态说明能力边界，不伪造新 RuleVersion。
- `/rules/backtests` 使用现有 `BacktestPage`。
- `/rules/results` 使用现有 `RegimeBacktestReportPage`，说明 Stage 6 才形成统一结果契约。
- `/authors` 包装现有 `PersonaPage`，显示“正式作者画像能力尚未建立”。
- `/strategies` 展示现有策略版本事实和能力边界。
- `/strategies/candidates` 使用现有 `BacktestCandidatesPage`。
- `/daily/overview` 只汇总现有盘前、盘后入口状态，不生成每日正式对象。
- `/daily/pre-market` 和 `/daily/after-close` 使用现有真实页面。

上述“使用现有页面”仅指复用其真实 API Hook、结果组件和安全业务动作。若旧页面包含工程表单，必须在正式入口拆分或增加 `mode="product"`，隐藏内部类型、步骤、文件路径和强制执行参数；旧路径继续以 `mode="compat"` 保留完整兼容能力和迁移说明。

- [ ] **Step 5: 系统管理按权限装配**

`/system/status` 对所有已认证用户开放只读状态。配置、数据、运行与告警页面复用现有真实能力；用户管理、数据库迁移和恢复操作继续按 admin 权限过滤。

- [ ] **Step 6: 运行入口、状态矩阵、用户旅程和现有页面回归**

Run:

```bash
cd web
pnpm test -- src/pages/product-entry-pages.test.tsx src/pages/product-page-state-matrix.test.tsx src/app/product-journey.test.tsx src/pages/articles/index.test.tsx src/pages/rule-pool/index.test.tsx src/pages/backtest/index.test.tsx src/pages/strategies/lifecycle.test.tsx src/pages/system/index.test.tsx
```

Expected: PASS。

## 5. Task 4：首页业务状态聚合 Service

**Files:**
- Create: `src/services/home_dashboard_service.py`
- Create: `tests/unit/services/test_home_dashboard_service.py`
- Modify: `src/services/system_service.py`

- [ ] **Step 1: 写日期和状态聚合失败测试**

使用注入的时钟、交易日历、Session Factory 和 JobService，至少覆盖：

```python
class FakeCalendar:
    def __init__(self, trade_dates: set[date]) -> None:
        self.trade_dates = trade_dates

    def is_trade_date(self, value: date) -> bool:
        return value in self.trade_dates

    def latest_on_or_before(self, value: date) -> date | None:
        candidates = [item for item in self.trade_dates if item <= value]
        return max(candidates) if candidates else None


class FakeStatusSource:
    def __init__(self, *, rule_error: Exception | None = None) -> None:
        self.rule_error = rule_error

    async def load(self, *, business_date: date, latest_trading_day: date | None, profile_id: str | None):
        if self.rule_error is not None:
            raise self.rule_error
        return {
            "data_readiness": {"status": "ready", "value": True},
            "premarket": {"status": "complete", "value": True},
            "postmarket": {"status": "complete", "value": True},
            "pending_rules": {"status": "ready", "value": 0},
        }


@pytest.mark.asyncio
async def test_build_summary_uses_latest_trade_day_on_non_trading_day():
    service = HomeDashboardService(
        clock=lambda: datetime(2026, 6, 13, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        calendar=FakeCalendar(trade_dates={date(2026, 6, 12)}),
        status_source=FakeStatusSource(),
    )
    result = await service.build_summary(profile_id=None)
    assert result["is_trading_day"] is False
    assert result["latest_trading_day"] == "2026-06-12"
```

```python
@pytest.mark.asyncio
async def test_build_summary_does_not_convert_missing_sources_to_false_or_zero():
    source = FakeStatusSource(rule_error=RuntimeError("database unavailable"))
    result = await HomeDashboardService(status_source=source).build_summary(profile_id=None)
    assert result["status"] == "partial"
    assert result["business_status"]["pending_rules"]["status"] == "unavailable"
    assert result["business_status"]["pending_rules"]["value"] is None
```

```python
def test_select_next_action_prioritizes_data_then_premarket_then_postmarket_then_rules():
    assert select_next_action({
        "data_readiness": {"status": "blocked"},
        "premarket": {"status": "pending"},
    })["id"] == "repair_data"
    assert select_next_action({
        "data_readiness": {"status": "ready"},
        "premarket": {"status": "pending"},
    })["id"] == "prepare_premarket"
    assert select_next_action({
        "data_readiness": {"status": "ready"},
        "premarket": {"status": "complete"},
        "postmarket": {"status": "pending"},
    })["id"] == "review_market"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m pytest tests/unit/services/test_home_dashboard_service.py -q
```

Expected: FAIL，原因是 Service 尚不存在。

- [ ] **Step 3: 实现聚合契约**

`home_dashboard_service.py` 定义：

```python
HomeStatusValue = Literal["ready", "pending", "complete", "blocked", "partial", "unavailable"]

class HomeDashboardService(BaseService):
    async def build_summary(self, *, profile_id: str | None) -> dict[str, Any]:
        now = self._clock().astimezone(ZoneInfo("Asia/Shanghai"))
        business_date = now.date()
        is_trading_day = self._calendar.is_trade_date(business_date)
        latest_trading_day = self._calendar.latest_on_or_before(business_date)
        business_status = await self._status_source.load(
            business_date=business_date,
            latest_trading_day=latest_trading_day,
            profile_id=profile_id,
        )
        return {
            "status": "ok",
            "business_date": business_date.isoformat(),
            "is_trading_day": is_trading_day,
            "latest_trading_day": latest_trading_day.isoformat() if latest_trading_day else None,
            "next_action": select_next_action(business_status),
            "business_status": business_status,
        }

def select_next_action(business_status: dict[str, dict[str, Any]]) -> dict[str, Any]:
    priorities = (
        ("data_readiness", {"blocked", "partial"}, "repair_data", "补齐缺失数据", "/system/data"),
        ("premarket", {"pending", "blocked"}, "prepare_premarket", "生成盘前计划", "/daily/pre-market"),
        ("postmarket", {"pending", "blocked"}, "review_market", "开始盘后复盘", "/daily/after-close"),
        ("pending_rules", {"ready"}, "review_rules", "审核候选规则", "/rules/review"),
    )
    for key, actionable, action_id, label, target_path in priorities:
        status = business_status.get(key, {}).get("status")
        value = business_status.get(key, {}).get("value")
        if status in actionable and (key != "pending_rules" or isinstance(value, int) and value > 0):
            return {"id": action_id, "label": label, "target_path": target_path}
    return {"id": "view_status", "label": "查看今日状态", "target_path": "/"}
```

实际实现还必须逐项捕获事实源异常，把对应状态转换为 unavailable，并将总状态改为 partial；不得让一个查询异常丢失其他已成功状态。

每个业务状态统一返回：

```python
{
    "status": "ready | pending | complete | blocked | partial | unavailable",
    "value": value_or_none,
    "label": "用户可读状态",
    "detail": "事实和影响说明",
    "source": "market_snapshots | market_regimes | rule_pool | trader_strategy_versions | jobs | unavailable",
    "updated_at": iso_or_none,
    "target_path": "/正式入口",
    "unavailable_reason": reason_or_none,
}
```

- [ ] **Step 4: 只使用已确认的真实来源**

| 首页状态 | Stage 1 事实源 |
| --- | --- |
| 数据是否就绪 | `market_snapshots` 中目标交易日最新快照的 `quality_status` 和缺失 section 数；无记录为 unavailable |
| 今日盘前 | `jobs` 中 `job_type=run-pre-market` 的最近真实运行；Stage 9 前标明仍是兼容运行 |
| 最近交易日盘后 | `jobs` 中 `job_type=run-after-close` 的最近真实运行；Stage 10 前标明仍是兼容运行 |
| 待审核规则 | `rule_pool.review_status=pending` 的真实 count |
| 画像建议 | 无正式 Proposal 事实源，固定返回 unavailable，不返回 0 |
| 策略建议 | 无正式 Proposal 事实源，固定返回 unavailable，不返回 0 |
| 当前策略版本 | `trader_strategy_versions.status=released` 的最新真实记录；同时标明 Stage 8 前是 legacy 策略版本 |
| 当前市场状态 | `market_regimes` 中目标交易日最新记录的 `primary_label`、版本和质量状态 |
| 失败运行 | 复用现有 `SystemService` 的 `failed_jobs`，不再重复查询第二次 |

`HomeDashboardService` 不读取临时 JSON 文件，不调用实时 Provider，不创建新表。

- [ ] **Step 5: 处理交易日历不可用**

复用现有 `TradeCalendar`，但通过适配器注入以便测试。日历加载失败时：

- `is_trading_day` 为 `None`。
- `latest_trading_day` 为 `None`。
- 依赖交易日的状态为 unavailable。
- Dashboard 总状态为 partial。
- 不把工作日自动当作交易日。

- [ ] **Step 6: 运行 Service 测试**

Run:

```bash
python -m pytest tests/unit/services/test_home_dashboard_service.py -q
```

Expected: PASS。

## 6. Task 5：扩展现有 Dashboard API

**Files:**
- Modify: `src/services/system_service.py`
- Modify: `api/routers/ui/system.py`
- Modify: `tests/api/routers/ui/test_ui_system_dashboard.py`
- Modify: `tests/unit/services/test_config_system_service.py`
- Modify: `web/src/types/system.ts`
- Modify: `web/src/lib/api/system.test.ts`

- [ ] **Step 1: 写向后兼容 API 失败测试**

API 测试同时断言旧字段和新字段：

```python
assert payload["health"]["database"]["status"] == "ok"
assert payload["failed_jobs"][0]["id"] == "job-failed-1"
assert payload["business_date"] == "2026-06-10"
assert payload["business_status"]["pending_rules"]["value"] == 3
assert payload["next_action"]["target_path"] == "/rules/review"
```

Service 测试模拟首页聚合失败，断言原运维 Dashboard 仍返回且整体为 partial。

先修复已确认的基线测试调用契约：`check_key_directories` 当前为异步关键字参数方法，测试必须使用：

```python
dir_result = asyncio.run(service.check_key_directories(config_path=config_path))
```

该修改只修正测试与现有公开签名不一致的问题，不改变生产行为。

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python -m pytest tests/api/routers/ui/test_ui_system_dashboard.py tests/unit/services/test_config_system_service.py -q
```

Expected: FAIL，新业务字段尚不存在。

- [ ] **Step 3: 注入 HomeDashboardService 并合并结果**

`SystemService.__init__` 增加：

```python
home_dashboard_service: HomeDashboardService | None = None
```

`build_dashboard_summary` 在已有运维结果完成后调用：

```python
business = await self._home_dashboard_service.build_summary(profile_id=resolved_profile_id)
payload.update(business)
if business["status"] != "ok":
    payload["status"] = "partial"
```

发生异常时仅新增 unavailable 业务状态和 warning，不删除或改名现有字段。

- [ ] **Step 4: 更新前端类型**

```ts
export type HomeBusinessStatusValue =
  | 'ready'
  | 'pending'
  | 'complete'
  | 'blocked'
  | 'partial'
  | 'unavailable';

export type HomeBusinessStatus = {
  status: HomeBusinessStatusValue;
  value: string | number | boolean | null;
  label: string;
  detail: string;
  source: string;
  updated_at: string | null;
  target_path: string;
  unavailable_reason: string | null;
};
```

保留 `SystemDashboardResponse` 的全部已有字段，并增量添加业务字段。

- [ ] **Step 5: 运行 API 和类型契约测试**

Run:

```bash
python -m pytest tests/api/routers/ui/test_ui_system_dashboard.py tests/unit/services/test_config_system_service.py -q
cd web
pnpm test -- src/lib/api/system.test.ts
```

Expected: PASS。

## 7. Task 6：实现首页三级信息结构

**Files:**
- Create: `web/src/pages/home/index.tsx`
- Create: `web/src/pages/home/index.test.tsx`
- Create: `web/src/features/home/use-home-dashboard.ts`
- Create: `web/src/features/home/home-dashboard.tsx`
- Create: `web/src/features/home/home-dashboard.test.tsx`
- Modify: `web/src/routes/overview.tsx`
- Modify: `web/src/app/route-config.tsx`

- [ ] **Step 1: 写首页失败测试**

覆盖：

```tsx
expect(screen.getAllByRole('link', { name: '补齐缺失数据' })).toHaveLength(1);
expect(screen.queryByText('最近 Job')).not.toBeInTheDocument();
expect(screen.queryByText('Artifact')).not.toBeInTheDocument();
expect(screen.getByText('画像建议能力尚未建立')).toBeInTheDocument();
expect(screen.getByText('部分状态暂不可用')).toBeInTheDocument();
```

同时验证首页卡片包含 TaskList 九项状态，unavailable 不显示 `0`，失败运行使用“失败运行”而不是 “Job failed”。

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd web
pnpm test -- src/features/home/home-dashboard.test.tsx src/pages/home/index.test.tsx
```

Expected: FAIL。

- [ ] **Step 3: 实现查询 Hook**

`use-home-dashboard.ts` 继续调用 `getSystemDashboard()`，使用单一 Query Key：

```ts
useQuery({
  queryKey: ['system-dashboard'],
  queryFn: getSystemDashboard,
  staleTime: 30_000,
});
```

系统管理的 Operational Dashboard 复用同一 Query Key，避免同一 API 在前端形成两份缓存事实源。

- [ ] **Step 4: 实现首页布局**

页面顺序固定：

1. 日期和市场状态上下文。
2. 一个主操作卡。
3. 九项紧凑业务状态。
4. 真实待办列表。
5. 从文章到盘后的完整业务流程。

首页不渲染最近 Job、Artifact、Worker、目录、接口路径或技术 Trace。

- [ ] **Step 5: 实现六类状态**

- 查询中：说明“正在读取今日业务状态”。
- 空状态：说明如何产生第一条真实数据。
- 错误：说明首页哪些状态无法判断，并提供“重新读取”。
- partial：保留可用状态，逐项标明不可用原因。
- permission denied：不展示不可执行按钮，提供可访问入口。
- unavailable：显示能力建设状态，不计入待办。

- [ ] **Step 6: 运行首页测试**

Run:

```bash
cd web
pnpm test -- src/features/home/home-dashboard.test.tsx src/pages/home/index.test.tsx src/components/dashboard/dashboard-status-summary.test.tsx
```

Expected: PASS。旧 Dashboard 组件测试如不再被生产代码使用，可保留测试或在确认无引用后删除组件；不得仅为消除失败删除仍有调用的测试。

## 8. Task 7：完成兼容链接迁移和编辑型工作台视觉

**Files:**
- Modify: `web/src/components/layout/sidebar.tsx`
- Modify: `web/src/components/layout/topbar.tsx`
- Modify: `web/src/components/layout/status-strip.tsx`
- Modify: `web/src/layouts/dashboard-layout.tsx`
- Modify: `web/src/styles/globals.css`
- Modify: `web/src/lib/error-recovery.ts`
- Modify: `web/src/lib/error-recovery.test.ts`
- Modify: all production files returned by `rg -l "'/dashboard'|\"/dashboard\"" web/src`

- [ ] **Step 1: 写产品文案和返回路径失败测试**

验证：

- Sidebar 品牌不再显示 `Web control console`。
- 普通导航只有七个业务中文入口。
- StatusStrip 不显示 `Route` 和路径。
- 错误恢复默认返回 `/`。
- 原本返回 `/dashboard` 的画像、策略、告警页面返回对应正式入口或 `/`。
- 正式页面按钮全部使用中文明确动作，不出现“执行”“运行”“提交”等无上下文词。
- 日期时间使用 `Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai' })`。

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd web
pnpm test -- src/components/layout/sidebar.test.tsx src/lib/error-recovery.test.ts
```

Expected: FAIL。

- [ ] **Step 3: 清理生产代码中的旧首页硬编码**

Run:

```bash
rg -n "'/dashboard'|\"/dashboard\"" web/src --glob '!**/*.test.*'
```

逐项替换：

- 全局恢复路径使用 `/`。
- 画像返回 `/authors`。
- 规则与回测返回 `/rules` 或对应子页。
- 策略返回 `/strategies`。
- 盘前盘后返回 `/daily`。
- `/dashboard` 只允许出现在集中兼容路由配置。

- [ ] **Step 4: 实现视觉变量和响应式规则**

在 `globals.css` 定义并应用：

```css
:root {
  --paper: #f3efe5;
  --paper-strong: #fffaf0;
  --forest: #173f35;
  --forest-deep: #0d2c25;
  --terracotta: #b95f43;
  --terracotta-strong: #98452f;
  --ink: #1f2925;
  --muted: #68736d;
  --line: #d8d1c3;
}
```

字体使用有明确中文回退的编辑型组合，不引入需要网络加载的字体。移动端：

- Sidebar 变抽屉。
- SectionNav `overflow-x: auto`。
- 首页卡片单列。
- 主操作保持首屏可见。
- 表格可横向滚动。

- [ ] **Step 5: 运行前端测试、类型检查和构建**

Run:

```bash
cd web
pnpm test
pnpm typecheck
pnpm lint
pnpm build
```

Expected: 全部 PASS。

- [ ] **Step 6: 使用 Browser 人工验收**

启动：

```bash
cd web
pnpm dev -- --host 127.0.0.1
```

使用 Browser 检查：

- 桌面 1440×900：首页、七个一级入口、规则二级导航、系统权限页面、中文 404。
- 移动 390×844：首页、导航抽屉、横向二级导航、主要动作。
- `/dashboard`、`/articles`、一个参数化历史深链和一个系统兼容入口。
- 控制台无 React 错误、资源错误或请求循环。

保存验收结论到实施记录，不生成 docs 目录外的正式报告。

## 9. Task 8：全量回归、迁移门禁和实施记录

**Files:**
- Modify: `docs/Refactor-Implementation-Log.md`
- Modify: `docs/Trade-Refactor-TaskList.md` only if the user-owned current changes allow a conflict-free status update

- [ ] **Step 1: 运行后端受影响测试**

Run:

```bash
python -m pytest \
  tests/unit/services/test_home_dashboard_service.py \
  tests/unit/services/test_config_system_service.py \
  tests/api/routers/ui/test_ui_system_dashboard.py \
  tests/api/routers/test_system_status.py \
  tests/api/test_ui_openapi_contract.py \
  -q
```

Expected: PASS。

- [ ] **Step 2: 运行前端全量测试和构建**

Run:

```bash
cd web
pnpm test
pnpm build
```

Expected: PASS。

- [ ] **Step 3: 运行仓库 Web 验收套件**

Run:

```bash
python -m pytest tests/e2e/test_web_acceptance.py -q
```

Expected: PASS。若依赖本地服务、浏览器或外部环境而无法运行，记录原始原因、已执行替代检查和剩余风险，不得写为通过。

- [ ] **Step 4: 执行静态迁移门禁**

Run:

```bash
rg -n "Job|Workflow|Pipeline|Artifact|Provider|Schema|CLI" web/src/app web/src/components/layout web/src/pages/home
rg -n "job_type|workflow_id|Pipeline Step|Artifact path|Provider|force" web/src/pages web/src/components/layout --glob '!**/*.test.*'
rg -n "'/dashboard'|\"/dashboard\"" web/src --glob '!**/*.test.*'
git diff --check
```

Expected:

- 第一条无普通导航或首页用户文案命中；类型名和管理员技术详情需逐项人工判断。
- 第二条在正式业务页面无命中；兼容页面和管理员技术详情的命中需逐项确认具有迁移说明或权限隔离。
- 第三条仅集中兼容配置允许命中。
- `git diff --check` 无错误。

- [ ] **Step 5: 对照 Stage 1 验收门禁**

逐项确认：

- 七个一级入口可达。
- 主导航无开发术语。
- 单一路由事实源成立。
- 49 条旧路由有自动化覆盖。
- 首页使用真实 API 和真实事实源。
- 首页只显示一个主操作。
- partial/unavailable 不被转换为 false 或 0。
- 六类页面状态可见。
- 每个正式主要页面明确展示用途、输入、处理状态、输出和下一步。
- 所有实际渲染页面通过六类状态覆盖矩阵。
- 用户主旅程不经过 Job、Workflow、Pipeline、Artifact 或 Provider 工具入口。
- 49条旧入口逐项具备目标入口、兼容模式、退役 Stage 和退役条件。
- 正式入口不暴露旧页面工程参数，旧工程表单只存在于兼容入口或管理员详情。
- 历史深链可用且有退役说明。
- 桌面和移动验收通过。
- 未新增数据库迁移、Prompt 或第二套 Schema。
- 未开始 Stage 2。

- [ ] **Step 6: 更新实施记录**

在 `docs/Refactor-Implementation-Log.md` 分别记录：

- `RT-S1-001`
- `RT-S1-002`
- `RT-S1-003`

每项包含状态、修改范围、关键设计决定、数据库迁移、兼容处理、测试、未完成项、风险和验收结论。只有全部门禁通过才标记 `[x]`；否则标记 `[-]` 或 `[!]`。

- [ ] **Step 7: 最终工作区审查**

Run:

```bash
git status --short
git diff --stat
git diff --check
```

区分本次 Stage 1 修改和用户已有修改，不撤销：

- `docs/Trade-Refactor-TaskList.md` 的已有修改。
- `docs/trade-strategy-ai-ai-conversation-templates.md` 的已有删除。

## 10. 数据库与回滚

本阶段不需要数据库迁移。所有首页状态只读现有表和 Service。

回滚方式：

1. 恢复旧前端路由配置和旧首页组件。
2. 移除 Dashboard 响应新增字段，不影响旧运维字段。
3. 保留历史路由和现有数据库数据。

由于不修改表结构和业务数据，回滚不需要数据恢复。若实施过程中发现必须新增表或迁移，立即停止并重新评审范围，不得在 Stage 1 临时扩大。

## 11. 完成判定

只有 Task 1 至 Task 8 全部完成，且 Stage 1 的全部验收门禁通过，才能将三个 Task 标记为 `[x]`。任何测试失败、未执行的关键验收、首页静态数据、路由遗漏或历史深链破坏，都必须保持 `[-] 进行中`，不得开始 Stage 2。
