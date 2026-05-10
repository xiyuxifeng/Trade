import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';

import { AuthProvider } from '@/features/auth/auth-context';
import { WorkflowParameterForm } from './workflow-parameter-form';
import { runWorkflow } from '@/lib/api/workflows';
import type { WorkflowDefinition } from '@/types/workflows';

vi.mock('@/lib/api/workflows', () => ({
  runWorkflow: vi.fn(),
}));

const mockedRunWorkflow = vi.mocked(runWorkflow);

const highRiskWorkflow = {
  workflow_id: 'install-config',
  title: '安装与配置',
  description: '完成项目初始化、数据库迁移和基础数据导入。',
  job_type: 'init-project',
  permissions: 'operator',
  job_definition: {
    risk: 'high',
    requires_confirmation: true,
    params_schema: {
      description: '安装参数',
      fields: {
        config_path: {
          type: 'path',
          description: '配置文件路径',
          required: true,
          enum: [],
        },
      },
      allow_additional_fields: false,
    },
  },
  steps: [],
} as unknown as WorkflowDefinition;

function renderForm() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider
        initialPrincipal={{
          role: 'operator',
          api_key_label: 'Local Operator',
          authenticated: true,
          source: 'api_key',
        }}
      >
        <WorkflowParameterForm workflow={highRiskWorkflow} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('WorkflowParameterForm', () => {
  it('includes the confirmation flag when submitting a high-risk workflow', async () => {
    const user = userEvent.setup();
    mockedRunWorkflow.mockResolvedValue({
      workflow: highRiskWorkflow,
      job: { id: 'job-1', job_type: 'init-project' },
    } as Awaited<ReturnType<typeof runWorkflow>>);

    renderForm();

    await user.click(screen.getByRole('button', { name: '继续并确认' }));
    expect(await screen.findByText('确认高风险操作')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '确认提交' }));

    await waitFor(() => {
      expect(mockedRunWorkflow).toHaveBeenCalledWith(
        'install-config',
        expect.objectContaining({
          created_by: 'web',
          confirmed: true,
          params: {
            config_path: 'config/app.yaml',
          },
        }),
      );
    });
  });

  it('disables submission when the principal lacks operator access', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
        mutations: {
          retry: false,
        },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider
          initialPrincipal={{
            role: 'viewer',
            api_key_label: 'Local Viewer',
            authenticated: true,
            source: 'api_key',
          }}
        >
          <WorkflowParameterForm workflow={highRiskWorkflow} />
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole('button', { name: '继续并确认' })).toBeDisabled();
    expect(screen.getByText(/仅可查看参数/)).toBeInTheDocument();
  });
});
