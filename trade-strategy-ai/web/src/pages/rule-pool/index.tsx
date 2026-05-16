import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';

export function RulePoolPage() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="预留模块"
        title="规则池"
        description="规则池入口已纳入正式信息架构，但详细能力将在后续阶段实现。"
      />

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="warning" className="w-fit">
              V3 预留
            </Badge>
            <CardTitle className="mt-2 text-slate-950">规则池暂未接入正式逻辑</CardTitle>
            <CardDescription className="text-slate-600">
              这里保留的是稳定入口和说明，不会提前暴露规则生成或规则选择逻辑。
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-slate-600">
            <p>当前阶段只要求 IA 可见、路由稳定、风格一致。</p>
            <p className="mt-2">后续实现会由 V3 的 rule pool 相关任务接管。</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">验收说明</CardTitle>
            <CardDescription className="text-slate-600">本页用于证明正式入口已存在。</CardDescription>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-slate-600">
            <p>页面必须可访问，不能是空白页。</p>
            <p className="mt-2">页面必须维持与 UI-V2-002 一致的浅色工作台风格。</p>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
