import { SystemHubPage } from './SystemHubPage';
import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { SystemStatusPanel } from '@/features/system-status/system-status-panel';
import { useQuery } from '@tanstack/react-query';
import { listProfiles } from '@/lib/api/profiles';
import { getSystemDashboard } from '@/lib/api/system';
import { LoadingState } from '@/components/kit';

function describeValidationStatus(status: string) {
  if (status === 'validated') return '已校验';
  if (status === 'draft') return '草稿';
  if (status === 'invalid_config') return '校验失败';
  if (status === 'archived') return '已归档';
  return '状态待确认';
}

function SystemConfigurationSummary() {
  const query = useQuery({
    queryKey: ['formal-system', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  if (query.isLoading) {
    return <LoadingState label="正在加载配置" description="正在读取已保存的业务配置。" />;
  }
  if (query.error) {
    return <p>配置读取失败，当前配置状态不可用，请稍后重试。</p>;
  }
  const items = query.data?.items ?? [];
  if (!items.length) {
    return <p>暂无可用配置，不会显示为已就绪。</p>;
  }
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.profile_id} className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="font-medium text-slate-950">{item.name}</p>
          <p className="mt-1 text-sm text-slate-600">校验状态：{describeValidationStatus(item.validation_status)}</p>
        </div>
      ))}
    </div>
  );
}

function SystemDataSummary() {
  const query = useQuery({
    queryKey: ['formal-system', 'dashboard'],
    queryFn: getSystemDashboard,
    staleTime: 15_000,
  });

  if (query.isLoading) {
    return <LoadingState label="正在检查数据" description="正在读取真实数据新鲜度状态。" />;
  }
  if (query.error || !query.data) {
    return <p>数据状态暂不可用，不会显示为空或成功。</p>;
  }
  const sources = query.data.freshness.sources;
  if (!sources.length) {
    return <p>没有可确认的数据状态，不会显示为数据已就绪。</p>;
  }
  return (
    <div className="space-y-2">
      {sources.map((source) => (
        <div key={`${source.source}-${source.entity_type}`} className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="font-medium text-slate-950">{source.entity_type}</p>
          <p className="mt-1 text-sm text-slate-600">{source.is_stale ? '需要更新' : '当前可用'}</p>
        </div>
      ))}
    </div>
  );
}

function SystemRunsSummary() {
  const query = useQuery({
    queryKey: ['formal-system', 'dashboard'],
    queryFn: getSystemDashboard,
    staleTime: 15_000,
  });

  if (query.isLoading) {
    return <LoadingState label="正在加载运行状态" description="正在读取失败影响和告警。" />;
  }
  if (query.error || !query.data) {
    return <p>运行状态暂不可用，请稍后重试。</p>;
  }
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <p className="text-sm text-slate-600">失败处理</p>
        <p className="mt-2 font-medium text-slate-950">{query.data.failed_jobs.length} 项</p>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <p className="text-sm text-slate-600">严重告警</p>
        <p className="mt-2 font-medium text-slate-950">{query.data.alerts.critical} 项</p>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <p className="text-sm text-slate-600">一般提醒</p>
        <p className="mt-2 font-medium text-slate-950">{query.data.alerts.warning} 项</p>
      </div>
    </div>
  );
}

export function SystemPage() {
  return <SystemHubPage />;
}

type FormalSystemPageProps = {
  availability?: PageAvailability;
};

export function SystemStatusPage({ availability }: FormalSystemPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="系统状态"
      queryState={state}
      purpose="查看服务和关键依赖是否能够支持当前业务操作。"
      inputDescription="本页无需输入，状态来自现有系统检查。"
      processingDescription="系统读取真实检查结果，不隐藏失败或缺失项。"
      outputDescription="输出为当前可用性、影响范围和建议处理动作。"
      businessAction={{ label: '查看配置管理', to: '/system/configuration' }}
      result={availability ? undefined : <SystemStatusPanel productMode />}
    />
  );
}

export function SystemConfigurationPage({ availability }: FormalSystemPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="配置管理"
      queryState={state}
      purpose="维护业务运行所需的受控配置。"
      inputDescription="输入来自现有配置记录和已保存版本。"
      processingDescription="正式业务化配置界面仍在迁移，现有配置能力继续保留。"
      outputDescription="输出为现有配置记录；内部文件和路径不在正式页面展示。"
      businessAction={{ label: '查看现有配置', to: '/profiles' }}
      result={availability ? undefined : <SystemConfigurationSummary />}
    />
  );
}

export function SystemDataPage({ availability }: FormalSystemPageProps = {}) {
  const state = availability ?? 'unavailable';
  return (
    <ProductPageAdapter
      title="数据管理"
      queryState={state}
      purpose="检查并补齐研究、回测和每日决策所需数据。"
      inputDescription="输入应来自已登记的数据版本和缺口检查。"
      processingDescription="业务化数据维护入口尚未迁入本页。"
      outputDescription="缺少真实数据状态时不展示零、空集合或成功。"
      businessAction={{ label: '返回系统状态', to: '/system/status' }}
      result={availability ? undefined : <SystemDataSummary />}
    />
  );
}

export function SystemRunsPage({ availability }: FormalSystemPageProps = {}) {
  const state = availability ?? 'unavailable';
  return (
    <ProductPageAdapter
      title="运行与告警"
      queryState={state}
      purpose="查看业务处理状态、失败影响和恢复建议。"
      inputDescription="输入应来自真实业务处理记录和告警。"
      processingDescription="业务化运行记录尚未迁入正式页。"
      outputDescription="当前不展示内部运行类型、参数或技术路径。"
      businessAction={{ label: '返回系统状态', to: '/system/status' }}
      result={availability ? undefined : <SystemRunsSummary />}
    />
  );
}
