import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { useAuth } from '@/features/auth/auth-context';

export function AdminPage() {
  const navigate = useNavigate();
  const { canAccess, principal } = useAuth();
  const canManage = canAccess('admin');

  if (!canManage) {
    return (
      <main className="page-stack">
        <Card className="border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-lg font-semibold text-slate-950">没有权限访问管理中心</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，需要 admin 权限。</p>
        </Card>
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="配置与管理"
        title="管理中心"
        description="将用户管理和运维恢复能力收束到正式入口，避免继续把它们散落在多个临时页面里。"
      />

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              正式入口
            </Badge>
            <CardTitle className="mt-2 text-slate-950">管理中心是用户和运维能力的统一门面</CardTitle>
            <CardDescription className="text-slate-600">
              当前只负责提供清晰的入口分发，不在这一层堆叠业务逻辑。
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-slate-600">
            <p>用户管理与运维恢复仍保留为单独页面，便于分权限和分职责处理。</p>
            <p className="mt-2">后续 V3 可以在这里继续扩展审计、备份和恢复入口。</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">管理入口</CardTitle>
            <CardDescription className="text-slate-600">进入下层页面继续执行具体操作。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate('/users')}>
              用户管理
            </Button>
            <Button className="w-full justify-start border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate('/admin/audit')}>
              权限与审计
            </Button>
            <Button className="w-full justify-start border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate('/ops')}>
              运维恢复
            </Button>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
