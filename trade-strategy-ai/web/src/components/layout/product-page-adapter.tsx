import type { ReactNode } from 'react';

import { useAuth } from '@/features/auth/auth-context';
import type { PageAction, PageAvailability, PageLayoutMode, PagePrerequisite } from './business-page-shell';
import { BusinessPageShell } from './business-page-shell';

type ProductPageAdapterProps = {
  title: string;
  queryState: PageAvailability;
  purpose: string;
  inputDescription: string;
  processingDescription: string;
  outputDescription: string;
  layoutMode?: PageLayoutMode;
  showInputSection?: boolean;
  showProcessingSection?: boolean;
  showOutputSection?: boolean;
  businessAction: PageAction;
  result?: ReactNode;
  input?: ReactNode;
  progress?: ReactNode;
  output?: ReactNode;
  help?: ReactNode;
  currentStep?: string;
  prerequisites?: PagePrerequisite[];
  advancedAdminDetails?: ReactNode;
  stateTitle?: string;
  stateDescription?: string;
  impact?: string;
  recoveryAction?: PageAction;
};

export function ProductPageAdapter({
  title,
  queryState,
  purpose,
  inputDescription,
  processingDescription,
  outputDescription,
  layoutMode,
  showInputSection,
  showProcessingSection,
  showOutputSection,
  businessAction,
  result,
  input,
  progress,
  output,
  help,
  currentStep,
  prerequisites,
  advancedAdminDetails,
  stateTitle,
  stateDescription,
  impact,
  recoveryAction,
}: ProductPageAdapterProps) {
  const { canAccess } = useAuth();
  const canViewAdvancedAdminDetails = advancedAdminDetails && canAccess('operator');

  return (
    <BusinessPageShell
      title={title}
      purpose={purpose}
      inputDescription={inputDescription}
      processingDescription={processingDescription}
      outputDescription={outputDescription}
      layoutMode={layoutMode}
      showInputSection={showInputSection}
      showProcessingSection={showProcessingSection}
      showOutputSection={showOutputSection}
      availability={queryState}
      currentStep={currentStep}
      prerequisites={prerequisites}
      stateTitle={stateTitle}
      stateDescription={stateDescription}
      impact={impact}
      recoveryAction={recoveryAction}
      input={input}
      progress={progress}
      output={output ?? result}
      help={help}
      nextAction={businessAction}
    >
      {canViewAdvancedAdminDetails ? (
        <details className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <summary className="cursor-pointer text-sm font-medium text-slate-800">查看运维诊断详情</summary>
          <div className="mt-3 text-sm text-slate-600">{advancedAdminDetails}</div>
        </details>
      ) : null}
    </BusinessPageShell>
  );
}
