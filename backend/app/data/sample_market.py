from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.domain.models import IntradayBar, StockSnapshot

TAIPEI_TZ = timezone(timedelta(hours=8))
SAMPLE_RUN_DATE = date(2026, 6, 25)


def sample_market_snapshots() -> list[StockSnapshot]:
    return [
        StockSnapshot(
            symbol="2345",
            name="智邦",
            previous_close=820.0,
            current_price=852.0,
            intraday_volume=18_200_000,
            avg_5d_volume=13_400_000,
            turnover_rate=7.2,
            market_cap_billion=472.0,
            limit_up_dates=[SAMPLE_RUN_DATE - timedelta(days=9)],
            bars=_bars(820.0, [828, 833, 836, 840, 843, 846, 845, 848, 850, 852]),
        ),
        StockSnapshot(
            symbol="3037",
            name="欣興",
            previous_close=164.0,
            current_price=170.8,
            intraday_volume=42_500_000,
            avg_5d_volume=25_000_000,
            turnover_rate=8.8,
            market_cap_billion=262.0,
            limit_up_dates=[SAMPLE_RUN_DATE - timedelta(days=15)],
            bars=_bars(164.0, [166, 167.2, 168, 168.5, 169.2, 168.7, 169.6, 170.2, 170.5, 170.8]),
        ),
        StockSnapshot(
            symbol="6446",
            name="藥華藥",
            previous_close=610.0,
            current_price=631.0,
            intraday_volume=5_200_000,
            avg_5d_volume=4_300_000,
            turnover_rate=5.4,
            market_cap_billion=214.0,
            limit_up_dates=[SAMPLE_RUN_DATE - timedelta(days=4)],
            bars=_bars(610.0, [616, 619, 621, 622, 625, 624, 626, 628, 630, 631]),
            warnings=["成交金額較集中，需確認委買委賣深度"],
        ),
        StockSnapshot(
            symbol="2330",
            name="台積電",
            previous_close=1440.0,
            current_price=1492.0,
            intraday_volume=35_000_000,
            avg_5d_volume=30_000_000,
            turnover_rate=0.8,
            market_cap_billion=38_000.0,
            limit_up_dates=[],
            bars=_bars(1440.0, [1450, 1462, 1470, 1480, 1484, 1488, 1490, 1492]),
        ),
        StockSnapshot(
            symbol="3017",
            name="奇鋐",
            previous_close=730.0,
            current_price=780.0,
            intraday_volume=16_000_000,
            avg_5d_volume=15_200_000,
            turnover_rate=6.8,
            market_cap_billion=294.0,
            limit_up_dates=[SAMPLE_RUN_DATE - timedelta(days=7)],
            bars=_bars(730.0, [742, 748, 755, 760, 752, 750, 758, 766, 774, 780]),
        ),
    ]


def _bars(previous_close: float, closes: list[float]) -> list[IntradayBar]:
    start = datetime(2026, 6, 25, 9, 1, tzinfo=TAIPEI_TZ)
    bars: list[IntradayBar] = []
    last_close = previous_close
    for index, close in enumerate(closes):
        volume = 100_000 + (index * 8_000)
        bars.append(
            IntradayBar(
                traded_at=start + timedelta(minutes=index),
                open=last_close,
                high=max(last_close, close) * 1.002,
                low=min(last_close, close) * 0.998,
                close=close,
                volume=volume,
                turnover=close * volume,
            )
        )
        last_close = close
    return bars
