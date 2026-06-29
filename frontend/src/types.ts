export interface TopPick {
  rank: number;
  symbol: string;
  company_name: string;
  score: number;
  close: number;
  sma50: number;
  sma200: number;
  volume_ratio: number;
  pct_from_52w_high: number;
  price_history_30d: number[];
}

export interface ScanResult {
  scan_timestamp: string;
  total_qualified: number;
  picks: TopPick[];
}

export interface BacktestPick {
  rank: number;
  symbol: string;
  company_name: string;
  score: number;
  close: number;
  forward_return_5d: number | null;
  forward_return_10d: number | null;
  forward_return_20d: number | null;
}

export interface BenchmarkReturns {
  return_5d: number | null;
  return_10d: number | null;
  return_20d: number | null;
}

export interface PrecisionRecall {
  precision_5d: number | null;
  precision_10d: number | null;
  precision_20d: number | null;
  recall_5d: number | null;
  recall_10d: number | null;
  recall_20d: number | null;
}

export interface BacktestResult {
  backtest_date: string;
  picks: BacktestPick[];
  benchmark_returns: BenchmarkReturns;
  total_qualified: number;
  precision_recall: PrecisionRecall;
}
