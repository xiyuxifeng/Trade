import { describe, expect, it } from 'vitest';
import { primaryNavigation } from './route-config';
import { mainNavigation, navigationGroups } from './navigation';

describe('navigation contract', () => {
  it('derives the seven formal entries from route config', () => {
    expect(navigationGroups).toEqual([{ title: '主要功能', items: primaryNavigation }]);
    expect(mainNavigation).toBe(primaryNavigation);
    expect(mainNavigation.map((item) => item.path)).toEqual([
      '/',
      '/research',
      '/rules',
      '/authors',
      '/strategies',
      '/daily',
      '/system',
    ]);
  });

  it('does not expose engineering entry names', () => {
    expect(JSON.stringify(mainNavigation)).not.toMatch(/Job|Workflow|Pipeline|Artifact|Provider|Schema|CLI/);
  });
});
