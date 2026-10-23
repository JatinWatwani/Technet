from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    DONOR = "DONOR"
    RIDER = "RIDER"
    SHELTER_COORDINATOR = "SHELTER_COORDINATOR"
    EMERGENCY_COORDINATOR = "EMERGENCY_COORDINATOR"


@dataclass
class User:
    id: str
    name: str
    email: str
    role: UserRole
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Donor:
    id: str
    user_id: str | None = None
    organization_name: str = ""
    contact_phone: str = ""
    address: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class StorageRequirement(StrEnum):
    AMBIENT = "AMBIENT"
    COLD = "COLD"
    FROZEN = "FROZEN"


@dataclass(frozen=True)
class ItemRules:
    safe_handling_minutes: int
    safety_buffer_minutes: int = 0
    required_prerequisites: frozenset[str] = frozenset()
    storage_requirement: StorageRequirement = StorageRequirement.AMBIENT

    def safe_until(self, created_at: datetime) -> datetime:
        return created_at + timedelta(minutes=self.safe_handling_minutes)


@dataclass
class Batch:
    id: str
    original_quantity: int
    item_rules: ItemRules
    created_at: datetime
    donor_id: str = "donor_default"
    item_type: str = "humanitarian_supplies"
    available_quantity: int = 0
    reserved_quantity: int = 0
    picked_up_quantity: int = 0
    delivered_quantity: int = 0
    spoiled_quantity: int = 0

    def __post_init__(self) -> None:
        if self.original_quantity <= 0:
            raise ValueError("original_quantity must be positive")
        # Default initialization for new batch
        if (
            self.available_quantity == 0
            and self.reserved_quantity == 0
            and self.picked_up_quantity == 0
            and self.delivered_quantity == 0
            and self.spoiled_quantity == 0
        ):
            self.available_quantity = self.original_quantity
        self.validate_invariants()

    def validate_invariants(self) -> None:
        """Enforce strict quantity conservation and non-negativity."""
        quantities = [
            self.available_quantity,
            self.reserved_quantity,
            self.picked_up_quantity,
            self.delivered_quantity,
            self.spoiled_quantity,
        ]
        if any(q < 0 for q in quantities):
            raise ValueError("Quantities cannot be negative")
        if sum(quantities) != self.original_quantity:
            raise ValueError(
                f"Quantity conservation violated: sum={sum(quantities)} != original={self.original_quantity}"
            )


@dataclass(frozen=True)
class GeoLocation:
    latitude: float
    longitude: float


class RiderStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT = "IN_TRANSIT"
    PAUSED = "PAUSED"
    OFFLINE = "OFFLINE"


@dataclass
class Rider:
    id: str
    capacity: int
    active_load: int = 0
    available: bool = True
    user_id: str | None = None
    status: RiderStatus = RiderStatus.AVAILABLE
    location: GeoLocation | None = None
    last_heartbeat_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if self.active_load < 0:
            raise ValueError("active_load cannot be negative")
        if self.active_load > self.capacity:
            raise ValueError("active_load cannot exceed total capacity")

    @property
    def remaining_capacity(self) -> int:
        return self.capacity - self.active_load


class ShelterStatus(StrEnum):
    OPEN = "OPEN"
    AT_CAPACITY = "AT_CAPACITY"
    CLOSED = "CLOSED"
    REOPENING_REVIEW = "REOPENING_REVIEW"


@dataclass(frozen=True)
class ReceivingHours:
    open_hour: int = 0
    close_hour: int = 24

    def is_within(self, hour: int) -> bool:
        if self.open_hour <= self.close_hour:
            return self.open_hour <= hour < self.close_hour
        # Overnight receiving window
        return hour >= self.open_hour or hour < self.close_hour


@dataclass
class Shelter:
    id: str
    demand_remaining: int
    receiving_capacity_remaining: int
    name: str = ""
    prerequisites: frozenset[str] = frozenset()
    open: bool = True
    status: ShelterStatus = ShelterStatus.OPEN
    location: GeoLocation | None = None
    receiving_hours: ReceivingHours = field(default_factory=ReceivingHours)

    def __post_init__(self) -> None:
        if self.demand_remaining < 0:
            raise ValueError("demand_remaining cannot be negative")
        if self.receiving_capacity_remaining < 0:
            raise ValueError("receiving_capacity_remaining cannot be negative")
        if not self.open:
            self.status = ShelterStatus.CLOSED


class AllocationState(StrEnum):
    CLAIMED = "CLAIMED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PICKED_UP = "PICKED_UP"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


@dataclass
class Allocation:
    id: str
    batch_id: str
    rider_id: str
    shelter_id: str
    quantity: int
    travel_minutes: int
    handoff_minutes: int
    state: AllocationState
    claimed_at: datetime
    safe_until: datetime
    lease_expires_at: datetime | None = None
    acknowledged_at: datetime | None = None
    picked_up_at: datetime | None = None


class DeliveryState(StrEnum):
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    REROUTE_PENDING = "REROUTE_PENDING"
    DELIVERED = "DELIVERED"
    INCIDENT_REVIEW = "INCIDENT_REVIEW"


@dataclass
class Delivery:
    id: str
    allocation_id: str
    batch_id: str
    rider_id: str
    current_shelter_id: str
    quantity: int
    state: DeliveryState
    picked_up_at: datetime
    delivered_at: datetime | None = None
    current_location: GeoLocation | None = None
    destination_history: list[str] = field(default_factory=list)


class IncidentSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"


@dataclass
class Incident:
    id: str
    severity: IncidentSeverity
    status: IncidentStatus
    affected_entity_type: str
    affected_entity_id: str
    reason_code: str
    description: str
    created_at: datetime
    evidence: dict[str, Any] = field(default_factory=dict)
    resolved_at: datetime | None = None


@dataclass(frozen=True)
class DispatchDecision:
    feasible: bool
    reason_code: str | None = None
    reason: str | None = None
    allocation: Allocation | None = None
    evidence: dict[str, object] = field(default_factory=dict)
