from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from datetime import UTC, date, datetime
from uuid import uuid4

from app.domain.models import (
    CandidateStock,
    MarketDataProvenance,
    RiskProfile,
    ScreenedOutStock,
    ScreeningRule,
    ScreeningRun,
)
from app.domain.screener import screen_market_with_exclusions
from app.services.market_data import MarketDataProvider


class MemoryRepository:
    def __init__(self) -> None:
        self.default_rule = ScreeningRule(id="default-rule", name="13:00 盤中篩選")
        self.default_risk_profile = RiskProfile(id="default-risk-profile", name="一般風控")
        self.rules: dict[str, ScreeningRule] = {self.default_rule.id: self.default_rule}
        self.risk_profiles: dict[str, RiskProfile] = {
            self.default_risk_profile.id: self.default_risk_profile
        }
        self.runs: dict[str, ScreeningRun] = {}
        self.candidates_by_run: dict[str, list[CandidateStock]] = {}
        self.exclusions_by_run: dict[str, list[ScreenedOutStock]] = {}
        self.provenance_by_run: dict[str, MarketDataProvenance] = {}

    def get_default_rule(self) -> ScreeningRule:
        return self.default_rule

    def get_default_risk_profile(self) -> RiskProfile:
        return self.default_risk_profile

    def upsert_rule(self, rule: ScreeningRule) -> ScreeningRule:
        if not rule.id:
            rule.id = str(uuid4())
        self.rules[rule.id] = rule
        if rule.id == self.default_rule.id:
            self.default_rule = rule
        return rule

    def patch_rule(self, rule_id: str, values: dict[str, object]) -> ScreeningRule:
        rule = self.rules[rule_id]
        current = asdict(rule)
        current.update(values)
        updated = ScreeningRule(**current)
        self.rules[rule_id] = updated
        if rule_id == self.default_rule.id:
            self.default_rule = updated
        return updated

    def patch_risk_profile(self, profile_id: str, values: dict[str, object]) -> RiskProfile:
        profile = self.risk_profiles[profile_id]
        current = asdict(profile)
        current.update(values)
        updated = RiskProfile(**current)
        self.risk_profiles[profile_id] = updated
        if profile_id == self.default_risk_profile.id:
            self.default_risk_profile = updated
        return updated

    def run_screening(
        self,
        provider: MarketDataProvider,
        rule: ScreeningRule | None = None,
        risk_profile: RiskProfile | None = None,
        run_date: date | None = None,
    ) -> tuple[ScreeningRun, list[CandidateStock]]:
        active_rule = rule or self.default_rule
        active_risk_profile = risk_profile or self.default_risk_profile
        today = run_date or datetime.now(UTC).date()
        snapshots = provider.get_intraday_snapshots()
        provenance = provider.provenance(snapshots)
        risk_profile_snapshot = asdict(active_risk_profile)
        run = ScreeningRun(
            id=str(uuid4()),
            rule_id=active_rule.id,
            run_date=today,
            status="running",
            data_version=provenance.data_version,
            started_at=datetime.now(UTC),
            rule_snapshot=asdict(active_rule),
            risk_profile_snapshot=risk_profile_snapshot,
            input_snapshot_hash=provenance.raw_snapshot_hash,
            universe_hash=provenance.symbol_universe_hash,
            risk_profile_hash=_dict_hash(risk_profile_snapshot),
            score_formula_version="match-score-v1",
        )
        self.runs[run.id] = run
        try:
            output = screen_market_with_exclusions(snapshots, active_rule, today)
            run.status = "completed"
            run.completed_at = datetime.now(UTC)
            self.candidates_by_run[run.id] = output.candidates
            self.exclusions_by_run[run.id] = output.exclusions
            self.provenance_by_run[run.id] = provenance
            return run, output.candidates
        except Exception as exc:
            run.status = "failed"
            run.completed_at = datetime.now(UTC)
            run.error_message = str(exc)
            self.candidates_by_run[run.id] = []
            self.exclusions_by_run[run.id] = []
            return run, []

    def latest_run(self, provider: MarketDataProvider) -> tuple[ScreeningRun, list[CandidateStock]]:
        completed_runs = [run for run in self.runs.values() if run.status == "completed"]
        if not completed_runs:
            raise LookupError("No completed screening run is available")
        run = max(completed_runs, key=lambda item: item.started_at)
        return run, self.candidates_by_run.get(run.id, [])

    def candidates_for_run(self, run_id: str) -> list[CandidateStock]:
        return self.candidates_by_run.get(run_id, [])

    def exclusions_for_run(self, run_id: str) -> list[ScreenedOutStock]:
        return self.exclusions_by_run.get(run_id, [])

    def provenance_for_run(self, run_id: str) -> MarketDataProvenance | None:
        return self.provenance_by_run.get(run_id)


def _universe_hash(symbols: list[str]) -> str:
    payload = json.dumps(sorted(symbols), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dict_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, default=str, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
