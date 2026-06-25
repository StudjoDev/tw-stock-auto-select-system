from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Protocol

from app.data.sample_market import sample_market_snapshots
from app.domain.models import MarketDataProvenance, StockSnapshot

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


class MarketDataProvider(Protocol):
    def get_intraday_snapshots(self) -> list[StockSnapshot]:
        """Return normalized snapshots for screening at 13:00 Asia/Taipei."""

    def provenance(self, snapshots: list[StockSnapshot]) -> MarketDataProvenance:
        """Return licensing and reproducibility metadata for a snapshot batch."""


class MockMarketDataProvider:
    def get_intraday_snapshots(self) -> list[StockSnapshot]:
        return sample_market_snapshots()

    def provenance(self, snapshots: list[StockSnapshot]) -> MarketDataProvenance:
        now = datetime.now(TAIPEI_TZ)
        cutoff_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
        payload = json.dumps([asdict(snapshot) for snapshot in snapshots], default=str, sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        universe_payload = json.dumps(sorted(snapshot.symbol for snapshot in snapshots))
        universe_hash = hashlib.sha256(universe_payload.encode("utf-8")).hexdigest()
        return MarketDataProvenance(
            ingestion_batch_id=f"mock-{cutoff_time:%Y%m%d}-1300-{digest[:8]}",
            provider="mock",
            mode="demo",
            license_status="not_licensed",
            can_redistribute=False,
            cutoff_time=cutoff_time,
            generated_at=datetime.now(TAIPEI_TZ),
            data_version=f"{cutoff_time.date().isoformat()}-mock-13:00-{digest[:10]}",
            raw_snapshot_hash=digest,
            raw_storage_pointer=f"memory://mock/{cutoff_time.date().isoformat()}/13:00/{digest}",
            provider_version="mock-v1",
            corporate_action_version="demo-ca-2026-06",
            calendar_version="twse-demo-calendar-2026",
            symbol_universe_hash=universe_hash,
            bar_interval="1m-demo",
            usage_notice="目前為展示資料，尚未取得正式行情授權，不可作為付費即時推播或再散布資料。",
        )


def get_market_data_provider(provider_name: str) -> MarketDataProvider:
    if provider_name == "mock":
        return MockMarketDataProvider()

    raise NotImplementedError(
        "Real-time provider integration is gated until commercial data licensing is confirmed."
    )
