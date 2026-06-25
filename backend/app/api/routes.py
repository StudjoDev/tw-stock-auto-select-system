from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from datetime import date, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import (
    BacktestDailyCandidate,
    BacktestRequest,
    BacktestResponse,
    BacktestRow,
    CandidateStockResponse,
    CheckoutRequest,
    CheckoutResponse,
    DataStatusResponse,
    ForwardReturnRow,
    MarketDataProvenanceResponse,
    NotificationTestRequest,
    NotificationTestResponse,
    PlanCode,
    RiskProfilePatch,
    RiskProfileResponse,
    ScreenedOutStockResponse,
    ScreeningRulePatch,
    ScreeningRuleRequest,
    ScreeningRuleResponse,
    ScreeningRunResponse,
    TodayRunsResponse,
)
from app.config import Settings, get_settings
from app.repositories.memory import MemoryRepository
from app.services.billing import BillingService
from app.services.market_data import get_market_data_provider
from app.services.notifications import NotificationService

router = APIRouter(prefix="/api")
repository = MemoryRepository()
notification_service = NotificationService()
billing_service = BillingService()


def _provider(settings: Settings):
    return get_market_data_provider(settings.market_data_provider)


def _effective_plan(plan: PlanCode, provenance: object | None) -> PlanCode:
    can_access_paid = bool(
        provenance
        and getattr(provenance, "license_status", None) == "licensed"
        and getattr(provenance, "can_redistribute", False)
    )
    return plan if plan == "pro" and can_access_paid else "free"


def _seed_demo_run() -> None:
    if repository.runs:
        return
    settings = get_settings()
    repository.run_screening(_provider(settings))


_seed_demo_run()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/rules/default", response_model=ScreeningRuleResponse)
def get_default_rule() -> ScreeningRuleResponse:
    return ScreeningRuleResponse.model_validate(repository.get_default_rule())


@router.get("/risk-profiles/default", response_model=RiskProfileResponse)
def get_default_risk_profile() -> RiskProfileResponse:
    return RiskProfileResponse.from_domain(repository.get_default_risk_profile())


@router.patch("/risk-profiles/default", response_model=RiskProfileResponse)
def patch_default_risk_profile(payload: RiskProfilePatch) -> RiskProfileResponse:
    values = payload.model_dump(exclude_none=True)
    profile = repository.patch_risk_profile(repository.get_default_risk_profile().id, values)
    return RiskProfileResponse.from_domain(profile)


@router.get("/today/runs", response_model=TodayRunsResponse)
def get_today_runs(
    plan: PlanCode = Query(default="free"),
    settings: Settings = Depends(get_settings),
) -> TodayRunsResponse:
    try:
        run, candidates = repository.latest_run(_provider(settings))
    except LookupError as exc:
        raise HTTPException(status_code=503, detail="No completed screening run is available") from exc
    provenance = repository.provenance_for_run(run.id)
    exclusions = repository.exclusions_for_run(run.id)
    effective_plan = _effective_plan(plan, provenance)
    return TodayRunsResponse(
        plan=effective_plan,
        run=ScreeningRunResponse.model_validate(run),
        rule=ScreeningRuleResponse.model_validate(run.rule_snapshot),
        risk_profile=RiskProfileResponse.model_validate(run.risk_profile_snapshot),
        provenance=MarketDataProvenanceResponse.from_domain(provenance) if provenance else None,
        candidates=[
            CandidateStockResponse.from_domain(candidate, plan=effective_plan, index=index)
            for index, candidate in enumerate(candidates)
        ],
        exclusions_preview=[
            ScreenedOutStockResponse.from_domain(stock) for stock in exclusions[:5]
        ],
        exclusions_count=len(exclusions),
        upgrade={
            "title": "解鎖完整 13:00 名單、策略參數與通知工作流",
            "price": "NT$499/月",
            "cta": "申請付費權限",
        },
        compliance_notice="本服務僅提供條件篩選工具與資料整理，不提供投資建議、績效承諾或自動下單。",
        risk_notice="系統會顯示風險因子、停損參考與部位上限；實際操作仍需使用者自行判斷並控管資金。",
        data_notice=provenance.usage_notice if provenance else "資料來源尚未完成授權檢查。",
    )


@router.get("/runs/{run_id}/candidates", response_model=list[CandidateStockResponse])
def get_run_candidates(
    run_id: str,
    plan: PlanCode = Query(default="free"),
) -> list[CandidateStockResponse]:
    candidates = repository.candidates_for_run(run_id)
    if not candidates:
        raise HTTPException(status_code=404, detail="Screening run not found or has no candidates")
    effective_plan = _effective_plan(plan, repository.provenance_for_run(run_id))
    return [
        CandidateStockResponse.from_domain(candidate, plan=effective_plan, index=index)
        for index, candidate in enumerate(candidates)
    ]


@router.get("/runs/{run_id}/exclusions", response_model=list[ScreenedOutStockResponse])
def get_run_exclusions(run_id: str) -> list[ScreenedOutStockResponse]:
    exclusions = repository.exclusions_for_run(run_id)
    if run_id not in repository.runs:
        raise HTTPException(status_code=404, detail="Screening run not found")
    return [ScreenedOutStockResponse.from_domain(stock) for stock in exclusions]


@router.get("/runs/{run_id}/provenance", response_model=MarketDataProvenanceResponse)
def get_run_provenance(run_id: str) -> MarketDataProvenanceResponse:
    provenance = repository.provenance_for_run(run_id)
    if provenance is None:
        raise HTTPException(status_code=404, detail="Provenance not found")
    return MarketDataProvenanceResponse.from_domain(provenance)


