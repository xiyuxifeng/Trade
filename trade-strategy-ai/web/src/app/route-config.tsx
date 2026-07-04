import type { ReactNode } from 'react';
import { Navigate, matchPath, useParams } from 'react-router-dom';
import type { PrincipalRole } from '@/types/auth';
import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { AuthorsPage } from '@/pages/authors';
import { DashboardPage } from '@/pages/dashboard';
import { DailyAfterClosePage, DailyOverviewPage, DailyPreMarketPage } from '@/pages/daily';
import { JobsPage, JobDetailPage, JobNewPage } from '@/pages/jobs';
import { LoginPage } from '@/pages/login';
import {
  ResearchAddPage,
  ResearchArticlesPage,
  ResearchResultsPage,
} from '@/pages/research';
import {
  StrategyCandidatesPage,
  StrategyOverviewPage,
} from '@/pages/strategies';
import {
  RulesBacktestsPage,
  RulesLibraryPage,
  RulesResultsPage,
  RulesReviewPage,
} from '@/pages/rules';
import {
  SystemPage,
  SystemConfigurationPage,
  SystemDataPage,
  SystemRunsPage,
  SystemStatusPage,
} from '@/pages/system';
import { AuditPage } from '@/pages/system/AuditPage';
import { BackupPage } from '@/pages/system/BackupPage';
import { DatabaseMigrationPage } from '@/pages/system/DatabaseMigrationPage';
import { HealthPage } from '@/pages/system/HealthPage';
import { UsersPage } from '@/pages/system/UsersPage';

export type LegacyRouteMode = 'redirect' | 'notice';

export type LegacyRouteMetadata = {
  targetPath: string;
  mode: LegacyRouteMode;
  retireStage: string;
  retireCondition: string;
  retirementRequired: boolean;
};

export type ProductRoute = {
  id: string;
  kind: 'canonical' | 'compat';
  path: string;
  label: string;
  description: string;
  element: ReactNode;
  primary?: boolean;
  parentId?: string;
  minRole?: PrincipalRole;
  visibleInNavigation?: boolean;
  legacy?: LegacyRouteMetadata;
  renderMode?: 'page' | 'redirect';
  renderWithAvailability?: (availability: PageAvailability) => ReactNode;
};

export type NavigationItem = {
  label: string;
  path: string;
  description: string;
  minRole?: PrincipalRole;
};

export const AUDITED_LEGACY_PATHS = [
  '/login',
  '/',
  '/dashboard',
  '/jobs',
  '/jobs/:jobId',
  '/profiles',
  '/profiles/import',
  '/profiles/:profileId',
  '/profiles/:profileId/edit',
  '/profiles/:profileId/snapshots/:snapshotId',
  '/workflows',
  '/workflows/pre-market',
  '/workflows/pre-market/run',
  '/workflows/after-close',
  '/workflows/after-close/run',
  '/workflows/:workflowId/run',
  '/articles',
  '/articles/run',
  '/articles/list',
  '/articles/quality',
  '/articles/results',
  '/alerts',
  '/backtest',
  '/backtest/regime',
  '/backtest/candidates',
  '/rule-pool',
  '/rule-pool/:ruleId',
  '/artifacts',
  '/artifacts/:artifactId',
  '/market',
  '/market/snapshots',
  '/market/datasets',
  '/market/kaipan',
  '/market/ohlcv',
  '/strategies',
  '/persona',
  '/strategies/pre-market',
  '/strategies/after-close',
  '/system',
  '/system/audit',
  '/system/users',
  '/system/health',
  '/system/db-migrate',
  '/system/backup',
  '/admin',
  '/admin/audit',
  '/system/restore',
  '/settings',
  '*',
] as const;

