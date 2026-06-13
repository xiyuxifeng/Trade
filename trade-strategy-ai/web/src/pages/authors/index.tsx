import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { PersonaPage } from '@/pages/persona';

type AuthorsPageProps = {
  availability?: PageAvailability;
};

export function AuthorsPage({ availability }: AuthorsPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="作者画像"
      queryState={state}
      purpose="汇总作者文章表达的方法、规则证据和验证观察。"
      inputDescription="输入来自已确认文章、规则证据和回测观察。"
      processingDescription="系统保留文章声明、模型推断、程序统计和人工批准的来源区别。"
      outputDescription="正式三层画像尚未建立；当前仅提供现有画像能力和明确边界。"
      businessAction={{ label: '进入策略中心', to: '/strategies' }}
      result={availability ? undefined : (
        <div className="space-y-4">
          <p>正式三层画像尚未建立，以下内容来自现有真实画像规则能力。</p>
          <PersonaPage productMode />
        </div>
      )}
    />
  );
}
