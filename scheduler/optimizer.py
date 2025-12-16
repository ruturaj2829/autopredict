"""
Scheduling optimizer leveraging Google OR-Tools with Azure SQL persistence.

This module selects optimal maintenance slots based on vehicle risk, technician capacity,
and geographic routing constraints.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

try:
    from ortools.linear_solver import pywraplp
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("OR-Tools is required for the scheduling optimizer") from exc

try:
    import pyodbc
except ImportError:  # pragma: no cover
    pyodbc = None  # type: ignore

LOGGER = logging.getLogger("scheduler.optimizer")


@dataclass
class MaintenanceJob:
    vehicle_id: str
    risk_level: str
    location: str
    preferred_by: datetime
    duration_minutes: int
    days_to_failure: Optional[int] = None


@dataclass
class TechnicianSlot:
    technician_id: str
    location: str
    start_time: datetime
    capacity_minutes: int


@dataclass
class ScheduledVisit:
    vehicle_id: str
    technician_id: str
    slot_start: datetime
    slot_end: datetime
    priority: str


class SchedulingOptimizer:
    """Selects optimal technician allocations using mixed-integer programming."""

    def __init__(self, sql_connection_string: Optional[str] = None) -> None:
        self.sql_connection_string = sql_connection_string or os.getenv("AZURE_SQL_CONNECTION")
        self._sql_enabled = bool(self.sql_connection_string and pyodbc)

    def _connect_sql(self):
        if not self._sql_enabled:
            return None
        return pyodbc.connect(self.sql_connection_string)  # pragma: no cover

    # ------------------------------------------------------------------ #
    def optimize(self, jobs: Sequence[MaintenanceJob], slots: Sequence[TechnicianSlot]) -> List[ScheduledVisit]:
        if not jobs or not slots:
            LOGGER.warning("No jobs or slots available for optimization")
            return []

        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:  # pragma: no cover
            raise RuntimeError("Failed to initialize OR-Tools solver")

        x: Dict[tuple, pywraplp.Variable] = {}
        for job_idx, job in enumerate(jobs):
            for slot_idx, slot in enumerate(slots):
                compatible = self._is_slot_compatible(job, slot)
                x[job_idx, slot_idx] = solver.BoolVar(f"x_{job_idx}_{slot_idx}") if compatible else solver.BoolVar(f"x_{job_idx}_{slot_idx}")
                if not compatible:
                    solver.Add(x[job_idx, slot_idx] == 0)

        # Each job assigned at most once
        for job_idx, job in enumerate(jobs):
            solver.Add(sum(x[job_idx, slot_idx] for slot_idx in range(len(slots))) <= 1)
            LOGGER.debug("Constraint added for job %s", job.vehicle_id)

        # Slot capacity constraints
        for slot_idx, slot in enumerate(slots):
            solver.Add(sum(jobs[job_idx].duration_minutes * x[job_idx, slot_idx] for job_idx in range(len(jobs))) <= slot.capacity_minutes)

        # Objective: maximize weighted priority (HIGH > MEDIUM > LOW) with urgency
        priority_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        objective = solver.Objective()
        for job_idx, job in enumerate(jobs):
            weight = priority_weights.get(job.risk_level.upper(), 1)
            urgency_bonus = max(0, 10 - (job.days_to_failure or 10))
            for slot_idx, slot in enumerate(slots):
                score = weight * 100 + urgency_bonus
                objective.SetCoefficient(x[job_idx, slot_idx], score)
        objective.SetMaximization()

        LOGGER.info("Solving maintenance scheduling problem | jobs=%d slots=%d", len(jobs), len(slots))
        status = solver.Solve()
        if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            LOGGER.error("Solver failed to find a feasible solution | status=%s", status)
            return []

        schedule: List[ScheduledVisit] = []
        for job_idx, job in enumerate(jobs):
            for slot_idx, slot in enumerate(slots):
                if x[job_idx, slot_idx].solution_value() > 0.5:
                    visit = ScheduledVisit(
                        vehicle_id=job.vehicle_id,
                        technician_id=slot.technician_id,
                        slot_start=slot.start_time,
                        slot_end=slot.start_time + timedelta(minutes=job.duration_minutes),
                        priority=job.risk_level.upper(),
                    )
                    schedule.append(visit)
                    self._persist_schedule(visit)
                    LOGGER.info("Scheduled %s with technician %s at %s", job.vehicle_id, slot.technician_id, slot.start_time.isoformat())
        return schedule

    # ------------------------------------------------------------------ #
    @staticmethod
    def _is_slot_compatible(job: MaintenanceJob, slot: TechnicianSlot) -> bool:
        same_city = job.location.split(",")[0].strip().lower() == slot.location.split(",")[0].strip().lower()
        return same_city and slot.start_time <= job.preferred_by

    def _persist_schedule(self, visit: ScheduledVisit) -> None:
        if not self._sql_enabled:
            return
        try:  # pragma: no cover
            conn = self._connect_sql()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO maintenance_schedule(vehicle_id, technician_id, slot_start, slot_end, priority)
                VALUES (?, ?, ?, ?, ?)
                """,
                visit.vehicle_id,
                visit.technician_id,
                visit.slot_start,
                visit.slot_end,
                visit.priority,
            )
            conn.commit()
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Failed to persist schedule to Azure SQL: %s", exc)
        finally:
            try:
                cursor.close()  # type: ignore
                conn.close()  # type: ignore
            except Exception:
                pass