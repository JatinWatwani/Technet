from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .clock import Clock
from .errors import ErrorCode
from .models import (
    Batch,
    GeoLocation,
    Rider,
    RiderStatus,
    Shelter,
    ShelterStatus,
    StorageRequirement,
)


@dataclass(frozen=True)
class RuleEvaluationResult:
    rule_name: str
    passed: bool
    reason_code: str | None = None
    reason: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SafetyEvaluationReport:
    feasible: bool
    primary_failure_code: str | None = None
    primary_failure_reason: str | None = None
    evaluated_rules: list[str] = field(default_factory=list)
    rule_results: list[RuleEvaluationResult] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feasible": self.feasible,
            "primary_failure_code": self.primary_failure_code,
            "primary_failure_reason": self.primary_failure_reason,
            "evaluated_rules": self.evaluated_rules,
            "evidence": self.evidence,
            "rule_results": [
                {
                    "rule_name": r.rule_name,
                    "passed": r.passed,
                    "reason_code": r.reason_code,
                    "reason": r.reason,
                    "evidence": r.evidence,
                }
                for r in self.rule_results
            ],
        }


@dataclass(frozen=True)
class LastSafeDecisionClock:
    """Estimates when a recovery or delivery option will cease to be feasible."""

    batch_id: str
    shelter_id: str
    safe_deadline: datetime
    latest_useful_decision_time: datetime
    remaining_safe_handling_minutes: float
    remaining_decision_window_minutes: float
    is_feasible: bool
    is_urgently_closing: bool
    travel_minutes: int
    handoff_minutes: int
    safety_buffer_minutes: int
    confirmation_minutes: int
    notification_minutes: int
    checked_at: datetime
    invalidating_factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "shelter_id": self.shelter_id,
            "safe_deadline": self.safe_deadline.isoformat(),
            "latest_useful_decision_time": self.latest_useful_decision_time.isoformat(),
            "remaining_safe_handling_minutes": round(self.remaining_safe_handling_minutes, 1),
            "remaining_decision_window_minutes": round(self.remaining_decision_window_minutes, 1),
            "is_feasible": self.is_feasible,
            "is_urgently_closing": self.is_urgently_closing,
            "travel_minutes": self.travel_minutes,
            "handoff_minutes": self.handoff_minutes,
            "safety_buffer_minutes": self.safety_buffer_minutes,
            "confirmation_minutes": self.confirmation_minutes,
            "notification_minutes": self.notification_minutes,
            "checked_at": self.checked_at.isoformat(),
            "invalidating_factors": self.invalidating_factors,
        }


