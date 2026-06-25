from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_today_runs_returns_masked_free_candidates() -> None:
    response = client.get("/api/today/runs?plan=free")

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan"] == "free"
    assert payload["run"]["status"] == "completed"
    assert payload["provenance"]["mode"] == "demo"
    assert payload["provenance"]["license_status"] == "not_licensed"
    assert payload["provenance"]["ingestion_batch_id"]
    assert payload["provenance"]["symbol_universe_hash"]
    assert payload["run"]["rule_snapshot"]
    assert payload["run"]["risk_profile_snapshot"]
    assert payload["run"]["input_snapshot_hash"]
    assert payload["run"]["risk_profile_hash"]
    assert payload["run"]["score_formula_version"] == "match-score-v1"
    assert payload["risk_profile"]["max_trade_risk_pct"] == 0.5
    assert len(payload["candidates"]) >= 3
    assert any(candidate["masked"] for candidate in payload["candidates"])
    assert "match_score" in payload["candidates"][0]
    assert "risk_level" in payload["candidates"][0]
    assert "reference_price" in payload["candidates"][0]
    assert "liquidity_twd_million" in payload["candidates"][0]
    assert "risk_flags" in payload["candidates"][0]
    assert payload["exclusions_preview"]
    assert payload["exclusions_count"] >= len(payload["exclusions_preview"])


def test_pro_plan_is_forced_to_free_until_market_data_is_licensed() -> None:
    response = client.get("/api/today/runs?plan=pro")

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan"] == "free"
    assert any(candidate["masked"] for candidate in payload["candidates"])
    assert "6446" not in {candidate["symbol"] for candidate in payload["candidates"]}

    run_id = payload["run"]["id"]
    candidates_response = client.get(f"/api/runs/{run_id}/candidates?plan=pro")
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()
    assert any(candidate["masked"] for candidate in candidates)
    assert "6446" not in {candidate["symbol"] for candidate in candidates}


def test_default_rule_can_be_patched() -> None:
    response = client.patch("/api/rules/default-rule", json={"min_pct_change": 2.8})

    assert response.status_code == 200
    assert response.json()["min_pct_change"] == 2.8


def test_default_risk_profile_can_be_patched() -> None:
    before = client.get("/api/today/runs?plan=free").json()
    response = client.patch("/api/risk-profiles/default", json={"max_trade_risk_pct": 0.25})
    after = client.get("/api/today/runs?plan=free").json()

    assert response.status_code == 200
    assert response.json()["max_trade_risk_pct"] == 0.25
    assert after["run"]["id"] == before["run"]["id"]
    assert after["risk_profile"] == after["run"]["risk_profile_snapshot"]
    assert after["risk_profile"]["max_trade_risk_pct"] == before["run"]["risk_profile_snapshot"]["max_trade_risk_pct"]


def test_checkout_is_blocked_until_market_data_gate_is_complete() -> None:
    response = client.post("/api/billing/checkout", json={"plan": "pro_monthly"})

    assert response.status_code == 403
    assert "market-data licensing" in response.json()["detail"]


def test_run_exclusions_and_provenance_are_available() -> None:
    today = client.get("/api/today/runs?plan=pro").json()
    run_id = today["run"]["id"]

    exclusions_response = client.get(f"/api/runs/{run_id}/exclusions")
    provenance_response = client.get(f"/api/runs/{run_id}/provenance")

    assert exclusions_response.status_code == 200
    assert provenance_response.status_code == 200
    assert provenance_response.json()["raw_snapshot_hash"]
    assert len(exclusions_response.json()) == today["exclusions_count"]


def test_data_status_and_backtest_are_explicitly_demo() -> None:
    status_response = client.get("/api/system/data-status")
    alias_response = client.get("/api/data/status")
    backtest_response = client.post("/api/backtests", json={"trading_days": 60})

    assert status_response.status_code == 200
    assert alias_response.status_code == 200
    assert status_response.json()["can_redistribute"] is False
    assert alias_response.json()["license_status"] == "not_licensed"
    assert backtest_response.status_code == 200
    assert backtest_response.json()["data_mode"] == "demo"
    assert backtest_response.json()["rows"][0]["window"] == "T+1"
    assert backtest_response.json()["daily"][0]["rule_snapshot_hash"]
    assert "mae_pct" in backtest_response.json()["daily"][1]["candidates"][0]


def test_get_today_runs_is_read_only_after_seed() -> None:
    first = client.get("/api/today/runs?plan=free").json()
    second = client.get("/api/today/runs?plan=free").json()

    assert first["run"]["id"] == second["run"]["id"]


def test_notification_test_is_not_marked_delivered_in_demo_mode() -> None:
    response = client.post(
        "/api/notifications/test",
        json={"channel": "email", "destination": "demo@example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["delivered"] is False
    assert "展示模式" in payload["message"]
