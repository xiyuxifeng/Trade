export type ImportTradeLogsRequest = {
  file: File;
  dryRun: boolean;
  source?: string;
};

export type ImportTradeLogsResponse = {
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  base_dir: string;
  csv_path: string;
  file_kind: string;
  source: string;
  rows_seen: number;
  invalid: number;
  duplicates: number;
  issues: Array<Record<string, unknown>>;
  parsed_count: number;
  stored_count: number;
  dry_run: boolean;
};

export type MigrateCrawlStateRequest = Record<string, never>;

export type MigrateCrawlStateResponse = {
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  base_dir: string;
  migrated: number;
  skipped: number;
  results: Array<Record<string, unknown>>;
};
