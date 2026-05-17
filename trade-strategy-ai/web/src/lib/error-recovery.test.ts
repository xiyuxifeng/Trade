import { describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from './error-recovery';

describe('buildErrorRecoveryState', () => {
  it('maps permission denied errors to a settings-focused recovery path', () => {
    const state = buildErrorRecoveryState(new ApiError(403, 'permission denied'), 'strategy');

    expect(state.category).toBe('permission denied');
    expect(state.retryable).toBe(false);
    expect(state.actions.some((action) => action.to === '/settings')).toBe(true);
    expect(state.actions.some((action) => action.to === '/dashboard')).toBe(true);
  });

  it('maps artifact missing errors to artifact and job recovery paths', () => {
    const state = buildErrorRecoveryState(new ApiError(404, 'artifact missing'), 'job-detail');

    expect(state.category).toBe('artifact missing');
    expect(state.retryable).toBe(true);
    expect(state.actions[0].label).toBe('打开产物中心');
    expect(state.actions.some((action) => action.to === '/artifacts')).toBe(true);
    expect(state.actions.some((action) => action.to === '/jobs')).toBe(true);
  });

  it('uses market snapshot browser wording for market recovery', () => {
    const state = buildErrorRecoveryState(new ApiError(503, 'provider unavailable'), 'market');

    expect(state.title).toContain('市场快照浏览器');
    expect(state.actions.some((action) => action.to === '/dashboard')).toBe(true);
    expect(state.actions.some((action) => action.to === '/settings')).toBe(true);
  });
});