@router.get("/system/data-status", response_model=DataStatusResponse)
@router.get("/data/status", response_model=DataStatusResponse)
def data_status(settings: Settings = Depends(get_settings)) -> DataStatusResponse:
    provider = _provider(settings)
    snapshots = provider.get_intraday_snapshots()
    provenance = provider.provenance(snapshots)
    return DataStatusResponse(
        provider=provenance.provider,
        mode=provenance.mode,
        license_status=provenance.license_status,
        can_redistribute=provenance.can_redistribute,
        next_gate="完成正式行情授權、再散布條款、通知內容與付費商用審閱後才能開啟付費 checkout。",
        usage_notice=provenance.usage_notice,
    )


@router.post("/backtests", response_model=BacktestResponse)
def create_backtest(payload: BacktestRequest) -> BacktestResponse:
    rule_snapshot = asdict(repository.get_default_rule())
    rule_snapshot_hash = hashlib.sha256(
        json.dumps(rule_snapshot, default=str, sort_keys=True).encode("utf-8")
    ).hexdigest()
    base_date = date(2026, 6, 25)
    daily = [
        BacktestDailyCandidate(
            run_date=base_date - timedelta(days=offset),
            data_version=f"demo-history-{offset:02d}",
            rule_snapshot_hash=rule_snapshot_hash,
            candidate_count=3 if offset % 3 else 0,
            excluded_count=2,
            candidates=[] if offset % 3 == 0 else [
                ForwardReturnRow(
                    symbol="3037",
                    name="欣興",
                    run_date=base_date - timedelta(days=offset),
                    window="T+1",
                    open_return_pct=round(0.4 + offset * 0.03, 2),
                    high_return_pct=round(2.1 + offset * 0.04, 2),
                    low_return_pct=round(-1.2 - offset * 0.02, 2),
                    close_return_pct=round(0.9 + offset * 0.02, 2),
                    mae_pct=round(-1.5 - offset * 0.02, 2),
                    mfe_pct=round(2.4 + offset * 0.04, 2),
                    assumed_cost_pct=0.18,
                ),
                ForwardReturnRow(
                    symbol="2345",
                    name="智邦",
                    run_date=base_date - timedelta(days=offset),
                    window="T+3",
                    open_return_pct=round(0.2 + offset * 0.02, 2),
                    high_return_pct=round(3.0 + offset * 0.03, 2),
                    low_return_pct=round(-2.0 - offset * 0.03, 2),
                    close_return_pct=round(1.1 + offset * 0.01, 2),
                    mae_pct=round(-2.2 - offset * 0.03, 2),
                    mfe_pct=round(3.2 + offset * 0.03, 2),
                    assumed_cost_pct=0.18,
                ),
            ],
        )
        for offset in range(5)
    ]
    return BacktestResponse(
        rule_id=payload.rule_id,
        data_mode="demo",
        trading_days=payload.trading_days,
        methodology_notice=(
            "目前為 demo 回測骨架，正式版需匯入已授權 intraday history，"
            "逐日保存候選、排除、成本假設、MAE/MFE 與風控分層結果。"
        ),
        rows=[
            BacktestRow(
                window="T+1",
                sample_days=payload.trading_days,
                candidate_days=37,
                median_next_day_range_pct=2.4,
                max_adverse_excursion_pct=-3.1,
                empty_day_ratio=0.18,
            ),
            BacktestRow(
                window="T+3",
                sample_days=payload.trading_days,
                candidate_days=37,
                median_next_day_range_pct=3.8,
                max_adverse_excursion_pct=-5.6,
                empty_day_ratio=0.18,
            ),
            BacktestRow(
                window="T+5",
                sample_days=payload.trading_days,
                candidate_days=37,
                median_next_day_range_pct=4.6,
                max_adverse_excursion_pct=-7.2,
                empty_day_ratio=0.18,
            ),
        ],
        daily=daily,
    )


@router.post("/rules", response_model=ScreeningRuleResponse)
def create_rule(payload: ScreeningRuleRequest) -> ScreeningRuleResponse:
    rule = repository.upsert_rule(payload.to_domain(str(uuid4())))
    return ScreeningRuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=ScreeningRuleResponse)
def patch_rule(rule_id: str, payload: ScreeningRulePatch) -> ScreeningRuleResponse:
    if rule_id not in repository.rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    values = payload.model_dump(exclude_none=True)
    rule = repository.patch_rule(rule_id, values)
    return ScreeningRuleResponse.model_validate(rule)


@router.post("/notifications/test", response_model=NotificationTestResponse)
def test_notification(payload: NotificationTestRequest) -> NotificationTestResponse:
    result = notification_service.send_test(payload.channel, payload.destination)
    return NotificationTestResponse(**asdict(result))


@router.post("/billing/checkout", response_model=CheckoutResponse)
def create_checkout(
    payload: CheckoutRequest,
    settings: Settings = Depends(get_settings),
) -> CheckoutResponse:
    provider = _provider(settings)
    provenance = provider.provenance(provider.get_intraday_snapshots())
    if provenance.license_status != "licensed" or not provenance.can_redistribute:
        raise HTTPException(
            status_code=403,
            detail="Paid checkout is disabled until market-data licensing and redistribution gates are complete.",
        )
    session = billing_service.create_checkout(payload.plan)
    return CheckoutResponse(**asdict(session))
