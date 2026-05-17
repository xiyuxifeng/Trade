import { describe, expect, it } from 'vitest';
import { allNavigationItems, mainNavigation, navigationGroups } from './navigation';

describe('navigation contract', () => {
  it('keeps the formal sidebar free of legacy entries', () => {
    expect(navigationGroups.map((group) => group.title)).toEqual(['正式入口', '业务工作台', '配置与管理']);
    expect(mainNavigation.map((item) => item.path)).toEqual([
      '/dashboard',
      '/jobs',
      '/workflows',
      '/articles',
      '/market',
      '/market/datasets',
      '/strategies',
      '/backtest',
      '/rule-pool',
      '/artifacts',
      '/profiles',
      '/admin',
      '/settings',
    ]);
  });

  it('still resolves legacy routes for current route chrome', () => {
    expect(allNavigationItems.some((item) => item.path === '/alerts')).toBe(true);
    expect(allNavigationItems.some((item) => item.path === '/reports')).toBe(true);
  });
});
