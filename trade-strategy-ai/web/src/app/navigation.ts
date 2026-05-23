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
    ],
  },
  {
    title: '业务工作台',
    items: [
      { label: '文章', path: '/articles', description: '文章工作台入口' },
      { label: '市场数据', path: '/market', description: '市场数据总览与入口' },
      { label: '策略', path: '/strategies', description: '策略状态摘要与工作台入口' },
      { label: '回测', path: '/backtest', description: '回测正式工作台' },
      { label: '规则池', path: '/rule-pool', description: '规则池审核中心' },
      { label: '产物', path: '/artifacts', description: '日志、下载文件与输出结果' },
    ],
  },
  {
    title: '配置与管理',
    items: [
      { label: '配置管理', path: '/profiles', description: '正式 Profile 配置入口' },
      { label: '系统管理', path: '/system', description: '系统健康、审计与运维入口', minRole: 'admin' },
    ],
  },
];

export const navigationGroups: NavGroup[] = [...formalNavigationGroups];

export const mainNavigation: NavItem[] = formalNavigationGroups.flatMap((group) => group.items);
export const allNavigationItems: NavItem[] = [...mainNavigation];
