export type SymbolListResponse = {
  count: number;
  items: string[];
};

export type OhlcvRow = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  turnover?: number | null;
};

export type OhlcvResponse = {
  symbol: string;
  start_date: string;
  end_date: string;
  count: number;
  items: OhlcvRow[];
};
