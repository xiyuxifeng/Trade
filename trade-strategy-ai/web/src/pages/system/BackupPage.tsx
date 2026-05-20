import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/layout/page-header';
import { BackupManagementSection } from '@/features/system-management/system-management-workspace';

export function BackupPage() {
  const navigate = useNavigate();

  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统管理"
        title="数据备份与恢复"
        description="从白名单目录创建备份，并在同页恢复已有备份。"
        actionLabel="返回系统管理"
        onAction={() => navigate('/system')}
      />
      <BackupManagementSection />
    </main>
  );
}
