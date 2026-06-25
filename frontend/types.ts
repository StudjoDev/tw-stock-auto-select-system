export type PlanCode = "free" | "pro";

export type ScreeningRule = {
  id: string;
  name: string;
  min_pct_change: number;
  max_pct_change: number;
  min_volume_intensity: number;
  min_turnover_rate: number;
  max_turnover_rate: number;
  min_market_cap_billion: number;
  max_market_cap_billion: number;
  limit_up_lookback_days: number;
  min_vwap_above_ratio: number;
  vwap_reclaim_bars: number;
  vwap_tolerance_pct: number;
  notification_time: string;
  enabled: boolean;
};

export type RiskProfile = {
  id: string;
  name: string;
  mode: "conservative" | "balanced" | "aggressive";
  account_capital_twd: number;
  max_trade_risk_pct: number;
  max_daily_risk_pct: number;
  max_holdings: number;
  min_liquidity_twd_million: number;
  slippage_buffer_pct: number;
  lot_size: number;
};

export type CandidateStock = {
  symbol: string;
  name: string;
  match_score: number;
  reference_price: number;
  pct_change: number;
  volume_intensity: number;
  turnover_rate: number;
  market_cap_billion: number;
  had_limit_up_recently: boolean;
  vwap_above_ratio: number;
  vwap_reclaimed_within_bars: boolean;
  vwap_breach_count: number;
  vwap_worst_distance_pct: number;
  risk_level: "low" | "medium" | "high";
  risk_notes: string[];
  risk_flags: string[];
  liquidity_twd_million: number;
  distance_to_limit_up_pct: number;
  intraday_pullback_pct: number;
  late_session_change_pct: number;
  stop_loss_reference_pct: number;
  max_position_pct: number;
  reasons: string[];
  warnings: string[];
  masked: boolean;
};

export type ScreenedOutStock = {
  symbol: string;
  name: string;
  primary_reason: string;
  failed_conditions: string[];
  pct_change: number;
  volume_intensity: number;
  turnover_rate: number;
  market_cap_billion: number;
};

export type MarketDataProvenance = {
  ingestion_batch_id: string;
  provider: string;
  mode: "demo" | "licensed" | "offline-demo";
  license_status: "not_licensed" | "licensed" | "unknown";
  can_redistribute: boolean;
  cutoff_time: string;
  generated_at: string;
  data_version: string;
  raw_snapshot_hash: string;
  raw_storage_pointer: string;
  provider_version: string;
  corporate_action_version: string;
  calendar_version: string;
  symbol_universe_hash: string;
  bar_interval: string;
  usage_notice: string;
};

export type ScreeningRun = {
  id: string;
  rule_id: string;
  run_date: string;
  status: string;
  data_version: string;
  started_at: string;
  rule_snapshot: Record<string, unknown>;
  risk_profile_snapshot: Record<string, unknown>;
  input_snapshot_hash: string;
  universe_hash: string;
  risk_profile_hash: string;
  score_formula_version: string;
  completed_at: string | null;
  error_message: string | null;
};

export type TodayResponse = {
  plan: PlanCode;
  run: ScreeningRun;
  rule: ScreeningRule;
  risk_profile: RiskProfile;
  provenance: MarketDataProvenance | null;
  candidates: CandidateStock[];
  exclusions_preview: ScreenedOutStock[];
  exclusions_count: number;
  upgrade: {
    title: string;
    price: string;
    cta: string;
  };
  compliance_notice: string;
  risk_notice: string;
  data_notice: string;
};

export type BacktestResponse = {
  rule_id: string;
  data_mode: string;
  trading_days: number;
  methodology_notice: string;
  rows: Array<{
    window: string;
    sample_days: number;
    candidate_days: number;
    median_next_day_range_pct: number;
    max_adverse_excursion_pct: number;
    empty_day_ratio: number;
  }>;
  daily: Array<{
    run_date: string;
    data_version: string;
    rule_snapshot_hash: string;
    candidate_count: number;
    excluded_count: number;
    candidates: Array<{
      symbol: string;
      name: string;
      run_date: string;
      window: string;
      open_return_pct: number;
      high_return_pct: number;
      low_return_pct: number;
      close_return_pct: number;
      mae_pct: number;
      mfe_pct: number;
      assumed_cost_pct: number;
    }>;
  }>;
};
