import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';

import { AuthProvider } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { listProfiles } from '@/lib/api/profiles';
import { WorkflowParameterForm } from './workflow-parameter-form';
import { runWorkflow } from '@/lib/api/workflows';
import type { WorkflowDefinition } from '@/types/workflows';

vi.mock('@/lib/api/workflows', () => ({
  runWorkflow: vi.fn(),
}));

vi.mock('@/lib/api/profiles', () => ({
  getProfile: vi.fn(),
  getProfileSnapshot: vi.fn(),
  importProfile: vi.fn(),
  listProfiles: vi.fn(),
}));

const mockedRunWorkflow = vi.mocked(runWorkflow);
const mockedListProfiles = vi.mocked(listProfiles);

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

const pipelineWorkflow = {
  workflow_id: 'pipeline',
  title: '数据 Pipeline',
  description: '串联抓取、清洗、抽取、聚类与回归验证。',
  job_type: 'pipeline-run',
  permissions: 'operator',
  job_definition: {
    risk: 'medium',
    requires_confirmation: false,
    params_schema: {
      description: 'Pipeline 参数',
      fields: {
        config_path: {
          type: 'path',
          description: '配置文件路径',
          required: true,
          enum: [],
        },
        max_articles: {
          type: 'integer',
          description: '最大文章数',
          required: false,
          default: 5,
          enum: [],
        },
      },
      allow_additional_fields: false,
    },
  },
  steps: [],
} as unknown as WorkflowDefinition;

const profileWorkflow = {
  workflow_id: 'profile-pipeline',
  title: 'Profile Pipeline',
  description: '使用 Profile 串联工作流。',
  job_type: 'pipeline-run',
  permissions: 'operator',
  job_definition: {
    risk: 'medium',
    requires_confirmation: false,
    params_schema: {
      description: 'Profile 参数',
      fields: {
        profile_id: {
          type: 'string',
          description: 'Profile ID',
          required: true,
          enum: [],
        },
        config_path: {
          type: 'path',
          description: '兼容路径',
          required: true,
          enum: [],
        },
        max_articles: {
          type: 'integer',
          description: '最大文章数',
          required: false,
          default: 5,
          enum: [],
        },
      },
      allow_additional_fields: false,
    },
  },
  steps: [],
} as unknown as WorkflowDefinition;

function renderForm({
  workflow = highRiskWorkflow,
  onSubmitted,
}: {
  workflow?: WorkflowDefinition;
  onSubmitted?: (jobId: string) => void;
} = {}) {
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
        <WorkflowParameterForm workflow={workflow} onSubmitted={onSubmitted} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedListProfiles.mockResolvedValue({
    count: 0,
    total: 0,
    skip: 0,
    limit: 50,
    items: [],
  });
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
            config_path: 'config/app.template.yaml',
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

  it('shows required validation errors on the matching field before submitting', async () => {
    const user = userEvent.setup();

    renderForm({ workflow: pipelineWorkflow });

    const configPath = screen.getByDisplayValue('config/app.template.yaml');
    await user.clear(configPath);
    await user.click(screen.getByRole('button', { name: '提交运行' }));

    expect(screen.getAllByText('config_path 为必填项')).toHaveLength(2);
    expect(configPath).toHaveAttribute('aria-invalid', 'true');
    expect(mockedRunWorkflow).not.toHaveBeenCalled();
  });

  it('maps structured backend validation errors to fields', async () => {
    const user = userEvent.setup();
    mockedRunWorkflow.mockRejectedValue(
      new ApiError(400, 'invalid workflow params', {
        detail: {
          code: 'validation_failed',
          message: 'validation failed',
          status: 'error',
          fields: {
            config_path: '配置文件不存在',
          },
        },
      } as never),
    );

    renderForm({ workflow: pipelineWorkflow });

    await user.click(screen.getByRole('button', { name: '提交运行' }));

    expect(await screen.findByText('配置文件不存在')).toBeInTheDocument();
    expect(screen.getByDisplayValue('config/app.template.yaml')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('invalid workflow params')).toBeInTheDocument();
  });

  it('calls the success redirect callback with the created job id', async () => {
    const user = userEvent.setup();
    const onSubmitted = vi.fn();
    mockedRunWorkflow.mockResolvedValue({
      workflow: pipelineWorkflow,
      job: { id: 'job-pipeline-1', job_type: 'pipeline-run' },
    } as Awaited<ReturnType<typeof runWorkflow>>);

    renderForm({ workflow: pipelineWorkflow, onSubmitted });

    await user.click(screen.getByRole('button', { name: '提交运行' }));

    await waitFor(() => {
      expect(onSubmitted).toHaveBeenCalledWith('job-pipeline-1');
    });
  });

  it('prefers profile selection and hides config_path when the schema includes profile_id', async () => {
    const user = userEvent.setup();
    mockedListProfiles.mockResolvedValueOnce({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [
        {
          profile_id: 'default',
          name: 'Default Profile',
          environment: 'production',
          version: 1,
          sections: {},
          secret_refs: {},
          validation_status: 'validated',
          created_by: 'web',
          created_at: '2026-05-16T08:00:00Z',
          updated_at: '2026-05-16T08:00:00Z',
          archived_at: null,
        },
      ],
    });
    mockedRunWorkflow.mockResolvedValue({
      workflow: profileWorkflow,
      job: { id: 'job-profile-1', job_type: 'pipeline-run' },
    } as Awaited<ReturnType<typeof runWorkflow>>);

    renderForm({ workflow: profileWorkflow });

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Profile' })).toHaveValue('default');
    });
    expect(screen.queryByDisplayValue('config/app.template.yaml')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '提交运行' }));

    await waitFor(() => {
      expect(mockedRunWorkflow).toHaveBeenCalledWith(
        'profile-pipeline',
        expect.objectContaining({
          created_by: 'web',
          confirmed: false,
          params: expect.objectContaining({
            profile_id: 'default',
            max_articles: 5,
          }),
        }),
      );
    });
  });
});
