import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { useNavigate } from 'react-router-dom';

export function BacktestPage() {
  const navigate = useNavigate();

  return (
    <main className="page-stack">
      <PageHeader
        kicker="预留模块"
        title="回测"
        description="回测能力在 V2 只保留正式入口与占位说明，实际实现会在后续阶段接入。"
      />

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="warning" className="w-fit">
              V3 预留
            </Badge>
            <CardTitle className="mt-2 text-slate-950">回测工作台尚未进入正式实现</CardTitle>
            <CardDescription className="text-slate-600">
              当前只提供占位入口，避免 UI 继续堆叠 Demo 逻辑。后续会在正式回测流程落地后替换为真实页面。
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-slate-600">
            <p>请先通过策略工作台、市场快照浏览器和产物中心完成前置数据检查。</p>
            <p className="mt-2">本页不展示本地文件路径，也不执行任何回测计算。</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">相关入口</CardTitle>
            <CardDescription className="text-slate-600">这些页面将作为回测前置条件使用。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate('/strategies')}>
              前往策略
            </Button>
            <Button className="w-full justify-start border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate('/market')}>
              前往市场快照浏览器
            </Button>
            <Button className="w-full justify-start border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate('/artifacts')}>
              前往产物中心
            </Button>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
