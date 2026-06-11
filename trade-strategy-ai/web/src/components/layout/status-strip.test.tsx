import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusStrip } from './status-strip';

describe('StatusStrip', () => {
  it('describes a formal page without exposing its route path', () => {
    render(
      <StatusStrip
        title="研究中心"
        description="导入文章、查看文章并处理规则提取结果。"
        path="/research"
      />,
    );

    expect(screen.getByText('正式入口')).toBeInTheDocument();
    expect(screen.queryByText('Route')).not.toBeInTheDocument();
    expect(screen.queryByText('/research')).not.toBeInTheDocument();
  });

  it('explains a compatibility page in business language', () => {
    render(
      <StatusStrip
        title="文章处理旧入口"
        description="继续使用现有文章导入和处理能力。"
        path="/articles/run"
        kind="compat"
      />,
    );

    expect(screen.getByText('历史入口')).toBeInTheDocument();
    expect(screen.getByText('该入口仅用于兼容已有链接')).toBeInTheDocument();
    expect(screen.queryByText('/articles/run')).not.toBeInTheDocument();
  });
});
