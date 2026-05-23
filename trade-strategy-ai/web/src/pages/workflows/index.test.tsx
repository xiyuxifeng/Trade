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
          workflow_id: 'snapshot',
          title: '快照中心',
          description: '构建候选池快照，供盘前盘后和回测使用。',
          job_type: 'snapshot-build',
          permissions: 'operator',
          job_definition: {
            job_type: 'snapshot-build',
            title: '构建快照',
            description: '构建候选池快照。',
            summary: '构建快照',
            permission: 'operator',
            risk: 'medium',
            can_retry: true,
            can_run_concurrently: false,
            concurrency_group: 'snapshot',
            requires_confirmation: false,
            runnable: true,
            params_schema: {
              description: '快照构建参数',
              allow_additional_fields: false,
              fields: {},
            },
          },
          steps: [],
        },
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
        {
          workflow_id: 'strategy',
          title: '策略版本',
          description: '按交易员和日期构建策略版本。',
          job_type: 'strategy-build',
          permissions: 'operator',
          job_definition: {
            job_type: 'strategy-build',
            title: '构建策略版本',
            description: '生成交易员策略版本。',
            summary: '构建策略版本',
            permission: 'operator',
            risk: 'medium',
            can_retry: true,
            can_run_concurrently: false,
            concurrency_group: 'strategy-build',
            requires_confirmation: false,
            runnable: true,
            params_schema: {
              description: '策略构建参数',
              allow_additional_fields: false,
              fields: {},
            },
          },
          steps: [],
        },
        {
          workflow_id: 'optimize',
          title: '优化中心',
          description: '基于验真和回测结果生成候选版本。',
          job_type: 'optimize-create-candidate',
          permissions: 'operator',
          job_definition: {
            job_type: 'optimize-create-candidate',
            title: '生成候选版本',
            description: '从规则调整生成候选策略版本。',
            summary: '生成候选版本',
            permission: 'operator',
            risk: 'medium',
            can_retry: true,
            can_run_concurrently: false,
            concurrency_group: 'optimize',
            requires_confirmation: false,
            runnable: true,
            params_schema: {
              description: '候选版本参数',
              allow_additional_fields: false,
              fields: {},
            },
          },
          steps: [],
        },
        {
          workflow_id: 'optimize-rule-pool',
          title: '优化与规则池',
          description: '串联候选创建、规则池回测和候选 / 规则审核。',
          job_type: 'optimize-create-candidate',
          permissions: 'operator',
          job_definition: {
            job_type: 'optimize-create-candidate',
            title: '生成候选版本',
            description: '从规则调整生成候选策略版本。',
            summary: '生成候选版本',
            permission: 'operator',
            risk: 'medium',
            can_retry: true,
            can_run_concurrently: false,
            concurrency_group: 'optimize',
            requires_confirmation: false,
            runnable: true,
            params_schema: {
              description: '候选版本参数',
              allow_additional_fields: false,
              fields: {},
            },
          },
          steps: [],
        },
        {
          workflow_id: 'rule-pool',
          title: '规则池管理',
          description: '围绕规则池回测和审核流程组织操作。',
          job_type: 'rule-pool-backtest',
          permissions: 'operator',
          job_definition: {
            job_type: 'rule-pool-backtest',
            title: '规则池回测',
            description: '对规则池进行回测并回写结果。',
            summary: '规则池回测',
            permission: 'operator',
            risk: 'medium',
            can_retry: true,
            can_run_concurrently: false,
            concurrency_group: 'rule-pool-backtest',
            requires_confirmation: false,
            runnable: true,
            params_schema: {
              description: '规则池回测参数',
              allow_additional_fields: false,
              fields: {},
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
      ],
      ['/workflows'],
    );

    expect(await screen.findByText('工作流目录')).toBeInTheDocument();
    expect(await screen.findByText('工作流摘要')).toBeInTheDocument();
    expect(screen.queryByText('快照中心')).not.toBeInTheDocument();
    expect(screen.queryByText('数据 Pipeline')).not.toBeInTheDocument();
    expect(screen.queryByText('策略版本')).not.toBeInTheDocument();
    expect(screen.queryByText('优化中心')).not.toBeInTheDocument();
    expect(screen.queryByText('优化与规则池')).not.toBeInTheDocument();
    expect(screen.queryByText('规则池管理')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/workflows');
    });
  });

  it('shows removed workflow state for old strategy deep links', async () => {
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
      ['/workflows/strategy/run'],
    );

    expect(await screen.findByText('该工作流已移除或不可用，请返回工作流目录选择其他流程。')).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: '运行入口' })).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/workflows/strategy/run');
  });

  it('shows removed workflow state for old backtest deep links', async () => {
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
      ['/workflows/backtest/run'],
    );

    expect(await screen.findByText('该工作流已移除或不可用，请返回工作流目录选择其他流程。')).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: '运行入口' })).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/workflows/backtest/run');
  });
});
