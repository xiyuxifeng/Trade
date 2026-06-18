import { describe, expect, it } from 'vitest';

import source from './formal-backtest-workbench.tsx?raw';

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
    expect(source).toContain('开始回测');
    expect(source).toContain('可复现证据');
    expect(source).toContain('适用性画像草稿');
  });
});
