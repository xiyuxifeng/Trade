import { describe, expect, it } from 'vitest';

import source from './formal-backtest-workbench.tsx?raw';
import resultsSource from './formal-backtest-results.tsx?raw';

describe('/rules/backtests formal workbench copy', () => {
  it('does not expose technical implementation terms to normal users', () => {
    const forbidden = [
      'Job',
      'Workflow',
      'Pipeline',
      'Artifact',
      'Provider',
      'config_path',
      'database',
      'Schema',
      'regime',
      'Regime',
    ];

    for (const term of forbidden) {
      expect(source).not.toContain(term);
    }
  });

  it('uses required business wording for formal backtest flow', () => {
    expect(source).toContain('规则与回测');
    expect(source).toContain('选择规则');
    expect(source).toContain('数据依赖');
    expect(source).toContain('市场状态');
    expect(source).toContain('Kaipan');
    expect(source).toContain('确认降级');
    expect(source).toContain('开始回测');
    expect(source).toContain('可复现证据');
    expect(source).toContain('适用性画像草稿');
  });

  it('uses market-state business wording in formal results', () => {
    const forbidden = [
      'Job',
      'Workflow',
      'Pipeline',
      'Artifact',
      'Provider',
      'config_path',
      'database',
      'Schema',
      'regime',
      'Regime',
      '/backtest_results',
    ];

    for (const term of forbidden) {
      expect(resultsSource).not.toContain(term);
    }
    expect(resultsSource).toContain('分市场状态结果');
    expect(resultsSource).toContain('市场状态模型');
    expect(resultsSource).toContain('Kaipan 数据不可用');
    expect(resultsSource).toContain('覆盖率');
    expect(resultsSource).toContain('可复现证据');
    expect(resultsSource).toContain('规则适用性画像');
    expect(resultsSource).toContain('生成适用性画像草稿');
    expect(resultsSource).toContain('系统建议');
    expect(resultsSource).toContain('人工审核状态');
    expect(resultsSource).toContain('批准画像');
  });
});
