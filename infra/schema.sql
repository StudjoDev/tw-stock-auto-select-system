CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  plan TEXT NOT NULL DEFAULT 'free',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS screening_rules (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  name TEXT NOT NULL,
  min_pct_change NUMERIC(6, 2) NOT NULL,
  max_pct_change NUMERIC(6, 2) NOT NULL,
  min_volume_intensity NUMERIC(8, 2) NOT NULL,
  min_turnover_rate NUMERIC(6, 2) NOT NULL,
  max_turnover_rate NUMERIC(6, 2) NOT NULL,
  min_market_cap_billion NUMERIC(10, 2) NOT NULL,
  max_market_cap_billion NUMERIC(10, 2) NOT NULL,
  limit_up_lookback_days INTEGER NOT NULL,
  min_vwap_above_ratio NUMERIC(5, 2) NOT NULL,
  vwap_reclaim_bars INTEGER NOT NULL,
  vwap_tolerance_pct NUMERIC(6, 3) NOT NULL,
  notification_time TIME NOT NULL DEFAULT '13:00:00',
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS risk_profiles (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  name TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'balanced',
  account_capital_twd INTEGER NOT NULL,
  max_trade_risk_pct NUMERIC(8, 3) NOT NULL,
  max_daily_risk_pct NUMERIC(8, 3) NOT NULL,
  max_holdings INTEGER NOT NULL,
  min_liquidity_twd_million NUMERIC(12, 3) NOT NULL,
  slippage_buffer_pct NUMERIC(8, 3) NOT NULL,
  lot_size INTEGER NOT NULL DEFAULT 1000,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS market_data_batches (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  mode TEXT NOT NULL,
  license_status TEXT NOT NULL,
  can_redistribute BOOLEAN NOT NULL,
  cutoff_time TIMESTAMPTZ NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL,
  data_version TEXT NOT NULL,
  raw_snapshot_hash TEXT NOT NULL,
  raw_storage_pointer TEXT NOT NULL,
  provider_version TEXT NOT NULL,
  corporate_action_version TEXT NOT NULL,
  calendar_version TEXT NOT NULL,
  symbol_universe_hash TEXT NOT NULL,
  bar_interval TEXT NOT NULL,
  usage_notice TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rule_snapshots (
  id UUID PRIMARY KEY,
  rule_id UUID REFERENCES screening_rules(id),
  rule_snapshot JSONB NOT NULL,
  rule_snapshot_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS intraday_bars (
  symbol TEXT NOT NULL,
  traded_at TIMESTAMPTZ NOT NULL,
  open_price NUMERIC(12, 4) NOT NULL,
  high_price NUMERIC(12, 4) NOT NULL,
  low_price NUMERIC(12, 4) NOT NULL,
  close_price NUMERIC(12, 4) NOT NULL,
  volume INTEGER NOT NULL,
  turnover NUMERIC(18, 2) NOT NULL,
  PRIMARY KEY (symbol, traded_at)
);

SELECT create_hypertable('intraday_bars', 'traded_at', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS screening_runs (
  id UUID PRIMARY KEY,
  rule_id UUID REFERENCES screening_rules(id),
  rule_snapshot JSONB NOT NULL DEFAULT '{}',
  input_snapshot_hash TEXT NOT NULL DEFAULT '',
  universe_hash TEXT NOT NULL DEFAULT '',
  score_formula_version TEXT NOT NULL DEFAULT 'match-score-v1',
  market_data_batch_id TEXT REFERENCES market_data_batches(id),
  run_date DATE NOT NULL,
  status TEXT NOT NULL,
  data_version TEXT NOT NULL,
  risk_profile_snapshot JSONB NOT NULL DEFAULT '{}',
  risk_profile_hash TEXT NOT NULL DEFAULT '',
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS candidate_stocks (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES screening_runs(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  name TEXT NOT NULL,
  score NUMERIC(8, 2) NOT NULL,
  reference_price NUMERIC(12, 4) NOT NULL DEFAULT 0,
  pct_change NUMERIC(6, 2) NOT NULL,
  volume_intensity NUMERIC(8, 2) NOT NULL,
  turnover_rate NUMERIC(6, 2) NOT NULL,
  market_cap_billion NUMERIC(10, 2) NOT NULL,
  had_limit_up_recently BOOLEAN NOT NULL,
  vwap_above_ratio NUMERIC(5, 2) NOT NULL,
  vwap_reclaimed_within_bars BOOLEAN NOT NULL,
  vwap_breach_count INTEGER NOT NULL DEFAULT 0,
  vwap_worst_distance_pct NUMERIC(8, 3) NOT NULL DEFAULT 0,
  risk_level TEXT NOT NULL DEFAULT 'low',
  risk_notes JSONB NOT NULL DEFAULT '[]',
  risk_flags JSONB NOT NULL DEFAULT '[]',
  liquidity_twd_million NUMERIC(12, 3) NOT NULL DEFAULT 0,
  distance_to_limit_up_pct NUMERIC(8, 3) NOT NULL DEFAULT 0,
  intraday_pullback_pct NUMERIC(8, 3) NOT NULL DEFAULT 0,
  late_session_change_pct NUMERIC(8, 3) NOT NULL DEFAULT 0,
  stop_loss_reference_pct NUMERIC(8, 3) NOT NULL DEFAULT 0,
  max_position_pct NUMERIC(8, 3) NOT NULL DEFAULT 0,
  reasons JSONB NOT NULL DEFAULT '[]',
  warnings JSONB NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS candidate_stocks_run_score_idx
  ON candidate_stocks (run_id, score DESC);

CREATE TABLE IF NOT EXISTS screened_out_stocks (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES screening_runs(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  name TEXT NOT NULL,
  primary_reason TEXT NOT NULL,
  failed_conditions JSONB NOT NULL DEFAULT '[]',
  pct_change NUMERIC(8, 3) NOT NULL,
  volume_intensity NUMERIC(8, 3) NOT NULL,
  turnover_rate NUMERIC(8, 3) NOT NULL,
  market_cap_billion NUMERIC(12, 3) NOT NULL
);

CREATE TABLE IF NOT EXISTS backtest_runs (
  id UUID PRIMARY KEY,
  rule_snapshot_id UUID REFERENCES rule_snapshots(id),
  trading_days INTEGER NOT NULL,
  data_mode TEXT NOT NULL,
  methodology_notice TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backtest_daily_candidates (
  id UUID PRIMARY KEY,
  backtest_run_id UUID REFERENCES backtest_runs(id) ON DELETE CASCADE,
  run_date DATE NOT NULL,
  data_version TEXT NOT NULL,
  rule_snapshot_hash TEXT NOT NULL,
  candidate_count INTEGER NOT NULL,
  excluded_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS forward_returns (
  id UUID PRIMARY KEY,
  backtest_daily_candidate_id UUID REFERENCES backtest_daily_candidates(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  name TEXT NOT NULL,
  window TEXT NOT NULL,
  open_return_pct NUMERIC(8, 3) NOT NULL,
  high_return_pct NUMERIC(8, 3) NOT NULL,
  low_return_pct NUMERIC(8, 3) NOT NULL,
  close_return_pct NUMERIC(8, 3) NOT NULL,
  mae_pct NUMERIC(8, 3) NOT NULL,
  mfe_pct NUMERIC(8, 3) NOT NULL,
  assumed_cost_pct NUMERIC(8, 3) NOT NULL
);
