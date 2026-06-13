import { describe, expect, it } from 'vitest';

import { resolveRoute, routeConfig } from './route-config';

const journey = [
  ['/research', '/research/articles'],
  ['/research/articles', '/rules/review'],
  ['/rules/review', '/rules/backtests'],
  ['/rules/backtests', '/authors'],
  ['/authors', '/strategies'],
  ['/strategies', '/daily/pre-market'],
  ['/daily/pre-market', '/daily/after-close'],
] as const;

describe('formal product journey', () => {
  it('connects the formal business journey without technical workbenches', () => {
    const canonicalPaths = new Set(
      routeConfig.filter((route) => route.kind === 'canonical').map((route) => route.path),
    );

    for (const [from, to] of journey) {
      expect(resolveRoute(from)).toBeDefined();
      expect(canonicalPaths.has(to)).toBe(true);
      expect(to).not.toMatch(/^\/(?:jobs|workflows|artifacts)(?:\/|$)|^\/market(?:\/|$)/);
    }
  });

  it('retains legacy paths only as compatibility routes', () => {
    for (const path of ['/jobs', '/workflows', '/artifacts', '/market']) {
      expect(resolveRoute(path)?.kind).toBe('compat');
      expect(resolveRoute(path)?.visibleInNavigation).toBe(false);
    }
  });
});
