import { describe, expect, it } from 'vitest';
import { routeConfig } from './route-config';
import { routeRegistry, resolveRouteByPathname } from './route-registry';

describe('resolveRouteByPathname', () => {
  it('derives the registry from route config', () => {
    expect(routeRegistry).toEqual(
      routeConfig.map(({ label, path, description, kind }) => ({
        label,
        path,
        description,
        kind,
      })),
    );
  });

  it('resolves canonical, compatibility, parameterized, and unknown paths', () => {
    expect(resolveRouteByPathname('/').label).toBe('首页');
    expect(resolveRouteByPathname('/dashboard').kind).toBe('compat');
    expect(resolveRouteByPathname('/articles').kind).toBe('compat');
    expect(resolveRouteByPathname('/strategies').label).toBe('策略中心');
    expect(resolveRouteByPathname('/jobs').kind).toBe('compat');
    expect(resolveRouteByPathname('/jobs/job-1').kind).toBe('compat');
    expect(resolveRouteByPathname('/market/snapshots').kind).toBe('compat');
    expect(resolveRouteByPathname('/system/audit').kind).toBe('canonical');
    expect(resolveRouteByPathname('/jobs/job-1').path).toBe('/jobs/:jobId');
    expect(resolveRouteByPathname('/not-registered').label).toBe('页面未找到');
  });
});
