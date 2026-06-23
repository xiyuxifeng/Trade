import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { SystemDataPage, SystemPage, SystemRunsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
}));

vi.mock('@/lib/api/system', () => ({
  cancelSystemDataOperation: vi.fn(),
  createSystemDataOperation: vi.fn(),
  getSystemCostControlSummary: vi.fn(),
  getSystemDashboard: vi.fn(),
  getSystemDataReadiness: vi.fn(),
  getSystemDataSchedule: vi.fn(),
  getSystemRolloutSummary: vi.fn(),
  listSystemRunTraces: vi.fn(),
  listSystemDataOperations: vi.fn(),
  resumeSystemDataOperation: vi.fn(),
  retrySystemDataOperation: vi.fn(),
}));

import { getSystemCostControlSummary, getSystemDataReadiness, getSystemDataSchedule, getSystemRolloutSummary, listSystemDataOperations, listSystemRunTraces } from '@/lib/api/system';

const mockedGetSystemCostControlSummary = vi.mocked(getSystemCostControlSummary);
const mockedGetSystemDataReadiness = vi.mocked(getSystemDataReadiness);
const mockedGetSystemDataSchedule = vi.mocked(getSystemDataSchedule);
const mockedGetSystemRolloutSummary = vi.mocked(getSystemRolloutSummary);
const mockedListSystemDataOperations = vi.mocked(listSystemDataOperations);
const mockedListSystemRunTraces = vi.mocked(listSystemRunTraces);

beforeEach(() => {
  mockedGetSystemCostControlSummary.mockReset();
  mockedGetSystemDataReadiness.mockReset();
  mockedGetSystemDataSchedule.mockReset();
  mockedGetSystemRolloutSummary.mockReset();
  mockedListSystemDataOperations.mockReset();
  mockedListSystemRunTraces.mockReset();
});

