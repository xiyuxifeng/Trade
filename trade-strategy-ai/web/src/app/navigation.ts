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
  { label: 'Snapshots', path: '/snapshots', description: 'Market universe snapshots' },
  { label: 'Strategy Studio', path: '/strategy-studio', description: 'Strategy versions, optimization, and rule pool' },
  { label: 'Signals', path: '/signals', description: 'Signal browsing and context summary' },
  { label: 'Persona', path: '/persona', description: 'Persona samples and cluster generation' },
  { label: 'Market State', path: '/market-state', description: 'Market state snapshot builder' },
  { label: 'Imports', path: '/imports', description: 'Trade logs and crawl state migration' },
  { label: 'Kaipan', path: '/kaipan', description: 'Kaipan fetch, normalize, and run controls' },
  { label: 'Data Health', path: '/data-health', description: 'Dashboard report and HTML artifact' },
  { label: 'Strategies', path: '/strategies', description: 'Strategy version library' },
  { label: 'Backtests', path: '/backtests', description: 'Backtest results and analysis' },
  { label: 'Alerts', path: '/alerts', description: 'Alert history and acknowledgements' },
  { label: 'Reports', path: '/reports', description: 'Pre/post market reports' },
  { label: 'Settings', path: '/settings', description: 'Configuration and secrets' },
  { label: 'Ops', path: '/ops', description: 'Deployment and recovery tooling' },
];
