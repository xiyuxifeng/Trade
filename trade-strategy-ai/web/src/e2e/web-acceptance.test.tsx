import { describe, expect, it } from 'vitest';

import {
  AUDITED_LEGACY_PATHS,
  primaryNavigation,
  renderRouteWithAvailability,
  resolveRoute,
  routeConfig,
} from '@/app/route-config';

const formalJourney = [
  '/research/articles',
  '/rules/review',
  '/rules/backtests',
  '/authors',
  '/strategies',
  '/daily/pre-market',
  '/daily/after-close',
] as const;

const technicalWorkbenches = ['/jobs', '/workflows', '/artifacts', '/market'] as const;

describe('Stage 1 web acceptance', () => {
  it('exposes the seven business navigation entries without technical workbenches', () => {
    expect(primaryNavigation.map((item) => item.label)).toEqual([
      '首页',
      '研究中心',
      '规则与回测',
      '作者画像',
      '策略中心',
      '每日交易',
      '系统管理',
    ]);
    expect(primaryNavigation.map((item) => item.path)).not.toEqual(
      expect.arrayContaining([...technicalWorkbenches]),
    );
  });

  it('keeps the complete business journey on registered canonical routes', () => {
    for (const path of formalJourney) {
      const route = resolveRoute(path);
      expect(route, path).toBeDefined();
      expect(route?.kind, path).toBe('canonical');
      expect(renderRouteWithAvailability(route!, 'unavailable'), path).not.toBeNull();
    }
  });

  it('keeps technical workbenches hidden as compatibility routes', () => {
    for (const path of technicalWorkbenches) {
      const route = resolveRoute(path);
      expect(route?.kind, path).toBe('compat');
      expect(route?.visibleInNavigation, path).toBe(false);
      expect(route?.legacy, path).toBeDefined();
    }
  });

  it('covers every audited legacy path from the centralized route config', () => {
    expect(AUDITED_LEGACY_PATHS).toHaveLength(49);
    for (const path of AUDITED_LEGACY_PATHS) {
      expect(resolveRoute(path === '*' ? '/not-a-real-page' : path.replace(/:[^/]+/g, 'sample')), path).toBeDefined();
    }
    expect(routeConfig.filter((route) => route.kind === 'compat').every((route) => route.legacy)).toBe(true);
  });
});
