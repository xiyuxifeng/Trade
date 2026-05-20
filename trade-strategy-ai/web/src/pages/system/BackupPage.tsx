import { PageHeader } from '@/components/layout/page-header';
import { BackupManagementSection } from '@/features/system-management/system-management-workspace';

export function BackupPage() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统管理"
        title="数据备份"
        description="从白名单目录创建备份 Job，并查看已有备份包。"
      />
      <BackupManagementSection />
    </main>
  );
}
