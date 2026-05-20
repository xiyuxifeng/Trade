import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/layout/page-header';
import { OperationalDashboardCenter } from '@/features/data-health';

export function HealthPage() {
  const navigate = useNavigate();

  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统管理"
        title="系统健康检查"
        description="查看 API、数据库、worker、队列和存储的运行状态。"
        actionLabel="返回系统管理"
        onAction={() => navigate('/system')}
      />
      <OperationalDashboardCenter />
    </main>
  );
}
