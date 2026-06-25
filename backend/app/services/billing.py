from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

BillingPlan = Literal["pro_monthly", "pro_yearly"]


@dataclass(slots=True)
class CheckoutSession:
    id: str
    plan: BillingPlan
    amount_twd: int
    checkout_url: str
    provider: str = "ecpay"
    sandbox: bool = True


class BillingService:
    prices = {
        "pro_monthly": 499,
        "pro_yearly": 4990,
    }

    def create_checkout(self, plan: BillingPlan) -> CheckoutSession:
        amount = self.prices[plan]
        session_id = f"demo_{uuid4().hex[:12]}"
        return CheckoutSession(
            id=session_id,
            plan=plan,
            amount_twd=amount,
            checkout_url=f"https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5?demo_session={session_id}",
        )

