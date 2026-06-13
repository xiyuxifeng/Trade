import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { HomeBusinessStatus, SystemDashboardResponse } from '@/types/system';

const statusOrder = [
  'data_readiness',
  'premarket',
  'postmarket',
  'pending_rules',
  'profile_proposals',
  'strategy_proposals',
  'current_strategy',
  'market_state',
  'failed_runs',
] as const;

const statusTitles: Record<(typeof statusOrder)[number], string> = {
  data_readiness: '今日数据',
  premarket: '今日盘前',
  postmarket: '最近盘后',
  pending_rules: '规则审核',
  profile_proposals: '画像建议',
  strategy_proposals: '策略建议',
  current_strategy: '策略版本',
  market_state: '市场状态',
  failed_runs: '失败运行',
};

function badgeVariant(status: HomeBusinessStatus['status']) {
  if (status === 'ready' || status === 'complete') return 'success' as const;
  if (status === 'blocked' || status === 'partial') return 'warning' as const;
  return 'default' as const;
}

export function HomeDashboard({ dashboard }: { dashboard: SystemDashboardResponse }) {
  const statuses = statusOrder.map((key) => [key, dashboard.business_status[key]] as const);
  const unavailableCount = statuses.filter(([, item]) => !item || item.status === 'unavailable' || item.status === 'partial').length;
  const actionable = statuses.filter(([, item]) => item && item.status !== 'unavailable' && (
    item.status === 'blocked'
    || item.status === 'pending'
    || (item.status === 'ready' && typeof item.value === 'number' && item.value > 0)
  ));

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[30px] border border-emerald-900/10 bg-[linear-gradient(135deg,#fffaf0_0%,#edf4e8_55%,#dcece3_100%)] p-6 shadow-[0_24px_70px_rgba(23,63,53,0.14)]">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-800">今日决策</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-emerald-950">今日决策首页</h1>
            <p className="mt-2 text-sm text-emerald-900/70">
              {dashboard.business_date ?? '业务日期不可用'} · {dashboard.is_trading_day === true ? '交易日' : dashboard.is_trading_day === false ? '非交易日' : '交易日状态不可用'}
            </p>
          </div>
          {dashboard.business_status.market_state ? (
            <div className="rounded-2xl border border-white/70 bg-white/70 px-4 py-3">
              <p className="text-xs text-slate-500">当前市场状态</p>
              <p className="mt-1 font-semibold text-slate-950">{dashboard.business_status.market_state.value ?? '不可用'}</p>
            </div>
          ) : null}
        </div>
      </section>

      <Card className="border-emerald-800/20 bg-emerald-950 text-white">
        <CardHeader>
          <p className="text-xs uppercase tracking-[0.18em] text-emerald-200">下一步主要操作</p>
          <CardTitle className="text-2xl text-white">{dashboard.next_action.label}</CardTitle>
        </CardHeader>
        <CardContent>
          <Link className="inline-flex rounded-lg bg-amber-100 px-4 py-2 text-sm font-semibold text-emerald-950" to={dashboard.next_action.target_path}>
            {dashboard.next_action.label}
          </Link>
        </CardContent>
      </Card>

      {unavailableCount ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          部分状态暂不可用，页面保留已确认结果，不会将缺失数据显示为零或完成。
        </div>
      ) : null}

      <section>
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">今日状态</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-950">九项业务状态</h2>
          </div>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {statuses.map(([key, item]) => (
            <Card data-testid="home-business-status" key={key}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <CardTitle className="text-base">{statusTitles[key]}</CardTitle>
                  <Badge variant={badgeVariant(item?.status ?? 'unavailable')}>
                    {item?.status === 'complete' ? '已完成' : item?.status === 'ready' ? '已确认' : item?.status === 'pending' ? '待处理' : item?.status === 'blocked' ? '受阻' : item?.status === 'partial' ? '部分可用' : '不可用'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="font-medium text-slate-950">{item?.label ?? '状态暂不可用'}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{item?.detail ?? '当前没有可确认的事实。'}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardHeader><CardTitle>真实待办</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {actionable.length ? actionable.map(([key, item]) => (
              <Link className="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-900" key={key} to={item.target_path}>
                {item.label}
              </Link>
            )) : <p className="text-sm text-slate-600">当前没有已确认待办。</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>从文章到盘后的业务流程</CardTitle></CardHeader>
          <CardContent>
            <ol className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
              {['导入文章', '提取规则', '人工审核', '历史回测', '市场状态验证', '作者画像', '策略发布', '今日盘前', '今日盘后'].map((step, index) => (
                <li className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2" key={step}>
                  <span className="mr-2 text-xs font-semibold text-emerald-800">{index + 1}</span>{step}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
