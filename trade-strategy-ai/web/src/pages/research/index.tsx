import { Link } from 'react-router-dom';

import { BusinessPageShell } from '@/components/layout/business-page-shell';
import { ArticleAddPage, ArticleExtractionResultsPage, ArticleLibraryPage } from '@/pages/articles';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { PageAvailability, PageLayoutMode } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';

const navigationTargets = {
  back: '/research',
  library: '/research/articles',
  add: '/research/add',
  results: '/research/results',
} as const;

const researchSections = [
  {
    title: '文章库',
    description: '查看已导入文章，确认来源和筛选范围。',
    href: navigationTargets.library,
    actionLabel: '进入文章库',
  },
  {
    title: '添加文章',
    description: '导入新文章并开始结构化处理。',
    href: navigationTargets.add,
    actionLabel: '开始添加',
  },
  {
    title: '提取结果',
    description: '查看结构化结果并切换当前使用版本。',
    href: navigationTargets.results,
    actionLabel: '查看结果',
  },
] as const;

function ResearchCard({
  title,
  description,
  href,
  actionLabel,
}: {
  title: string;
  description: string;
  href: string;
  actionLabel: string;
}) {
  return (
    <Card className="flex h-full flex-col border-slate-200 bg-white/95 shadow-sm">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="mt-auto">
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800"
          to={href}
        >
          {actionLabel}
        </Link>
      </CardContent>
    </Card>
  );
}

export function ResearchPage() {
  return (
    <main className="page-stack">
      <section className="page-card">
        <p className="page-kicker">正式业务页面</p>
        <h1>研究中心</h1>
        <p className="hero-copy">从文章库开始，逐步完成文章导入和提取结果确认。</p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {researchSections.map((section) => (
          <ResearchCard key={section.title} title={section.title} description={section.description} href={section.href} actionLabel={section.actionLabel} />
        ))}
      </section>
    </main>
  );
}

function ResearchAvailabilityBoundary({
  title,
  availability,
  layoutMode = 'workflow',
}: {
  title: string;
  availability: PageAvailability;
  layoutMode?: PageLayoutMode;
}) {
  return (
    <ProductPageAdapter
      title={title}
      queryState={availability}
      purpose="处理研究文章并保留真实结果。"
      inputDescription="输入来自已有文章和用户选择。"
      processingDescription="系统读取真实研究数据。"
      outputDescription="输出只展示当前可确认的结果。"
      layoutMode={layoutMode}
      showPurposeSection={false}
      businessAction={{ label: '返回研究中心', to: '/research' }}
    />
  );
}

export function ResearchArticlesPage({ availability }: { availability?: PageAvailability } = {}) {
  if (availability) return <ResearchAvailabilityBoundary title="文章库" availability={availability} layoutMode="library" />;
  return <ArticleLibraryPage productMode navigationTargets={navigationTargets} />;
}

export function ResearchAddPage({ availability }: { availability?: PageAvailability } = {}) {
  if (availability) return <ResearchAvailabilityBoundary title="添加文章" availability={availability} layoutMode="workflow" />;
  return <ArticleAddPage productMode navigationTargets={navigationTargets} />;
}

export function ResearchResultsPage({ availability }: { availability?: PageAvailability } = {}) {
  if (availability) {
    return (
      <BusinessPageShell
        title="提取结果"
        purpose="查看文章提取后的分析结果，并在需要时继续人工审核。"
        inputDescription="当前页面不需要额外输入。"
        processingDescription="系统保留真实可用结果，不会用默认值补齐缺失分析。"
        outputDescription="当前页面不再使用单独输出壳层。"
        availability={availability}
        showPurposeSection={false}
        showInputSection={false}
        showProcessingSection={false}
        showOutputSection={false}
        stateTitle={availability === 'partial' ? '部分完成' : undefined}
        stateDescription={availability === 'partial' ? '文章列表可用，但当前选中文章的详细结果还未完全就绪。' : undefined}
        nextAction={{ label: '返回研究中心', to: '/research' }}
      >
        <Card>
          <CardHeader>
            <CardTitle>文章分析与审核</CardTitle>
            <CardDescription>左侧选择文章，右侧查看结构化分析、自动审核和人工审核动作。</CardDescription>
          </CardHeader>
        </Card>
      </BusinessPageShell>
    );
  }
  return <ArticleExtractionResultsPage productMode navigationTargets={navigationTargets} />;
}

export default ResearchPage;
