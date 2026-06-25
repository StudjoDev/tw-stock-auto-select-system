from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, time
from pathlib import Path
from typing import Any

from zoneinfo import ZoneInfo

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
ROOT_DIR = Path(__file__).resolve().parents[1]
PUBLIC_DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"
RULE_CONFIG_PATH = ROOT_DIR / "config" / "screening_rule.json"
RISK_PROFILE_CONFIG_PATH = ROOT_DIR / "config" / "risk_profile.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.domain.models import RiskProfile, ScreeningRule
from app.repositories.memory import MemoryRepository
from app.services.market_data import get_market_data_provider
from app.api.schemas import (
    CandidateStockResponse,
    MarketDataProvenanceResponse,
    RiskProfileResponse,
    ScreeningRuleResponse,
    ScreeningRunResponse,
    ScreenedOutStockResponse,
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        return {}
    return payload


def _coerce_rule_time(raw_time: Any) -> time:
    if isinstance(raw_time, time):
        return raw_time
    if not isinstance(raw_time, str):
        return time(13, 0)
    normalized = raw_time.strip()
    if not normalized:
        return time(13, 0)
    try:
        return datetime.fromisoformat(normalized).time()
    except ValueError:
        parts = normalized.split(":")
        hour = int(parts[0]) if parts else 13
        minute = int(parts[1]) if len(parts) > 1 else 0
        return time(hour=hour % 24, minute=minute % 60)


def _apply_rule_overrides(default_rule: ScreeningRule, payload: dict[str, Any]) -> ScreeningRule:
    merged = asdict(default_rule)
    merged.update(payload)
    merged["notification_time"] = _coerce_rule_time(merged.get("notification_time"))
    merged["id"] = default_rule.id
    return ScreeningRule(**merged)


def _apply_risk_profile_overrides(
    default_profile: RiskProfile,
    payload: dict[str, Any],
) -> RiskProfile:
    merged = asdict(default_profile)
    merged.update(payload)
    merged["id"] = default_profile.id
    return RiskProfile(**merged)


def _run_once() -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    repository = MemoryRepository()
    default_rule = repository.get_default_rule()
    default_profile = repository.get_default_risk_profile()

    rule_overrides = _load_json(RULE_CONFIG_PATH)
    risk_overrides = _load_json(RISK_PROFILE_CONFIG_PATH)

    repository.upsert_rule(_apply_rule_overrides(default_rule, rule_overrides))
    repository.patch_risk_profile(default_profile.id, risk_overrides)

    settings = get_settings()
    provider = get_market_data_provider(settings.market_data_provider)
    run_date = datetime.now(ZoneInfo("Asia/Taipei")).date()
    run, _ = repository.run_screening(provider, run_date=run_date)

    candidates = repository.candidates_for_run(run.id)
    exclusions = repository.exclusions_for_run(run.id)
    provenance = repository.provenance_for_run(run.id)
    if provenance is None:
        raise RuntimeError("No provenance data produced in screening run")

    run_payload = ScreeningRunResponse.model_validate(run).model_dump(mode="json")
    rule_payload = ScreeningRuleResponse.model_validate(run.rule_snapshot).model_dump(mode="json")
    profile_payload = RiskProfileResponse.from_domain(repository.get_default_risk_profile()).model_dump(mode="json")
    provenance_payload = MarketDataProvenanceResponse.from_domain(provenance).model_dump(mode="json")
    candidate_payload = [
        CandidateStockResponse.from_domain(candidate, plan="free", index=index).model_dump(mode="json")
        for index, candidate in enumerate(candidates)
    ]
    exclusion_payload = [ScreenedOutStockResponse.from_domain(stock).model_dump(mode="json") for stock in exclusions]

    return (
        {
            "plan": "free",
            "run": run_payload,
            "rule": rule_payload,
            "risk_profile": profile_payload,
            "provenance": provenance_payload,
            "candidates": candidate_payload,
            "exclusions_preview": exclusion_payload[:5],
            "exclusions": exclusion_payload,
            "exclusions_count": len(exclusions),
            "upgrade": {
                "title": "Upgrade to Pro",
                "price": "NT$299 / mo",
                "cta": "Subscribe for full features",
            },
            "compliance_notice": "Static demo mode. This page is for reference only.",
            "risk_notice": "Risk warnings are included for every pick based on current rule output.",
            "data_notice": provenance_payload.get("usage_notice", "Daily source snapshot refreshed by scheduled workflow."),
        },
        run_payload,
    )


def _build_history_payload(
    output: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(ZoneInfo("Asia/Taipei")).isoformat()
    history_path = PUBLIC_DATA_DIR / "history.json"
    items: list[dict[str, Any]] = []
    if history_path.exists():
        try:
            with history_path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, dict):
                loaded_items = loaded.get("runs")
                if isinstance(loaded_items, list):
                    items = loaded_items
        except json.JSONDecodeError:
            items = []

    run_entry = {
        "run_id": output["run"]["id"],
        "run_date": output["run"]["run_date"],
        "generated_at": now,
        "candidate_count": len(output["candidates"]),
        "exclusion_count": output["exclusions_count"],
        "data_version": output["run"]["data_version"],
        "provider": output["provenance"]["provider"],
    }
    items = [item for item in items if item.get("run_id") != run_entry["run_id"]]
    items.insert(0, run_entry)
    items = items[:30]

    return {"updated_at": now, "runs": items}


def main() -> None:
    if not PUBLIC_DATA_DIR.exists():
        PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

    output, run_payload = _run_once()
    today_path = PUBLIC_DATA_DIR / "today.json"
    with today_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    run_dir = PUBLIC_DATA_DIR / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_path = run_dir / f"{run_payload['id']}.json"
    with run_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    history_payload = _build_history_payload(output)
    with (PUBLIC_DATA_DIR / "history.json").open("w", encoding="utf-8") as file:
        json.dump(history_payload, file, ensure_ascii=False, indent=2)

    print(f"generated:{today_path.as_posix()}")
    print(f"run_count:{len(history_payload['runs'])}")


if __name__ == "__main__":
    main()
