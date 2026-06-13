import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { ProductPageAdapter } from './product-page-adapter';
import { AuthProvider } from '@/features/auth/auth-context';
import type { PrincipalRole } from '@/types/auth';

function renderAdapter(element: React.ReactElement, role: PrincipalRole = 'viewer') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider
        initialPrincipal={{
          role,
          api_key_label: null,
          authenticated: true,
          source: 'session',
          username: role,
        }}
      >
        <MemoryRouter>{element}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('ProductPageAdapter', () => {
  it('does not expose engineering details to ordinary users', () => {
    renderAdapter(
      <ProductPageAdapter
        title="盘前计划"
        queryState="ready"
        purpose="生成今日盘前计划。"
        inputDescription="需要可用的市场数据和规则。"
        processingDescription="系统会整理业务状态并输出可执行计划。"
        outputDescription="输出盘前计划和下一步操作。"
        businessAction={{ label: '开始生成计划', onClick: () => void 0 }}
        result={<p>已生成盘前计划。</p>}
        advancedAdminDetails={<p>force=true config_path=/tmp/internal.json</p>}
      />,
    );

    expect(screen.getByText('已生成盘前计划。')).toBeInTheDocument();
    expect(screen.queryByText(/force=true/)).not.toBeInTheDocument();
    expect(screen.queryByText(/config_path=/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始生成计划' })).toBeInTheDocument();
    expect(screen.queryByText('管理员查看技术细节')).not.toBeInTheDocument();
  });

  it('allows administrators to inspect explicitly marked technical details', () => {
    renderAdapter(
      <ProductPageAdapter
        title="系统状态"
        queryState="partial"
        purpose="查看系统状态。"
        inputDescription="无需输入。"
        processingDescription="读取真实状态。"
        outputDescription="输出可用性。"
        businessAction={{ label: '返回首页', to: '/' }}
        advancedAdminDetails={<p>database=/tmp/internal.db</p>}
      />,
      'admin',
    );

    expect(screen.getByText('管理员查看技术细节')).toBeInTheDocument();
    expect(screen.getByText(/database=\/tmp/)).toBeInTheDocument();
  });

  it.each([
    ['loading', '正在加载', '页面内容正在获取中，请稍后再看。', '你暂时还不能查看完整内容。', '等待加载完成后刷新页面。'],
    ['empty', '暂无内容', '当前没有可展示的业务内容。', '这部分页面暂时不会给出结果。', '补齐输入后重新查看。'],
    ['error', '出现问题', '读取页面内容时发生了错误。', '当前结果可能不完整或无法展示。', '查看失败原因后重新处理。'],
    ['partial', '部分完成', '已返回一部分内容，仍有项目未处理完。', '你看到的是当前可用的部分结果。', '补齐缺失部分后继续处理。'],
    ['permission_denied', '无权限', '当前账号没有查看这部分内容的权限。', '高风险操作不会显示。', '切换到有权限的账号，或联系管理员。'],
    ['unavailable', '当前不可用', '相关服务或数据暂时不可用。', '暂时无法继续查看完整页面。', '稍后重试，或先补齐缺失数据。'],
  ] as const)('renders truthful state copy for %s', (queryState, title, description, impact, recoveryAction) => {
    renderAdapter(
      <ProductPageAdapter
        title="盘前计划"
        queryState={queryState}
        purpose="生成今日盘前计划。"
        inputDescription="需要可用的市场数据和规则。"
        processingDescription="系统会整理业务状态并输出可执行计划。"
        outputDescription="输出盘前计划和下一步操作。"
        businessAction={{ label: '开始生成计划', onClick: () => void 0 }}
        result={<p>已生成盘前计划。</p>}
      />,
    );

    expect(screen.getAllByText(title).length).toBeGreaterThan(0);
    expect(screen.getAllByText(description).length).toBeGreaterThan(0);
    expect(screen.getByText('影响：')).toBeInTheDocument();
    expect(screen.getByText(impact)).toBeInTheDocument();
    expect(screen.getByText('处理方式：')).toBeInTheDocument();
    expect(screen.getByText(recoveryAction)).toBeInTheDocument();
  });
});
