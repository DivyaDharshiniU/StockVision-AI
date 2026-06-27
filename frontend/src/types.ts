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
