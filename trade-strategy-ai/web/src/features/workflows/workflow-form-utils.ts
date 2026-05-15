import type { WorkflowDefinition, WorkflowParamField, WorkflowParamSchema } from '@/types/workflows';
import { formatLocalDateInputOffset } from '@/lib/date';

export type WorkflowFieldValue = string | boolean;
export type WorkflowFieldValues = Record<string, WorkflowFieldValue>;

function stringifyDefault(value: unknown) {
  if (typeof value === 'string') return value;
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return String(value);
  if (value == null) return '';
  return JSON.stringify(value, null, 2);
}

export function getWorkflowRunSchema(workflow: WorkflowDefinition): WorkflowParamSchema | null {
  return workflow.job_definition?.params_schema ?? workflow.steps[0]?.param_schema ?? null;
}

export function isHighRiskWorkflow(workflow: WorkflowDefinition): boolean {
  const risk = workflow.job_definition?.risk ?? workflow.steps[0]?.risk ?? 'medium';
  return workflow.job_definition?.requires_confirmation === true || risk === 'high' || risk === 'critical';
}

export function buildWorkflowDefaultValues(schema: WorkflowParamSchema | null): WorkflowFieldValues {
  const values: WorkflowFieldValues = {};
  if (!schema) return values;

  for (const [name, field] of Object.entries(schema.fields)) {
    if (field.default !== undefined) {
      values[name] = field.type === 'boolean' ? Boolean(field.default) : stringifyDefault(field.default);
      continue;
    }

    if (field.type === 'boolean') {
      values[name] = false;
      continue;
    }

    if (field.required) {
      values[name] = buildFieldPlaceholder(name, field);
    }
  }

  return values;
}

export function buildFieldPlaceholder(name: string, field: WorkflowParamField): WorkflowFieldValue {
  if (field.type === 'boolean') return false;
  if (field.type === 'integer' || field.type === 'number') return field.required ? '1' : '';
  if (field.type === 'date') return formatLocalDateInputOffset(0);
  if (field.type === 'path') {
    if (name === 'config_path') return 'config/app.yaml';
    if (name === 'base_dir') return 'trade-strategy-ai';
    if (name === 'backup_dir') return 'data/backups';
    if (name === 'adjustments_path') return 'data/processed/optimize/advise.json';
    if (name === 'parent_path') return 'data/processed/optimize/parent.json';
    if (name === 'clusters_dest') return 'data/processed/persona/clusters.real.json';
    if (name === 'csv_path') return 'data/raw/trade_logs.csv';
    return `${name}.json`;
  }
  if (field.type === 'array') return '[]';
  if (field.type === 'object') return '{}';
  return field.required ? `${name}-value` : '';
}

function parseJsonField(name: string, value: string, kind: 'array' | 'object') {
  if (!value.trim()) {
    throw new Error(`${name} 不能为空`);
  }

  const parsed = JSON.parse(value);
  if (kind === 'array') {
    if (!Array.isArray(parsed)) throw new Error(`${name} 必须是 JSON 数组`);
    return parsed;
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error(`${name} 必须是 JSON 对象`);
  }
  return parsed;
}

export function validateWorkflowValues(schema: WorkflowParamSchema | null, values: WorkflowFieldValues) {
  if (!schema) {
    return { params: {}, errors: [] as string[], fieldErrors: {} as Record<string, string> };
  }

  const params: Record<string, unknown> = {};
  const errors: string[] = [];
  const fieldErrors: Record<string, string> = {};

  for (const [name, field] of Object.entries(schema.fields)) {
    const raw = values[name];
    if (field.required && (raw === '' || raw === undefined || raw === null)) {
      const message = `${name} 为必填项`;
      errors.push(message);
      fieldErrors[name] = message;
      continue;
    }

    if (raw === undefined || raw === null || raw === '') {
      continue;
    }

    try {
      if (field.enum.length && typeof raw === 'string' && !field.enum.includes(raw)) {
        throw new Error(`${name} 必须是以下值之一: ${field.enum.join(', ')}`);
      }

      if (field.type === 'boolean') {
        params[name] = Boolean(raw);
        continue;
      }
      if (field.type === 'integer') {
        const parsed = Number.parseInt(String(raw), 10);
        if (Number.isNaN(parsed)) throw new Error(`${name} 必须是整数`);
        params[name] = parsed;
        continue;
      }
      if (field.type === 'number') {
        const parsed = Number(String(raw));
        if (Number.isNaN(parsed)) throw new Error(`${name} 必须是数字`);
        params[name] = parsed;
        continue;
      }
      if (field.type === 'date') {
        const text = String(raw);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) {
          throw new Error(`${name} 必须是 YYYY-MM-DD`);
        }
        params[name] = text;
        continue;
      }
      if (field.type === 'path' || field.type === 'string') {
        params[name] = String(raw);
        continue;
      }
      if (field.type === 'array') {
        params[name] = parseJsonField(name, String(raw), 'array');
        continue;
      }
      if (field.type === 'object') {
        params[name] = parseJsonField(name, String(raw), 'object');
        continue;
      }

      params[name] = raw;
    } catch (error) {
      const message = error instanceof Error ? error.message : `${name} 格式无效`;
      errors.push(message);
      fieldErrors[name] = message;
    }
  }

  return { params, errors, fieldErrors };
}

export function summarizeWorkflowRisk(workflow: WorkflowDefinition) {
  const risk = workflow.job_definition?.risk ?? workflow.steps[0]?.risk ?? 'medium';
  const requiresConfirmation = isHighRiskWorkflow(workflow);
  return {
    risk,
    requiresConfirmation,
    label: requiresConfirmation ? '需要二次确认' : '可直接运行',
  };
}
