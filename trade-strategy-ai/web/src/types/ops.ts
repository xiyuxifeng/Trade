export type RecoveryBackupItem = {
  path: string;
  name: string;
  size_bytes: number;
  modified_at: string;
  tables: string[];
  row_counts: Record<string, number>;
  include_processed: boolean;
  processed_copied: boolean;
  artifacts_copied?: boolean;
};

export type RecoveryBackupsResponse = {
  base_dir: string;
  backup_root: string;
  count: number;
  items: RecoveryBackupItem[];
};

export type RecoveryBackupRequest = {
  backup_dir?: string;
  include_processed?: boolean;
};

export type RecoveryBackupResponse = {
  backup_dir: string;
  tables: string[];
  row_counts: Record<string, number>;
  include_processed: boolean;
  processed_copied: boolean;
  artifacts_copied?: boolean;
  backup_item?: RecoveryBackupItem | null;
};

export type RecoveryRestoreRequest = {
  backup_path: string;
  include_processed?: boolean;
  confirmed: boolean;
};

export type RecoveryRestoreResponse = {
  backup_dir: string;
  tables: string[];
  row_counts: Record<string, number>;
  include_processed: boolean;
  processed_restored: boolean;
  artifacts_restored?: boolean;
  backup_item?: RecoveryBackupItem | null;
};

export type RecoveryStaleRequest = {
  stale_before_minutes?: number;
};

export type RecoveryStaleResponse = {
  count: number;
  job_ids: string[];
  stale_before: string;
  stale_before_minutes: number;
};
