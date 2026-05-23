import { describe, expect, it } from 'vitest';
import { mainNavigation, navigationGroups } from './navigation';

describe('navigation contract', () => {
  it('keeps the formal sidebar free of legacy entries', () => {
    expect(navigationGroups.map((group) => group.title)).toEqual(['正式入口', '业务工作台', '配置与管理']);
    expect(mainNavigation.map((item) => item.path)).toEqual([
      '/dashboard',
      '/jobs',
      '/articles',
      '/market',
      '/strategies',
      '/backtest',
      '/rule-pool',
      '/artifacts',
      '/profiles',
      '/system',
    ]);
    expect(mainNavigation.find((item) => item.path === '/rule-pool')?.description).toBe('规则池审核中心');
  });

});
