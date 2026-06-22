import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Activity, ArchiveRestore, Database, Shield, Users, type LucideIcon } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { useAuth } from '@/features/auth/auth-context';

type QuickEntry = {
  title: string;
  description: string;
  to: string;
};

type ManagementGroup = {
  title: string;
  description: string;
  to: string;
  icon: LucideIcon;
  badge: string;
  related: string[];
  adminOnly?: boolean;
};

const quickEntries: QuickEntry[] = [
  {
    title: '系统状态',
    description: '先查看当前可用性、影响范围和下一步。',
    to: '/system/status',
  },
  {
    title: '配置管理',
    description: '查看已保存配置和版本状态。',
    to: '/system/configuration',
  },
  {
    title: '数据与调度',
    description: '查看数据就绪、时间窗口和修复方向。',
    to: '/system/data',
  },
  {
    title: '运行与告警',
    description: '查看最近失败、告警和恢复建议。',
    to: '/system/runs',
  },
];

const managementGroups: ManagementGroup[] = [
  {
    title: 'Profile 配置',
    description: '统一管理配置列表、导入、详情和版本快照。',
    to: '/system/configuration',
    icon: Database,
    badge: '配置',
    related: ['配置列表', '导入配置', '配置详情', '配置版本'],
  },
  {
    title: '数据源',
    description: '汇总市场数据、盘前盘后数据、历史行情和数据集入口。',
    to: '/system/data',
    icon: Activity,
    badge: '数据',
    related: ['市场数据', '盘前盘后数据', '历史行情', '市场快照', '回测数据集'],
  },
  {
    title: '数据与调度',
    description: '查看就绪状态、调度窗口和最小范围补齐入口。',
    to: '/system/data',
    icon: Activity,
    badge: '调度',
    related: ['就绪状态', '调度窗口', '补齐', '回灌', '重算'],
  },
  {
    title: '任务运行',
    description: '查看运行记录、流程运行和结果附件的对应入口。',
    to: '/system/runs',
    icon: Shield,
    badge: '运行',
    related: ['运行记录', '流程运行', '结果附件'],
  },
  {
    title: '失败与告警',
    description: '查看失败影响、告警记录和修复建议。',
    to: '/system/runs',
    icon: Shield,
    badge: '告警',
    related: ['失败记录', '告警记录', '系统健康'],
  },
  {
    title: '数据库与备份',
    description: '管理数据库迁移、备份和恢复入口。',
    to: '/system/backup',
    icon: ArchiveRestore,
    badge: '备份',
    related: ['数据库迁移', '备份恢复', '恢复入口'],
    adminOnly: true,
  },
  {
    title: '权限与审计',
    description: '管理用户、权限和审计记录。',
    to: '/system/audit',
    icon: Users,
    badge: '审计',
    related: ['审计记录', '用户管理'],
    adminOnly: true,
  },
];

function EntryCard({ entry }: { entry: QuickEntry }) {
  const navigate = useNavigate();

  return (
    <Card className="border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <CardHeader>
        <CardTitle className="text-slate-950">{entry.title}</CardTitle>
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

function GroupCard({
  group,
  isAdmin,
}: {
  group: ManagementGroup;
  isAdmin: boolean;
}) {
  const navigate = useNavigate();
  const Icon = group.icon;
  const disabled = group.adminOnly && !isAdmin;

  return (
    <Card className="border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-slate-700">
            <Icon className="h-5 w-5" />
          </div>
          <Badge variant={disabled ? 'warning' : 'info'} className="shrink-0">
            {group.badge}
          </Badge>
        </div>
        <CardTitle className="mt-4 text-slate-950">{group.title}</CardTitle>
        <CardDescription className="text-slate-600">{group.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2 text-xs text-slate-600">
          {group.related.map((item) => (
            <span key={item} className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1">
              {item}
            </span>
          ))}
        </div>
        {disabled ? (
          <p className="text-sm text-slate-500">仅管理员可以进入此分类。</p>
        ) : (
          <Button
            className="w-full justify-between border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            variant="outline"
            onClick={() => {
              navigate(group.to);
            }}
          >
            打开 {group.title}
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export function SystemHubPage() {
  const { canAccess, principal } = useAuth();
  const canSeeFullHub = canAccess('operator');
  const isAdmin = canAccess('admin');
  const pageDescription = useMemo(() => {
    if (isAdmin) {
      return '先看状态，再进入七类系统管理分类。';
    }
    if (canSeeFullHub) {
      return '先看状态，再进入可访问的系统管理分类。';
    }
    return '先看状态和修复入口，更多管理分类只对管理员和操作员展示。';
  }, [canSeeFullHub, isAdmin]);

  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统管理"
        title="系统管理"
        description={pageDescription}
      />

      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <Badge variant="info" className="w-fit">
            使用说明
          </Badge>
          <CardTitle className="mt-2 text-slate-950">本页用于查看系统状态并按分类进入管理入口</CardTitle>
          <CardDescription className="text-slate-600">
            普通用户先看状态和修复入口，管理员和操作员可查看更完整的系统管理分类。
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm leading-6 text-slate-600 md:grid-cols-2 xl:grid-cols-5">
          <div>
            <p className="font-medium text-slate-950">页面用途</p>
            <p className="mt-1">汇总低频管理入口。</p>
          </div>
          <div>
            <p className="font-medium text-slate-950">当前需要的输入</p>
            <p className="mt-1">当前账号权限。</p>
          </div>
          <div>
            <p className="font-medium text-slate-950">系统将执行的处理</p>
            <p className="mt-1">按权限显示可访问入口。</p>
          </div>
          <div>
            <p className="font-medium text-slate-950">输出结果</p>
            <p className="mt-1">状态、修复入口和管理分类。</p>
          </div>
          <div>
            <p className="font-medium text-slate-950">下一步操作</p>
            <p className="mt-1">先看状态，再进入对应分类。</p>
          </div>
        </CardContent>
      </Card>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {quickEntries.map((entry) => (
          <EntryCard entry={entry} key={entry.to} />
        ))}
      </section>

      {canSeeFullHub ? (
        <section className="space-y-4">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">完整分类</p>
            <h2 className="text-xl font-semibold tracking-tight text-slate-950">七类系统管理入口</h2>
            <p className="text-sm leading-6 text-slate-600">
              {isAdmin ? '管理员可直接打开所有分类。' : '操作员可查看完整分类说明，管理员专用入口会标明受限。'}
            </p>
          </div>

          {!isAdmin ? (
            <Card className="border-amber-200 bg-amber-50 shadow-sm">
              <CardContent className="pt-6 text-sm text-amber-900">
                你可以查看更完整的系统管理分类说明，但数据库与备份、权限与审计等高风险入口仅管理员可打开。
              </CardContent>
            </Card>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {managementGroups.map((group) => (
              <GroupCard group={group} isAdmin={isAdmin} key={group.title} />
            ))}
          </div>
        </section>
      ) : (
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardContent className="pt-6 text-sm leading-6 text-slate-600">
            普通用户只显示状态和修复入口。若需要数据库与备份、权限与审计等分类，请联系管理员。
          </CardContent>
        </Card>
      )}

      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <CardTitle className="text-slate-950">当前账号</CardTitle>
          <CardDescription className="text-slate-600">便于确认当前可见范围。</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          当前身份：{principal.role}
        </CardContent>
      </Card>
    </main>
  );
}
