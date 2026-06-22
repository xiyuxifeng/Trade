import { ApiError } from '@/lib/api/http';

export type ErrorRecoveryCategory =
  | 'validation error'
  | 'permission denied'
  | 'config missing'
  | 'provider unavailable'
  | 'data empty'
  | 'artifact missing'
  | 'job failed'
  | 'network error';

export type ErrorRecoveryPage =
  | 'jobs'
  | 'job-detail'
  | 'profiles'
  | 'profile-detail'
  | 'market'
  | 'artifacts'
  | 'artifact-detail'
  | 'artifact-filter-options'
  | 'strategy'
  | 'backtest'
  | 'backtest-results'
  | 'backtest-detail'
  | 'backtest-report'
  | 'backtest-validation'
  | 'admin-audit'
  | 'admin-audit-detail';

export type ErrorRecoveryAction = {
  label: string;
  to: string;
};

export type ErrorRecoveryState = {
  category: ErrorRecoveryCategory;
  title: string;
  description: string;
  suggestion: string;
  happened: string;
  affected: string;
  repairGuidance: string;
  detail: string;
  retryable: boolean;
  actions: ErrorRecoveryAction[];
};

function toText(value: unknown) {
  if (typeof value === 'string') return value;
  if (value && typeof value === 'object') return JSON.stringify(value, null, 2);
  return '';
}

