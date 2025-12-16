"""Telemetry consumer for generating ML-ready features from streaming vehicle data."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

import websockets
from websockets import ConnectionClosed, WebSocketException

WEBSOCKET_ENDPOINT = "ws://localhost:8765"
WINDOW_SIZE = 60  # readings
WINDOW_DURATION = timedelta(minutes=5)
MIN_SEQUENCE_LENGTH = 10
OPTIMAL_TIRE_PRESSURE = 32.0
CRITICAL_DTCS = {"P0300", "P0420", "P0128", "P0171", "P0442", "P0455"}
ALLOWED_USAGE_PATTERNS = {"city", "highway", "mixed"}
RECONNECT_INITIAL_SECONDS = 1.0
RECONNECT_MAX_SECONDS = 30.0
PING_INTERVAL_SECONDS = 30
PING_TIMEOUT_SECONDS = 30

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "telemetry_features.jsonl"

LOGGER = logging.getLogger("telemetry_consumer")


@dataclass(frozen=True)
class TelemetryReading:
    """Represents a single telemetry reading for a vehicle."""

    timestamp: datetime
    engine_temp: float
    battery_voltage: float
    brake_wear: float
    tire_pressure: float
    dtcs: Tuple[str, ...]
    usage_pattern: str


class VehicleTelemetryBuffer:
    """Maintains a rolling telemetry window and computes ML-ready features."""

    def __init__(self, vehicle_id: str) -> None:
        self.vehicle_id = vehicle_id
        self._readings: Deque[TelemetryReading] = deque()
        self._ready_logged = False

    def add_reading(self, reading: TelemetryReading) -> None:
        """Add a new reading and prune to the rolling window constraints."""

        self._readings.append(reading)
        self._prune_old_readings()

    def _prune_old_readings(self) -> None:
        """Remove readings that exceed the window size or duration."""

        while len(self._readings) > WINDOW_SIZE:
            self._readings.popleft()

        if not self._readings:
            return

        newest_timestamp = self._readings[-1].timestamp
        cutoff = newest_timestamp - WINDOW_DURATION
        while self._readings and self._readings[0].timestamp < cutoff:
            self._readings.popleft()

    def window_length(self) -> int:
        return len(self._readings)

    def _elapsed_minutes(self) -> float:
        if len(self._readings) < 2:
            return 0.0
        delta = self._readings[-1].timestamp - self._readings[0].timestamp
        return max(delta.total_seconds() / 60.0, 0.0)

    def compute_feature_payload(self) -> Optional[Dict[str, Any]]:
        if not self._readings:
            return None

        temps = [r.engine_temp for r in self._readings]
        battery = [r.battery_voltage for r in self._readings]
        brakes = [r.brake_wear for r in self._readings]
        tires = [r.tire_pressure for r in self._readings]
        dtc_codes = [code for r in self._readings for code in r.dtcs]

        elapsed_minutes = self._elapsed_minutes()
        safe_elapsed = elapsed_minutes if elapsed_minutes > 0 else 1.0

        latest = self._readings[-1]
        earliest = self._readings[0]

        rf_features = {
            "engine_temp_mean": fmean(temps),
            "engine_temp_max": max(temps),
            "engine_temp_std": pstdev(temps) if len(temps) > 1 else 0.0,
            "engine_temp_rate_per_min": (latest.engine_temp - earliest.engine_temp) / safe_elapsed,
            "battery_voltage_mean": fmean(battery),
            "battery_voltage_min": min(battery),
            "battery_voltage_drop_per_min": (earliest.battery_voltage - latest.battery_voltage) / safe_elapsed,
            "brake_wear_current": latest.brake_wear,
            "brake_wear_rate_per_min": (latest.brake_wear - earliest.brake_wear) / safe_elapsed,
            "tire_pressure_mean_dev": fmean([value - OPTIMAL_TIRE_PRESSURE for value in tires]),
            "dtc_count": len(dtc_codes),
            "critical_dtc_present": 1 if any(code in CRITICAL_DTCS for code in dtc_codes) else 0,
            "usage_city": 1 if latest.usage_pattern == "city" else 0,
            "usage_highway": 1 if latest.usage_pattern == "highway" else 0,
            "usage_mixed": 1 if latest.usage_pattern == "mixed" else 0,
            "hour_of_day": latest.timestamp.hour,
            "day_of_week": latest.timestamp.weekday(),
            "window_size": len(self._readings),
            "window_span_minutes": elapsed_minutes,
        }

        lstm_sequence = [
            [
                reading.engine_temp,
                reading.battery_voltage,
                reading.brake_wear,
                reading.tire_pressure,
                1.0 if reading.dtcs else 0.0,
                1.0 if reading.usage_pattern == "city" else 0.0,
                1.0 if reading.usage_pattern == "highway" else 0.0,
                1.0 if reading.usage_pattern == "mixed" else 0.0,
            ]
            for reading in self._readings
        ]

        payload = {
            "vehicle_id": self.vehicle_id,
            "timestamp": latest.timestamp.isoformat(),
            "rf_features": rf_features,
            "lstm_sequence": lstm_sequence,
        }

        if len(self._readings) >= MIN_SEQUENCE_LENGTH and not self._ready_logged:
            LOGGER.info(
                "Vehicle %s reached minimum sequence length (%d readings) for ML inference",
                self.vehicle_id,
                len(self._readings),
            )
            self._ready_logged = True
        elif len(self._readings) < MIN_SEQUENCE_LENGTH:
            self._ready_logged = False

        return payload


class TelemetryFeatureManager:
    """Transforms raw telemetry messages into ML-ready feature payloads."""

    def __init__(self) -> None:
        self._buffers: Dict[str, VehicleTelemetryBuffer] = {}
        self.latest_features: Dict[str, Dict[str, Any]] = {}

    def handle_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        vehicle_id = str(payload["vehicle_id"]).strip()
        buffer_ = self._buffers.setdefault(vehicle_id, VehicleTelemetryBuffer(vehicle_id))
        reading = self._build_reading(payload)
        buffer_.add_reading(reading)
        feature_payload = buffer_.compute_feature_payload()
        if feature_payload:
            self.latest_features[vehicle_id] = feature_payload
            LOGGER.info("Updated features for vehicle %s", vehicle_id)
        return feature_payload

    @staticmethod
    def _build_reading(data: Dict[str, Any]) -> TelemetryReading:
        timestamp = parse_timestamp(str(data["timestamp"]))
        engine_temp = float(data["engine_temp"])
        battery_voltage = float(data["battery_voltage"])
        brake_wear = float(data["brake_wear"])
        tire_pressure = float(data["tire_pressure"])

        dtc_field = data.get("dtc")
        dtcs: Tuple[str, ...]
        if dtc_field is None:
            dtcs = ()
        elif isinstance(dtc_field, str):
            cleaned = dtc_field.strip().upper()
            dtcs = (cleaned,) if cleaned else ()
        elif isinstance(dtc_field, Iterable):
            dtcs = tuple(str(item).strip().upper() for item in dtc_field if str(item).strip())
        else:
            dtcs = ()

        usage_raw = str(data.get("usage_pattern", "mixed")).strip().lower()
        usage_pattern = usage_raw if usage_raw in ALLOWED_USAGE_PATTERNS else "mixed"

        return TelemetryReading(
            timestamp=timestamp,
            engine_temp=engine_temp,
            battery_voltage=battery_voltage,
            brake_wear=brake_wear,
            tire_pressure=tire_pressure,
            dtcs=dtcs,
            usage_pattern=usage_pattern,
        )


def parse_timestamp(raw: str) -> datetime:
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: {raw}") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def ensure_required_fields(message: Dict[str, Any]) -> bool:
    required = {
        "vehicle_id",
        "timestamp",
        "engine_temp",
        "battery_voltage",
        "brake_wear",
        "tire_pressure",
        "usage_pattern",
    }
    missing = [field for field in required if field not in message]
    if missing:
        LOGGER.warning("Dropping telemetry message missing fields: %s", ", ".join(missing))
        return False
    return True


def prepare_output(feature_payload: Dict[str, Any]) -> str:
    return json.dumps(feature_payload, default=str)


async def consume_telemetry(output_path: Path = OUTPUT_PATH) -> None:
    manager = TelemetryFeatureManager()
    backoff = RECONNECT_INITIAL_SECONDS
    output_handle = None
    try:
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_handle = output_path.open("a", encoding="utf-8")
            LOGGER.info("Appending telemetry features to %s", output_path)

        while True:
            try:
                async with websockets.connect(
                    WEBSOCKET_ENDPOINT,
                    ping_interval=PING_INTERVAL_SECONDS,
                    ping_timeout=PING_TIMEOUT_SECONDS,
                    max_size=None,
                ) as websocket:
                    LOGGER.info("Connected to telemetry server at %s", WEBSOCKET_ENDPOINT)
                    backoff = RECONNECT_INITIAL_SECONDS

                    async for message in websocket:
                        try:
                            payload = json.loads(message)
                        except json.JSONDecodeError:
                            LOGGER.warning("Received malformed JSON: %s", message)
                            continue

                        if not isinstance(payload, dict):
                            LOGGER.warning("Received non-dict payload: %s", payload)
                            continue

                        if not ensure_required_fields(payload):
                            continue

                        try:
                            feature_payload = manager.handle_message(payload)
                        except Exception as exc:  # pragma: no cover - defensive logging
                            LOGGER.exception("Failed to process telemetry message: %s", exc)
                            continue

                        if feature_payload is not None:
                            serialized = prepare_output(feature_payload)
                            print(serialized)
                            if output_handle is not None:
                                output_handle.write(serialized + "\n")
                                output_handle.flush()

            except (ConnectionRefusedError, ConnectionResetError, WebSocketException, ConnectionClosed) as exc:
                LOGGER.warning("Telemetry connection issue: %s", exc)
            except asyncio.CancelledError:
                LOGGER.info("Telemetry consumer task cancelled")
                raise
            except Exception as exc:  # pragma: no cover - unexpected failures
                LOGGER.exception("Unexpected telemetry consumer failure: %s", exc)

            LOGGER.info("Attempting reconnect in %.1f seconds", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, RECONNECT_MAX_SECONDS)
    finally:
        if output_handle is not None:
            output_handle.close()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> None:
    configure_logging()
    try:
        asyncio.run(consume_telemetry())
    except KeyboardInterrupt:
        LOGGER.info("Telemetry consumer stopped by user")


if __name__ == "__main__":
    main()
