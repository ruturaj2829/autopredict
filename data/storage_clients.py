"""
Data storage clients for telemetry, maintenance, and UEBA logs.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

LOGGER = logging.getLogger("data.storage_clients")

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None  # type: ignore

try:
    from influxdb_client import InfluxDBClient, Point
except ImportError:  # pragma: no cover
    InfluxDBClient = None  # type: ignore
    Point = None  # type: ignore

try:
    from elasticsearch import Elasticsearch
except ImportError:  # pragma: no cover
    Elasticsearch = None  # type: ignore


@dataclass
class TimeseriesPoint:
    measurement: str
    tags: Dict[str, str]
    fields: Dict[str, float]
    timestamp: Optional[str] = None


class TimescaleClient:
    def __init__(self, dsn: Optional[str] = None) -> None:
        self.dsn = dsn or os.getenv("TIMESCALE_DSN")
        if not self.dsn or not psycopg2:
            raise RuntimeError("TimescaleDB requires psycopg2 and a connection DSN")
        self.connection = psycopg2.connect(self.dsn)
        LOGGER.info("Connected to TimescaleDB")

    def write(self, table: str, payloads: Iterable[Dict[str, Any]]) -> None:
        cursor = self.connection.cursor()
        for payload in payloads:
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(["%s"] * len(payload))
            cursor.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                list(payload.values()),
            )
        self.connection.commit()
        cursor.close()

    def close(self) -> None:
        self.connection.close()


class InfluxTelemetryClient:
    def __init__(self, url: str, token: str, org: str, bucket: str) -> None:
        if not InfluxDBClient or not Point:
            raise RuntimeError("influxdb-client library is required")
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.bucket = bucket
        self.org = org

    def write_points(self, points: Iterable[TimeseriesPoint]) -> None:
        write_api = self.client.write_api()
        influx_points = []
        for point in points:
            p = Point(point.measurement)
            for key, value in point.tags.items():
                p = p.tag(key, value)
            for key, value in point.fields.items():
                p = p.field(key, value)
            if point.timestamp:
                p = p.time(point.timestamp)
            influx_points.append(p)
        write_api.write(bucket=self.bucket, org=self.org, record=influx_points)


class AzurePostgresClient:
    def __init__(self, dsn: Optional[str] = None) -> None:
        self.dsn = dsn or os.getenv("AZURE_POSTGRES_DSN")
        if not self.dsn or not psycopg2:
            raise RuntimeError("Azure PostgreSQL requires psycopg2 and DSN")
        self.connection = psycopg2.connect(self.dsn)
        LOGGER.info("Connected to Azure Database for PostgreSQL")

    def upsert_maintenance_record(self, record: Dict[str, Any]) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO maintenance_events(vehicle_id, component, risk_level, scheduled_for, notes)
            VALUES (%(vehicle_id)s, %(component)s, %(risk_level)s, %(scheduled_for)s, %(notes)s)
            ON CONFLICT (vehicle_id, component) DO UPDATE SET
                risk_level = EXCLUDED.risk_level,
                scheduled_for = EXCLUDED.scheduled_for,
                notes = EXCLUDED.notes
            """,
            record,
        )
        self.connection.commit()
        cursor.close()

    def close(self) -> None:
        self.connection.close()


class ElasticLogClient:
    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None) -> None:
        if not Elasticsearch:
            raise RuntimeError("elasticsearch package is required")
        url = endpoint or os.getenv("ELASTICSEARCH_URL")
        key = api_key or os.getenv("AZURE_ELASTIC_API_KEY")
        if not url:
            raise RuntimeError("ELASTICSEARCH_URL must be set for ElasticLogClient")
        self.client = Elasticsearch(url, api_key=key) if key else Elasticsearch(url)
        LOGGER.info("Connected to Elasticsearch at %s | api_key=%s", url, bool(key))