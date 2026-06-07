import { describe, expect, it } from 'vitest';
import { routeRegistry, resolveRouteByPathname } from './route-registry';

describe('resolveRouteByPathname', () => {
  it('resolves the current user-facing routes and compatibility paths', () => {
    expect(resolveRouteByPathname('/dashboard').label).toBe('概览');
    expect(resolveRouteByPathname('/dashboard').description).toBe('主流程概览与系统摘要');
    expect(resolveRouteByPathname('/jobs').label).toBe('任务中心');
    expect(resolveRouteByPathname('/jobs/job-1').path).toBe('/jobs/:jobId');
    expect(resolveRouteByPathname('/articles').label).toBe('文章与规则');
    expect(resolveRouteByPathname('/articles/run').label).toBe('文章导入与处理');
    expect(resolveRouteByPathname('/market').label).toBe('市场上下文');
    expect(resolveRouteByPathname('/market/snapshots').label).toBe('市场上下文快照');
    expect(resolveRouteByPathname('/market/kaipan').label).toBe('市场数据健康');
    expect(resolveRouteByPathname('/market/ohlcv').label).toBe('OHLCV 数据');
    expect(resolveRouteByPathname('/backtest').label).toBe('回测与画像');
    expect(resolveRouteByPathname('/rule-pool').label).toBe('规则审核');
    expect(resolveRouteByPathname('/persona').label).toBe('交易员画像');
    expect(resolveRouteByPathname('/strategies').label).toBe('规则工作台（兼容入口）');
    expect(resolveRouteByPathname('/strategies').description).toBe('旧规则工作台兼容入口');
    expect(resolveRouteByPathname('/strategies/versions').label).toBe('规则版本');
    expect(resolveRouteByPathname('/strategies/candidates').label).toBe('候选规则版本');
    expect(resolveRouteByPathname('/strategies/history').label).toBe('兼容入口历史');
    expect(resolveRouteByPathname('/strategies/pre-market').label).toBe('盘前分析');
    expect(resolveRouteByPathname('/strategies/after-close').label).toBe('盘后复盘');
    expect(resolveRouteByPathname('/strategies/regime-selection').label).toBe('规则选择');
    expect(resolveRouteByPathname('/artifacts').label).toBe('产物中心');
    expect(resolveRouteByPathname('/profiles').label).toBe('配置与管理');
    expect(resolveRouteByPathname('/system').label).toBe('系统管理');
    expect(resolveRouteByPathname('/system/backup').label).toBe('数据备份与恢复');
    expect(routeRegistry.some((route) => route.path === '/admin')).toBe(false);
  });
});
