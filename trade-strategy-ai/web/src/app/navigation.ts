export type NavItem = {
  label: string;
  path: string;
  description: string;
};

export const mainNavigation: NavItem[] = [
  { label: 'Overview', path: '/', description: 'System health and entry summary' },
  { label: 'Jobs', path: '/jobs', description: 'Long-running task center' },
  { label: 'Workflows', path: '/workflows', description: 'UserManual guided flows' },
  { label: 'Artifacts', path: '/artifacts', description: 'Logs, downloads, and outputs' },
  { label: 'Market', path: '/market', description: 'Symbols and OHLCV lookup' },
  { label: 'Strategies', path: '/strategies', description: 'Strategy version library' },
  { label: 'Backtests', path: '/backtests', description: 'Backtest results and analysis' },
  { label: 'Reports', path: '/reports', description: 'Pre/post market reports' },
  { label: 'Settings', path: '/settings', description: 'Configuration and secrets' },
  { label: 'Ops', path: '/ops', description: 'Deployment and recovery tooling' },
];
