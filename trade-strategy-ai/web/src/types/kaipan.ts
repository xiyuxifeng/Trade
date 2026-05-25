export type KaipanFetchRequest = {
  trade_date?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  slot?: string;
};

export type KaipanFetchResponse = {
  config_path: string;
  base_dir: string;
  trade_date: string;
  slots: string[];
  slot_results: Record<string, Record<string, unknown>>;
  normalize_results: unknown;
};

export type KaipanStatusResponse = {
  config_path: string;
  base_dir: string;
  raw_base: string;
  latest_slot: string | null;
  scheduler_started?: boolean;
  scheduler_pre_market?: string | null;
  scheduler_post_close?: string | null;
};

export type KaipanNormalizeRequest = {
  trade_date?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  slot?: string;
};

export type KaipanNormalizeResponse = {
  config_path: string;
  base_dir: string;
  trade_date: string;
  slots: string[];
  results: unknown;
};

export type KaipanRunRequest = {
  start_scheduler?: boolean;
  block?: boolean;
};

export type KaipanRunResponse = {
  config_path: string;
  base_dir: string;
  pre_market: string;
  post_close: string;
  started?: boolean;
  scheduler_started?: boolean;
};

export type KaipanStopResponse = {
  config_path: string;
  base_dir: string;
  started: boolean;
  pre_market?: string | null;
  post_close?: string | null;
};