class SafetyEngine:
    """Evaluates the 10 Hard Feasibility Constraints and Last-Safe-Decision Clocks."""

    @classmethod
    def evaluate_feasibility(
        cls,
        batch: Batch,
        rider: Rider,
        shelter: Shelter,
        quantity: int,
        travel_minutes: int,
        handoff_minutes: int,
        now: datetime,
        is_route_accessible: bool = True,
        actor_role: str = "DISPATCHER",
        max_heartbeat_staleness_minutes: int = 120,
    ) -> SafetyEvaluationReport:
        rule_results: list[RuleEvaluationResult] = []
        evaluated_rules: list[str] = []

        # 1. Quantity Positive and Durations Non-Negative
        if quantity <= 0:
            res = RuleEvaluationResult(
                rule_name="QUANTITY_POSITIVE",
                passed=False,
                reason_code=ErrorCode.INVALID_QUANTITY,
                reason="Quantity must be strictly positive",
                evidence={"quantity": quantity},
            )
            return cls._fail_fast(res, [res])
        rule_results.append(RuleEvaluationResult(rule_name="QUANTITY_POSITIVE", passed=True))
        evaluated_rules.append("QUANTITY_POSITIVE")

        if travel_minutes < 0 or handoff_minutes < 0:
            res = RuleEvaluationResult(
                rule_name="DURATION_NON_NEGATIVE",
                passed=False,
                reason_code=ErrorCode.INVALID_DURATION,
                reason="Travel and handoff durations cannot be negative",
                evidence={"travel_minutes": travel_minutes, "handoff_minutes": handoff_minutes},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="DURATION_NON_NEGATIVE", passed=True))
        evaluated_rules.append("DURATION_NON_NEGATIVE")

        # 2. Hard Constraint 1: Inventory available
        if batch.available_quantity < quantity:
            res = RuleEvaluationResult(
                rule_name="INVENTORY_AVAILABLE",
                passed=False,
                reason_code=ErrorCode.INVENTORY_INSUFFICIENT,
                reason=f"Batch has only {batch.available_quantity} available units, requested {quantity}",
                evidence={"available": batch.available_quantity, "requested": quantity},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="INVENTORY_AVAILABLE", passed=True))
        evaluated_rules.append("INVENTORY_AVAILABLE")

        # 3. Hard Constraint 2: Rider Capacity & Availability
        if not rider.available or rider.status != RiderStatus.AVAILABLE:
            res = RuleEvaluationResult(
                rule_name="RIDER_AVAILABLE",
                passed=False,
                reason_code=ErrorCode.RIDER_UNAVAILABLE,
                reason=f"Rider is currently {rider.status.value}",
                evidence={"status": rider.status.value, "available": rider.available},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="RIDER_AVAILABLE", passed=True))
        evaluated_rules.append("RIDER_AVAILABLE")

        if rider.remaining_capacity < quantity:
            res = RuleEvaluationResult(
                rule_name="RIDER_CAPACITY",
                passed=False,
                reason_code=ErrorCode.RIDER_CAPACITY_EXCEEDED,
                reason=f"Assignment ({quantity}) exceeds rider's remaining capacity ({rider.remaining_capacity})",
                evidence={"remaining_capacity": rider.remaining_capacity, "requested": quantity},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="RIDER_CAPACITY", passed=True))
        evaluated_rules.append("RIDER_CAPACITY")

        # 4. Hard Constraint 3: Recipient demand and receiving capacity
        if not shelter.open or shelter.status == ShelterStatus.CLOSED:
            res = RuleEvaluationResult(
                rule_name="SHELTER_OPEN",
                passed=False,
                reason_code=ErrorCode.SHELTER_CLOSED,
                reason="Receiving shelter is closed",
                evidence={"status": shelter.status.value, "open": shelter.open},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="SHELTER_OPEN", passed=True))
        evaluated_rules.append("SHELTER_OPEN")

        if shelter.demand_remaining < quantity:
            res = RuleEvaluationResult(
                rule_name="SHELTER_DEMAND",
                passed=False,
                reason_code=ErrorCode.SHELTER_DEMAND_EXCEEDED,
                reason=f"Assignment ({quantity}) exceeds shelter's remaining demand ({shelter.demand_remaining})",
                evidence={"demand_remaining": shelter.demand_remaining, "requested": quantity},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="SHELTER_DEMAND", passed=True))
        evaluated_rules.append("SHELTER_DEMAND")

        if shelter.receiving_capacity_remaining < quantity:
            res = RuleEvaluationResult(
                rule_name="SHELTER_CAPACITY",
                passed=False,
                reason_code=ErrorCode.SHELTER_CAPACITY_EXCEEDED,
                reason=f"Assignment ({quantity}) exceeds shelter's receiving capacity ({shelter.receiving_capacity_remaining})",
                evidence={"receiving_capacity": shelter.receiving_capacity_remaining, "requested": quantity},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="SHELTER_CAPACITY", passed=True))
        evaluated_rules.append("SHELTER_CAPACITY")

        # 5. Hard Constraint 4: Prerequisites check
        missing = batch.item_rules.required_prerequisites - shelter.prerequisites
        if missing:
            res = RuleEvaluationResult(
                rule_name="PREREQUISITES_SATISFIED",
                passed=False,
                reason_code=ErrorCode.MISSING_PREREQUISITE,
                reason=f"Shelter lacks required prerequisites: {sorted(list(missing))}",
                evidence={"missing": sorted(list(missing)), "required": sorted(list(batch.item_rules.required_prerequisites))},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="PREREQUISITES_SATISFIED", passed=True))
        evaluated_rules.append("PREREQUISITES_SATISFIED")

        # 6. Hard Constraint 5: Storage Compatibility (e.g. COLD requires refrigeration)
        if batch.item_rules.storage_requirement == StorageRequirement.COLD and "refrigeration" not in shelter.prerequisites:
            res = RuleEvaluationResult(
                rule_name="STORAGE_COMPATIBILITY",
                passed=False,
                reason_code=ErrorCode.MISSING_PREREQUISITE,
                reason="Cold-chain item requires refrigeration storage at destination",
                evidence={"required_storage": "COLD"},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="STORAGE_COMPATIBILITY", passed=True))
        evaluated_rules.append("STORAGE_COMPATIBILITY")

        # 7. Hard Constraint 6: Safe-Handling Deadline
        safe_until = batch.item_rules.safe_until(batch.created_at)
        total_trip_minutes = travel_minutes + handoff_minutes + batch.item_rules.safety_buffer_minutes
        estimated_arrival = now.replace(microsecond=0) + timedelta(minutes=total_trip_minutes)

        if estimated_arrival > safe_until:
            res = RuleEvaluationResult(
                rule_name="SAFETY_DEADLINE",
                passed=False,
                reason_code=ErrorCode.SAFETY_DEADLINE_UNSAFE,
                reason="Delivery cannot complete prior to safe-handling deadline with required safety buffer",
                evidence={
                    "estimated_completion": estimated_arrival.isoformat(),
                    "safe_until": safe_until.isoformat(),
                    "total_trip_minutes": total_trip_minutes,
                },
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="SAFETY_DEADLINE", passed=True))
        evaluated_rules.append("SAFETY_DEADLINE")

        # 8. Hard Constraint 7: Receiving Hours & Staffing
        arrival_hour = estimated_arrival.hour
        if not shelter.receiving_hours.is_within(arrival_hour):
            res = RuleEvaluationResult(
                rule_name="RECEIVING_HOURS",
                passed=False,
                reason_code=ErrorCode.DESTINATION_UNAVAILABLE,
                reason=f"Estimated arrival at {arrival_hour}:00 is outside shelter receiving hours ({shelter.receiving_hours.open_hour}:00 - {shelter.receiving_hours.close_hour}:00)",
                evidence={"arrival_hour": arrival_hour, "open_hour": shelter.receiving_hours.open_hour, "close_hour": shelter.receiving_hours.close_hour},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="RECEIVING_HOURS", passed=True))
        evaluated_rules.append("RECEIVING_HOURS")

        # 9. Hard Constraint 8: Route Accessibility (Disaster / Flood disruption check)
        if not is_route_accessible:
            res = RuleEvaluationResult(
                rule_name="ROUTE_ACCESSIBLE",
                passed=False,
                reason_code=ErrorCode.ROUTE_INFEASIBLE,
                reason="Route or destination is blocked or rendered inaccessible by hazards (e.g. flood)",
                evidence={"is_route_accessible": False},
            )
            return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="ROUTE_ACCESSIBLE", passed=True))
        evaluated_rules.append("ROUTE_ACCESSIBLE")

        # 10. Hard Constraint 9: Data Freshness
        if rider.last_heartbeat_at is not None:
            staleness = (now - rider.last_heartbeat_at).total_seconds() / 60.0
            if staleness > max_heartbeat_staleness_minutes:
                res = RuleEvaluationResult(
                    rule_name="DATA_FRESHNESS",
                    passed=False,
                    reason_code=ErrorCode.RIDER_HEARTBEAT_EXPIRED,
                    reason=f"Rider telemetry is stale ({round(staleness)} mins since last heartbeat)",
                    evidence={"staleness_minutes": staleness, "threshold": max_heartbeat_staleness_minutes},
                )
                return cls._fail_fast(res, rule_results)
        rule_results.append(RuleEvaluationResult(rule_name="DATA_FRESHNESS", passed=True))
        evaluated_rules.append("DATA_FRESHNESS")

        evidence = {
            "batch_id": batch.id,
            "rider_id": rider.id,
            "shelter_id": shelter.id,
            "quantity": quantity,
            "available_quantity": batch.available_quantity,
            "rider_remaining_capacity": rider.remaining_capacity,
            "shelter_demand_remaining": shelter.demand_remaining,
            "estimated_completion": estimated_arrival.isoformat(),
            "safe_until": safe_until.isoformat(),
        }

        return SafetyEvaluationReport(
            feasible=True,
            evaluated_rules=evaluated_rules,
            rule_results=rule_results,
            evidence=evidence,
        )

    @classmethod
    def calculate_last_safe_decision(
        cls,
        batch: Batch,
        shelter_id: str,
        travel_minutes: int,
        handoff_minutes: int,
        now: datetime,
        confirmation_minutes: int = 3,
        notification_minutes: int = 2,
    ) -> LastSafeDecisionClock:
        """Calculates the deadline before which a recovery or dispatch decision must be made."""
        safe_deadline = batch.item_rules.safe_until(batch.created_at)
        safety_buffer = batch.item_rules.safety_buffer_minutes

        total_overhead_minutes = (
            travel_minutes
            + handoff_minutes
            + safety_buffer
            + confirmation_minutes
            + notification_minutes
        )

        latest_useful_decision = safe_deadline - timedelta(minutes=total_overhead_minutes)

        remaining_safe_sec = (safe_deadline - now).total_seconds()
        remaining_safe_min = max(0.0, remaining_safe_sec / 60.0)

        decision_window_sec = (latest_useful_decision - now).total_seconds()
        decision_window_min = decision_window_sec / 60.0

        is_feasible = decision_window_min >= 0.0
        is_urgently_closing = 0.0 <= decision_window_min <= 15.0

        invalidating_factors = []
        if decision_window_min < 0:
            invalidating_factors.append("decision_window_expired")
        if remaining_safe_min < total_overhead_minutes:
            invalidating_factors.append("insufficient_safe_handling_duration")

        return LastSafeDecisionClock(
            batch_id=batch.id,
            shelter_id=shelter_id,
            safe_deadline=safe_deadline,
            latest_useful_decision_time=latest_useful_decision,
            remaining_safe_handling_minutes=remaining_safe_min,
            remaining_decision_window_minutes=decision_window_min,
            is_feasible=is_feasible,
            is_urgently_closing=is_urgently_closing,
            travel_minutes=travel_minutes,
            handoff_minutes=handoff_minutes,
            safety_buffer_minutes=safety_buffer,
            confirmation_minutes=confirmation_minutes,
            notification_minutes=notification_minutes,
            checked_at=now,
            invalidating_factors=invalidating_factors,
        )

    @classmethod
    def _fail_fast(
        cls,
        failing_rule: RuleEvaluationResult,
        rule_results: list[RuleEvaluationResult],
    ) -> SafetyEvaluationReport:
        evaluated_rules = [r.rule_name for r in rule_results]
        return SafetyEvaluationReport(
            feasible=False,
            primary_failure_code=failing_rule.reason_code,
            primary_failure_reason=failing_rule.reason,
            evaluated_rules=evaluated_rules,
            rule_results=rule_results,
            evidence=failing_rule.evidence,
        )
