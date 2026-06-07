import { matchPath } from 'react-router-dom';

export type RouteKind = 'canonical';

export type RouteRecord = {
  label: string;
  path: string;
  description: string;
  kind: RouteKind;
};

export const routeRegistry: RouteRecord[] = [
  { label: '概览', path: '/dashboard', description: '主流程概览与系统摘要', kind: 'canonical' },
  { label: '任务中心', path: '/jobs', description: '统一查看任务状态、日志和结果', kind: 'canonical' },
  { label: '任务详情', path: '/jobs/:jobId', description: '统一查看任务状态、日志和结果', kind: 'canonical' },
  { label: '重点告警', path: '/alerts', description: '查看重点告警摘要和历史记录', kind: 'canonical' },
  { label: '工作流兼容入口', path: '/workflows', description: '旧工作流入口的兼容页', kind: 'canonical' },
  { label: '工作流兼容入口', path: '/workflows/:workflowId/run', description: '旧工作流入口的兼容页', kind: 'canonical' },
  { label: '文章与规则', path: '/articles', description: '导入文章、提取规则、查看结果', kind: 'canonical' },
  { label: '文章导入与处理', path: '/articles/run', description: '导入文章并启动规则提取流程', kind: 'canonical' },
  { label: '文章列表', path: '/articles/list', description: '文章列表页面', kind: 'canonical' },
  { label: '文章质量', path: '/articles/quality', description: '文章数据质量页面', kind: 'canonical' },
  { label: '最近任务', path: '/articles/jobs', description: '文章页历史任务入口（兼容）', kind: 'canonical' },
  { label: '处理结果', path: '/articles/results', description: '文章处理结果页面', kind: 'canonical' },
  { label: '高级维护', path: '/articles/maintenance', description: '文章高级维护页面（兼容）', kind: 'canonical' },
  { label: '市场上下文', path: '/market', description: '查看统一市场上下文和数据资产', kind: 'canonical' },
  { label: '市场上下文快照', path: '/market/snapshots', description: '浏览统一市场上下文快照', kind: 'canonical' },
  { label: '市场数据集', path: '/market/datasets', description: '浏览市场数据集', kind: 'canonical' },
  { label: '市场数据健康', path: '/market/kaipan', description: '查看市场数据健康与抓取状态', kind: 'canonical' },
  { label: 'OHLCV 数据', path: '/market/ohlcv', description: '查看 OHLCV 数据资产', kind: 'canonical' },
  { label: '规则工作台（兼容入口）', path: '/strategies', description: '旧规则工作台兼容入口', kind: 'canonical' },
  { label: '交易员画像', path: '/persona', description: '交易风格画像与行为规则', kind: 'canonical' },
  { label: '规则版本', path: '/strategies/versions', description: '规则版本构建与查看', kind: 'canonical' },
  { label: '候选规则版本', path: '/strategies/candidates', description: '候选规则版本生成与审核', kind: 'canonical' },
  { label: '兼容入口历史', path: '/strategies/history', description: '规则工作台兼容入口历史与筛选', kind: 'canonical' },
  { label: '盘前分析', path: '/strategies/pre-market', description: '盘前分析与关注对象建议', kind: 'canonical' },
  { label: '盘后复盘', path: '/strategies/after-close', description: '盘后复盘与偏差分析', kind: 'canonical' },
  { label: '规则选择', path: '/strategies/regime-selection', description: '兼容到回测与画像流程的规则选择视图', kind: 'canonical' },
  { label: '回测与画像', path: '/backtest', description: '验证规则、沉淀画像并查看回测结果', kind: 'canonical' },
  { label: '市场状态回测', path: '/backtest/regime', description: '市场状态回测报告', kind: 'canonical' },
  { label: '规则审核', path: '/rule-pool', description: '规则池审核中心', kind: 'canonical' },
  { label: '规则审核', path: '/rule-pool/:ruleId', description: '规则池详情与审核', kind: 'canonical' },
  { label: '产物中心', path: '/artifacts', description: '日志、下载文件与输出结果', kind: 'canonical' },
  { label: '产物详情', path: '/artifacts/:artifactId', description: '产物详情与预览下载', kind: 'canonical' },
  { label: '配置与管理', path: '/profiles', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置导入', path: '/profiles/import', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置编辑', path: '/profiles/:profileId/edit', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置快照', path: '/profiles/:profileId/snapshots/:snapshotId', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置详情', path: '/profiles/:profileId', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '系统管理', path: '/system', description: '系统健康、审计与运维入口', kind: 'canonical' },
  { label: '权限与审计', path: '/system/audit', description: '权限、审计与高风险操作历史', kind: 'canonical' },
  { label: '用户管理', path: '/system/users', description: '添加、删除、禁用和改密入口', kind: 'canonical' },
  { label: '系统健康检查', path: '/system/health', description: 'API、DB、worker 与存储健康状态', kind: 'canonical' },
  { label: '数据库迁移', path: '/system/db-migrate', description: '数据库迁移高风险操作入口', kind: 'canonical' },
  { label: '数据备份与恢复', path: '/system/backup', description: '备份与恢复统一入口', kind: 'canonical' },
];

export function resolveRouteByPathname(pathname: string) {
  return (
    routeRegistry.find((route) => matchPath({ path: route.path, end: true }, pathname)) ??
    routeRegistry[0]
  );
}
