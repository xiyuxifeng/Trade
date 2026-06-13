import { ErrorState, LoadingState } from '@/components/kit';
import { HomeDashboard } from '@/features/home/home-dashboard';
import { useHomeDashboard } from '@/features/home/use-home-dashboard';

export function HomePage() {
  const query = useHomeDashboard();

  if (query.isLoading) {
    return <LoadingState label="正在读取今日业务状态" description="正在汇总数据、盘前盘后、规则、策略和市场状态。" />;
  }
  if (query.error || !query.data) {
    return (
      <ErrorState
        category="network error"
        title="今日业务状态读取失败"
        description="首页暂时无法判断数据、盘前盘后和待办状态。"
        suggestion="重新读取；如持续失败，请先查看系统状态。"
        retryLabel="重新读取"
        onRetry={() => void query.refetch()}
        actions={[{ label: '查看系统状态', to: '/system/status' }]}
      />
    );
  }

  return <HomeDashboard dashboard={query.data} />;
}
