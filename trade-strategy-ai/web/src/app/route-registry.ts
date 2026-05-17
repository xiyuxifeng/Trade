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
  { label: '工作流', path: '/workflows', description: '基于用户手册的引导流程', kind: 'canonical' },
  { label: '工作流', path: '/workflows/:workflowId/run', description: '基于用户手册的引导流程', kind: 'canonical' },
  { label: '文章', path: '/articles', description: '文章处理链路的验收入口', kind: 'canonical' },
  { label: '市场数据', path: '/market', description: '市场快照浏览器', kind: 'canonical' },
  { label: '策略', path: '/strategies', description: '策略版本与正式工作台入口', kind: 'canonical' },
  { label: '回测', path: '/backtest', description: '回测能力预留入口', kind: 'canonical' },
  { label: '规则池', path: '/rule-pool', description: '规则池能力预留入口', kind: 'canonical' },
  { label: '产物', path: '/artifacts', description: '日志、下载文件与输出结果', kind: 'canonical' },
  { label: '配置管理', path: '/profiles', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/import', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/:profileId/edit', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/:profileId/snapshots/:snapshotId', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '配置管理', path: '/profiles/:profileId', description: '正式 Profile 配置入口', kind: 'canonical' },
  { label: '管理中心', path: '/admin', description: '用户、运维与权限管理入口', kind: 'canonical' },
  { label: '设置', path: '/settings', description: '应用配置与密钥管理', kind: 'canonical' },
  { label: '告警', path: '/alerts', description: '告警历史与处理详情', kind: 'legacy', retirementStage: 'V3' },
  { label: '告警', path: '/alerts/:recordId', description: '告警历史与处理详情', kind: 'legacy', retirementStage: 'V3' },
  { label: '报告', path: '/reports', description: '盘前/盘后报告中心', kind: 'legacy', retirementStage: 'V3' },
  { label: '快照', path: '/snapshots', description: '市场全貌快照管理', kind: 'legacy', retirementStage: 'V3' },
  { label: '信号', path: '/signals', description: '信号浏览与上下文摘要', kind: 'legacy', retirementStage: 'V3' },
  { label: '画像', path: '/persona', description: '画像样本与聚类生成', kind: 'legacy', retirementStage: 'V3' },
  { label: '市场状态', path: '/market-state', description: '市场状态快照构建器', kind: 'legacy', retirementStage: 'V3' },
  { label: '导入', path: '/imports', description: '交易日志与爬虫状态迁移', kind: 'legacy', retirementStage: 'V3' },
  { label: '开盘', path: '/kaipan', description: 'Kaipan 获取、清洗与运行控制', kind: 'legacy', retirementStage: 'V3' },
  { label: '数据健康', path: '/data-health', description: '运维仪表盘与 HTML 报告产物', kind: 'legacy', retirementStage: 'V3' },
  { label: '策略实验室', path: '/strategy-studio', description: '旧策略实验入口，仅作兼容', kind: 'legacy', retirementStage: 'V3' },
  { label: '回测中心', path: '/backtests', description: '旧回测入口，仅作兼容', kind: 'legacy', retirementStage: 'V3' },
  { label: '用户管理', path: '/users', description: '用户、角色与权限管理', kind: 'legacy', retirementStage: 'V3' },
  { label: '运维', path: '/ops', description: '部署与恢复工具', kind: 'legacy', retirementStage: 'V3' },
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
