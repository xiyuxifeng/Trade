import { useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowRight, CheckCircle2, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { LoadingState } from '@/components/kit';
import { useAuth } from '@/features/auth/auth-context';
import { checkFormalBacktestDependencies, createFormalBacktestRun, getFormalBacktestRun } from '@/lib/api/backtests';
import { ApiError } from '@/lib/api/http';
import type { FormalBacktestLevel, FormalBacktestSelection } from '@/types/backtests';

const DEFAULT_BENCHMARK_SYMBOL = '000300.SH';

function splitSymbols(value: string) {
  return value
    .split(/[\s,，]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function dependencyMessage(error: unknown) {
  if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
    return '当前账号只能查看自己有权限的数据，请联系管理员确认权限。';
  }
  if (error instanceof ApiError && error.status === 409) {
    return '当前输入无法创建正式回测，请先处理页面列出的数据限制。';
  }
  return '数据依赖检查失败，请稍后重试或调整输入。';
}

function stateTone(state: string) {
  if (state === '可运行') return 'border-emerald-200 bg-emerald-50 text-emerald-900';
  if (state === '可降级' || state === '需修复' || state === '覆盖不足') return 'border-amber-200 bg-amber-50 text-amber-900';
  if (state === '无权限' || state === '冲突' || state === '不可运行') return 'border-rose-200 bg-rose-50 text-rose-900';
  return 'border-slate-200 bg-slate-50 text-slate-800';
}

function levelLabel(level: string) {
  if (level === 'level_1') return 'Level 1：历史行情';
  if (level === 'level_2') return 'Level 2：历史行情 + 市场状态';
  if (level === 'level_3') return 'Level 3：历史行情 + 市场状态 + Kaipan 数据';
  return level;
}

export function FormalBacktestWorkbench() {
  const { canAccess, principal } = useAuth();
  const today = useMemo(() => dayjs().format('YYYY-MM-DD'), []);
  const defaultStart = useMemo(() => dayjs(today).subtract(30, 'day').format('YYYY-MM-DD'), [today]);
  const [ruleMode, setRuleMode] = useState<'rule_version' | 'rule_family'>('rule_version');
  const [ruleId, setRuleId] = useState('');
  const [dateFrom, setDateFrom] = useState(defaultStart);
  const [dateTo, setDateTo] = useState(today);
  const [symbols, setSymbols] = useState('000001.SZ');
  const [benchmarkSymbol, setBenchmarkSymbol] = useState(DEFAULT_BENCHMARK_SYMBOL);
  const [mode, setMode] = useState<FormalBacktestSelection['mode']>('full');
  const [requestedLevel, setRequestedLevel] = useState<FormalBacktestLevel>('level_1');
  const [profileId, setProfileId] = useState('');
  const [reason, setReason] = useState('验证规则在固定历史数据中的表现');
  const [runId, setRunId] = useState<string | null>(null);
  const [acceptDowngrade, setAcceptDowngrade] = useState(false);

  const selection: FormalBacktestSelection = {
    rule_version_id: ruleMode === 'rule_version' ? ruleId || null : null,
    rule_family_id: ruleMode === 'rule_family' ? ruleId || null : null,
    date_from: dateFrom,
    date_to: dateTo,
    universe: { symbols: splitSymbols(symbols) },
    benchmark_symbol: benchmarkSymbol,
    mode,
    requested_level: requestedLevel,
    profile_id: profileId || null,
  };

  const dependencyMutation = useMutation({
    mutationFn: () => checkFormalBacktestDependencies(selection),
  });

  const createMutation = useMutation({
    mutationFn: () => createFormalBacktestRun({
      selection,
      reason,
      accept_downgrade: acceptDowngrade,
      accepted_effective_level: acceptDowngrade && dependency?.effective_level !== 'unavailable' ? dependency?.effective_level : null,
    }),
    onSuccess: (run) => setRunId(run.run_id),
  });

  const runQuery = useQuery({
    queryKey: ['formal-backtest-run', runId],
    queryFn: () => getFormalBacktestRun(runId as string),
    enabled: Boolean(runId),
    staleTime: 10_000,
  });

  const dependency = dependencyMutation.data;
  const canSubmit = canAccess('operator') && Boolean(dependency?.can_create_run || (dependency?.downgrade_allowed && acceptDowngrade)) && !createMutation.isPending;
  const dependencyError = dependencyMutation.error ?? createMutation.error;

  return (
    <div className="space-y-5" data-testid="formal-backtest-product">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-950">规则与回测</p>
            <p className="mt-1 text-sm text-slate-600">选择规则和固定数据范围，先检查数据依赖，再创建正式回测记录。</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
            当前身份：{principal.role}
          </div>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-slate-700">
              <span>选择规则</span>
              <Select value={ruleMode} onChange={(event) => setRuleMode(event.target.value as typeof ruleMode)}>
                <option value="rule_version">规则版本</option>
                <option value="rule_family">规则族</option>
              </Select>
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>{ruleMode === 'rule_version' ? '规则版本 ID' : '规则族 ID'}</span>
              <Input value={ruleId} onChange={(event) => setRuleId(event.target.value)} placeholder="输入已审核的正式 ID" />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>回测开始日期</span>
              <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>回测结束日期</span>
              <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
            </label>
            <label className="space-y-2 text-sm text-slate-700 md:col-span-2">
              <span>标的范围</span>
              <Input value={symbols} onChange={(event) => setSymbols(event.target.value)} placeholder="例如 000001.SZ, 600000.SH" />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>基准</span>
              <Input value={benchmarkSymbol} onChange={(event) => setBenchmarkSymbol(event.target.value)} />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>回测模式</span>
              <Select value={mode} onChange={(event) => setMode(event.target.value as FormalBacktestSelection['mode'])}>
                <option value="full">完整验证</option>
                <option value="replay">历史回放</option>
                <option value="rule_validation">规则验真</option>
              </Select>
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>数据等级</span>
              <Select value={requestedLevel} onChange={(event) => setRequestedLevel(event.target.value as FormalBacktestLevel)}>
                <option value="level_1">{levelLabel('level_1')}</option>
                <option value="level_2">{levelLabel('level_2')}</option>
                <option value="level_3">{levelLabel('level_3')}</option>
              </Select>
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>配置上下文</span>
              <Input value={profileId} onChange={(event) => setProfileId(event.target.value)} placeholder="可选，不作为被验证事实来源" />
            </label>
            <label className="space-y-2 text-sm text-slate-700 md:col-span-2">
              <span>创建原因</span>
              <Input value={reason} onChange={(event) => setReason(event.target.value)} />
            </label>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Button disabled={!ruleId || dependencyMutation.isPending} onClick={() => dependencyMutation.mutate()}>
              检查数据依赖
            </Button>
            <Button disabled={!canSubmit} onClick={() => createMutation.mutate()}>
              开始回测
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
          {!canAccess('operator') ? (
            <p className="mt-3 text-sm text-amber-700">当前账号可以检查数据依赖；创建正式回测需要 operator 权限。</p>
          ) : null}
        </div>

        <aside className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="font-semibold text-slate-950">处理状态</p>
            {dependencyMutation.isPending ? <LoadingState label="正在检查数据依赖" description="系统正在核对规则、历史行情和所需市场状态。" /> : null}
            {dependency ? (
              <div className={`mt-3 rounded-lg border p-3 text-sm ${stateTone(dependency.business_state)}`}>
                <p className="font-medium">{dependency.business_state}</p>
                <p className="mt-1">请求等级：{levelLabel(dependency.requested_level)}</p>
                <p>有效等级：{dependency.effective_level === 'unavailable' ? '不可用' : levelLabel(dependency.effective_level)}</p>
                <p>规则最低等级：{levelLabel(dependency.minimum_required_level)}</p>
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-600">请先填写输入并检查数据依赖。</p>
            )}
            {dependency?.downgrade_allowed ? (
              <label className="mt-3 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <input
                  type="checkbox"
                  checked={acceptDowngrade}
                  onChange={(event) => setAcceptDowngrade(event.target.checked)}
                  className="mt-1 h-4 w-4"
                />
                <span>
                  确认降级为{dependency.effective_level === 'unavailable' ? '可用等级' : levelLabel(dependency.effective_level)}回测。
                  {dependency.downgrade_reason ? ` ${dependency.downgrade_reason}` : ''}
                </span>
              </label>
            ) : null}
            {dependencyError ? <p className="mt-3 text-sm text-rose-700">{dependencyMessage(dependencyError)}</p> : null}
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="font-semibold text-slate-950">输出</p>
            {runQuery.data ? (
              <div className="mt-3 space-y-2 text-sm text-slate-700">
                <p className="flex items-center gap-2 font-medium text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" />
                  已创建正式回测记录
                </p>
                <p className="break-all">运行编号：{runQuery.data.run_id}</p>
                <p>当前进度：{String(runQuery.data.progress.current_step ?? '等待执行')}</p>
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-600">通过依赖检查后可创建正式回测记录。</p>
            )}
          </div>
        </aside>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="font-semibold text-slate-950">数据覆盖和限制</p>
          {dependency?.missing_requirements.length ? (
            <ul className="mt-2 space-y-2 text-sm text-slate-600">
              {dependency.missing_requirements.map((reason) => (
                <li key={reason.code}>{reason.message}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-slate-600">依赖检查会列出缺失范围、影响和处理方式。</p>
          )}
          {dependency?.limitations.map((item) => (
            <p className="mt-2 text-sm text-amber-700" key={item}>{item}</p>
          ))}
          {dependency?.repair_guidance.map((item) => (
            <p className="mt-2 text-sm text-slate-700" key={item}>{item}</p>
          ))}
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="flex items-center gap-2 font-semibold text-slate-950">
            <ShieldCheck className="h-4 w-4" />
            可复现证据入口
          </p>
          <p className="mt-2 break-all text-sm text-slate-600">
            {runQuery.data?.reproducibility_fingerprint ?? '创建正式回测后显示请求指纹和复现指纹。'}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="font-semibold text-slate-950">下一步</p>
          <div className="mt-2 space-y-2 text-sm text-slate-600">
            <p>查看整体结果入口：正式执行完成后进入回测结果页。</p>
            <p>查看分市场状态结果入口：后续任务接入完整分市场状态执行。</p>
            <p>查看或生成适用性画像草稿入口：后续任务从正式结果生成草稿。</p>
          </div>
        </div>
      </section>
    </div>
  );
}
