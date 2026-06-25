from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.models import CandidateStock

NotificationChannel = Literal["email", "line", "web_push"]


@dataclass(slots=True)
class NotificationResult:
    channel: NotificationChannel
    delivered: bool
    message: str


class NotificationService:
    def send_test(self, channel: NotificationChannel, destination: str) -> NotificationResult:
        if not destination:
            return NotificationResult(channel=channel, delivered=False, message="缺少通知目的地。")
        return NotificationResult(
            channel=channel,
            delivered=False,
            message="展示模式：尚未串接正式 Email/LINE/Web Push，沒有實際送達。",
        )

    def send_screening_alert(
        self,
        channel: NotificationChannel,
        destination: str,
        candidates: list[CandidateStock],
    ) -> NotificationResult:
        if not destination:
            return NotificationResult(channel=channel, delivered=False, message="缺少通知目的地。")
        return NotificationResult(
            channel=channel,
            delivered=False,
            message=f"展示模式：已產生 {len(candidates)} 檔候選摘要，但通知尚未實際送達。",
        )
