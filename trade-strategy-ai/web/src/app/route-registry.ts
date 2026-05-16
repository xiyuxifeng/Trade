import { matchPath } from 'react-router-dom';

export type RouteKind = 'canonical' | 'legacy';

export type RouteRecord = {
  label: string;
  path: string;
  description: string;
  kind: RouteKind;
  retirementStage?: 'V1' | 'V2' | 'V3';
};

export const routeRegistry: RouteRecord[] = [
  { label: '仪表盘', path: '/dashboard', description: '系统运行状态与入口摘要', kind: 'canonical' },
  { label: '任务', path: '/jobs', description: '长时间运行的任务中心', kind: 'canonical' },
  { label: '任务', path: '/jobs/:jobId', description: '长时间运行的任务中心', kind: 'canonical' },
  { label: '配置管理', path: '/profiles', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/import', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/:profileId/edit', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/:profileId/snapshots/:snapshotId', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/:profileId', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '工作流', path: '/workflows', description: '基于用户手册的引导流程', kind: 'canonical' },
  { label: '工作流', path: '/workflows/:workflowId/run', description: '基于用户手册的引导流程', kind: 'canonical' },
  { label: '文章', path: '/articles', description: '文章处理链路的验收入口', kind: 'canonical' },
  { label: '产物', path: '/artifacts', description: '日志、下载文件与输出结果', kind: 'canonical' },
  { label: '市场数据', path: '/market', description: '市场数据工作台', kind: 'canonical' },
  { label: '告警', path: '/alerts', description: '告警历史与处理详情', kind: 'canonical' },
  { label: '告警', path: '/alerts/:recordId', description: '告警历史与处理详情', kind: 'canonical' },
  { label: '设置', path: '/settings', description: '应用配置与密钥管理', kind: 'canonical' },
  { label: '仪表盘', path: '/', description: '系统运行状态与入口摘要', kind: 'legacy', retirementStage: 'V3' },
  { label: '仪表盘', path: '/overview', description: '系统运行状态与入口摘要', kind: 'legacy', retirementStage: 'V3' },
  { label: '工作流', path: '/workflows/:workflowId', description: '基于用户手册的引导流程', kind: 'legacy', retirementStage: 'V3' },
  { label: '兼容层', path: '/legacy/*', description: '临时兼容入口', kind: 'legacy', retirementStage: 'V3' },
];

export function resolveRouteByPathname(pathname: string) {
  return (
    routeRegistry.find((route) => matchPath({ path: route.path, end: true }, pathname)) ??
    routeRegistry[0]
  );
}
