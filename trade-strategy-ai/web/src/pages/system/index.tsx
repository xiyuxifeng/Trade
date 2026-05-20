import { PageHeader } from '@/components/layout/page-header';
import { SystemManagementWorkspace } from '@/features/system-management/system-management-workspace';

export function SystemPage() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统管理"
        title="系统管理"
        description="统一查看健康状态、管理用户、查看审计，并执行受限备份与恢复。"
      />

      <SystemManagementWorkspace />
    </main>
  );
}
