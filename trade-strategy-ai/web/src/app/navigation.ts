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
      { label: '概览', path: '/dashboard', description: '主流程概览与系统摘要' },
      { label: '任务中心', path: '/jobs', description: '统一查看任务状态、日志和结果' },
    ],
  },
  {
    title: '主流程',
    items: [
      { label: '文章与规则', path: '/articles', description: '导入文章、提取规则、查看结果' },
      { label: '市场上下文', path: '/market', description: '查看统一市场上下文和数据资产' },
      { label: '回测与画像', path: '/backtest', description: '验证规则、沉淀画像并查看回测结果' },
      { label: '盘前分析', path: '/strategies/pre-market', description: '结合当天市场上下文生成盘前建议' },
      { label: '盘后复盘', path: '/strategies/after-close', description: '对照盘前判断复盘当天结果' },
    ],
  },
  {
    title: '辅助入口',
    items: [
      { label: '产物中心', path: '/artifacts', description: '日志、下载文件与输出结果' },
      { label: '配置与管理', path: '/profiles', description: '正式 Profile 配置入口' },
      { label: '系统管理', path: '/system', description: '系统健康、审计与运维入口', minRole: 'admin' },
    ],
  },
];

export const navigationGroups: NavGroup[] = [...formalNavigationGroups];

export const mainNavigation: NavItem[] = formalNavigationGroups.flatMap((group) => group.items);
export const allNavigationItems: NavItem[] = [...mainNavigation];
