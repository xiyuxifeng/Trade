import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { WorkflowsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listWorkflows } from '@/lib/api/workflows';

vi.mock('@/lib/api/workflows', () => ({
  listWorkflows: vi.fn(),
  runWorkflow: vi.fn(),
}));

const mockedListWorkflows = vi.mocked(listWorkflows);

describe('WorkflowsPage', () => {
  it('loads the workflow catalog and selects the default workflow', async () => {
    mockedListWorkflows.mockResolvedValue({
      count: 1,
      items: [
        {
          workflow_id: 'install-config',
          title: '安装与配置',
          description: '完成项目初始化、数据库迁移和基础数据导入。',
          job_type: 'init-project',
          permissions: 'operator',
          job_definition: {
            job_type: 'init-project',
            title: '初始化项目',
            description: '执行初始化并完成最小可运行状态。',
            summary: '初始化项目',
            permission: 'operator',
            risk: 'high',
            can_retry: false,
            can_run_concurrently: false,
            concurrency_group: 'project-init',
            requires_confirmation: true,
            runnable: true,
            params_schema: {
              description: '初始化项目参数',
              allow_additional_fields: false,
              fields: {
                config_path: {
                  type: 'path',
                  description: '配置文件路径',
                  required: true,
                  enum: [],
                },
              },
            },
          },
          steps: [
            {
              step_id: 'init-project',
              title: '初始化项目',
              description: '执行初始化并完成最小可运行状态。',
              required_job_type: 'init-project',
              parameters: ['config_path'],
              param_schema: {
                description: '初始化项目参数',
                allow_additional_fields: false,
                fields: {
                  config_path: {
                    type: 'path',
                    description: '配置文件路径',
                    required: true,
                    enum: [],
                  },
                },
              },
              risk: 'high',
              requires_confirmation: true,
            },
          ],
        },
      ],
    });

    const { router } = renderWithRouter(
      [
        { path: '/workflows', element: <WorkflowsPage /> },
        { path: '/workflows/:workflowId', element: <WorkflowsPage /> },
      ],
      ['/workflows'],
    );

    expect(await screen.findByText('Workflow catalog')).toBeInTheDocument();
    expect(await screen.findByText('Workflow summary')).toBeInTheDocument();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/workflows/install-config');
    });
  });
});
