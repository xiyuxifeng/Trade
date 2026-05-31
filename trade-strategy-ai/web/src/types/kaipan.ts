export type KaipanFetchRequest = {
  profile_id?: string | null;
  trade_date?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  slot?: string;
};

export type KaipanFetchResponse = {
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  base_dir: string;
  trade_date: string;
  slots: string[];
  slot_results: Record<string, Record<string, unknown>>;
  normalize_results: unknown;
};

export type KaipanStatusResponse = {
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  base_dir: string;
  raw_base: string;
  latest_slot: string | null;
  scheduler_started?: boolean;
  scheduler_pre_market?: string | null;
  scheduler_post_close?: string | null;
};

export type KaipanNormalizeRequest = {
  profile_id?: string | null;
  trade_date?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  slot?: string;
};

export type KaipanNormalizeResponse = {
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  base_dir: string;
  trade_date: string;
  slots: string[];
  results: unknown;
};

export type KaipanRunRequest = {
  profile_id?: string | null;
  start_scheduler?: boolean;
  block?: boolean;
};

export type KaipanRunResponse = {
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  base_dir: string;
  pre_market: string;
  post_close: string;
  started?: boolean;
  scheduler_started?: boolean;
};

export type KaipanStopResponse = {
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  base_dir: string;
  started: boolean;
  pre_market?: string | null;
  post_close?: string | null;
};
