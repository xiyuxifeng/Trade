import { PageHeader } from '@/components/layout/page-header';
import { BackupManagementSection } from '@/features/system-management/system-management-workspace';

export function RestorePage() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统管理"
        title="数据恢复"
        description="按备份 ID 发起恢复 Job，并在提交前完成风险确认。"
      />
      <BackupManagementSection />
    </main>
  );
}
