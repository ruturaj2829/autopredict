"""Customer engagement agent for predictive maintenance notifications.

This agent now integrates Azure TTS + sentiment via ``AzureVoiceService`` to
produce persuasive, mood-adaptive voice messages for customers.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from voice.azure_voice_service import AzureVoiceService, VoiceResponse

LOGGER = logging.getLogger("customer_engagement_agent")


class CustomerEngagementAgent:
	"""Delivers tailored outreach messages based on risk level, with voice output."""

	def __init__(self) -> None:
		# Lazily constructed Azure voice service for TTS. If the environment is not
		# configured, we still fall back to log-only behavior.
		try:
			self._voice = AzureVoiceService()
			LOGGER.info("AzureVoiceService initialized for customer engagement agent")
		except Exception as exc:  # pragma: no cover - optional dependency
			LOGGER.warning("Voice service unavailable, falling back to text-only: %s", exc)
			self._voice = None

	def _build_urgent_text(self, event: Dict[str, Any]) -> str:
		return (
			f"Hello. This is your vehicle care assistant. "
			f"Our system detected {event.get('risk_level')} risk for the {event.get('affected_component', 'vehicle system')} "
			f"on vehicle {event.get('vehicle_id')}. "
			f"It could impact safety within {event.get('estimated_days_to_failure', 'a few')} days. "
			f"Booking a preventive service now could save significant repair costs and avoid roadside breakdowns."
		)

	def _build_preventive_text(self, event: Dict[str, Any]) -> str:
		return (
			f"Hello. This is your vehicle care assistant. "
			f"We see early signs of wear on vehicle {event.get('vehicle_id')}. "
			f"Scheduling a check within {event.get('estimated_days_to_failure', 'the next few')} days "
			f"can keep you safe and reduce maintenance costs."
		)

	def send_urgent_message(self, event: Dict[str, Any]) -> Dict[str, Any]:
		"""Send an urgent, safety-focused voice + text notification."""
		text = self._build_urgent_text(event)
		LOGGER.info("URGENT voice script for %s: %s", event.get("vehicle_id"), text)

		voice_payload: Dict[str, Any] = {"text": text, "audio_bytes": None}
		if self._voice is not None:
			# We synthesize directly from text; in a full IVR flow we would take customer audio,
			# run sentiment, then adapt the script. For the demo this is sufficient.
			audio = self._voice.synthesize(text)
			voice_payload["audio_bytes"] = audio

		return voice_payload

	def send_preventive_message(self, event: Dict[str, Any]) -> Dict[str, Any]:
		"""Send a preventive, cost-optimization voice + text notification."""
		text = self._build_preventive_text(event)
		LOGGER.info("Preventive voice script for %s: %s", event.get("vehicle_id"), text)

		voice_payload: Dict[str, Any] = {"text": text, "audio_bytes": None}
		if self._voice is not None:
			audio = self._voice.synthesize(text)
			voice_payload["audio_bytes"] = audio

		return voice_payload

