from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class EventType(StrEnum):
    # Inventory events
    DONATION_BATCH_CREATED = "DONATION_BATCH_CREATED"
    INVENTORY_RESERVED = "INVENTORY_RESERVED"
    INVENTORY_RELEASED = "INVENTORY_RELEASED"

    # Allocation events
    ALLOCATION_CLAIMED = "ALLOCATION_CLAIMED"
    ALLOCATION_ACKNOWLEDGED = "ALLOCATION_ACKNOWLEDGED"
    ALLOCATION_EXPIRED = "ALLOCATION_EXPIRED"
    ALLOCATION_CANCELLED = "ALLOCATION_CANCELLED"

    # Physical Delivery events
    CARGO_PICKED_UP = "CARGO_PICKED_UP"
    DELIVERY_IN_TRANSIT = "DELIVERY_IN_TRANSIT"
    DELIVERY_REROUTE_REQUESTED = "DELIVERY_REROUTE_REQUESTED"
    DELIVERY_REROUTED = "DELIVERY_REROUTED"
    DELIVERY_COMPLETED = "DELIVERY_COMPLETED"
    DELIVERY_FAILED = "DELIVERY_FAILED"

    # Operational status events
    RIDER_STATUS_CHANGED = "RIDER_STATUS_CHANGED"
    RIDER_HEARTBEAT_RECORDED = "RIDER_HEARTBEAT_RECORDED"
    SHELTER_STATUS_CHANGED = "SHELTER_STATUS_CHANGED"
    SHELTER_DEMAND_UPDATED = "SHELTER_DEMAND_UPDATED"

    # Incident events
    INCIDENT_RECORDED = "INCIDENT_RECORDED"
    INCIDENT_ESCALATED = "INCIDENT_ESCALATED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"


@dataclass(frozen=True)
class OperationalEvent:
    """Tamper-evident append-only operational event."""

    id: str
    event_type: EventType | str
    aggregate_id: str
    aggregate_type: str
    occurred_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)
    actor: str = "system"
    correlation_id: str = field(default_factory=lambda: uuid4().hex)
    evidence: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: EventType | str,
        aggregate_id: str,
        aggregate_type: str,
        occurred_at: datetime,
        payload: dict[str, Any] | None = None,
        actor: str = "system",
        correlation_id: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> OperationalEvent:
        return cls(
            id=f"evt_{uuid4().hex}",
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            occurred_at=occurred_at,
            payload=payload or {},
            actor=actor,
            correlation_id=correlation_id or uuid4().hex,
            evidence=evidence or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": str(self.event_type),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "occurred_at": self.occurred_at.isoformat(),
            "payload": self.payload,
            "actor": self.actor,
            "correlation_id": self.correlation_id,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class AuditRecord:
    """Audit log entry capturing decision context and evaluation criteria."""

    id: str
    event_id: str
    actor: str
    command: str
    decision: str
    constraints_evaluated: list[str]
    evidence: dict[str, Any]
    created_at: datetime

    @classmethod
    def record(
        cls,
        actor: str,
        command: str,
        decision: str,
        constraints: list[str],
        evidence: dict[str, Any],
        now: datetime,
        event_id: str | None = None,
    ) -> AuditRecord:
        return cls(
            id=f"aud_{uuid4().hex}",
            event_id=event_id or f"evt_{uuid4().hex}",
            actor=actor,
            command=command,
            decision=decision,
            constraints_evaluated=constraints,
            evidence=evidence,
            created_at=now,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "actor": self.actor,
            "command": self.command,
            "decision": self.decision,
            "constraints_evaluated": self.constraints_evaluated,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
        }
