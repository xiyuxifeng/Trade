export type ProfileValidationStatus = 'draft' | 'validated' | 'invalid_config' | 'archived' | string;

export type ProfileSectionMap = Record<string, unknown>;

export type ProfileRecord = {
  profile_id: string;
  name: string;
  environment: string;
  version: number;
  sections: ProfileSectionMap;
  secret_refs: Record<string, unknown>;
  validation_status: ProfileValidationStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type ProfileListResponse = {
  count: number;
  total: number;
  skip: number;
  limit: number;
  items: ProfileRecord[];
};

export type ProfileLinkedJob = {
  job_id: string;
  job_type: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ProfileSnapshotRecord = {
  snapshot_id: string;
  profile_id: string;
  job_id: string | null;
  source: string;
  config_path: string;
  config_hash: string;
  masked_snapshot: Record<string, unknown>;
  masked_sections: string[];
  validation_status: ProfileValidationStatus;
  captured_at: string;
  snapshot_path: string;
};

export type ProfileDetailResponse = {
  profile: ProfileRecord;
  linked_jobs: ProfileLinkedJob[];
  snapshots: ProfileSnapshotRecord[];
};

export type ProfileImportRequest = {
  profile_id: string;
  config_path: string;
  created_by?: string;
};

export type ProfileImportResponse = {
  created: boolean;
  profile: ProfileRecord;
  snapshot: ProfileSnapshotRecord | null;
};

export type ProfileSnapshotResponse = {
  profile: ProfileRecord;
  snapshot: ProfileSnapshotRecord;
  linked_job: ProfileLinkedJob | null;
};