const RETIREMENT = {
  dashboard: '新首页接入真实业务状态，旧入口重定向测试通过，且外部链接不再使用旧主入口。',
  research: '研究中心完成文章新契约迁移，历史文章与提取结果可追溯。',
  runtime: '业务页面可创建、查看并恢复运行，历史运行深链可解析，普通用户不再提交内部类型。',
  profiles: '配置统一进入系统管理，历史配置与快照标识可解析，业务页可自动选择有效配置。',
  rules: '规则、固定数据版本和回测结果完成迁移，历史结果可读且复现对账通过。',
  market: '数据检查、修复和调度入口完成业务化，普通用户不再直接调用技术动作。',
  persona: '三层作者画像落库、审核和版本化，历史画像迁移报告通过。',
  strategy: '稳定策略、每日实例和盘后建议完成分离，历史策略与报告均有映射。',
  alerts: '告警已嵌入首页和受影响业务页，并能直接定位修复动作。',
  system: '系统管理入口保持可用，权限和用户文案符合产品约束。',
  redirects: '新系统入口稳定，旧深链观察期结束，访问记录无有效调用。',
  notFound: '中文 404 持续覆盖未知路径并提供返回首页入口。',
} as const;

function redirect(targetPath: string) {
  return <Navigate to={targetPath} replace />;
}

function JobDetailRedirect() {
  const { jobId } = useParams<{ jobId?: string }>();
  return <Navigate to={`/system/jobs/${encodeURIComponent(jobId ?? '')}`} replace />;
}

function legacy(
  targetPath: string,
  mode: LegacyRouteMode,
  retireStage: string,
  retireCondition: string,
  retirementRequired = true,
): LegacyRouteMetadata {
  return { targetPath, mode, retireStage, retireCondition, retirementRequired };
}

function NotFoundPage() {
  return (
    <main className="page-stack">
      <section className="page-card">
        <p className="page-kicker">404</p>
        <h1>页面未找到</h1>
        <p>请求的页面不存在或入口已经迁移，请返回首页继续。</p>
        <a href="/">返回首页</a>
      </section>
    </main>
  );
}

