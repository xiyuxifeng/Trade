import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { BacktestPage } from '@/pages/backtest';
import { RegimeBacktestReportPage } from '@/pages/backtest/RegimeBacktestReportPage';
import { RulePoolPage } from '@/pages/rule-pool';

type FormalPageProps = {
  availability?: PageAvailability;
};

export function RulesReviewPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="待审核规则"
      queryState={state}
      purpose="确认文章提取出的候选规则是否可以进入后续验证。"
      inputDescription="输入来自文章提取结果和当前规则证据。"
      processingDescription="系统读取真实候选规则、证据和审核状态。"
      outputDescription="输出为已确认的审核决定和后续验证入口。"
      businessAction={{ label: '开始回测', to: '/rules/backtests' }}
      result={availability ? undefined : <RulePoolPage productMode />}
    />
  );
}

export function RulesLibraryPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="正式规则"
      queryState={state}
      purpose="查看已经通过人工审核的规则，并说明当前版本化边界。"
      inputDescription="输入来自现有规则库中的真实审核状态。"
      processingDescription="系统按真实审核结果展示规则，不推断尚未建立的正式版本。"
      outputDescription="当前输出为已审核规则；完整规则版本能力仍待后续任务建立。"
      businessAction={{ label: '查看待审核规则', to: '/rules/review' }}
      result={availability ? undefined : <RulePoolPage productMode />}
    />
  );
}

export function RulesBacktestsPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="回测实验"
      queryState={state}
      purpose="使用固定历史数据验证规则表现，并保留真实运行结果。"
      inputDescription="选择已有规则、日期范围、基准和可用数据。"
      processingDescription="系统使用现有回测能力提交验证并读取真实结果。"
      outputDescription="输出为全周期回测结果和当前可用的验证证据。"
      businessAction={{ label: '查看作者画像', to: '/authors' }}
      result={availability ? undefined : <BacktestPage productMode />}
    />
  );
}

export function RulesResultsPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="回测结果"
      queryState={state}
      purpose="查看全周期及分市场状态的回测验证结果。"
      inputDescription="输入来自已经完成且可追溯的回测记录。"
      processingDescription="系统只展示已保存的真实结果和明确的数据缺口。"
      outputDescription="输出为现有全周期和分市场状态结果；统一结果契约仍待后续任务建立。"
      businessAction={{ label: '返回回测实验', to: '/rules/backtests' }}
      result={availability ? undefined : <RegimeBacktestReportPage productMode />}
    />
  );
}
