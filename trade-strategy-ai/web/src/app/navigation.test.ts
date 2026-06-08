import { describe, expect, it } from 'vitest';
import { mainNavigation, navigationGroups } from './navigation';

describe('navigation contract', () => {
  it('keeps the formal sidebar free of legacy entries', () => {
    expect(navigationGroups.map((group) => group.title)).toEqual(['正式入口', '主流程', '辅助入口']);
    expect(mainNavigation.map((item) => item.path)).toEqual([
      '/dashboard',
      '/jobs',
      '/articles',
      '/market',
      '/backtest',
      '/strategies/pre-market',
      '/strategies/after-close',
      '/artifacts',
      '/profiles',
      '/system',
    ]);
    expect(mainNavigation.find((item) => item.path === '/articles')?.description).toBe('导入文章、提取规则、查看结果');
    expect(mainNavigation.find((item) => item.path === '/backtest')?.description).toBe('验证规则、沉淀画像并查看回测结果');
    expect(mainNavigation.find((item) => item.path === '/market')?.description).toBe('查看统一市场上下文和数据资产');
  });

});
