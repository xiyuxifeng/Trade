import dayjs from 'dayjs';
import type { WorkflowDefinition, WorkflowParamField, WorkflowStep } from '@/types/workflows';

const DEFAULT_CONFIG_PATH = 'config/app.yaml';
const DEFAULT_BASE_DIR = 'trade-strategy-ai';
const DEFAULT_BACKUP_DIR = 'data/backups';
const DEFAULT_DEMO_SYMBOL = '000001.SZ';
const DEFAULT_TRADER_ID = 'trader_a';
const DEFAULT_RULE_ID = 'RULE-001';

function isDateFieldName(name: string) {
  return (
    name.includes('date') ||
    name.includes('as_of') ||
    name.includes('strategy_date') ||
    name.includes('trade_date')
  );
}

function isPathFieldName(name: string) {
  return (
    name.includes('path') ||
    name.includes('dir') ||
    name.includes('dest') ||
    name.includes('output') ||
    name.includes('backup')
  );
}

function getFieldPlaceholder(name: string, field: WorkflowParamField): unknown {
  if (field.default !== undefined && field.default !== null) {
    return field.default;
  }

  if (field.type === 'boolean') {
    return false;
  }

  if (field.type === 'integer' || field.type === 'number') {
    return name.includes('limit') || name.includes('max') ? 10 : 1;
  }

  if (field.type === 'array') {
    return name === 'symbols' ? [DEFAULT_DEMO_SYMBOL] : [];
  }

  if (field.type === 'object') {
    return {};
  }

  if (field.type === 'date') {
    if (name === 'date_from' || name === 'start_date') {
      return dayjs().subtract(30, 'day').format('YYYY-MM-DD');
    }
    return dayjs().format('YYYY-MM-DD');
  }

  if (field.type === 'path') {
    if (name === 'config_path') return DEFAULT_CONFIG_PATH;
    if (name === 'base_dir') return DEFAULT_BASE_DIR;
    if (name === 'backup_dir') return DEFAULT_BACKUP_DIR;
    if (name === 'adjustments_path') return 'data/processed/optimize/advise.json';
    if (name === 'parent_path') return 'data/processed/optimize/parent.json';
    if (name === 'clusters_dest') return 'data/processed/persona/clusters.real.json';
    if (name === 'csv_path') return 'data/raw/trade_logs.csv';
    if (name === 'output') return 'data/processed/output.json';
    return `${name}.json`;
  }

  if (field.type === 'string') {
    if (name === 'config_path') return DEFAULT_CONFIG_PATH;
    if (name === 'trader_id' || name === 'trader') return DEFAULT_TRADER_ID;
    if (name === 'rule_id') return DEFAULT_RULE_ID;
    if (name === 'step') return 'crawl';
    if (name === 'version') return 'v1';
    if (name === 'mode') return field.default ?? 'full';
    if (name === 'snapshot_type') return field.default ?? 'all';
    if (name === 'slot') return field.default ?? '17-30';
    if (name === 'from_step') return 'crawl';
    if (name === 'new_version') return 'stage5-preview';
    if (name === 'job_type') return field.default ?? 'workflow';
    if (isDateFieldName(name)) return dayjs().format('YYYY-MM-DD');
    if (isPathFieldName(name)) return `${name}.json`;
    return `${name}-demo`;
  }

  return field.default ?? '';
}

export function buildWorkflowPreviewParams(workflow: WorkflowDefinition): Record<string, unknown> {
  const schema = workflow.job_definition?.params_schema as
    | { fields?: Record<string, WorkflowParamField> }
    | undefined;
  const fields = schema?.fields ?? {};
  const params: Record<string, unknown> = {};

  for (const [name, field] of Object.entries(fields)) {
    if (!field.required && field.default === undefined) {
      continue;
    }
    params[name] = getFieldPlaceholder(name, field);
  }

  return params;
}

export function getWorkflowPrimaryStep(workflow: WorkflowDefinition): WorkflowStep | null {
  return workflow.steps[0] ?? null;
}
