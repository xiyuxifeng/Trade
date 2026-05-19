import { describe, expect, it } from 'vitest';
import { resolveRouteByPathname } from './route-registry';

describe('resolveRouteByPathname', () => {
  it('resolves canonical routes', () => {
    expect(resolveRouteByPathname('/dashboard').path).toBe('/dashboard');
    expect(resolveRouteByPathname('/jobs').path).toBe('/jobs');
    expect(resolveRouteByPathname('/jobs/job-1').path).toBe('/jobs/:jobId');
    expect(resolveRouteByPathname('/workflows').path).toBe('/workflows');
    expect(resolveRouteByPathname('/workflows/pipeline/run').path).toBe('/workflows/:workflowId/run');
    expect(resolveRouteByPathname('/articles').path).toBe('/articles');
    expect(resolveRouteByPathname('/market').path).toBe('/market');
    expect(resolveRouteByPathname('/market').description).toBe('市场快照浏览器');
    expect(resolveRouteByPathname('/market/datasets').path).toBe('/market/datasets');
    expect(resolveRouteByPathname('/market/datasets').description).toBe('市场数据集浏览器');
    expect(resolveRouteByPathname('/strategies').path).toBe('/strategies');
    expect(resolveRouteByPathname('/strategies/regime-selection').path).toBe('/strategies/regime-selection');
    expect(resolveRouteByPathname('/backtest').path).toBe('/backtest');
    expect(resolveRouteByPathname('/backtest/regime').path).toBe('/backtest/regime');
    expect(resolveRouteByPathname('/rule-pool').path).toBe('/rule-pool');
    expect(resolveRouteByPathname('/rule-pool').description).toBe('规则池审核中心');
    expect(resolveRouteByPathname('/artifacts').path).toBe('/artifacts');
    expect(resolveRouteByPathname('/profiles').path).toBe('/profiles');
    expect(resolveRouteByPathname('/profiles/default').path).toBe('/profiles/:profileId');
    expect(resolveRouteByPathname('/profiles/import').path).toBe('/profiles/import');
    expect(resolveRouteByPathname('/profiles/default/edit').path).toBe('/profiles/:profileId/edit');
    expect(resolveRouteByPathname('/profiles/default/snapshots/snapshot-1').path).toBe('/profiles/:profileId/snapshots/:snapshotId');
    expect(resolveRouteByPathname('/admin').path).toBe('/admin');
    expect(resolveRouteByPathname('/admin/audit').path).toBe('/admin/audit');
    expect(resolveRouteByPathname('/admin/audit').label).toBe('权限与审计');
    expect(resolveRouteByPathname('/settings').path).toBe('/settings');
    expect(resolveRouteByPathname('/settings').label).toBe('配置管理');
  });

});
