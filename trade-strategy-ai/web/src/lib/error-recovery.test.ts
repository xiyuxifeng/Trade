import { describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from './error-recovery';

describe('buildErrorRecoveryState', () => {
  it('maps permission denied errors to a profile-focused recovery path', () => {
    const state = buildErrorRecoveryState(new ApiError(403, 'permission denied'), 'strategy');

    expect(state.category).toBe('permission denied');
    expect(state.happened).toBe('当前身份无法查看或操作该内容。');
    expect(state.affected).toBe('当前账号暂时不能查看或处理这部分内容。');
    expect(state.repairGuidance).toBe('请切换到有权限的账号，或联系管理员调整权限。');
    expect(state.retryable).toBe(false);
    expect(state.actions.some((action) => action.to === '/system/configuration')).toBe(true);
    expect(state.actions.some((action) => action.to === '/')).toBe(true);
  });

  it('maps artifact missing errors to system run recovery paths', () => {
    const state = buildErrorRecoveryState(new ApiError(404, 'artifact missing'), 'job-detail');

    expect(state.category).toBe('artifact missing');
    expect(state.affected).toContain('相关结果材料暂时无法查看');
    expect(state.retryable).toBe(true);
    expect(state.actions[0].label).toBe('打开运行产出记录');
    expect(state.actions.every((action) => action.to === '/system/runs')).toBe(true);
  });

  it('routes empty market recovery back to the market page', () => {
    const state = buildErrorRecoveryState(new ApiError(404, 'no market data'), 'market');

    expect(state.category).toBe('data empty');
    expect(state.repairGuidance).toContain('返回列表重新筛选');
    expect(state.actions).toEqual([]);
  });
});