export const routeConfig: ProductRoute[] = [
  {
    id: 'login',
    kind: 'canonical',
    path: '/login',
    label: '登录',
    description: '登录后进入交易研究与每日决策产品。',
    element: <LoginPage />,
    visibleInNavigation: false,
    legacy: legacy('/login', 'notice', '长期保留', '认证入口长期保留并继续使用现有会话逻辑。', false),
  },
  {
    id: 'home',
    kind: 'canonical',
    path: '/',
    label: '首页',
    description: '查看今日状态、待办事项和下一步操作。',
    element: <DashboardPage />,
    primary: true,
    legacy: legacy('/', 'notice', '长期保留', '首页作为正式产品入口长期保留。', false),
  },
  {
    id: 'research',
    kind: 'canonical',
    path: '/research',
    label: '研究中心',
    description: '导入文章、查看文章并处理规则提取结果。',
    element: redirect('/research/articles'),
    renderMode: 'redirect',
    primary: true,
  },
  {
    id: 'research-articles',
    kind: 'canonical',
    path: '/research/articles',
    label: '文章库',
    description: '查看已导入文章及其处理状态。',
    element: <ResearchArticlesPage />,
    renderWithAvailability: (availability) => <ResearchArticlesPage availability={availability} />,
    parentId: 'research',
  },
  {
    id: 'research-add',
    kind: 'canonical',
    path: '/research/add',
    label: '添加文章',
    description: '导入文章并启动现有结构化处理流程。',
    element: <ResearchAddPage />,
    renderWithAvailability: (availability) => <ResearchAddPage availability={availability} />,
    parentId: 'research',
  },
  {
    id: 'research-results',
    kind: 'canonical',
    path: '/research/results',
    label: '提取结果',
    description: '查看文章结构化和规则提取结果。',
    element: <ResearchResultsPage />,
    renderWithAvailability: (availability) => <ResearchResultsPage availability={availability} />,
    parentId: 'research',
  },
  {
    id: 'rules',
    kind: 'canonical',
    path: '/rules',
    label: '规则与回测',
    description: '审核规则、运行回测并查看验证结果。',
    element: redirect('/rules/review'),
    renderMode: 'redirect',
    primary: true,
  },
  {
    id: 'rules-review',
    kind: 'canonical',
    path: '/rules/review',
    label: '待审核规则',
    description: '审核从文章中提取的候选规则。',
    element: <RulesReviewPage />,
    renderWithAvailability: (availability) => <RulesReviewPage availability={availability} />,
    parentId: 'rules',
  },
  {
    id: 'rules-library',
    kind: 'canonical',
    path: '/rules/library',
    label: '正式规则',
    description: '查看当前规则库和规则详情。',
    element: <RulesLibraryPage />,
    renderWithAvailability: (availability) => <RulesLibraryPage availability={availability} />,
    parentId: 'rules',
  },
  {
    id: 'rules-backtests',
    kind: 'canonical',
    path: '/rules/backtests',
    label: '回测实验',
    description: '使用现有真实能力创建和查看回测。',
    element: <RulesBacktestsPage />,
    renderWithAvailability: (availability) => <RulesBacktestsPage availability={availability} />,
    parentId: 'rules',
  },
  {
    id: 'rules-results',
    kind: 'canonical',
    path: '/rules/results',
    label: '回测结果',
    description: '查看全周期和分市场状态回测结果。',
    element: <RulesResultsPage />,
    renderWithAvailability: (availability) => <RulesResultsPage availability={availability} />,
    parentId: 'rules',
  },
  {
    id: 'authors',
    kind: 'canonical',
    path: '/authors',
    label: '作者画像',
    description: '查看作者文章方法与现有画像证据。',
    element: <AuthorsPage />,
    renderWithAvailability: (availability) => <AuthorsPage availability={availability} />,
    primary: true,
  },
  {
    id: 'strategies',
    kind: 'canonical',
    path: '/strategies',
    label: '策略中心',
    description: '查看策略候选版本和当前策略能力。',
    element: <StrategyOverviewPage />,
    renderWithAvailability: (availability) => <StrategyOverviewPage availability={availability} />,
    primary: true,
    legacy: legacy(
      '/strategies',
      'notice',
      '长期保留',
      '策略中心作为正式入口长期保留，后续在同一路径替换领域实现。',
      false,
    ),
  },
  {
    id: 'strategies-candidates',
    kind: 'canonical',
    path: '/strategies/candidates',
    label: '候选版本',
    description: '查看现有真实策略候选版本。',
    element: <StrategyCandidatesPage />,
    renderWithAvailability: (availability) => <StrategyCandidatesPage availability={availability} />,
    parentId: 'strategies',
  },
  {
    id: 'daily',
    kind: 'canonical',
    path: '/daily',
    label: '每日交易',
    description: '查看今日总览、盘前计划和盘后复盘。',
    element: redirect('/daily/overview'),
    renderMode: 'redirect',
    primary: true,
  },
  {
    id: 'daily-overview',
    kind: 'canonical',
    path: '/daily/overview',
    label: '今日总览',
    description: '查看每日交易当前状态和可执行入口。',
    element: <DailyOverviewPage />,
    renderWithAvailability: (availability) => <DailyOverviewPage availability={availability} />,
    parentId: 'daily',
  },
  {
    id: 'daily-pre-market',
    kind: 'canonical',
    path: '/daily/pre-market',
    label: '今日盘前',
    description: '使用现有真实能力生成和查看盘前分析。',
    element: <DailyPreMarketPage />,
    renderWithAvailability: (availability) => <DailyPreMarketPage availability={availability} />,
    parentId: 'daily',
  },
  {
    id: 'daily-after-close',
    kind: 'canonical',
    path: '/daily/after-close',
    label: '今日盘后',
    description: '使用现有真实能力执行和查看盘后复盘。',
    element: <DailyAfterClosePage />,
    renderWithAvailability: (availability) => <DailyAfterClosePage availability={availability} />,
    parentId: 'daily',
  },
  {
    id: 'system',
    kind: 'canonical',
    path: '/system',
    label: '系统管理',
    description: '查看系统状态、分类入口和修复路径。',
    element: <SystemPage />,
    primary: true,
    legacy: legacy('/system/status', 'notice', '长期保留', RETIREMENT.system, false),
  },
  {
    id: 'system-status',
    kind: 'canonical',
    path: '/system/status',
    label: '系统状态',
    description: '查看系统运行状态和关键依赖。',
    element: <SystemStatusPage />,
    renderWithAvailability: (availability) => <SystemStatusPage availability={availability} />,
    parentId: 'system',
  },
  {
    id: 'system-configuration',
    kind: 'canonical',
    path: '/system/configuration',
    label: '配置管理',
    description: '管理配置、版本和导入入口。',
    element: <SystemConfigurationPage />,
    renderWithAvailability: (availability) => <SystemConfigurationPage availability={availability} />,
    parentId: 'system',
  },
  {
    id: 'system-data',
    kind: 'canonical',
    path: '/system/data',
    label: '数据与调度',
    description: '查看数据状态、调度窗口和维护入口。',
    element: <SystemDataPage />,
    renderWithAvailability: (availability) => <SystemDataPage availability={availability} />,
    parentId: 'system',
  },
  {
    id: 'system-jobs',
    kind: 'canonical',
    path: '/system/jobs',
    label: '任务管理',
    description: '查看、筛选和控制后台任务。',
    element: <JobsPage />,
    parentId: 'system',
  },
  {
    id: 'system-job-new',
    kind: 'canonical',
    path: '/system/jobs/new',
    label: '新建任务',
    description: '操作员和管理员创建高级系统任务。',
    element: <JobNewPage />,
    minRole: 'operator',
    parentId: 'system',
  },
  {
    id: 'system-job-detail',
    kind: 'canonical',
    path: '/system/jobs/:jobId',
    label: '任务详情',
    description: '查看单个任务的状态、进度、日志、结果和产物。',
    element: <JobDetailPage />,
    parentId: 'system',
  },
  {
    id: 'system-runs',
    kind: 'canonical',
    path: '/system/runs',
    label: '运行与告警',
    description: '查看系统运行记录和失败原因。',
    element: <SystemRunsPage />,
    renderWithAvailability: (availability) => <SystemRunsPage availability={availability} />,
    parentId: 'system',
  },
  {
    id: 'dashboard-compat',
    kind: 'compat',
    path: '/dashboard',
    label: '首页旧入口',
    description: '旧首页入口已迁移到产品首页。',
    element: redirect('/'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/', 'redirect', 'Stage 1', RETIREMENT.dashboard),
  },
  {
    id: 'jobs',
    kind: 'compat',
    path: '/jobs',
    label: '任务管理旧入口',
    description: '旧任务管理入口已迁移到系统任务管理。',
    element: redirect('/system/jobs'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/jobs', 'redirect', 'Post-delivery Task 2', RETIREMENT.runtime),
  },
  {
    id: 'job-detail',
    kind: 'compat',
    path: '/jobs/:jobId',
    label: '任务详情旧入口',
    description: '旧任务详情入口已迁移到系统任务管理。',
    element: <JobDetailRedirect />,
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/jobs/:jobId', 'redirect', 'Post-delivery Task 2', RETIREMENT.runtime),
  },
  {
    id: 'profiles',
    kind: 'compat',
    path: '/profiles',
    label: '配置列表',
    description: '查看现有配置。',
    element: redirect('/system/configuration'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/configuration', 'redirect', 'Stage 11', RETIREMENT.profiles),
  },
  {
    id: 'profiles-import',
    kind: 'compat',
    path: '/profiles/import',
    label: '导入配置',
    description: '导入现有配置。',
    element: redirect('/system/configuration'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/configuration', 'redirect', 'Stage 11', RETIREMENT.profiles),
  },
  {
    id: 'profile-detail',
    kind: 'compat',
    path: '/profiles/:profileId',
    label: '配置详情',
    description: '查看现有配置详情。',
    element: redirect('/system/configuration'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/configuration', 'redirect', 'Stage 12', RETIREMENT.profiles),
  },
  {
    id: 'profile-edit',
    kind: 'compat',
    path: '/profiles/:profileId/edit',
    label: '编辑配置',
    description: '编辑现有配置。',
    element: redirect('/system/configuration'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/configuration', 'redirect', 'Stage 12', RETIREMENT.profiles),
  },
  {
    id: 'profile-snapshot',
    kind: 'compat',
    path: '/profiles/:profileId/snapshots/:snapshotId',
    label: '配置版本',
    description: '查看现有配置版本。',
    element: redirect('/system/configuration'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/configuration', 'redirect', 'Stage 12', RETIREMENT.profiles),
  },
  {
    id: 'workflows',
    kind: 'compat',
    path: '/workflows',
    label: '历史流程入口',
    description: '继续访问现有流程记录。',
    element: redirect('/system/runs'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/runs', 'redirect', 'Stage 11', RETIREMENT.runtime),
  },
  {
    id: 'workflow-pre-market',
    kind: 'compat',
    path: '/workflows/pre-market',
    label: '盘前流程旧入口',
    description: '旧盘前流程入口已迁移。',
    element: redirect('/daily/pre-market'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/daily/pre-market', 'redirect', 'Stage 9', RETIREMENT.strategy),
  },
  {
    id: 'workflow-pre-market-run',
    kind: 'compat',
    path: '/workflows/pre-market/run',
    label: '盘前执行旧入口',
    description: '旧盘前执行入口已迁移。',
    element: redirect('/daily/pre-market'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/daily/pre-market', 'redirect', 'Stage 9', RETIREMENT.strategy),
  },
  {
    id: 'workflow-after-close',
    kind: 'compat',
    path: '/workflows/after-close',
    label: '盘后流程旧入口',
    description: '旧盘后流程入口已迁移。',
    element: redirect('/daily/after-close'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/daily/after-close', 'redirect', 'Stage 10', RETIREMENT.strategy),
  },
  {
    id: 'workflow-after-close-run',
    kind: 'compat',
    path: '/workflows/after-close/run',
    label: '盘后执行旧入口',
    description: '旧盘后执行入口已迁移。',
    element: redirect('/daily/after-close'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/daily/after-close', 'redirect', 'Stage 10', RETIREMENT.strategy),
  },
  {
    id: 'workflow-run',
    kind: 'compat',
    path: '/workflows/:workflowId/run',
    label: '历史流程运行',
    description: '继续访问现有流程运行入口。',
    element: redirect('/system/runs'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/runs', 'redirect', 'Stage 12', RETIREMENT.runtime),
  },
  {
    id: 'articles',
    kind: 'compat',
    path: '/articles',
    label: '研究中心旧入口',
    description: '旧文章入口已迁移到研究中心。',
    element: redirect('/research/articles'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/research/articles', 'redirect', 'Stage 1', RETIREMENT.research),
  },
  {
    id: 'articles-run',
    kind: 'compat',
    path: '/articles/run',
    label: '文章处理旧入口',
    description: '继续使用现有文章导入和处理能力。',
    element: redirect('/research/add'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/research/add', 'redirect', 'Stage 3', RETIREMENT.research),
  },
  {
    id: 'articles-list',
    kind: 'compat',
    path: '/articles/list',
    label: '文章列表旧入口',
    description: '继续访问现有文章列表。',
    element: redirect('/research/articles'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/research/articles', 'redirect', 'Stage 3', RETIREMENT.research),
  },
  {
    id: 'articles-quality',
    kind: 'compat',
    path: '/articles/quality',
    label: '文章质量旧入口',
    description: '继续查看现有文章质量结果。',
    element: redirect('/research/results'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/research/results', 'redirect', 'Stage 3', RETIREMENT.research),
  },
  {
    id: 'articles-results',
    kind: 'compat',
    path: '/articles/results',
    label: '提取结果旧入口',
    description: '继续查看现有文章处理结果。',
    element: redirect('/research/results'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/research/results', 'redirect', 'Stage 4', RETIREMENT.research),
  },
  {
    id: 'alerts',
    kind: 'compat',
    path: '/alerts',
    label: '告警旧入口',
    description: '继续查看现有告警记录。',
    element: redirect('/system/runs'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/runs', 'redirect', 'Stage 11', RETIREMENT.alerts),
  },
  {
    id: 'backtest',
    kind: 'compat',
    path: '/backtest',
    label: '回测旧入口',
    description: '继续使用现有回测能力。',
    element: redirect('/rules/backtests'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/rules/backtests', 'redirect', 'Stage 6', RETIREMENT.rules),
  },
  {
    id: 'backtest-regime',
    kind: 'compat',
    path: '/backtest/regime',
    label: '分市场状态回测旧入口',
    description: '继续查看现有分市场状态回测结果。',
    element: redirect('/rules/results'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/rules/results', 'redirect', 'Stage 12', RETIREMENT.rules),
  },
  {
    id: 'backtest-candidates',
    kind: 'compat',
    path: '/backtest/candidates',
    label: '策略候选旧入口',
    description: '继续查看现有策略候选版本。',
    element: redirect('/strategies/candidates'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/strategies/candidates', 'redirect', 'Stage 8', RETIREMENT.strategy),
  },
  {
    id: 'rule-pool',
    kind: 'compat',
    path: '/rule-pool',
    label: '规则列表旧入口',
    description: '继续使用现有规则审核能力。',
    element: redirect('/rules/review'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/rules/review', 'redirect', 'Stage 4', RETIREMENT.rules),
  },
  {
    id: 'rule-pool-detail',
    kind: 'compat',
    path: '/rule-pool/:ruleId',
    label: '规则详情旧入口',
    description: '继续查看现有规则详情。',
    element: redirect('/rules/library'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/rules/library', 'redirect', 'Stage 12', RETIREMENT.rules),
  },
  {
    id: 'artifacts',
    kind: 'compat',
    path: '/artifacts',
    label: '结果附件旧入口',
    description: '继续查看现有运行输出。',
    element: redirect('/system/runs'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/runs', 'redirect', 'Stage 12', RETIREMENT.runtime),
  },
  {
    id: 'artifact-detail',
    kind: 'compat',
    path: '/artifacts/:artifactId',
    label: '结果附件详情',
    description: '继续查看现有运行输出详情。',
    element: redirect('/system/runs'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/runs', 'redirect', 'Stage 12', RETIREMENT.runtime),
  },
  {
    id: 'market',
    kind: 'compat',
    path: '/market',
    label: '市场数据旧入口',
    description: '继续使用现有市场数据维护能力。',
    element: redirect('/system/data'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/data', 'redirect', 'Stage 5', RETIREMENT.market),
  },
  {
    id: 'market-snapshots',
    kind: 'compat',
    path: '/market/snapshots',
    label: '市场快照详情',
    description: '继续查看现有市场快照。',
    element: redirect('/system/data'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/data', 'redirect', 'Stage 12', RETIREMENT.market),
  },
  {
    id: 'market-datasets',
    kind: 'compat',
    path: '/market/datasets',
    label: '回测数据版本详情',
    description: '继续查看现有市场数据集。',
    element: redirect('/system/data'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/data', 'redirect', 'Stage 12', RETIREMENT.market),
  },
  {
    id: 'market-kaipan',
    kind: 'compat',
    path: '/market/kaipan',
    label: '盘前盘后数据旧入口',
    description: '继续使用现有盘前盘后数据维护能力。',
    element: redirect('/system/data'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/data', 'redirect', 'Stage 5', RETIREMENT.market),
  },
  {
    id: 'market-ohlcv',
    kind: 'compat',
    path: '/market/ohlcv',
    label: '历史行情旧入口',
    description: '继续使用现有历史行情维护能力。',
    element: redirect('/system/data'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/data', 'redirect', 'Stage 5', RETIREMENT.market),
  },
  {
    id: 'persona',
    kind: 'compat',
    path: '/persona',
    label: '画像旧入口',
    description: '继续查看现有画像证据。',
    element: redirect('/authors'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/authors', 'redirect', 'Stage 7', RETIREMENT.persona),
  },
  {
    id: 'strategies-pre-market',
    kind: 'compat',
    path: '/strategies/pre-market',
    label: '盘前分析旧入口',
    description: '继续使用现有盘前分析能力。',
    element: redirect('/daily/pre-market'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/daily/pre-market', 'redirect', 'Stage 9', RETIREMENT.strategy),
  },
  {
    id: 'strategies-after-close',
    kind: 'compat',
    path: '/strategies/after-close',
    label: '盘后复盘旧入口',
    description: '继续使用现有盘后复盘能力。',
    element: redirect('/daily/after-close'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/daily/after-close', 'redirect', 'Stage 10', RETIREMENT.strategy),
  },
  {
    id: 'system-audit',
    kind: 'canonical',
    path: '/system/audit',
    label: '权限与审计',
    description: '查看权限和高风险操作记录。',
    element: <AuditPage />,
    parentId: 'system',
    minRole: 'admin',
    legacy: legacy('/system/audit', 'notice', '长期保留', RETIREMENT.system, false),
  },
  {
    id: 'system-users',
    kind: 'canonical',
    path: '/system/users',
    label: '用户管理',
    description: '管理系统用户和访问权限。',
    element: <UsersPage />,
    parentId: 'system',
    minRole: 'admin',
    legacy: legacy('/system/users', 'notice', '长期保留', RETIREMENT.system, false),
  },
  {
    id: 'system-health',
    kind: 'canonical',
    path: '/system/health',
    label: '系统健康',
    description: '查看系统依赖和服务健康状态。',
    element: <HealthPage />,
    parentId: 'system',
    minRole: 'admin',
    legacy: legacy('/system/health', 'notice', '长期保留', RETIREMENT.system, false),
  },
  {
    id: 'system-db-migrate',
    kind: 'canonical',
    path: '/system/db-migrate',
    label: '数据库迁移',
    description: '执行受权限保护的数据库迁移。',
    element: <DatabaseMigrationPage />,
    parentId: 'system',
    minRole: 'admin',
    visibleInNavigation: false,
    legacy: legacy('/system/db-migrate', 'notice', '长期保留', RETIREMENT.system, false),
  },
  {
    id: 'system-backup',
    kind: 'canonical',
    path: '/system/backup',
    label: '备份恢复',
    description: '管理系统数据备份和恢复。',
    element: <BackupPage />,
    parentId: 'system',
    minRole: 'admin',
    legacy: legacy('/system/backup', 'notice', '长期保留', RETIREMENT.system, false),
  },
  {
    id: 'admin',
    kind: 'compat',
    path: '/admin',
    label: '系统管理旧入口',
    description: '旧管理入口已迁移到系统管理。',
    element: redirect('/system/status'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/status', 'redirect', 'Stage 12', RETIREMENT.redirects),
  },
  {
    id: 'admin-audit',
    kind: 'compat',
    path: '/admin/audit',
    label: '审计旧入口',
    description: '旧审计入口已迁移。',
    element: redirect('/system/audit'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/audit', 'redirect', 'Stage 12', RETIREMENT.redirects),
  },
  {
    id: 'system-restore',
    kind: 'compat',
    path: '/system/restore',
    label: '恢复旧入口',
    description: '旧恢复入口已迁移到备份恢复。',
    element: redirect('/system/backup'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/backup', 'redirect', 'Stage 12', RETIREMENT.redirects),
  },
  {
    id: 'settings',
    kind: 'compat',
    path: '/settings',
    label: '配置旧入口',
    description: '旧配置入口已迁移到系统管理。',
    element: redirect('/system/configuration'),
    renderMode: 'redirect',
    visibleInNavigation: false,
    legacy: legacy('/system/configuration', 'redirect', 'Stage 12', RETIREMENT.profiles),
  },
  {
    id: 'not-found',
    kind: 'canonical',
    path: '*',
    label: '页面未找到',
    description: '请求的页面不存在或入口已经迁移。',
    element: <NotFoundPage />,
    visibleInNavigation: false,
    legacy: legacy('*', 'notice', '长期保留', RETIREMENT.notFound, false),
  },
];

function toNavigationItem(route: ProductRoute): NavigationItem {
  return {
    label: route.label,
    path: route.path,
    description: route.description,
    ...(route.minRole ? { minRole: route.minRole } : {}),
  };
}

export const primaryNavigation = routeConfig
  .filter((route) => route.primary && route.visibleInNavigation !== false)
  .map(toNavigationItem);

export const canonicalRoutes = routeConfig.filter((route) => route.kind === 'canonical');
export const compatibilityRoutes = routeConfig.filter((route) => route.kind === 'compat');

export function renderRouteWithAvailability(route: ProductRoute, availability: PageAvailability) {
  if (route.renderMode === 'redirect') {
    return null;
  }
  if (route.renderWithAvailability) {
    return route.renderWithAvailability(availability);
  }

  const nextPath = route.legacy?.targetPath && route.legacy.targetPath !== '*'
    ? route.legacy.targetPath
    : '/';

  return (
    <ProductPageAdapter
      title={route.label}
      queryState={availability}
      purpose={route.description}
      inputDescription="输入来自当前页面连接的真实业务记录。"
      processingDescription="系统按当前可用性展示处理状态，不用默认值替代缺失事实。"
      outputDescription="输出只展示已经确认的结果；不可用内容会明确说明影响。"
      businessAction={{ label: nextPath === '/' ? '返回首页' : '前往正式入口', to: nextPath }}
    />
  );
}

export function getSectionNavigation(parentId: string) {
  return routeConfig
    .filter((route) => route.parentId === parentId && route.visibleInNavigation !== false)
    .map(toNavigationItem);
}

export function resolveRoute(pathname: string) {
  return routeConfig.find((route) => matchPath({ path: route.path, end: true }, pathname));
}

export function resolveLegacyRoute(path: string) {
  return routeConfig.find((route) => route.path === path && route.legacy);
}
