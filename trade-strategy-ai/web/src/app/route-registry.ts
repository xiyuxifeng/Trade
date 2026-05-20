import { matchPath } from 'react-router-dom';

export type RouteKind = 'canonical';

export type RouteRecord = {
  label: string;
  path: string;
  description: string;
  kind: RouteKind;
};

export const routeRegistry: RouteRecord[] = [
  { label: '仪表盘', path: '/dashboard', description: '系统运行状态与入口摘要', kind: 'canonical' },
  { label: '任务', path: '/jobs', description: '长时间运行的任务中心', kind: 'canonical' },
  { label: '任务', path: '/jobs/:jobId', description: '长时间运行的任务中心', kind: 'canonical' },
  { label: '工作流', path: '/workflows', description: '基于用户手册的引导流程', kind: 'canonical' },
  { label: '工作流', path: '/workflows/:workflowId/run', description: '基于用户手册的引导流程', kind: 'canonical' },
  { label: '文章', path: '/articles', description: '文章处理链路的验收入口', kind: 'canonical' },
  { label: '市场数据', path: '/market', description: '市场快照浏览器', kind: 'canonical' },
  { label: '市场数据集', path: '/market/datasets', description: '市场数据集浏览器', kind: 'canonical' },
  { label: '策略', path: '/strategies', description: '策略版本与正式工作台入口', kind: 'canonical' },
  { label: '规则选择', path: '/strategies/regime-selection', description: 'Regime-aware 规则选择视图', kind: 'canonical' },
  { label: '回测', path: '/backtest', description: '回测正式工作台', kind: 'canonical' },
  { label: 'Regime 回测', path: '/backtest/regime', description: 'Regime-aware 回测报告', kind: 'canonical' },
  { label: '规则池', path: '/rule-pool', description: '规则池审核中心', kind: 'canonical' },
  { label: '产物', path: '/artifacts', description: '日志、下载文件与输出结果', kind: 'canonical' },
  { label: '配置管理', path: '/profiles', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/import', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/:profileId/edit', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/:profileId/snapshots/:snapshotId', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/:profileId', description: '正式 Profile 配置入口', kind: 'canonical' },
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
