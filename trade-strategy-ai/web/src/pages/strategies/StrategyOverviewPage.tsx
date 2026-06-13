import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { CandidatesPage } from '@/pages/backtest/CandidatesPage';

type FormalPageProps = {
  availability?: PageAvailability;
};

export function StrategyOverviewPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="策略中心"
      queryState={state}
      purpose="查看候选调整并进入策略验证，避免把每日结果直接覆盖为正式策略。"
      inputDescription="输入来自已审核规则、回测证据和当前候选版本。"
      processingDescription="系统复用现有候选能力；发布、回滚和正式版本化仍待后续任务。"
      outputDescription="正式策略版本尚未建立；当前输出只代表真实候选能力。"
      businessAction={{ label: '查看候选版本', to: '/strategies/candidates' }}
      result={availability ? undefined : (
        <div className="space-y-4">
          <p>正式策略版本尚未建立，以下内容来自现有真实候选版本。</p>
          <CandidatesPage productMode />
        </div>
      )}
    />
  );
}

export function StrategyCandidatesPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="候选版本"
      queryState={state}
      purpose="查看真实候选版本并核对其来源规则和调整建议。"
      inputDescription="输入来自已经保存的规则版本和候选调整。"
      processingDescription="系统读取现有候选数据，不生成不存在的正式策略。"
      outputDescription="输出为当前真实候选版本及其审核入口。"
      businessAction={{ label: '进入今日盘前', to: '/daily/pre-market' }}
      result={availability ? undefined : <CandidatesPage productMode />}
    />
  );
}
