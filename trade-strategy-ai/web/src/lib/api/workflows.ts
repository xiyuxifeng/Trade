import { fetchJson } from './http';
import type {
  WorkflowDetailResponse,
  WorkflowRunRequest,
  WorkflowRunResponse,
  WorkflowsListResponse,
} from '@/types/workflows';

export function listWorkflows() {
  return fetchJson<WorkflowsListResponse>('/workflows');
}

export function getWorkflow(workflowId: string) {
  return fetchJson<WorkflowDetailResponse>(`/workflows/${workflowId}`);
}

export function runWorkflow(workflowId: string, request: WorkflowRunRequest) {
  return fetchJson<WorkflowRunResponse>(`/workflows/${workflowId}/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
