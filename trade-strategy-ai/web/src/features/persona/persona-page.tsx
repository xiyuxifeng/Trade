import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { EmptyState, LoadingState, PageHeader, SectionCard, ErrorState } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { listBehaviorRules } from '@/lib/api/persona';
import type { BehaviorRuleRecord } from '@/types/persona';
import { PersonaCenter } from './persona-center';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 403 || error.status === 401) return '当前账号没有权限查看行为规则。';
    if (error.status === 404) return '未找到行为规则数据。';
    return '行为规则加载失败，请稍后重试。';
  }
  if (error instanceof Error) return '行为规则加载失败，请稍后重试。';
  return '行为规则加载失败，请稍后重试。';
}

function SummaryCard({ title, value, note }: { title: string; value: string | number; note: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className="mt-2 break-all text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{note}</p>
    </div>
  );
}

function formatConditionExpression(condition: BehaviorRuleRecord['conditions'][number]) {
  return condition.expression || `${condition.field} ${condition.op} ${String(condition.value)}`;
}

type BehaviorRuleGroup = {
  name: string;
  rules: BehaviorRuleRecord[];
  enabledCount: number;
};

function RuleCard({ rule, productMode = false }: { rule: BehaviorRuleRecord; productMode?: boolean }) {
  return (
    <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-slate-950">
              {rule.label}
              <span className="ml-2 text-sm font-normal text-slate-500">· {rule.description}</span>
            </CardTitle>
            <CardDescription className="mt-1 text-slate-600">
              {rule.condition_summary}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={rule.enabled ? 'success' : 'warning'}>{rule.enabled ? '已启用' : '已停用'}</Badge>
            {!productMode ? <Badge variant="info">优先级 {rule.priority}</Badge> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="default">{rule.category}</Badge>
          {rule.signals.map((signal) => (
            <Badge key={signal} variant="info">
              {signal}
            </Badge>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">条件</p>
          <div className="mt-3 space-y-2">
            {rule.conditions.map((condition) => (
              <div key={`${rule.label}-${condition.field}-${condition.op}-${String(condition.value)}`} className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                <p className="text-sm font-medium text-slate-950">{formatConditionExpression(condition)}</p>
                {!productMode ? (
                  <p className="mt-1 text-xs text-slate-500">
                    字段 {condition.field} · 操作 {condition.op} · 值 {String(condition.value)}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function BehaviorRulesPanel({ productMode = false }: { productMode?: boolean }) {
  const query = useQuery({
    queryKey: ['persona', 'behavior-rules'],
    queryFn: () => listBehaviorRules(),
    staleTime: 300_000,
  });
  const payload = query.data;
  const groupedRules = useMemo<BehaviorRuleGroup[]>(() => {
    if (!payload) return [];

    return payload.rules.reduce<BehaviorRuleGroup[]>((groups, rule) => {
      const existing = groups.find((group) => group.name === rule.category);
      if (existing) {
        existing.rules.push(rule);
        if (rule.enabled) existing.enabledCount += 1;
        return groups;
      }

      groups.push({
        name: rule.category,
        rules: [rule],
        enabledCount: rule.enabled ? 1 : 0,
      });
      return groups;
    }, []);
  }, [payload]);

  if (query.isLoading) {
    return (
      <LoadingState
        label="正在加载行为规则"
        description={productMode ? '正在读取已保存的行为规则。' : '正在读取只读规则文件并整理成预览结构。'}
      />
    );
  }

  if (query.error || !payload) {
    return (
      <ErrorState
        category="config missing"
        title="行为规则加载失败"
        description={getErrorMessage(query.error)}
        suggestion={productMode ? '请稍后重试；如持续失败，请联系管理员检查规则数据。' : '检查规则文件是否存在，或直接切换回上方的交易风格样例继续使用其他能力。'}
        actions={productMode ? undefined : [{ label: '返回作者画像', to: '/authors' }]}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  if (payload.rules.length === 0) {
    return (
      <EmptyState
        title="暂无行为规则"
        description={productMode ? '当前没有可展示的行为规则。' : '当前规则文件没有可展示的规则。请检查 config/rules/behavior_rules.yaml 是否已正确配置。'}
      />
    );
  }

  return (
    <section className="space-y-4">
      <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <Badge variant="info">只读预览</Badge>
              <CardTitle className="mt-3 text-slate-950">{payload.title}</CardTitle>
              <CardDescription className="mt-2 text-slate-600">{payload.description}</CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              {!productMode ? <Badge variant="default">schema {payload.schema_version}</Badge> : null}
              <Badge variant="success">{payload.rule_count} 条规则</Badge>
              <Badge variant="info">{payload.enabled_rule_count} 条启用</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <SummaryCard title="规则总数" value={payload.rule_count} note="按文件顺序展示。数值越大的优先级越靠前。" />
            <SummaryCard title="启用规则" value={payload.enabled_rule_count} note="停用规则只会在文件里保留，不参与命中。" />
            <SummaryCard title="规则分类" value={payload.category_count} note="按业务语义分组，便于理解和维护。" />
            {!productMode ? <SummaryCard title="来源文件" value={payload.source_path} note="当前页面只读，不支持在线编辑。" /> : null}
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">分类概览</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {payload.categories.map((category) => (
                <Badge key={category.name} variant="default">
                  {category.name} · {category.rule_count} 条
                </Badge>
              ))}
            </div>
          </div>
          {!productMode ? (
            <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm leading-6 text-sky-800">
              <p className="font-medium">说明</p>
              <p className="mt-1">
                规则引擎仍然按文件顺序做第一次命中；`priority` 主要用于展示和维护理解。这个页面用来解释“为什么会命中这个标签”，不承担在线编辑。
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="space-y-6">
        {groupedRules.map((group) => (
          <SectionCard
            key={group.name}
            title={`${group.name}（${group.rules.length} 条）`}
            description={`启用 ${group.enabledCount} 条 · 仅展示，只读不编辑`}
          >
            <div className="grid gap-4 xl:grid-cols-2">
              {group.rules.map((rule) => (
                <RuleCard key={rule.id} rule={rule} productMode={productMode} />
              ))}
            </div>
          </SectionCard>
        ))}
      </div>
    </section>
  );
}

export function PersonaPage({ productMode = false }: { productMode?: boolean } = {}) {
  const navigate = useNavigate();

  if (productMode) {
    return <BehaviorRulesPanel productMode />;
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="画像"
        title="交易风格画像"
        description="查看交易风格样例和行为规则，了解系统如何归纳交易者风格。"
        actionLabel="返回首页"
        onAction={() => navigate('/authors')}
      />

      <Tabs className="space-y-4" defaultValue="clusters">
        <TabsList className="flex w-fit gap-1 rounded-2xl border border-slate-200 bg-white p-1 shadow-sm shadow-slate-200/40">
          <TabsTrigger value="clusters">交易风格样例</TabsTrigger>
          <TabsTrigger value="rules">行为规则</TabsTrigger>
        </TabsList>

        <TabsContent value="clusters" className="mt-0">
          <PersonaCenter />
        </TabsContent>

        <TabsContent value="rules" className="mt-0">
          <BehaviorRulesPanel />
        </TabsContent>
      </Tabs>
    </main>
  );
}
