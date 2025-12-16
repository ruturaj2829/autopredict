"""Scheduler agent responsible for maintenance bookings."""

from __future__ import annotations

import logging
from typing import Literal

LOGGER = logging.getLogger("scheduling_agent")


class SchedulingAgent:
	"""Schedules maintenance visits based on predictive risk signals."""

	def schedule_priority_visit(self, vehicle_id: str, risk_level: str, days_to_failure: int) -> None:
		slot = self._determine_slot(days_to_failure, urgent=True)
		LOGGER.info(
			"Priority maintenance scheduled | vehicle=%s | risk=%s | slot=%s",
			vehicle_id,
			risk_level,
			slot,
		)

	def schedule_standard_visit(self, vehicle_id: str, risk_level: str, days_to_failure: int) -> None:
		slot = self._determine_slot(days_to_failure, urgent=False)
		LOGGER.info(
			"Standard maintenance scheduled | vehicle=%s | risk=%s | slot=%s",
			vehicle_id,
			risk_level,
			slot,
		)

	def _determine_slot(self, days_to_failure: int, urgent: bool) -> str:
		if urgent or days_to_failure <= 2:
			return "within 24h"
		if days_to_failure <= 7:
			return "next 3 days"
		return "next available window"
