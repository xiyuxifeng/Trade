import type { PrincipalRole } from '@/types/auth';

export type NavItem = {
  label: string;
  path: string;
  description: string;
  minRole?: PrincipalRole;
};

export type NavGroup = {
  title: string;
  items: NavItem[];
};

const formalNavigationGroups: NavGroup[] = [
  {
    title: '正式入口',
    items: [
      { label: '仪表盘', path: '/dashboard', description: '系统运行状态与入口摘要' },
      { label: '任务', path: '/jobs', description: '长时间运行的任务中心' },
      { label: '工作流', path: '/workflows', description: '基于用户手册的引导流程' },
    ],
  },
  {
    title: '业务工作台',
    items: [
      { label: '文章', path: '/articles', description: '文章处理链路的验收入口' },
      { label: '市场数据', path: '/market', description: '市场快照浏览器' },
      { label: '策略', path: '/strategies', description: '策略版本与正式工作台入口' },
      { label: '回测', path: '/backtest', description: '回测能力预留入口' },
      { label: '规则池', path: '/rule-pool', description: '规则池能力预留入口' },
      { label: '产物', path: '/artifacts', description: '日志、下载文件与输出结果' },
    ],
  },
  {
    title: '配置与管理',
    items: [
      { label: '配置管理', path: '/profiles', description: '正式 Profile 配置入口' },
      { label: '管理中心', path: '/admin', description: '用户、运维与权限管理入口', minRole: 'admin' },
      { label: '设置', path: '/settings', description: '应用配置与密钥管理' },
    ],
  },
];

const compatibilityNavigationItems: NavItem[] = [
  { label: '快照', path: '/snapshots', description: '市场全貌快照管理' },
  { label: '告警', path: '/alerts', description: '告警历史与确认' },
  { label: '报告', path: '/reports', description: '盘前/盘后报告中心' },
  { label: '信号', path: '/signals', description: '信号浏览与上下文摘要' },
  { label: '画像', path: '/persona', description: '画像样本与聚类生成' },
  { label: '市场状态', path: '/market-state', description: '市场状态快照构建器' },
  { label: '导入', path: '/imports', description: '交易日志与爬虫状态迁移' },
  { label: '开盘', path: '/kaipan', description: 'Kaipan 获取、清洗与运行控制' },
  { label: '数据健康', path: '/data-health', description: '运维仪表盘与 HTML 报告产物' },
  { label: '策略实验室', path: '/strategy-studio', description: '旧策略实验入口，仅作兼容' },
  { label: '回测中心', path: '/backtests', description: '旧回测入口，仅作兼容' },
  { label: '用户管理', path: '/users', description: '用户、角色与权限管理', minRole: 'admin' },
  { label: '运维', path: '/ops', description: '部署与恢复工具', minRole: 'admin' },
];

export const navigationGroups: NavGroup[] = [
  ...formalNavigationGroups,
  {
    title: '兼容入口',
    items: compatibilityNavigationItems,
  },
];

export const mainNavigation: NavItem[] = formalNavigationGroups.flatMap((group) => group.items);
export const allNavigationItems: NavItem[] = navigationGroups.flatMap((group) => group.items);
