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
    expect(resolveRouteByPathname('/artifacts').path).toBe('/artifacts');
    expect(resolveRouteByPathname('/settings').path).toBe('/settings');
  });

  it('resolves legacy compatibility routes', () => {
    expect(resolveRouteByPathname('/').path).toBe('/');
    expect(resolveRouteByPathname('/overview').path).toBe('/overview');
    expect(resolveRouteByPathname('/workflows/pipeline').path).toBe('/workflows/:workflowId');
    expect(resolveRouteByPathname('/legacy/jobs').path).toBe('/legacy/*');
  });
});