describe('SystemPage', () => {
  it('renders the grouped system management hub for admin principals', async () => {
    renderWithRouter([{ path: '/system', element: <SystemPage /> }], ['/system'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '系统管理' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '七类系统管理入口' })).toBeInTheDocument();
    for (const group of [
      'Profile 配置',
      '数据源',
      '数据与调度',
      '任务运行',
      '失败与告警',
      '数据库与备份',
      '权限与审计',
    ]) {
      expect(screen.getAllByRole('heading', { name: group }).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole('button', { name: '打开 数据库与备份' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '打开 权限与审计' })).toBeInTheDocument();
  });

  it('shows only status and repair entry points for viewer principals', async () => {
    const { container } = renderWithRouter([{ path: '/system', element: <SystemPage /> }], ['/system'], {
      initialPrincipal: {
        role: 'viewer',
        api_key_label: 'Local Viewer',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '系统管理' })).toBeInTheDocument();
    for (const entry of ['系统状态', '配置管理', '数据与调度', '运行与告警']) {
      expect(screen.getByRole('button', { name: `进入 ${entry}` })).toBeInTheDocument();
    }
    expect(screen.queryByRole('heading', { name: '七类系统管理入口' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '数据库与备份' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '权限与审计' })).not.toBeInTheDocument();
    for (const term of [
      'Jo' + 'b',
      'Work' + 'flow',
      'Pipe' + 'line',
      'Arti' + 'fact',
      'Pro' + 'vider',
      'config_' + 'path',
      'prompt_' + 'run_' + 'id',
      'run_' + 'id',
    ]) {
      expect(container.textContent).not.toContain(term);
    }
  });

  it('shows the full hub but keeps admin-only actions unavailable for operator principals', async () => {
    renderWithRouter([{ path: '/system', element: <SystemPage /> }], ['/system'], {
      initialPrincipal: {
        role: 'operator',
        api_key_label: 'Local Operator',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '系统管理' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '七类系统管理入口' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '数据库与备份' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '权限与审计' })).toBeInTheDocument();
    expect(screen.getAllByText('仅管理员可以进入此分类。')).toHaveLength(2);
    expect(screen.queryByRole('button', { name: '打开 数据库与备份' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '打开 权限与审计' })).not.toBeInTheDocument();
  });

  it('uses Chinese business wording on the data scheduling page shell', async () => {
    const { container } = renderWithRouter(
      [{ path: '/system/data', element: <SystemDataPage availability="error" /> }],
      ['/system/data'],
      {
        initialPrincipal: {
          role: 'viewer',
          api_key_label: 'Viewer',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByRole('heading', { name: '数据与调度' })).toBeInTheDocument();
    expect(container.textContent).not.toContain('readiness');
  });

  it('shows /market/datasets under the system data compatibility mapping', async () => {
    mockedGetSystemDataReadiness.mockResolvedValue({
      status: 'ready',
      target_trade_date: '2026-06-22',
      phase: 'post_close',
      latest_successful_update_at: '2026-06-22T10:00:00Z',
      summary: '正式数据已就绪。',
      repair_available: false,
      facts: {
        latest_ohlcv_trade_date: '2026-06-22',
        latest_indicator_trade_date: '2026-06-22',
        dataset_snapshot_status: 'ready',
        pre_market_snapshot_status: 'ready',
        post_close_snapshot_status: 'ready',
        market_state_status: 'ready',
        unavailable_reasons: [],
        missing_coverages: [],
      },
      repair_plan: {
        steps: [],
      },
    } as never);
    mockedGetSystemDataSchedule.mockResolvedValue({
      timezone: 'Asia/Shanghai',
      entries: [],
    } as never);
    mockedListSystemDataOperations.mockResolvedValue({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    } as never);

    renderWithRouter(
      [{ path: '/system/data', element: <SystemDataPage /> }],
      ['/system/data'],
      {
        initialPrincipal: {
          role: 'viewer',
          api_key_label: 'Viewer',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByText('数据源兼容入口')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '回测数据版本详情' })).toHaveAttribute('href', '/market/datasets');
  });

  it.each([
    ['invalid', '状态无效', '正式数据存在无效状态，不能继续依赖。', '先修复无效状态，再重新进入当前页面。'],
    ['conflict', '数据冲突', '正式数据之间存在冲突，需要先修复再继续。', '先确认冲突来源并完成修复，再继续后续操作。'],
    ['insufficient_coverage', '覆盖不足', '覆盖范围不足，不能把结果当成正式就绪。', '先查看受限原因，再补齐缺失依赖或联系管理员处理。'],
    ['failed', '执行失败', '最近一次正式操作失败，需要人工处理。', '查看失败原因后重新处理。'],
  ] as const)('maps readiness status %s to truthful product-page error copy', async (status, title, impact, repair) => {
    mockedGetSystemDataReadiness.mockResolvedValue({
      status,
      target_trade_date: '2026-06-22',
      phase: 'post_close',
      latest_successful_update_at: '2026-06-22T10:00:00Z',
      summary: '测试摘要。',
      repair_available: false,
      facts: {
        latest_ohlcv_trade_date: '2026-06-22',
        latest_indicator_trade_date: '2026-06-22',
        dataset_snapshot_status: 'ready',
        pre_market_snapshot_status: 'ready',
        post_close_snapshot_status: 'ready',
        market_state_status: 'ready',
        unavailable_reasons: [],
        missing_coverages: [],
      },
      repair_plan: {
        steps: [],
      },
    } as never);
    mockedGetSystemDataSchedule.mockResolvedValue({
      timezone: 'Asia/Shanghai',
      entries: [],
    } as never);
    mockedListSystemDataOperations.mockResolvedValue({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    } as never);

    renderWithRouter(
      [{ path: '/system/data', element: <SystemDataPage /> }],
      ['/system/data'],
      {
        initialPrincipal: {
          role: 'viewer',
          api_key_label: 'Viewer',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findAllByText(title)).not.toHaveLength(0);
    expect(screen.getByText('发生了什么')).toBeInTheDocument();
    expect(screen.getAllByText('测试摘要。').length).toBeGreaterThan(0);
    expect(screen.getByText(impact)).toBeInTheDocument();
    expect(screen.getByText(repair)).toBeInTheDocument();
  });

  it('renders formal run traces on /system/runs for viewers without exposing diagnostics', async () => {
    mockedListSystemRunTraces.mockResolvedValue({
      count: 1,
      items: [
        {
          run_id: 'daily-plan:2026-06-22',
          business_label: '生成今日交易计划',
          status: 'partial',
          started_at: '2026-06-22T08:55:00Z',
          finished_at: '2026-06-22T08:58:00Z',
          duration_seconds: 180,
          happened: '今日交易计划已生成，但仍有部分输入处于降级状态。',
          affected: '普通用户可以查看今日计划，但需要关注降级输入对执行范围的影响。',
          repair_guidance: '先补齐缺失的盘前输入，或在降级范围内继续查看本次结果。',
          next_action: { label: '查看今日计划', target_path: '/daily/pre-market' },
          attempt: { attempt_id: 'attempt-1', retry_count: 0, state: 'ready' },
          steps: [],
          prompt_calls: [],
          data_fetches: [
            {
              source: 'dataset_snapshot',
              provider: 'wind',
              date_range: { date_from: '2026-06-01', date_to: '2026-06-22' },
              trade_date: '2026-06-22',
              slot: 'pre_market',
              coverage: { symbols: 120 },
              captured_at: '2026-06-22T08:30:00Z',
              available_at: '2026-06-22T08:35:00Z',
              effective_at: '2026-06-22T08:35:00Z',
              quality_status: 'ready',
              missing_ranges: [],
              repair_guidance: '如缺失，请补齐今日盘前数据。',
            },
          ],
          backtests: [
            {
              dataset_snapshot_id: 'dataset-1',
              data_fingerprints: { dataset: 'dataset-fp', market_snapshots: ['market-fp'] },
              rule_version: {
                rule_version_id: 'rule-version-1',
                rule_version_no: 3,
                rule_version_fingerprint: 'rule-fp',
              },
              market_state_model_version: 'market-state-v2',
              code_version: 'engine-v5',
              decision_time_policy: 't+0-close',
              reproducibility_fingerprint: 'repro-fp',
              coverage: { coverage_state: 'ready' },
              limitations: ['coverage-limited'],
            },
          ],
          linked_records: [],
          admin_diagnostics: null,
        },
      ],
    } as never);

    const { container } = renderWithRouter(
      [{ path: '/system/runs', element: <SystemRunsPage /> }],
      ['/system/runs'],
      {
        initialPrincipal: {
          role: 'viewer',
          api_key_label: 'Viewer',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByRole('heading', { name: '运行与告警' })).toBeInTheDocument();
    expect(await screen.findByText('生成今日交易计划')).toBeInTheDocument();
    expect(screen.getByText('今日交易计划已生成，但仍有部分输入处于降级状态。')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看今日计划' })).toHaveAttribute('href', '/daily/pre-market');
    expect(container.textContent).not.toContain('run_id');
    expect(container.textContent).not.toContain('job_id');
    expect(container.textContent).not.toContain('workflow_run_id');
  });

  it('shows admin diagnostics on /system/runs only for admins', async () => {
    mockedGetSystemRolloutSummary.mockResolvedValue({
      generated_at: '2026-06-23T10:00:00Z',
      supported_rollout_states: [
        { state: 'legacy_new_comparison', label: '新旧链路对照', description: '对照' },
        { state: 'new_read_only', label: '新链路只读展示', description: '只读' },
        { state: 'limited_enablement', label: '小范围启用', description: '受控' },
        { state: 'new_default', label: '新链路成为默认', description: '默认' },
        { state: 'legacy_read_only', label: '旧入口只读', description: '旧入口只读' },
        { state: 'retired', label: '最终退役', description: '退役' },
      ],
      items: [
        {
          migration_id: 'stage2_canonical_database',
          label: '正式数据库迁移',
          domain: 'database',
          current_state: 'new_default',
          state_label: '新链路成为默认',
          formal_source: 'Stage 2 canonical 数据库结构',
          legacy_mode: 'compatibility_only',
          duplicate_formal_source_detected: false,
          happened: '正式数据库已切到 canonical 结构。',
          affected: '可核对迁移前后计数。',
          repair_guidance: '补齐 migration report。',
          comparison: {
            status: 'ready',
            pre_counts: { raw_articles: 2 },
            post_counts: { raw_articles: 2 },
            rejected_rows: 0,
            conflicted_rows: 1,
          },
          rollback_or_recovery: {
            status: 'ready',
            mode: 'recovery',
            no_silent_data_loss: true,
          },
        },
        {
          migration_id: 'stage3_prompt_contracts',
          label: 'Prompt 合同迁移',
          domain: 'prompt',
          current_state: 'new_default',
          state_label: '新链路成为默认',
          formal_source: 'PromptRun + v1 Prompt 注册表',
          legacy_mode: 'compatibility_only',
          duplicate_formal_source_detected: false,
          happened: '新 Prompt 合同已经是正式默认写入路径。',
          affected: '可核对当前与上一版 Prompt 合同。',
          repair_guidance: '回滚前先选择上一版 prompt/schema 合同。',
          comparison: {
            status: 'ready',
            current_contract: {
              prompt_name: 'article_analysis_v1',
              prompt_version: 'article_analysis_v2',
              schema_version: 'article_analysis_schema_v2',
            },
          },
          rollback_or_recovery: {
            status: 'ready',
            mode: 'rollback',
            selected_previous_contract: {
              prompt_name: 'article_analysis_v1',
              prompt_version: 'article_analysis_v1',
              schema_version: 'article_analysis_schema_v1',
            },
          },
        },
        {
          migration_id: 'stage3_batch_processing',
          label: '批量文章处理恢复',
          domain: 'batch',
          current_state: 'limited_enablement',
          state_label: '小范围启用',
          formal_source: 'Stage 3 批处理 Job + PromptRun 证据',
          legacy_mode: 'compatibility_only',
          duplicate_formal_source_detected: false,
          happened: '批量文章处理仍按固定样本门禁和受控并发执行。',
          affected: '恢复时必须保留幂等键和继续点。',
          repair_guidance: '使用最近安全检查点继续执行。',
          comparison: {
            status: 'ready',
            processed_count: 1,
          },
          rollback_or_recovery: {
            status: 'ready',
            mode: 'recovery',
            idempotency_key: 'stage3-article-batch:test',
            resume_point: 'revision-1',
          },
        },
        {
          migration_id: 'legacy_routes',
          label: '旧入口兼容与只读',
          domain: 'routes',
          current_state: 'legacy_read_only',
          state_label: '旧入口只读',
          formal_source: '/system 及正式业务页',
          legacy_mode: 'compatibility_only',
          duplicate_formal_source_detected: false,
          happened: '旧路由继续保留兼容深链。',
          affected: 'Stage 11 不会删除旧入口。',
          repair_guidance: '最终退役必须等 Stage 12。',
          comparison: {
            status: 'ready',
            legacy_routes_retired: false,
          },
          rollback_or_recovery: {
            status: 'ready',
            mode: 'compatibility',
            stage12_required_for_retirement: true,
          },
        },
      ],
    } as never);
    mockedGetSystemCostControlSummary.mockResolvedValue({
      generated_at: '2026-06-23T09:00:00Z',
      llm_cost_summary: {
        currency: 'USD',
        total_cost: 12.48,
        prompt_run_count: 3,
        total_tokens: 1200,
      },
      budget_warning: {
        status: 'warning',
        message: '最近 7 天的 LLM 成本已接近预算上限。',
        enforcement: 'notify_only',
        affected_flows: ['文章结构化', '作者方法画像'],
      },
      concurrency_limits: [
        { task_type: 'stage3_article_batch', label: '文章批处理', limit: 2 },
      ],
      retry_caps: [
        { task_type: 'stage3_article_batch', label: '文章批处理', max_retries: 1 },
      ],
      prompt_cache_samples: [
        {
          prompt_name: 'article_analysis_v1',
          prompt_version: 'article_analysis_v1',
          schema_version: 'article_analysis_v1',
          model: 'gpt-5.4',
          input_hash: 'hash-1',
          retry_count: 0,
          cache_status: 'stale',
          invalidation_reasons: ['schema_version_changed'],
          content_hash_status: 'ready',
          article_revision_id: 'revision-2',
          content_hash: 'content-hash-1',
        },
      ],
      backtest_reuse_samples: [
        {
          run_id: 'backtest-run-1',
          reuse_status: 'reused',
          invalidation_reasons: [],
          metric_cache_status: 'ready',
          calculation_version: 'stage6-market-state-metric-v1',
        },
      ],
      incremental_profile_samples: [
        {
          profile_kind: 'method',
          author_id: 'author-1',
          update_scope: 'changed_article_revision_group',
          status: 'draft_only',
          invalidation_reasons: [],
        },
      ],
    } as never);
    mockedListSystemRunTraces.mockResolvedValue({
      count: 1,
      items: [
        {
          run_id: 'daily-plan:2026-06-22',
          business_label: '生成今日交易计划',
          status: 'partial',
          started_at: '2026-06-22T08:55:00Z',
          finished_at: '2026-06-22T08:58:00Z',
          duration_seconds: 180,
          happened: '今日交易计划已生成，但仍有部分输入处于降级状态。',
          affected: '普通用户可以查看今日计划，但需要关注降级输入对执行范围的影响。',
          repair_guidance: '先补齐缺失的盘前输入，或在降级范围内继续查看本次结果。',
          next_action: { label: '查看今日计划', target_path: '/daily/pre-market' },
          attempt: { attempt_id: 'attempt-1', retry_count: 0, state: 'ready' },
          steps: [],
          prompt_calls: [
            {
              run_id: 'prompt-run-1',
              provider: 'openai',
              model: 'gpt-5.4',
              prompt_version: 'article_analysis_v1',
              schema_version: 'article_analysis_schema_v1',
              input_hash: 'hash-1',
              validation_state: 'valid',
              retry_count: 0,
              tokens: { total_tokens: 200 },
              cost: { amount: 0.42, currency: 'USD' },
              started_at: '2026-06-22T08:40:00Z',
              completed_at: '2026-06-22T08:41:00Z',
              linked_business_object: {
                object_type: 'article_revision',
                object_id: 'article-1',
                version_id: 'revision-2',
              },
            },
          ],
          data_fetches: [
            {
              source: 'dataset_snapshot',
              provider: 'wind',
              date_range: { date_from: '2026-06-01', date_to: '2026-06-22' },
              trade_date: '2026-06-22',
              slot: 'pre_market',
              coverage: { symbols: 120 },
              captured_at: '2026-06-22T08:30:00Z',
              available_at: '2026-06-22T08:35:00Z',
              effective_at: '2026-06-22T08:35:00Z',
              quality_status: 'ready',
              missing_ranges: [],
              repair_guidance: '如缺失，请补齐今日盘前数据。',
            },
          ],
          backtests: [
            {
              dataset_snapshot_id: 'dataset-1',
              data_fingerprints: { dataset: 'dataset-fp', market_snapshots: ['market-fp'] },
              rule_version: {
                rule_version_id: 'rule-version-1',
                rule_version_no: 3,
                rule_version_fingerprint: 'rule-fp',
              },
              market_state_model_version: 'market-state-v2',
              code_version: 'engine-v5',
              decision_time_policy: 't+0-close',
              reproducibility_fingerprint: 'repro-fp',
              coverage: { coverage_state: 'ready' },
              limitations: ['coverage-limited'],
            },
          ],
          linked_records: [],
          admin_diagnostics: {
            technical_status: 'partial',
            linked_ids: { job_ids: ['job-1'], workflow_run_ids: ['workflow-1'] },
            payload_fingerprints: { idempotency_key: 'system-data-operation:abc' },
            raw_metadata: { retry_policy: { max_retries: 3, backoff_seconds: 300 } },
          },
        },
      ],
    } as never);

    renderWithRouter(
      [{ path: '/system/runs', element: <SystemRunsPage /> }],
      ['/system/runs'],
      {
        initialPrincipal: {
          role: 'admin',
          api_key_label: 'Admin',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByText('查看运维诊断详情')).toBeInTheDocument();
    expect(screen.getByText('灰度迁移与回滚')).toBeInTheDocument();
    expect(screen.getByText('正式数据库迁移')).toBeInTheDocument();
    expect(screen.getByText('静默数据丢失：未发现')).toBeInTheDocument();
    expect(screen.getByText('上一版 Prompt 合同：article_analysis_v1 / article_analysis_schema_v1')).toBeInTheDocument();
    expect(screen.getByText('幂等键：stage3-article-batch:test')).toBeInTheDocument();
    expect(screen.getByText('旧入口退役需 Stage 12 或单独授权。')).toBeInTheDocument();
    expect(screen.getByText('成本与增量控制')).toBeInTheDocument();
    expect(screen.getByText('最近 7 天的 LLM 成本已接近预算上限。')).toBeInTheDocument();
    expect(screen.getByText('通知提示，不会自动阻断已接受流程。')).toBeInTheDocument();
    expect(screen.getByText('文章批处理：2')).toBeInTheDocument();
    expect(screen.getByText('文章批处理：最多重试 1 次')).toBeInTheDocument();
    expect(screen.getByText('article_analysis_v1 · stale')).toBeInTheDocument();
    expect(screen.getByText('schema_version_changed')).toBeInTheDocument();
    expect(screen.getByText('运行编号：backtest-run-1 · reused')).toBeInTheDocument();
    expect(screen.getByText('changed_article_revision_group')).toBeInTheDocument();
    expect(screen.getByText('job-1')).toBeInTheDocument();
    expect(screen.getByText('workflow-1')).toBeInTheDocument();
    expect(screen.getByText('Prompt 调用')).toBeInTheDocument();
    expect(screen.getByText('openai / gpt-5.4')).toBeInTheDocument();
    expect(screen.getByText('数据抓取')).toBeInTheDocument();
    expect(screen.getByText('来源提供方：wind')).toBeInTheDocument();
    expect(screen.getByText('交易日期：2026-06-22')).toBeInTheDocument();
    expect(screen.getByText('时段：pre_market')).toBeInTheDocument();
    expect(screen.getByText('采集时间：2026-06-22 08:30:00 UTC')).toBeInTheDocument();
    expect(screen.getByText('可用时间：2026-06-22 08:35:00 UTC')).toBeInTheDocument();
    expect(screen.getByText('生效时间：2026-06-22 08:35:00 UTC')).toBeInTheDocument();
    expect(screen.getByText('正式回测证据')).toBeInTheDocument();
    expect(screen.getByText('代码版本：engine-v5')).toBeInTheDocument();
    expect(screen.getByText('idempotency_key：')).toBeInTheDocument();
    expect(screen.getByText(/max_retries/)).toBeInTheDocument();
  });

  it('shows operator automation diagnostics on recent system data operations', async () => {
    mockedGetSystemDataReadiness.mockResolvedValue({
      status: 'partial',
      target_trade_date: '2026-06-22',
      phase: 'post_close',
      latest_successful_update_at: '2026-06-22T10:00:00Z',
      summary: '正式数据仍需继续处理。',
      repair_available: false,
      facts: {
        latest_ohlcv_trade_date: '2026-06-22',
        latest_indicator_trade_date: '2026-06-22',
        dataset_snapshot_status: 'ready',
        pre_market_snapshot_status: 'ready',
        post_close_snapshot_status: 'partial',
        market_state_status: 'partial',
        unavailable_reasons: [],
        missing_coverages: [],
      },
      repair_plan: { steps: [] },
    } as never);
    mockedGetSystemDataSchedule.mockResolvedValue({
      timezone: 'Asia/Shanghai',
      entries: [],
    } as never);
    mockedListSystemDataOperations.mockResolvedValue({
      items: [
        {
          operation_id: 'op-1',
          label: '补齐缺失数据',
          action: 'repair',
          status: 'failed',
          target_trade_date: '2026-06-22',
          created_at: '2026-06-22T09:00:00Z',
          updated_at: '2026-06-22T09:10:00Z',
          cancel_requested: false,
          action_level: 'notify_only',
          impact: '用于补齐缺失数据，不会直接发布业务决策。',
          repair_guidance: '请先查看失败证据、幂等键和最近尝试记录，再决定重试或继续执行。',
          admin_details: {
            run_id: 'system-data-operation:op-1',
            idempotency_key: 'system-data-operation:abc',
            operation_fingerprint: 'system-data-operation:abc',
            retry_policy: {
              retry_count: 1,
              max_retries: 2,
              backoff_seconds: 300,
              retry_after_max_requires_admin: true,
            },
            attempt_history: [{ status: 'failed' }],
            failure_evidence: { error: { message: 'provider timeout' } },
            last_safe_checkpoint: null,
          },
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    } as never);

    renderWithRouter(
      [{ path: '/system/data', element: <SystemDataPage /> }],
      ['/system/data'],
      {
        initialPrincipal: {
          role: 'operator',
          api_key_label: 'Operator',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByText('管理员诊断')).toBeInTheDocument();
    expect(screen.getByText('幂等键：system-data-operation:abc')).toBeInTheDocument();
    expect(screen.getByText('重试策略：1 / 2，退避 300 秒')).toBeInTheDocument();
    expect(screen.getByText(/provider timeout/)).toBeInTheDocument();
  });
});
