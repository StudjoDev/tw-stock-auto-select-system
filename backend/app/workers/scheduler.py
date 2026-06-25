from __future__ import annotations

from datetime import UTC, datetime

from app.api.routes import repository
from app.config import get_settings
from app.services.market_data import get_market_data_provider
from app.services.notifications import NotificationService


def run_screening_once() -> None:
    settings = get_settings()
    provider = get_market_data_provider(settings.market_data_provider)
    run, candidates = repository.run_screening(provider, run_date=datetime.now(UTC).date())
    NotificationService().send_screening_alert(
        channel="email",
        destination=settings.default_user_email,
        candidates=candidates,
    )
    print(f"screening_run={run.id} status={run.status} candidates={len(candidates)}")


if __name__ == "__main__":
    run_screening_once()

