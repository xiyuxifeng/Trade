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
          workflow_id: 'pipeline',
          title: '数据 Pipeline',
          description: '串联抓取、清洗、抽取、聚类与回归验证。',
          job_type: 'pipeline-run',
          permissions: 'operator',
          job_definition: {
            job_type: 'pipeline-run',
            title: '执行完整 Pipeline',
            description: '运行完整 pipeline。',
            summary: '执行完整 Pipeline',
            permission: 'operator',
            risk: 'medium',
            can_retry: true,
            can_run_concurrently: false,
            concurrency_group: 'pipeline',
            requires_confirmation: false,
            runnable: true,
            params_schema: {
              description: 'Pipeline 参数',
              allow_additional_fields: false,
              fields: {},
            },
          },
          steps: [],
        },
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

    expect(await screen.findByText('工作流目录')).toBeInTheDocument();
    expect(await screen.findByText('工作流摘要')).toBeInTheDocument();
    expect(screen.queryByText('数据 Pipeline')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/workflows');
    });
  });

  it('shows removed workflow state for old data pipeline deep links', async () => {
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
          steps: [],
        },
      ],
    });

    const { router } = renderWithRouter(
      [
        { path: '/workflows', element: <WorkflowsPage /> },
        { path: '/workflows/:workflowId', element: <WorkflowsPage /> },
        { path: '/workflows/:workflowId/run', element: <WorkflowsPage /> },
      ],
      ['/workflows/pipeline/run'],
    );

    expect(await screen.findByText('该工作流已移除或不可用，请返回工作流目录选择其他流程。')).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: '运行入口' })).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/workflows/pipeline/run');
  });
});
