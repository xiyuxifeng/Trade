import type { PrincipalRole } from '@/types/auth';

export type NavItem = {
  label: string;
  path: string;
  description: string;
  minRole?: PrincipalRole;
};

export const mainNavigation: NavItem[] = [
  { label: '仪表盘', path: '/dashboard', description: '系统运行状态与入口摘要' },
  { label: '任务', path: '/jobs', description: '长时间运行的任务中心' },
  { label: '配置管理', path: '/profiles', description: '正式 Profile 配置入口' },
  { label: '工作流', path: '/workflows', description: '基于用户手册的引导流程' },
  { label: '文章', path: '/articles', description: '文章处理链路的验收入口' },
  { label: '产物', path: '/artifacts', description: '日志、下载文件与输出结果' },
  { label: '市场', path: '/market', description: '标的与 K 线数据查询' },
  { label: '快照', path: '/snapshots', description: '市场全貌快照管理' },
  { label: '策略实验室', path: '/strategy-studio', description: '策略版本、优化与规则池' },
  { label: '信号', path: '/signals', description: '信号浏览与上下文摘要' },
  { label: '画像', path: '/persona', description: '画像样本与聚类生成' },
  { label: '市场状态', path: '/market-state', description: '市场状态快照构建器' },
  { label: '导入', path: '/imports', description: '交易日志与爬虫状态迁移' },
  { label: '开盘', path: '/kaipan', description: 'Kaipan 获取、清洗与运行控制' },
  { label: '数据健康', path: '/data-health', description: '运维仪表盘与 HTML 报告产物' },
  { label: '策略', path: '/strategies', description: '策略版本库' },
  { label: '回测', path: '/backtests', description: '回测结果与分析' },
  { label: '告警', path: '/alerts', description: '告警历史与确认' },
  { label: '报告', path: '/reports', description: '盘前/盘后报告中心' },
  { label: '设置', path: '/settings', description: '应用配置与密钥管理' },
  { label: '用户管理', path: '/users', description: '用户、角色与权限管理', minRole: 'admin' },
  { label: '运维', path: '/ops', description: '部署与恢复工具', minRole: 'admin' },
];
