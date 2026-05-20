import { PageHeader } from '@/components/layout/page-header';
import { DatabaseMigrationSection } from '@/features/system-management/system-management-workspace';

export function DatabaseMigrationPage() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统管理"
        title="数据库迁移"
        description="通过受控 Job 触发数据库迁移并进入 Job 详情页。"
      />
      <DatabaseMigrationSection />
    </main>
  );
}
