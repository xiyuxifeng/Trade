export type TraderOptionsSource = 'all' | 'strategy' | 'backtest';

export type TraderOptionsResponse = {
  status: string;
  count: number;
  items: string[];
};
