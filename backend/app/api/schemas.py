from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import (
    CandidateStock,
    MarketDataProvenance,
    RiskProfile,
    RiskMode,
    ScreenedOutStock,
    ScreeningRule,
)


PlanCode = Literal["free", "pro"]


class ScreeningRuleRequest(BaseModel):
    name: str = "13:00 盤中篩選"
    min_pct_change: float = 3.0
    max_pct_change: float = 5.0
    min_volume_intensity: float = 1.0
    min_turnover_rate: float = 5.0
    max_turnover_rate: float = 10.0
    min_market_cap_billion: float = 200.0
    max_market_cap_billion: float = 1000.0
    limit_up_lookback_days: int = 20
    min_vwap_above_ratio: float = Field(default=0.80, ge=0, le=1)
    vwap_reclaim_bars: int = 3
    vwap_tolerance_pct: float = 0.2
    notification_time: time = time(hour=13, minute=0)
    enabled: bool = True

    def to_domain(self, rule_id: str) -> ScreeningRule:
        return ScreeningRule(id=rule_id, **self.model_dump())


class ScreeningRulePatch(BaseModel):
    name: str | None = None
    min_pct_change: float | None = None
    max_pct_change: float | None = None
    min_volume_intensity: float | None = None
    min_turnover_rate: float | None = None
    max_turnover_rate: float | None = None
    min_market_cap_billion: float | None = None
    max_market_cap_billion: float | None = None
    limit_up_lookback_days: int | None = None
    min_vwap_above_ratio: float | None = Field(default=None, ge=0, le=1)
    vwap_reclaim_bars: int | None = None
    vwap_tolerance_pct: float | None = None
    notification_time: time | None = None
    enabled: bool | None = None


class ScreeningRuleResponse(BaseModel):
    id: str
    name: str
    min_pct_change: float
    max_pct_change: float
    min_volume_intensity: float
    min_turnover_rate: float
    max_turnover_rate: float
    min_market_cap_billion: float
    max_market_cap_billion: float
    limit_up_lookback_days: int
    min_vwap_above_ratio: float
    vwap_reclaim_bars: int
    vwap_tolerance_pct: float
    notification_time: time
    enabled: bool

    model_config = ConfigDict(from_attributes=True)


class RiskProfilePatch(BaseModel):
    name: str | None = None
    mode: RiskMode | None = None
    account_capital_twd: int | None = Field(default=None, ge=1)
    max_trade_risk_pct: float | None = Field(default=None, ge=0.01, le=10)
    max_daily_risk_pct: float | None = Field(default=None, ge=0.01, le=20)
    max_holdings: int | None = Field(default=None, ge=1, le=50)
    min_liquidity_twd_million: float | None = Field(default=None, ge=0)
    slippage_buffer_pct: float | None = Field(default=None, ge=0, le=5)
    lot_size: int | None = Field(default=None, ge=1)


class RiskProfileResponse(BaseModel):
    id: str
    name: str
    mode: RiskMode
    account_capital_twd: int
    max_trade_risk_pct: float
    max_daily_risk_pct: float
    max_holdings: int
    min_liquidity_twd_million: float
    slippage_buffer_pct: float
    lot_size: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, profile: RiskProfile) -> "RiskProfileResponse":
        return cls.model_validate(profile)


class CandidateStockResponse(BaseModel):
    symbol: str
    name: str
    match_score: float
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
    risk_level: str
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

    @classmethod
    def from_domain(cls, candidate: CandidateStock, plan: PlanCode, index: int) -> "CandidateStockResponse":
        payload = asdict(candidate)
        payload["match_score"] = payload.pop("score")
        if plan == "free" and index >= 2:
            payload.update(
                {
                    "symbol": f"{candidate.symbol[:2]}**",
                    "name": "付費版揭露",
                    "reasons": ["升級後可查看完整入選原因"],
                    "risk_notes": ["升級後可查看完整風控註記"],
                    "risk_flags": ["masked"],
                    "warnings": [],
                    "masked": True,
                }
            )
        return cls(**payload)


class ScreenedOutStockResponse(BaseModel):
    symbol: str
    name: str
    primary_reason: str
    failed_conditions: list[str]
    pct_change: float
    volume_intensity: float
    turnover_rate: float
    market_cap_billion: float

    @classmethod
    def from_domain(cls, stock: ScreenedOutStock) -> "ScreenedOutStockResponse":
        return cls(**asdict(stock))


class MarketDataProvenanceResponse(BaseModel):
    ingestion_batch_id: str
    provider: str
    mode: str
    license_status: str
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

    @classmethod
    def from_domain(cls, provenance: MarketDataProvenance) -> "MarketDataProvenanceResponse":
        return cls(**asdict(provenance))


class ScreeningRunResponse(BaseModel):
    id: str
    rule_id: str
    run_date: date
    status: str
    data_version: str
    started_at: datetime
    rule_snapshot: dict[str, object]
    risk_profile_snapshot: dict[str, object]
    input_snapshot_hash: str
    universe_hash: str
    risk_profile_hash: str
    score_formula_version: str
    completed_at: datetime | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TodayRunsResponse(BaseModel):
    plan: PlanCode
    run: ScreeningRunResponse
    rule: ScreeningRuleResponse
    risk_profile: RiskProfileResponse
    provenance: MarketDataProvenanceResponse | None
    candidates: list[CandidateStockResponse]
    exclusions_preview: list[ScreenedOutStockResponse]
    exclusions_count: int
    upgrade: dict[str, str]
    compliance_notice: str
    risk_notice: str
    data_notice: str


class DataStatusResponse(BaseModel):
    provider: str
    mode: str
    license_status: str
    can_redistribute: bool
    next_gate: str
    usage_notice: str


class BacktestRequest(BaseModel):
    rule_id: str = "default-rule"
    trading_days: int = Field(default=60, ge=20, le=250)


class BacktestRow(BaseModel):
    window: str
    sample_days: int
    candidate_days: int
    median_next_day_range_pct: float
    max_adverse_excursion_pct: float
    empty_day_ratio: float


class ForwardReturnRow(BaseModel):
    symbol: str
    name: str
    run_date: date
    window: str
    open_return_pct: float
    high_return_pct: float
    low_return_pct: float
    close_return_pct: float
    mae_pct: float
    mfe_pct: float
    assumed_cost_pct: float


class BacktestDailyCandidate(BaseModel):
    run_date: date
    data_version: str
    rule_snapshot_hash: str
    candidate_count: int
    excluded_count: int
    candidates: list[ForwardReturnRow]


class BacktestResponse(BaseModel):
    rule_id: str
    data_mode: str
    trading_days: int
    methodology_notice: str
    rows: list[BacktestRow]
    daily: list[BacktestDailyCandidate]


class NotificationTestRequest(BaseModel):
    channel: Literal["email", "line", "web_push"]
    destination: str


class NotificationTestResponse(BaseModel):
    channel: str
    delivered: bool
    message: str


class CheckoutRequest(BaseModel):
    plan: Literal["pro_monthly", "pro_yearly"] = "pro_monthly"


class CheckoutResponse(BaseModel):
    id: str
    plan: str
    amount_twd: int
    checkout_url: str
    provider: str
    sandbox: bool
