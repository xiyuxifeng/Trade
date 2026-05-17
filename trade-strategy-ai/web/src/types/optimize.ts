import type {
  ActiveTraderFilterRequest,
  CandidateCreateRequest,
  CandidateCreateResponse,
  RuleValidationItem,
  StrategyVersionDetailItem,
  StrategyVersionDetailResponse,
  StrategyVersionListResponse,
  StrategyVersionSummaryItem,
} from '@/types/strategyStudio';

export type OptimizeVersionQuery = {
  trader_id?: string;
  status?: string;
  version_type?: string;
  date_from?: string;
  date_to?: string;
  skip?: number;
  limit?: number;
};

export type OptimizeVersionSummaryItem = StrategyVersionSummaryItem;
export type OptimizeVersionDetailItem = StrategyVersionDetailItem;
export type OptimizeVersionListResponse = StrategyVersionListResponse;
export type OptimizeVersionDetailResponse = StrategyVersionDetailResponse;
export type OptimizeRuleValidationItem = RuleValidationItem;
export type OptimizeActiveTraderFilterRequest = ActiveTraderFilterRequest;
export type OptimizeCandidateCreateRequest = CandidateCreateRequest;
export type OptimizeCandidateCreateResponse = CandidateCreateResponse;

