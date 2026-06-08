import { describe, expect, it } from 'vitest';
import { routeRegistry, resolveRouteByPathname } from './route-registry';

describe('resolveRouteByPathname', () => {
  it('resolves the current user-facing routes and omits retired compatibility paths', () => {
    expect(resolveRouteByPathname('/dashboard').label).toBe('概览');
    expect(resolveRouteByPathname('/dashboard').description).toBe('主流程概览与系统摘要');
    expect(resolveRouteByPathname('/jobs').label).toBe('任务中心');
    expect(resolveRouteByPathname('/jobs/job-1').path).toBe('/jobs/:jobId');
    expect(resolveRouteByPathname('/articles').label).toBe('文章与规则');
    expect(resolveRouteByPathname('/articles/run').label).toBe('文章导入与处理');
    expect(routeRegistry.some((route) => route.path === '/articles/jobs')).toBe(false);
    expect(routeRegistry.some((route) => route.path === '/articles/maintenance')).toBe(false);
    expect(resolveRouteByPathname('/market').label).toBe('市场上下文');
    expect(resolveRouteByPathname('/market/snapshots').label).toBe('市场上下文快照');
    expect(resolveRouteByPathname('/market/kaipan').label).toBe('市场数据健康');
    expect(resolveRouteByPathname('/market/ohlcv').label).toBe('OHLCV 数据');
    expect(resolveRouteByPathname('/backtest').label).toBe('回测与画像');
    expect(resolveRouteByPathname('/rule-pool').label).toBe('规则审核');
    expect(resolveRouteByPathname('/persona').label).toBe('交易员画像');
    expect(routeRegistry.some((route) => route.path === '/strategies')).toBe(false);
    expect(resolveRouteByPathname('/strategies/pre-market').label).toBe('盘前分析');
    expect(resolveRouteByPathname('/strategies/pre-market').kind).toBe('canonical');
    expect(resolveRouteByPathname('/strategies/after-close').label).toBe('盘后复盘');
    expect(resolveRouteByPathname('/strategies/after-close').kind).toBe('canonical');
    expect(routeRegistry.some((route) => route.path === '/strategies/versions')).toBe(false);
    expect(routeRegistry.some((route) => route.path === '/strategies/candidates')).toBe(false);
    expect(routeRegistry.some((route) => route.path === '/strategies/history')).toBe(false);
    expect(routeRegistry.some((route) => route.path === '/strategies/regime-selection')).toBe(false);
    expect(resolveRouteByPathname('/artifacts').label).toBe('产物中心');
    expect(resolveRouteByPathname('/profiles').label).toBe('配置与管理');
    expect(resolveRouteByPathname('/system').label).toBe('系统管理');
    expect(resolveRouteByPathname('/system/backup').label).toBe('数据备份与恢复');
    expect(routeRegistry.some((route) => route.path === '/admin')).toBe(false);
  });
});
