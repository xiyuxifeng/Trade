export type AuthorProfileStatusState =
  | 'ready'
  | 'loading'
  | 'empty'
  | 'error'
  | 'partial'
  | 'permission_denied'
  | 'unavailable'
  | 'draft'
  | 'pending_review'
  | 'published'
  | 'archived';

export type AuthorProfileVersion = {
  author_profile_version_id: string;
  author_profile_id: string;
  author_id: string;
  profile_kind: 'method' | 'rule' | 'validated';
  profile_kind_label: string;
  version_no: number;
  lifecycle_state: string;
  lifecycle_label: string;
  review_status: string;
  status_state: string;
  schema_version: string;
  prompt_version?: string | null;
  evidence_period: { from?: string | null; to?: string | null };
  effective_period: { from?: string | null; to?: string | null };
  source_versions: Record<string, unknown>;
  evidence_fingerprint?: string | null;
  profile_fingerprint?: string | null;
  quality_status: string;
  partial_reasons: string[];
  limitations: string[];
  payload: Record<string, unknown>;
  evidence: Record<string, unknown>;
  source_bindings: Record<string, unknown>;
  supersession: Record<string, unknown>;
  published_at?: string | null;
  archived_at?: string | null;
};

export type AuthorProfileListResponse = {
  state: 'ready' | 'empty' | 'partial';
  items: AuthorProfileVersion[];
  count: number;
};