function collectErrorText(error: unknown) {
  if (!error || typeof error !== 'object') {
    return '';
  }

  const record = error as {
    type?: unknown;
    message?: unknown;
    detail?: unknown;
    payload?: unknown;
    code?: unknown;
    metadata?: unknown;
  };

  return [
    toText(record.type),
    toText(record.message),
    toText(record.detail),
    toText(record.payload),
    toText(record.code),
    toText(record.metadata),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function classifyCategory(error: unknown): ErrorRecoveryCategory {
  if (error instanceof ApiError) {
    const rawText = `${error.message} ${toText(error.detail)} ${toText(error.payload)} ${collectErrorText(error.payload)}`.toLowerCase();

    if (error.status === 401 || error.status === 403 || rawText.includes('permission') || rawText.includes('unauthorized')) {
      return 'permission denied';
    }
    if (error.status === 400 || rawText.includes('validation')) {
      return 'validation error';
    }
    if (rawText.includes('config')) {
      return 'config missing';
    }
    if (rawText.includes('provider') || rawText.includes('service unavailable') || error.status === 503) {
      return 'provider unavailable';
    }
    if (rawText.includes('artifact')) {
      return 'artifact missing';
    }
    if (rawText.includes('job failed') || rawText.includes('runner') || rawText.includes('handler')) {
      return 'job failed';
    }
    if (error.status === 404) {
      return 'data empty';
    }
    return error.status >= 500 ? 'provider unavailable' : 'network error';
  }

  const rawText = collectErrorText(error);
  if (rawText) {
    if (rawText.includes('permission') || rawText.includes('unauthorized')) {
      return 'permission denied';
    }
    if (rawText.includes('validation')) {
      return 'validation error';
    }
    if (rawText.includes('config')) {
      return 'config missing';
    }
    if (rawText.includes('provider') || rawText.includes('service unavailable')) {
      return 'provider unavailable';
    }
    if (rawText.includes('artifact')) {
      return 'artifact missing';
    }
    if (rawText.includes('job failed') || rawText.includes('runner') || rawText.includes('handler')) {
      return 'job failed';
    }
  }

  if (error instanceof TypeError) {
    return 'network error';
  }

  return 'network error';
}

function getPageRoute(page: ErrorRecoveryPage) {
  switch (page) {
    case 'jobs':
      return '/jobs';
    case 'job-detail':
      return '/jobs';
    case 'backtest':
    case 'backtest-results':
    case 'backtest-detail':
    case 'backtest-report':
    case 'backtest-validation':
      return '/backtest';
    case 'profiles':
      return '/profiles';
    case 'profile-detail':
      return '/profiles';
    case 'market':
      return '/market';
    case 'artifacts':
    case 'artifact-detail':
    case 'artifact-filter-options':
      return '/artifacts';
    case 'strategy':
      return '/strategies';
    case 'admin-audit':
    case 'admin-audit-detail':
      return '/system/audit';
    default:
      return '/';
  }
}

function getPageHomeRoute(page: ErrorRecoveryPage) {
  switch (page) {
    case 'jobs':
      return '/';
    case 'job-detail':
      return '/jobs';
    case 'backtest':
    case 'backtest-results':
    case 'backtest-detail':
    case 'backtest-report':
    case 'backtest-validation':
      return '/';
    case 'profiles':
      return '/';
    case 'profile-detail':
      return '/profiles';
    case 'market':
      return '/';
    case 'artifacts':
    case 'artifact-detail':
    case 'artifact-filter-options':
      return '/';
    case 'strategy':
      return '/';
    case 'admin-audit':
    case 'admin-audit-detail':
      return '/';
    default:
      return '/';
  }
}

function getConfigRoute(page: ErrorRecoveryPage) {
  if (page === 'profiles' || page === 'profile-detail') {
    return '/profiles';
  }
  return '/profiles';
}

function getArtifactsRoute() {
  return '/artifacts';
}

function getTitleAndSuggestion(category: ErrorRecoveryCategory, page: ErrorRecoveryPage) {
  const pageTitles: Record<ErrorRecoveryPage, string> = {
    jobs: '任务',
    'job-detail': '任务详情',
    profiles: '配置列表',
    'profile-detail': '配置详情',
    market: '市场上下文',
    artifacts: '产物中心',
    'artifact-detail': '产物详情',
    'artifact-filter-options': '产物筛选',
    strategy: '规则与市场分析',
    backtest: '回测中心',
    'backtest-results': '回测结果',
    'backtest-detail': '回测详情',
    'backtest-report': '回测报告',
    'backtest-validation': '规则验真',
    'admin-audit': '系统审计',
    'admin-audit-detail': '审计详情',
  };
  const pageTitle = pageTitles[page];

  switch (category) {
    case 'validation error':
      return {
        title: `${pageTitle}输入校验失败`,
        description: '提交的数据没有通过后端校验。',
        suggestion: '请先修正输入，再重新提交。',
      };
    case 'permission denied':
      return {
        title: `没有权限访问${pageTitle}`,
        description: '当前身份无法查看或操作该内容。',
        suggestion: '请切换到有权限的账号，或联系管理员调整权限。',
      };
    case 'config missing':
      return {
        title: '配置缺失',
        description: '页面依赖的配置或市场上下文快照没有找到。',
        suggestion: '先检查画像，再重新打开页面。',
      };
    case 'provider unavailable':
      if (page === 'market') {
        return {
          title: '市场上下文暂不可用',
          description: '后端服务或 provider 当前无法响应。',
          suggestion: '请稍后重试，或先确认上游服务状态。',
        };
      }
      return {
        title: '上游服务不可用',
        description: '后端服务或 provider 当前无法响应。',
        suggestion: '稍后重试，或先确认上游服务状态。',
      };
    case 'data empty':
      return {
        title: '没有找到可展示的数据',
        description: '当前查询结果为空，或者记录尚未生成。',
        suggestion: '可以调整筛选条件，或稍后刷新页面。',
      };
    case 'artifact missing':
      return {
        title: '产物不可用',
        description: '相关 artifact 尚未生成、已过期或无法访问。',
        suggestion: '先查看来源 Job，再判断是否需要重新运行。',
      };
    case 'job failed':
      return {
        title: '任务执行失败',
        description: '当前任务已经失败，建议先查看失败原因和日志。',
        suggestion: '先打开 Job 详情确认错误，再决定是否重试。',
      };
    case 'network error':
      return {
        title: '网络请求失败',
        description: '前端没有拿到后端响应。',
        suggestion: '请确认网络连接后重试。',
      };
    default:
      return {
        title: '请求失败',
        description: '页面遇到了无法识别的错误。',
        suggestion: '请刷新页面或返回工作台后重试。',
      };
  }
}

function getAffectedText(category: ErrorRecoveryCategory) {
  switch (category) {
    case 'validation error':
      return '当前提交不会生效，相关结果也不会更新。';
    case 'permission denied':
      return '当前账号暂时不能查看或处理这部分内容。';
    case 'config missing':
      return '依赖配置未准备好，当前结果不能当成正式依据。';
    case 'provider unavailable':
      return '本页需要的上游服务暂时没有返回完整结果。';
    case 'data empty':
      return '当前页面不会显示正式结果，需要等待记录生成或调整筛选条件。';
    case 'artifact missing':
      return '相关结果材料暂时无法查看，后续判断会受限。';
    case 'job failed':
      return '本次处理结果可能缺失或不完整，相关业务步骤暂时不能继续。';
    case 'network error':
      return '前端没有拿到完整响应，当前显示不能作为正式结果。';
    default:
      return '当前页面结果暂时不可直接使用。';
  }
}

function buildActions(category: ErrorRecoveryCategory, page: ErrorRecoveryPage): ErrorRecoveryAction[] {
  const pageRoute = getPageRoute(page);
  const homeRoute = getPageHomeRoute(page);
  const profilesRoute = '/profiles';

  switch (category) {
    case 'permission denied':
      return [
        { label: '返回首页', to: homeRoute },
        { label: '前往配置管理', to: profilesRoute },
      ];
    case 'config missing':
      return [
        { label: '前往配置管理', to: getConfigRoute(page) },
        { label: '返回工作台', to: homeRoute },
      ];
    case 'provider unavailable':
      return [
        { label: '返回工作台', to: homeRoute },
        { label: '前往配置管理', to: profilesRoute },
      ];
    case 'data empty':
      return [];
    case 'artifact missing':
      return [
        { label: '打开产物中心', to: getArtifactsRoute() },
        { label: '查看任务列表', to: '/jobs' },
      ];
    case 'job failed':
      return [
        { label: '查看任务列表', to: '/jobs' },
        { label: '返回工作台', to: homeRoute },
      ];
    case 'validation error':
      return [
        { label: '返回当前页面', to: pageRoute },
        { label: '前往配置管理', to: getConfigRoute(page) },
      ];
    case 'network error':
      return [
        { label: '返回工作台', to: homeRoute },
        { label: '前往配置管理', to: profilesRoute },
      ];
    default:
      return [
        { label: '返回工作台', to: homeRoute },
      ];
  }
}

export function buildErrorRecoveryState(error: unknown, page: ErrorRecoveryPage): ErrorRecoveryState {
  const category = classifyCategory(error);
  const titleAndSuggestion = getTitleAndSuggestion(category, page);
  const isApi404 = error instanceof ApiError && error.status === 404;
  const pageSpecific404: Partial<Record<ErrorRecoveryPage, { title: string; description: string; suggestion: string }>> =
    isApi404 && category === 'data empty'
      ? {
        'job-detail': {
          title: '任务不存在',
          description: '系统没有找到该 Job 记录。',
          suggestion: '请检查任务 ID 是否正确，或返回任务列表查看最近任务。',
        },
        'profile-detail': {
          title: '配置不存在',
          description: '系统没有找到该配置记录。',
          suggestion: '请检查配置 ID 是否正确，或返回配置列表查看可用配置。',
        },
        jobs: {
          title: '任务列表暂不可用',
          description: '当前任务列表没有返回可展示的记录。',
          suggestion: '请稍后刷新页面，或返回工作台查看其他入口。',
        },
        profiles: {
          title: '配置列表暂不可用',
          description: '当前配置列表没有返回可展示的记录。',
          suggestion: '请稍后刷新页面，或前往配置管理继续查看。',
        },
        market: {
          title: '市场上下文快照不存在',
          description: '系统没有找到该市场上下文快照。',
          suggestion: '请检查 snapshot_id 是否正确，或返回列表重新筛选。',
        },
        artifacts: {
          title: '产物列表暂不可用',
          description: '当前产物中心没有返回可展示的数据。',
          suggestion: '请稍后重试，或调整筛选条件后再看一次。',
        },
        'artifact-detail': {
          title: '产物详情暂不可用',
          description: '当前产物详情没有返回可展示的数据。',
          suggestion: '请检查 artifact_id 是否正确，或返回产物列表重新选择。',
        },
        strategy: {
          title: '规则与市场分析暂不可用',
          description: '当前规则与市场分析页面没有返回可展示的数据。',
          suggestion: '请稍后重试，或切换到盘前分析、盘后复盘与任务中心继续排查。',
        },
        'backtest': {
          title: '回测中心暂不可用',
          description: '当前回测中心没有返回可展示的数据。',
          suggestion: '请稍后重试，或返回工作台查看其他入口。',
        },
        'backtest-results': {
          title: '回测结果暂不可用',
          description: '当前回测结果没有返回可展示的数据。',
          suggestion: '请稍后重试，或放宽筛选条件再看一次。',
        },
        'backtest-detail': {
          title: '回测详情暂不可用',
          description: '当前回测详情没有返回可展示的数据。',
          suggestion: '请检查 result_id 是否正确，或返回结果列表重新选择。',
        },
        'backtest-report': {
          title: '回测报告暂不可用',
          description: '当前回测报告没有返回可展示的数据。',
          suggestion: '请稍后重试，或重新生成回测结果。',
        },
        'backtest-validation': {
          title: '规则验真暂不可用',
          description: '当前规则验真报告没有返回可展示的数据。',
          suggestion: '请稍后重试，或先确认回测结果是否存在。',
        },
        'admin-audit': {
          title: '系统审计暂不可用',
          description: '当前系统审计没有返回可展示的数据。',
          suggestion: '请稍后重试，或返回工作台查看其他入口。',
        },
        'admin-audit-detail': {
          title: '审计详情暂不可用',
          description: '当前审计详情没有返回可展示的数据。',
          suggestion: '请检查审计 ID 是否正确，或返回审计列表重新选择。',
        },
      }
      : {};
  const pageSpecific404Entry = pageSpecific404[page] ?? null;
  const { title, description, suggestion } = pageSpecific404Entry ?? titleAndSuggestion;
  const detail = error instanceof ApiError
    ? JSON.stringify(
        {
          status: error.status,
          message: error.message,
          requestId: error.requestId ?? null,
          detail: error.detail ?? null,
          payload: error.payload ?? null,
        },
        null,
        2,
      )
    : error instanceof Error
      ? JSON.stringify({ name: error.name, message: error.message }, null, 2)
      : JSON.stringify({ message: String(error ?? 'unknown error') }, null, 2);

  const retryable =
    category === 'artifact missing' ||
    (!isApi404 && category !== 'permission denied' && category !== 'validation error');

  return {
    category,
    title,
    description,
    suggestion,
    happened: description,
    affected: getAffectedText(category),
    repairGuidance: suggestion,
    detail,
    retryable,
    actions: isApi404 && category !== 'artifact missing' ? buildActions('data empty', page) : buildActions(category, page),
  };
}
