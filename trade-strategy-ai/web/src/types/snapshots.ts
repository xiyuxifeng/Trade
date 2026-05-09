export type SnapshotType = 'hot_topics' | 'topic_constituents' | 'strong_symbols' | 'market_universe';

export type SnapshotSummaryItem = {
  snapshot_id: string;
  trade_date: string;
  slot: string;
  type: SnapshotType;
};

export type SnapshotListResponse = {
  count: number;
  total: number;
  skip: number;
  limit: number;
  items: SnapshotSummaryItem[];
};

export type HotTopicItem = {
  kind: string;
  topic_id: string;
  topic_name: string;
  score: number | null;
  increase_pct: number | null;
  speed_pct: number | null;
  turnover: number | null;
  net_inflow: number | null;
};

export type TopicConstituentItem = {
  kind: string;
  topic_id: string | null;
  topic_name: string | null;
  symbol: string | null;
  name: string | null;
  topic_change_pct: number | null;
  leader_symbol: string | null;
  leader_name: string | null;
  leader_change_pct: number | null;
  board_num: number | null;
  net_buy: number | null;
  brief_intro: string | null;
};

export type StrongSymbolItem = {
  kind: string;
  symbol: string | null;
  name: string | null;
  strength_score: number | null;
  change_pct: number | null;
  turnover: number | null;
  turnover_ratio: number | null;
  return_pct: number | null;
  net_inflow: number | null;
  main_force_buy: number | null;
  main_force_sell: number | null;
  rt_change_pct: number | null;
  bid_net: number | null;
  bid_turnover: number | null;
  topic_tags: string | null;
};

export type SnapshotDetail = {
  trade_date: string;
  slot: string;
  fetched_at: string | null;
  hot_topics: {
    trade_date: string;
    slot: string;
    topics: HotTopicItem[];
    sources: string[];
    fetched_at: string | null;
  } | null;
  topic_constituents: {
    trade_date: string;
    slot: string;
    constituents: TopicConstituentItem[];
    sources: string[];
    fetched_at: string | null;
  } | null;
  strong_symbols: {
    trade_date: string;
    slot: string;
    symbols: StrongSymbolItem[];
    sources: string[];
    fetched_at: string | null;
  } | null;
  metadata: Record<string, unknown>;
};

export type SnapshotDetailResponse = {
  item: SnapshotDetail;
};
