"""Billing service stub for tests."""

from typing import Dict, Any


class BillingService:
	async def record_usage(self, user_id: str, action: str, metadata: Dict[str, Any] | None = None) -> None:
		return None


billing_service = BillingService()
