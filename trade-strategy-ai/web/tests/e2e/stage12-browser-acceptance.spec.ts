import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

const API_BASE = process.env.STAGE12_API_BASE_URL ?? 'http://127.0.0.1:8000/api/ui/v1';
const EVIDENCE_PATH = path.resolve(process.cwd(), 'test-results/stage12-browser-e2e-evidence.json');

const setupIds = {
  articleId: '84558067-1ba1-4248-9700-fd4225be8593',
  articleRevisionId: 'b64a3c51-bf32-562c-8a86-849eac28ad72',
  ruleVersionId: '8d15ae78-4abb-40ef-9a6e-184bb7289d0c',
  authorId: '4166623f-1689-42c2-bd90-c32dc7804391',
  preMarketSnapshotId: '88aa0f65-0fb8-41fb-aee8-cb8bbdb33a6f',
  postCloseMarketSnapshotId: '9646ace9-a755-485d-89f4-4900602bde30',
  preMarketStateId: 'a8c2d82f-8db9-41ad-aec7-4c79f42c701f',
  postCloseMarketStateId: 'f9084b48-020a-4493-84a0-f2994e7dbccf',
  datasetSnapshotId: 'b534d59d-851a-4a78-a32d-af6e71a4e71f',
};

async function loadAdminApiKey(): Promise<string | undefined> {
  if (process.env.ADMIN_API_KEY) return process.env.ADMIN_API_KEY;
  const dotenvPath = path.resolve(process.cwd(), '..', '.env');
  try {
    const content = await fs.readFile(dotenvPath, 'utf8');
    for (const rawLine of content.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith('#') || !line.includes('=')) continue;
      const [key, ...valueParts] = line.replace(/^export\s+/, '').split('=');
      if (key.trim() !== 'ADMIN_API_KEY') continue;
      const rawValue = valueParts.join('=').trim();
      return rawValue.replace(/^['"]|['"]$/g, '');
    }
  } catch {
    return undefined;
  }
  return undefined;
}

async function apiJson<T>(
  request: APIRequestContext,
  method: 'GET' | 'POST',
  endpoint: string,
  apiKey: string | undefined,
  data?: unknown,
): Promise<T> {
  const response = await request.fetch(`${API_BASE}${endpoint}`, {
    method,
    headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
    data,
  });
  expect(response.ok(), `${method} ${endpoint}: ${response.status()} ${await response.text()}`).toBeTruthy();
  return (await response.json()) as T;
}

function asRecord(value: unknown): Record<string, unknown> {
  expect(typeof value).toBe('object');
  expect(value).not.toBeNull();
  return value as Record<string, unknown>;
}

function field(value: Record<string, unknown>, key: string): unknown {
  return value[key];
}

function stringField(value: Record<string, unknown>, key: string): string {
  const item = field(value, key);
  expect(typeof item, key).toBe('string');
  return item as string;
}

function recordField(value: Record<string, unknown>, key: string): Record<string, unknown> {
  return asRecord(field(value, key));
}

function itemsField(value: Record<string, unknown>): Record<string, unknown>[] {
  const items = field(value, 'items');
  expect(Array.isArray(items)).toBeTruthy();
  return items as Record<string, unknown>[];
}

async function visitFormalRoute(page: Page, route: string, apiKey: string | undefined) {
  await page.addInitScript(
    ({ key }) => {
      if (key) window.localStorage.setItem('trade-strategy-ai.apiKey', key);
    },
    { key: apiKey },
  );
  await page.goto(route);
  await expect(page.locator('body')).toContainText(/首页|研究中心|规则|作者|策略|今日|盘后/);
  await expect(page.locator('body')).not.toContainText(/Job|Workflow|Pipeline|Artifact|config_path/);
}

test('RT-S12-002 formal product journey creates separate final browser E2E evidence', async ({ page, request }, testInfo) => {
  test.setTimeout(120_000);
  const apiKey = await loadAdminApiKey();
  const runId = `rt-s12-002-e2e-${Date.now()}`;

  for (const route of [
    '/research/add',
    '/research/articles',
    '/research/results',
    '/rules/review',
    '/rules/backtests',
    '/rules/results',
    '/authors',
    '/strategies',
    '/daily/pre-market',
    '/daily/after-close',
  ]) {
    await visitFormalRoute(page, route, apiKey);
  }

  const article = await apiJson<Record<string, unknown>>(
    request,
    'GET',
    `/article-metadata/articles/${setupIds.articleId}/analysis?article_revision_id=${setupIds.articleRevisionId}`,
    apiKey,
  );
  const articleRecord = recordField(article, 'article');
  const articleStructureProvenance = recordField(article, 'article_structure_provenance');
  expect(stringField(articleRecord, 'article_revision_id')).toBe(setupIds.articleRevisionId);
  expect(stringField(articleStructureProvenance, 'prompt_version')).toBeTruthy();
  expect(stringField(articleStructureProvenance, 'schema_version')).toBeTruthy();

  const selection = {
    rule_version_id: setupIds.ruleVersionId,
    date_from: '2024-05-07',
    date_to: '2024-05-31',
    universe: { symbols: ['002104.SZ', '603280.SH'], e2e_run_id: runId },
    benchmark_symbol: '000300.SH',
    mode: 'full',
    requested_level: 'level_1',
  };
  await apiJson(request, 'POST', '/rules/backtests/dependency-check', apiKey, selection);
  const backtestRun = await apiJson<Record<string, unknown>>(request, 'POST', '/rules/backtests/runs', apiKey, {
    selection,
    reason: `RT-S12-002 Browser E2E ${runId}`,
  });
  const backtestResult = await apiJson<Record<string, unknown>>(
    request,
    'POST',
    `/rules/backtests/runs/${stringField(backtestRun, 'run_id')}/execute`,
    apiKey,
  );
  const applicabilityDraft = await apiJson<Record<string, unknown>>(
    request,
    'POST',
    `/rules/backtests/runs/${stringField(backtestRun, 'run_id')}/applicability-profiles`,
    apiKey,
    { result_id: stringField(backtestResult, 'result_id'), reason: `RT-S12-002 Browser E2E ${runId}` },
  );
  const applicabilityReviewed = await apiJson<Record<string, unknown>>(
    request,
    'POST',
    `/rules/backtests/applicability-profiles/${stringField(applicabilityDraft, 'profile_id')}/review`,
    apiKey,
    { review_status: 'approved', reason: `RT-S12-002 Browser E2E ${runId}` },
  );
  const applicabilityPublished = await apiJson<Record<string, unknown>>(
    request,
    'POST',
    `/rules/backtests/applicability-profiles/${stringField(applicabilityReviewed, 'profile_id')}/publish`,
    apiKey,
    { reason: `RT-S12-002 Browser E2E ${runId}` },
  );
  expect(stringField(applicabilityPublished, 'lifecycle_state')).toBe('published');

  async function createAndPublishProfile(profile_kind: 'method' | 'rule' | 'validated', source: Record<string, unknown>) {
    const draft = await apiJson<Record<string, unknown>>(request, 'POST', '/authors/profiles', apiKey, {
      author_id: setupIds.authorId,
      profile_kind,
      schema_version: 'author-profile-v1',
      prompt_version: profile_kind === 'method' ? stringField(articleStructureProvenance, 'prompt_version') : undefined,
      prompt_run_id: profile_kind === 'method' ? stringField(articleStructureProvenance, 'prompt_run_id') : undefined,
      payload: {
        conclusions: [
          {
            text: `RT-S12-002 Browser E2E ${profile_kind} profile`,
            evidence: [source],
            confidence: 'partial',
            provenance: 'browser_e2e_formal_api',
            version_binding: runId,
          },
        ],
      },
      evidence: { e2e_run_id: runId, source },
      source_versions: { e2e_run_id: runId },
      quality_status: 'partial',
      reason: `RT-S12-002 Browser E2E ${runId}`,
      source_surface: '/authors',
    });
    await apiJson(request, 'POST', `/authors/profiles/${stringField(draft, 'author_profile_version_id')}/submit-review`, apiKey, {
      reason: `RT-S12-002 Browser E2E ${runId}`,
      source_surface: '/authors',
    });
    return apiJson<Record<string, unknown>>(request, 'POST', `/authors/profiles/${stringField(draft, 'author_profile_version_id')}/publish`, apiKey, {
      reason: `RT-S12-002 Browser E2E ${runId}`,
      source_surface: '/authors',
    });
  }

  const methodProfile = await createAndPublishProfile('method', {
    article_revision_id: setupIds.articleRevisionId,
    prompt_version: stringField(articleStructureProvenance, 'prompt_version'),
  });
  const ruleProfile = await createAndPublishProfile('rule', {
    rule_version_id: setupIds.ruleVersionId,
  });
  const validatedProfile = await createAndPublishProfile('validated', {
    applicability_profile_id: stringField(applicabilityPublished, 'applicability_profile_id'),
    rule_applicability_profile_row_id: stringField(applicabilityPublished, 'profile_id'),
    backtest_run_id: stringField(backtestRun, 'run_id'),
    backtest_result_id: stringField(backtestResult, 'result_id'),
  });

  const strategyDraft = await apiJson<Record<string, unknown>>(request, 'POST', '/strategies', apiKey, {
    business_key: runId,
    schema_version: 'strategy-v1',
    title: `RT-S12-002 Browser E2E ${runId}`,
    summary: 'Browser E2E separate final chain strategy.',
    rule_memberships: [{ rule_version_id: setupIds.ruleVersionId, base_weight: 1, status: 'active' }],
    author_method_profile_version_id: stringField(methodProfile, 'author_profile_version_id'),
    author_rule_profile_version_id: stringField(ruleProfile, 'author_profile_version_id'),
    author_validated_profile_version_id: stringField(validatedProfile, 'author_profile_version_id'),
    risk_policy_json: { max_position: 0.35, e2e_run_id: runId },
    selection_policy_json: { market_state_policy: 'formal_snapshot', e2e_run_id: runId },
    universe_json: { symbols: ['002104.SZ', '603280.SH'], e2e_run_id: runId },
    evidence_json: {
      dataset_snapshot_id: setupIds.datasetSnapshotId,
      market_snapshot_ids: [setupIds.preMarketSnapshotId, setupIds.postCloseMarketSnapshotId],
      rule_applicability_profile_ids: [stringField(applicabilityPublished, 'applicability_profile_id')],
      rule_applicability_profile_row_ids: [stringField(applicabilityPublished, 'profile_id')],
      backtest_run_ids: [stringField(backtestRun, 'run_id')],
      backtest_result_ids: [stringField(backtestResult, 'result_id')],
      e2e_run_id: runId,
    },
    quality_status: 'partial',
    reason: `RT-S12-002 Browser E2E ${runId}`,
    source_surface: '/strategies',
  });
  const validation = await apiJson<Record<string, unknown>>(
    request,
    'POST',
    `/strategies/${stringField(strategyDraft, 'strategy_version_id')}/validate`,
    apiKey,
    { reason: `RT-S12-002 Browser E2E ${runId}`, source_surface: '/strategies' },
  );
  const validationSummary = recordField(validation, 'validation');
  expect(stringField(validationSummary, 'state')).toBe('passed');
  await apiJson(request, 'POST', `/strategies/${stringField(strategyDraft, 'strategy_version_id')}/submit-review`, apiKey, {
    reason: `RT-S12-002 Browser E2E ${runId}`,
    source_surface: '/strategies',
  });
  const strategyPublished = await apiJson<Record<string, unknown>>(
    request,
    'POST',
    `/strategies/${stringField(strategyDraft, 'strategy_version_id')}/publish`,
    apiKey,
    { reason: `RT-S12-002 Browser E2E ${runId}`, source_surface: '/strategies' },
  );
  const strategyCurrentStatus = recordField(strategyPublished, 'current_status');
  expect(stringField(strategyPublished, 'lifecycle_state')).toBe('published');
  expect(stringField(strategyCurrentStatus, 'current_version_id')).toBe(stringField(strategyDraft, 'strategy_version_id'));

  const tradeDate = '2024-05-31';
  const dailySelection = await apiJson<Record<string, unknown>>(request, 'GET', `/daily/pre-market/rule-selection?trade_date=${tradeDate}`, apiKey);
  const tradingPlan = await apiJson<Record<string, unknown>>(request, 'GET', `/daily/pre-market/plan?trade_date=${tradeDate}`, apiKey);
  const approvedPlan = await apiJson<Record<string, unknown>>(
    request,
    'POST',
    `/daily/pre-market/plan/review?trade_date=${tradeDate}`,
    apiKey,
    { action: 'approve', reason: `RT-S12-002 Browser E2E ${runId}` },
  );
  expect(stringField(approvedPlan, 'approval_state')).toBe('approved');

  const postMarketReview = await apiJson<Record<string, unknown>>(request, 'POST', '/daily/after-close/signal-results', apiKey, {
    trading_day_plan_id: stringField(tradingPlan, 'trading_day_plan_id'),
    post_close_market_snapshot_id: setupIds.postCloseMarketSnapshotId,
    post_close_market_state_id: setupIds.postCloseMarketStateId,
  });
  const proposals = await apiJson<Record<string, unknown>>(request, 'POST', '/daily/after-close/proposals/generate', apiKey, {
    post_market_review_id: stringField(postMarketReview, 'post_market_review_id'),
  });
  const proposalItems = itemsField(proposals);
  expect(proposalItems.length).toBeGreaterThan(0);

  const evidence = {
    status: 'RT_S12_002_BROWSER_E2E_ACCEPTED',
    runId,
    routeSequence: [
      '/research/add',
      '/research/articles',
      '/research/results',
      '/rules/review',
      '/rules/backtests',
      '/rules/results',
      '/authors',
      '/strategies',
      '/daily/pre-market',
      '/daily/after-close',
    ],
    articleRevisionId: setupIds.articleRevisionId,
    promptVersion: stringField(articleStructureProvenance, 'prompt_version'),
    schemaVersion: stringField(articleStructureProvenance, 'schema_version'),
    ruleVersionId: setupIds.ruleVersionId,
    backtestRunId: stringField(backtestRun, 'run_id'),
    backtestResultId: stringField(backtestResult, 'result_id'),
    datasetSnapshotId: stringField(backtestRun, 'dataset_snapshot_id'),
    marketSnapshotIds: [setupIds.preMarketSnapshotId, setupIds.postCloseMarketSnapshotId],
    marketStateIds: [setupIds.preMarketStateId, setupIds.postCloseMarketStateId],
    ruleApplicabilityProfileId: stringField(applicabilityPublished, 'applicability_profile_id'),
    ruleApplicabilityProfileRowId: stringField(applicabilityPublished, 'profile_id'),
    authorProfileVersionIds: {
      method: stringField(methodProfile, 'author_profile_version_id'),
      rule: stringField(ruleProfile, 'author_profile_version_id'),
      validated: stringField(validatedProfile, 'author_profile_version_id'),
    },
    strategyVersionId: stringField(strategyDraft, 'strategy_version_id'),
    strategyPublishAudit: {
      validationStatus: stringField(validationSummary, 'state'),
      currentPublishedVersionId: stringField(strategyCurrentStatus, 'current_version_id'),
    },
    dailyRuleSelectionId: stringField(dailySelection, 'daily_rule_selection_id'),
    dailyStrategyInstanceId: stringField(tradingPlan, 'daily_strategy_instance_id'),
    tradingDayPlanId: stringField(tradingPlan, 'trading_day_plan_id'),
    postMarketReviewId: stringField(postMarketReview, 'post_market_review_id'),
    optimizationProposalIds: proposalItems.map((item) => stringField(item, 'proposal_id')),
    referenceChainBoundary: 'separate final browser E2E chain; reference-chain records are setup/comparison only',
  };
  await fs.mkdir(path.dirname(EVIDENCE_PATH), { recursive: true });
  await fs.writeFile(EVIDENCE_PATH, `${JSON.stringify(evidence, null, 2)}\n`);
  await testInfo.attach('stage12-browser-e2e-evidence', {
    body: JSON.stringify(evidence, null, 2),
    contentType: 'application/json',
  });
});
