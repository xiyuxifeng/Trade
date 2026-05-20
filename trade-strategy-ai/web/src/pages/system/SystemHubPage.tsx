import { useNavigate } from 'react-router-dom';
import { ArrowRight, Activity, Shield, Users, Database, ArchiveRestore, type LucideIcon } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { useAuth } from '@/features/auth/auth-context';

type HubEntry = {
  title: string;
  description: string;
  to: string;
  icon: LucideIcon;
  badge: string;
};

const hubEntries: HubEntry[] = [
  {
    title: '权限与审计',
    description: '查看高风险操作、确认轨迹和权限拒绝历史。',
    to: '/system/audit',
    icon: Shield,
    badge: '审计',
  },
  {
    title: '用户管理',
    description: '添加、删除、修改权限和密码。',
    to: '/system/users',
    icon: Users,
    badge: '账号',
  },
  {
    title: '系统健康检查',
    description: '查看 API、DB、worker、队列和存储状态。',
    to: '/system/health',
    icon: Activity,
    badge: '健康',
  },
  {
    title: '数据库迁移',
    description: '触发高风险迁移 Job 并进入 Job Detail。',
    to: '/system/db-migrate',
    icon: Database,
    badge: 'Job',
  },
  {
    title: '数据备份与恢复',
    description: '从白名单目录创建备份，并在同页恢复已有备份。',
    to: '/system/backup',
    icon: ArchiveRestore,
    badge: '备份',
  },
];

function HubCard({ entry }: { entry: HubEntry }) {
  const Icon = entry.icon;
  const navigate = useNavigate();

  return (
    <Card className="border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-slate-700">
            <Icon className="h-5 w-5" />
          </div>
          <Badge variant="info" className="shrink-0">
            {entry.badge}
          </Badge>
        </div>
        <CardTitle className="mt-4 text-slate-950">{entry.title}</CardTitle>
        <CardDescription className="text-slate-600">{entry.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button
          className="w-full justify-between border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
          variant="outline"
          onClick={() => {
            navigate(entry.to);
          }}
        >
          进入 {entry.title}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  );
}

export function SystemHubPage() {
  const { canAccess, principal } = useAuth();
  const canManage = canAccess('admin');

  if (!canManage) {
    return (
      <main className="page-stack">
        <Card className="border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-lg font-semibold text-slate-950">没有权限访问系统管理</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，需要 admin 权限。</p>
        </Card>
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统管理"
        title="系统管理"
        description="作为统一管理入口，先选择子功能，再进入对应的详细设置页面。"
      />

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              管理入口
            </Badge>
            <CardTitle className="mt-2 text-slate-950">把系统管理收束成单一入口，再分发到子功能页</CardTitle>
            <CardDescription className="text-slate-600">
              这里不承载具体业务操作，只负责入口汇总和导航分发。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6 text-slate-600">
            <p>权限与审计、用户管理、系统健康、迁移、备份、恢复都拆成独立页面。</p>
            <p>每个子功能页都保留完整的加载、错误、空态和确认交互。</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">安全提示</CardTitle>
            <CardDescription className="text-slate-600">高风险操作仍然需要进入具体页面后确认。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600">
            <p>系统管理只对 admin 角色开放。</p>
            <p>备份与恢复会通过 Job Center 执行并保留审计记录。</p>
            <p>系统健康检查不会创建 Job，但仍需要查看权限结果。</p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {hubEntries.map((entry) => (
          <HubCard entry={entry} key={entry.to} />
        ))}
      </section>
    </main>
  );
}
