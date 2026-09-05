export type Direction = "bullish" | "bearish" | "neutral";
export type Classification = "exceptional" | "strong" | "good" | "watch" | "ignore";
export type SignalStatus =
  | "active"
  | "hit_target1"
  | "hit_target2"
  | "hit_target3"
  | "hit_stop"
  | "expired"
  | "suppressed";

export interface Confirmation {
  label: string;
  passed: boolean;
  detail: string;
}

export interface SignalListItem {
  id: number;
  symbol: string;
  timeframe: string;
  pattern_name: string;
  direction: Direction;
  detected_at: string;
  quality_score: number;
  classification: Classification;
  status: SignalStatus;
  current_price: number;
  entry_price: number;
}

export interface SignalDetail extends SignalListItem {
  pattern_key: string;
  candle_timestamp: string;
  score_breakdown: Record<string, number | Record<string, number>>;
  stop_loss: number;
  target_1: number;
  target_2: number;
  target_3: number;
  risk_per_share: number;
  reward_to_t1: number;
  reward_to_t2: number;
  reward_to_t3: number;
  rr_t1: number;
  rr_t2: number;
  rr_t3: number;
  risk_methodology: string;
  technical_confirmations: Confirmation[];
  news_context: { status: string; reason: string; items: any[] };
  market_context: { regime: string; spy_trend: string; sector: string; sector_trend: string };
  explanation: string;
}

export interface WatchlistItem {
  id: number;
  symbol: string;
  market: string;
  enabled: boolean;
  timeframes: string[] | null;
  min_score_override: number | null;
  enabled_patterns: string[] | null;
  notification_channels: string[] | null;
}

export interface PatternInfo {
  key: string;
  display_name: string;
  direction: Direction;
}

export interface ScoringWeights {
  pattern: number;
  trend: number;
  volume: number;
  support_resistance: number;
  momentum: number;
  risk_reward: number;
  news: number;
  macro: number;
  sector: number;
}

export interface ScoreThresholds {
  exceptional: number;
  strong: number;
  good: number;
  watch: number;
}

export interface RiskPolicy {
  suppress_on_critical_conflict: boolean;
  min_risk_reward_t1: number;
}

export interface ScoringConfig {
  weights: ScoringWeights;
  thresholds: ScoreThresholds;
  risk_policy: RiskPolicy;
  min_signal_score: number;
}

export interface NotificationPreference {
  channel: string;
  enabled: boolean;
  config: Record<string, unknown> | null;
}

export interface SystemStatus {
  app_name: string;
  environment: string;
  polling_enabled: boolean;
  market_data_provider: string;
  news_provider: string;
  supported_timeframes: string[];
  active_watchlist_symbols: number;
  market_status: string;
  latest_signal_at: string | null;
  server_time_utc: string;
}
