from datetime import date
from unittest import TestCase

from app.data.sample_market import sample_market_snapshots
from app.domain.models import ScreeningRule
from app.domain.screener import evaluate_vwap, screen_market


class ScreenerTest(TestCase):
    def test_default_rule_returns_explainable_candidates(self) -> None:
        rule = ScreeningRule(id="rule", name="default")
        candidates = screen_market(sample_market_snapshots(), rule, date(2026, 6, 25))

        self.assertGreaterEqual(len(candidates), 3)
        self.assertEqual(candidates[0].symbol, "3037")
        self.assertTrue(all(candidate.reasons for candidate in candidates))
        self.assertTrue(all(3.0 <= candidate.pct_change <= 5.0 for candidate in candidates))
        self.assertTrue(all(5.0 <= candidate.turnover_rate <= 10.0 for candidate in candidates))
        self.assertTrue(all(candidate.reference_price > 0 for candidate in candidates))
        self.assertTrue(all(candidate.liquidity_twd_million > 0 for candidate in candidates))
        self.assertTrue(all(candidate.risk_flags is not None for candidate in candidates))

    def test_market_cap_filter_excludes_large_cap(self) -> None:
        rule = ScreeningRule(id="rule", name="default", max_market_cap_billion=300)
        candidates = screen_market(sample_market_snapshots(), rule, date(2026, 6, 25))

        symbols = {candidate.symbol for candidate in candidates}
        self.assertNotIn("2330", symbols)
        self.assertIn("3037", symbols)

    def test_vwap_reclaim_rule_blocks_weak_recovery(self) -> None:
        snapshot = sample_market_snapshots()[0]
        rule = ScreeningRule(id="rule", name="strict", vwap_reclaim_bars=0)

        evaluation = evaluate_vwap(snapshot, rule)

        self.assertGreaterEqual(evaluation.above_ratio, 0.8)
        self.assertTrue(evaluation.reclaimed_within_bars)
