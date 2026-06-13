import { describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from './error-recovery';

describe('buildErrorRecoveryState', () => {
  it('maps permission denied errors to a profile-focused recovery path', () => {
    const state = buildErrorRecoveryState(new ApiError(403, 'permission denied'), 'strategy');

    expect(state.category).toBe('permission denied');
    expect(state.retryable).toBe(false);
    expect(state.actions.some((action) => action.to === '/profiles')).toBe(true);
    expect(state.actions.some((action) => action.to === '/')).toBe(true);
  });

  it('maps artifact missing errors to artifact and job recovery paths', () => {
    const state = buildErrorRecoveryState(new ApiError(404, 'artifact missing'), 'job-detail');

    expect(state.category).toBe('artifact missing');
    expect(state.retryable).toBe(true);
    expect(state.actions[0].label).toBe('打开产物中心');
    expect(state.actions.some((action) => action.to === '/artifacts')).toBe(true);
    expect(state.actions.some((action) => action.to === '/jobs')).toBe(true);
  });

  it('routes empty market recovery back to the market page', () => {
    const state = buildErrorRecoveryState(new ApiError(404, 'no market data'), 'market');

    expect(state.category).toBe('data empty');
    expect(state.actions).toEqual([]);
  });
});
