import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/layout/page-header';
import { UserManagementSection } from '@/features/system-management/system-management-workspace';

export function UsersPage() {
  const navigate = useNavigate();

  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统管理"
        title="用户管理"
        description="添加或删除用户，修改用户权限、启用状态和密码。"
        actionLabel="返回系统管理"
        onAction={() => navigate('/system')}
      />
      <UserManagementSection />
    </main>
  );
}
