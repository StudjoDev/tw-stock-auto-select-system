from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Literal


PlanCode = Literal["free", "pro"]
RunStatus = Literal["pending", "running", "completed", "failed"]
RiskLevel = Literal["low", "medium", "high"]
RiskMode = Literal["conservative", "balanced", "aggressive"]
DataMode = Literal["demo", "licensed", "offline-demo"]
LicenseStatus = Literal["not_licensed", "licensed", "unknown"]


@dataclass(slots=True)
class ScreeningRule:
    id: str
    name: str
    min_pct_change: float = 3.0
    max_pct_change: float = 5.0
    min_volume_intensity: float = 1.0
    min_turnover_rate: float = 5.0
    max_turnover_rate: float = 10.0
    min_market_cap_billion: float = 200.0
    max_market_cap_billion: float = 1000.0
    limit_up_lookback_days: int = 20
    min_vwap_above_ratio: float = 0.80
    vwap_reclaim_bars: int = 3
    vwap_tolerance_pct: float = 0.2
    notification_time: time = time(hour=13, minute=0)
    enabled: bool = True


@dataclass(slots=True)
class RiskProfile:
    id: str
    name: str = "default-risk"
    mode: RiskMode = "balanced"
    account_capital_twd: int = 1_000_000
    max_trade_risk_pct: float = 0.5
    max_daily_risk_pct: float = 1.5
    max_holdings: int = 4
    min_liquidity_twd_million: float = 50.0
    slippage_buffer_pct: float = 0.15
    lot_size: int = 1000


@dataclass(slots=True)
class IntradayBar:
    traded_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    turnover: float


@dataclass(slots=True)
class StockSnapshot:
    symbol: str
    name: str
    previous_close: float
    current_price: float
    intraday_volume: int
    avg_5d_volume: int
    turnover_rate: float
    market_cap_billion: float
    limit_up_dates: list[date]
    bars: list[IntradayBar]
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VwapEvaluation:
    above_ratio: float
    reclaimed_within_bars: bool
    breach_count: int
    worst_distance_pct: float
    reason: str


@dataclass(slots=True)
class CandidateStock:
    symbol: str
    name: str
    score: float
    reference_price: float
    pct_change: float
    volume_intensity: float
    turnover_rate: float
    market_cap_billion: float
    had_limit_up_recently: bool
    vwap_above_ratio: float
    vwap_reclaimed_within_bars: bool
    vwap_breach_count: int
    vwap_worst_distance_pct: float
    risk_level: RiskLevel
    risk_notes: list[str]
    risk_flags: list[str]
    liquidity_twd_million: float
    distance_to_limit_up_pct: float
    intraday_pullback_pct: float
    late_session_change_pct: float
    stop_loss_reference_pct: float
    max_position_pct: float
    reasons: list[str]
    warnings: list[str]
    masked: bool = False


@dataclass(slots=True)
class ScreenedOutStock:
    symbol: str
    name: str
    primary_reason: str
    failed_conditions: list[str]
    pct_change: float
    volume_intensity: float
    turnover_rate: float
    market_cap_billion: float


@dataclass(slots=True)
class ScreeningOutput:
    candidates: list[CandidateStock]
    exclusions: list[ScreenedOutStock]


@dataclass(slots=True)
class MarketDataProvenance:
    ingestion_batch_id: str
    provider: str
    mode: DataMode
    license_status: LicenseStatus
    can_redistribute: bool
    cutoff_time: datetime
    generated_at: datetime
    data_version: str
    raw_snapshot_hash: str
    raw_storage_pointer: str
    provider_version: str
    corporate_action_version: str
    calendar_version: str
    symbol_universe_hash: str
    bar_interval: str
    usage_notice: str


@dataclass(slots=True)
class ScreeningRun:
    id: str
    rule_id: str
    run_date: date
    status: RunStatus
    data_version: str
    started_at: datetime
    rule_snapshot: dict[str, object] = field(default_factory=dict)
    risk_profile_snapshot: dict[str, object] = field(default_factory=dict)
    input_snapshot_hash: str = ""
    universe_hash: str = ""
    risk_profile_hash: str = ""
    score_formula_version: str = "match-score-v1"
    completed_at: datetime | None = None
    error_message: str | None = None
