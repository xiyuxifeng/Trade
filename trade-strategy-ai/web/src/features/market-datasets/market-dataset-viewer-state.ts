import type { ErrorRecoveryState } from '@/lib/error-recovery';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';

function readErrorText(error: unknown) {
  if (!error || typeof error !== 'object') {
    return '';
  }

  const record = error as {
    message?: unknown;
    detail?: unknown;
    payload?: unknown;
  };

  return [record.message, record.detail, record.payload]
    .map((value) => (typeof value === 'string' ? value : value ? JSON.stringify(value) : ''))
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function buildDatasetActions() {
  return [
    { label: '返回数据集列表', to: '/market/datasets' },
    { label: '返回 Market 浏览器', to: '/market' },
  ];
}

function buildDatasetErrorState(
  state: Pick<ErrorRecoveryState, 'category' | 'title' | 'description' | 'suggestion' | 'detail' | 'retryable' | 'actions'>,
): ErrorRecoveryState {
  const affectedByCategory: Record<ErrorRecoveryState['category'], string> = {
    'provider unavailable': '当前无法读取正式数据集内容，相关排查和回链结果会受影响。',
    'data empty': '当前页面不会显示目标数据集，后续核对无法继续。',
    'permission denied': '当前账号暂时不能查看该数据集及其关联结果。',
    'validation error': '当前查询不会返回正式结果，需要先修正参数。',
    'config missing': '依赖配置缺失，当前数据集结果不能作为正式依据。',
    'artifact missing': '相关结果材料暂时无法查看，后续判断会受限。',
    'job failed': '本次处理结果可能缺失或不完整，相关业务步骤暂时不能继续。',
    'network error': '当前页面没有拿到完整响应，显示结果不能作为正式依据。',
  };

  return {
    ...state,
    happened: state.description,
    affected: affectedByCategory[state.category],
    repairGuidance: state.suggestion,
  };
}

export function buildDatasetListErrorState(error: unknown): ErrorRecoveryState {
  if (error instanceof ApiError) {
    const text = readErrorText(error);
    if (error.status === 503 || text.includes('provider') || text.includes('service unavailable')) {
      return buildDatasetErrorState({
        category: 'provider unavailable',
        title: '上游服务不可用',
        description: '后端服务或 provider 当前无法响应。',
        suggestion: '请稍后重试，或先确认上游服务状态。',
        detail: JSON.stringify(
          {
            status: error.status,
            message: error.message,
            requestId: error.requestId ?? null,
            detail: error.detail ?? null,
            payload: error.payload ?? null,
          },
          null,
          2,
        ),
        retryable: true,
        actions: buildDatasetActions(),
      });
    }
  }
  return buildErrorRecoveryState(error, 'market');
}

export function buildDatasetDetailErrorState(error: unknown): ErrorRecoveryState {
  const text = readErrorText(error);
  if (error instanceof ApiError) {
    if (error.status === 404 || text.includes('dataset not found') || text.includes('dataset_not_found')) {
      return buildDatasetErrorState({
        category: 'data empty',
        title: '数据集不存在',
        description: '系统没有找到该数据集。',
        suggestion: '请检查 dataset_id 是否正确，或返回列表重新选择。',
        detail: JSON.stringify(
          {
            status: error.status,
            message: error.message,
            requestId: error.requestId ?? null,
            detail: error.detail ?? null,
            payload: error.payload ?? null,
          },
          null,
          2,
        ),
        retryable: false,
        actions: buildDatasetActions(),
      });
    }
    if (error.status === 403 || text.includes('permission') || text.includes('unauthorized')) {
      return buildDatasetErrorState({
        category: 'permission denied',
        title: '没有权限访问数据集',
        description: '当前身份无法查看该数据集。',
        suggestion: '请切换到有权限的账号，或联系管理员调整权限。',
        detail: JSON.stringify(
          {
            status: error.status,
            message: error.message,
            requestId: error.requestId ?? null,
            detail: error.detail ?? null,
            payload: error.payload ?? null,
          },
          null,
          2,
        ),
        retryable: false,
        actions: buildDatasetActions(),
      });
    }
    if (error.status === 422 || text.includes('validation') || text.includes('invalid query')) {
      return buildDatasetErrorState({
        category: 'validation error',
        title: '无效查询参数',
        description: '当前查询参数没有通过校验。',
        suggestion: '请修正 dataset_id、limit 或 offset 后再重新查看。',
        detail: JSON.stringify(
          {
            status: error.status,
            message: error.message,
            requestId: error.requestId ?? null,
            detail: error.detail ?? null,
            payload: error.payload ?? null,
          },
          null,
          2,
        ),
        retryable: false,
        actions: buildDatasetActions(),
      });
    }
    if (error.status === 503 || text.includes('provider') || text.includes('service unavailable')) {
      return buildDatasetErrorState({
        category: 'provider unavailable',
        title: '上游服务不可用',
        description: '后端服务或 provider 当前无法响应。',
        suggestion: '请稍后重试，或先确认上游服务状态。',
        detail: JSON.stringify(
          {
            status: error.status,
            message: error.message,
            requestId: error.requestId ?? null,
            detail: error.detail ?? null,
            payload: error.payload ?? null,
          },
          null,
          2,
        ),
        retryable: true,
        actions: buildDatasetActions(),
      });
    }
  }

  return buildErrorRecoveryState(error, 'market');
}

export function buildInvalidDatasetQueryState(detail: string): ErrorRecoveryState {
  return buildDatasetErrorState({
    category: 'validation error',
    title: '无效查询参数',
    description: '当前 URL 参数无法解析为合法的 dataset viewer 查询。',
    suggestion: '请清理 limit / offset 后重新打开页面。',
    detail,
    retryable: false,
    actions: buildDatasetActions(),
  });
}
