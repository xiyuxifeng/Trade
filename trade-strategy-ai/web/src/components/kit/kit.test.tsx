import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  JsonViewer,
  LoadingState,
  LogViewer,
  PageHeader,
  RiskBadge,
  SchemaForm,
  SectionCard,
  StatusBadge,
} from '@/components/kit';

describe('kit', () => {
  it('exports the shared V2 workbench primitives', () => {
    render(
      <SectionCard title="章节标题" description="章节说明">
        <PageHeader kicker="正式入口" title="标题" description="说明" />
        <StatusBadge value="validated" />
        <RiskBadge value="high" />
        <LoadingState label="加载中" />
        <EmptyState title="暂无数据" description="先完成一次提交再查看。" />
        <ErrorState
          category="data empty"
          title="任务不存在"
          description="无法读取任务详情。"
          suggestion="请返回任务列表重新选择一个 Job。"
        />
        <JsonViewer value={{ ok: true }} />
        <LogViewer lines={['line-1', 'line-2']} />
        <SchemaForm title="表单" description="说明" />
        <ConfirmDialog
          open={false}
          onOpenChange={vi.fn()}
          title="确认"
          description="确认继续？"
        />
      </SectionCard>,
    );

    expect(screen.getByText('章节标题')).toBeInTheDocument();
    expect(screen.getByText('正式入口')).toBeInTheDocument();
    expect(screen.getByText('加载中')).toBeInTheDocument();
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });
});
