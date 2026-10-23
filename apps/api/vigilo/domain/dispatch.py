from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from .clock import Clock, SystemClock
from .errors import (
    ConstraintViolationError,
    EntityNotFoundError,
    ErrorCode,
    StateTransitionError,
    VigiloError,
)
from .events import AuditRecord, EventType, OperationalEvent
from .ledger import (
    InventoryLedgerEntry,
    InventoryState,
    ReconciliationReport,
)
from .ledger_service import InventoryLedgerService
from .models import (
    Allocation,
    AllocationState,
    Batch,
    Delivery,
    DeliveryState,
    DispatchDecision,
    Donor,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    Rider,
    RiderStatus,
    Shelter,
    ShelterStatus,
    User,
)
from .state_machines import AllocationStateMachine, DeliveryStateMachine, RiderStateMachine, ShelterStateMachine


@dataclass(frozen=True)
class DispatchRequest:
    batch_id: str
    rider_id: str
    shelter_id: str
    quantity: int
    travel_minutes: int
    handoff_minutes: int
    now: datetime | None = None
    idempotency_key: str | None = None


# Keep backwards compatibility for code importing DispatchError
class DispatchError(VigiloError):
    def __init__(self, code: str, message: str, evidence: dict[str, object] | None = None) -> None:
        super().__init__(code=code, message=message, evidence=evidence or {})


class DispatchService:
    """Authoritative domain service for dispatch, feasibility, state transitions,
    and immutable inventory ledger tracking."""

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock = clock or SystemClock()
        self.ledger = InventoryLedgerService(clock=self.clock)
        self.users: dict[str, User] = {}
        self.donors: dict[str, Donor] = {}
        self.batches: dict[str, Batch] = {}
        self.riders: dict[str, Rider] = {}
        self.shelters: dict[str, Shelter] = {}
        self.allocations: dict[str, Allocation] = {}
        self.deliveries: dict[str, Delivery] = {}
        self.incidents: dict[str, Incident] = {}
        self.events: list[OperationalEvent] = []
        self.audit_records: list[AuditRecord] = []

    def record_event(
        self,
        event_type: EventType | str,
        aggregate_id: str,
        aggregate_type: str,
        payload: dict[str, Any] | None = None,
        actor: str = "system",
        evidence: dict[str, Any] | None = None,
    ) -> OperationalEvent:
        event = OperationalEvent.create(
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            occurred_at=self.clock.now(),
            payload=payload or {},
            actor=actor,
            evidence=evidence or {},
        )
        self.events.append(event)
        return event

    def preview(self, request: DispatchRequest) -> DispatchDecision:
        now = request.now or self.clock.now()
        batch = self.batches.get(request.batch_id)
        rider = self.riders.get(request.rider_id)
        shelter = self.shelters.get(request.shelter_id)

        evaluated_rules: list[str] = []

        if batch is None:
            return self._rejection(ErrorCode.BATCH_NOT_FOUND, "The batch does not exist.")
        evaluated_rules.append("BATCH_EXISTS")

        if rider is None:
            return self._rejection(ErrorCode.RIDER_NOT_FOUND, "The rider does not exist.")
        evaluated_rules.append("RIDER_EXISTS")

        if shelter is None:
            return self._rejection(ErrorCode.SHELTER_NOT_FOUND, "The shelter does not exist.")
        evaluated_rules.append("SHELTER_EXISTS")

        if request.quantity <= 0:
            return self._rejection(ErrorCode.INVALID_QUANTITY, "Quantity must be positive.")
        evaluated_rules.append("QUANTITY_POSITIVE")

        if request.travel_minutes < 0 or request.handoff_minutes < 0:
            return self._rejection(ErrorCode.INVALID_DURATION, "Travel and handoff minutes cannot be negative.")
        evaluated_rules.append("DURATION_NON_NEGATIVE")

        # Hard constraint 1: Inventory available
        if batch.available_quantity < request.quantity:
            return self._rejection(
                ErrorCode.INVENTORY_INSUFFICIENT,
                "The batch does not have enough available inventory.",
                {"available": batch.available_quantity, "requested": request.quantity},
            )
        evaluated_rules.append("INVENTORY_AVAILABLE")

        # Hard constraint 2: Rider available and within capacity
        if not rider.available or rider.status != RiderStatus.AVAILABLE:
            return self._rejection(ErrorCode.RIDER_UNAVAILABLE, "The rider is not available.")
        if rider.remaining_capacity < request.quantity:
            return self._rejection(
                ErrorCode.RIDER_CAPACITY_EXCEEDED,
                "The assignment exceeds the rider's remaining capacity.",
                {"remaining_capacity": rider.remaining_capacity, "requested": request.quantity},
            )
        evaluated_rules.append("RIDER_CAPACITY_FIT")

        # Hard constraint 3: Shelter open, within demand and receiving capacity
        if not shelter.open or shelter.status == ShelterStatus.CLOSED:
            return self._rejection(ErrorCode.SHELTER_CLOSED, "The shelter is not accepting deliveries.")
        if shelter.demand_remaining < request.quantity:
            return self._rejection(
                ErrorCode.SHELTER_DEMAND_EXCEEDED,
                "The assignment exceeds the shelter's remaining demand.",
                {"demand_remaining": shelter.demand_remaining, "requested": request.quantity},
            )
        if shelter.receiving_capacity_remaining < request.quantity:
            return self._rejection(
                ErrorCode.SHELTER_CAPACITY_EXCEEDED,
                "The assignment exceeds the shelter's receiving capacity.",
                {"capacity_remaining": shelter.receiving_capacity_remaining, "requested": request.quantity},
            )
        evaluated_rules.append("SHELTER_DEMAND_AND_CAPACITY_FIT")

        # Hard constraint 4: Prerequisites check
        missing = batch.item_rules.required_prerequisites - shelter.prerequisites
        if missing:
            return self._rejection(
                ErrorCode.MISSING_PREREQUISITE,
                "The shelter does not have all prerequisites for this supply.",
                {"missing": sorted(missing)},
            )
        evaluated_rules.append("PREREQUISITES_SATISFIED")

        # Hard constraint 5: Safe-handling deadline
        safe_until = batch.item_rules.safe_until(batch.created_at)
        estimated_arrival = now.replace(microsecond=0) + timedelta(
            minutes=request.travel_minutes
            + request.handoff_minutes
            + batch.item_rules.safety_buffer_minutes
        )
        if estimated_arrival > safe_until:
            return self._rejection(
                ErrorCode.SAFETY_DEADLINE_UNSAFE,
                "The delivery cannot complete within the safe-handling deadline.",
                {
                    "estimated_completion": estimated_arrival.isoformat(),
                    "safe_until": safe_until.isoformat(),
                },
            )
        evaluated_rules.append("SAFETY_DEADLINE_SATISFIED")

        evidence = {
            "available_quantity": batch.available_quantity,
            "rider_remaining_capacity": rider.remaining_capacity,
            "shelter_demand_remaining": shelter.demand_remaining,
            "shelter_receiving_capacity_remaining": shelter.receiving_capacity_remaining,
            "estimated_completion": estimated_arrival.isoformat(),
            "safe_until": safe_until.isoformat(),
            "evaluated_rules": evaluated_rules,
        }

        return DispatchDecision(feasible=True, evidence=evidence)

    def commit(self, request: DispatchRequest, actor: str = "dispatcher") -> Allocation:
        now = request.now or self.clock.now()

        # Check idempotency first if key provided
        if request.idempotency_key:
            existing_entry = self.ledger._idempotency_records.get(request.idempotency_key)
            if existing_entry and existing_entry.allocation_id in self.allocations:
                return self.allocations[existing_entry.allocation_id]

        decision = self.preview(request)
        if not decision.feasible:
            self.record_event(
                event_type="DISPATCH_ATTEMPT_REJECTED",
                aggregate_id=request.batch_id,
                aggregate_type="Batch",
                payload={"reason_code": decision.reason_code, "reason": decision.reason},
                actor=actor,
                evidence=decision.evidence,
            )
            raise DispatchError(
                code=decision.reason_code or "DISPATCH_REJECTED",
                message=decision.reason or "Dispatch rejected",
                evidence=decision.evidence,
            )

        batch = self.batches[request.batch_id]
        rider = self.riders[request.rider_id]
        shelter = self.shelters[request.shelter_id]
        safe_until = batch.item_rules.safe_until(batch.created_at)

        # 15-minute lease for acknowledgement and pickup
        lease_expires_at = now + timedelta(minutes=15)
        alloc_id = f"alloc_{uuid4().hex[:12]}"

        # Atomically record hold in the immutable ledger
        self.ledger.hold_reservation(
            batch=batch,
            quantity=request.quantity,
            allocation_id=alloc_id,
            actor=actor,
            reason=f"Claimed by rider {rider.id} for shelter {shelter.id}",
            idempotency_key=request.idempotency_key,
        )

        allocation = Allocation(
            id=alloc_id,
            batch_id=batch.id,
            rider_id=rider.id,
            shelter_id=shelter.id,
            quantity=request.quantity,
            travel_minutes=request.travel_minutes,
            handoff_minutes=request.handoff_minutes,
            state=AllocationState.CLAIMED,
            claimed_at=now,
            lease_expires_at=lease_expires_at,
            safe_until=safe_until,
        )

        rider.active_load += request.quantity
        rider.status = RiderStatus.ASSIGNED

        shelter.demand_remaining -= request.quantity
        shelter.receiving_capacity_remaining -= request.quantity

        self.allocations[allocation.id] = allocation

        # Record domain event & audit log
        self.record_event(
            event_type=EventType.ALLOCATION_CLAIMED,
            aggregate_id=allocation.id,
            aggregate_type="Allocation",
            payload={
                "batch_id": batch.id,
                "rider_id": rider.id,
                "shelter_id": shelter.id,
                "quantity": allocation.quantity,
                "state": allocation.state.value,
            },
            actor=actor,
            evidence=decision.evidence,
        )

        audit = AuditRecord.record(
            actor=actor,
            command="dispatch.commit",
            decision="COMMITTED",
            constraints=decision.evidence.get("evaluated_rules", []),
            evidence=decision.evidence,
            now=now,
        )
        self.audit_records.append(audit)

        return allocation

    def acknowledge_allocation(self, allocation_id: str, actor: str = "rider") -> Allocation:
        allocation = self.allocations.get(allocation_id)
        if allocation is None:
            raise EntityNotFoundError(ErrorCode.ALLOCATION_NOT_FOUND, "Allocation", allocation_id)

        AllocationStateMachine.validate_transition(
            allocation.state, AllocationState.ACKNOWLEDGED, allocation_id
        )

        allocation.state = AllocationState.ACKNOWLEDGED
        allocation.acknowledged_at = self.clock.now()

        self.record_event(
            event_type=EventType.ALLOCATION_ACKNOWLEDGED,
            aggregate_id=allocation.id,
            aggregate_type="Allocation",
            actor=actor,
            payload={"state": allocation.state.value},
        )
        return allocation

    def pickup_allocation(self, allocation_id: str, actor: str = "rider") -> Delivery:
        """Confirm physical pickup of cargo by the rider.

        Transitions ledger state from RESERVED to PICKED_UP,
        updates allocation state to PICKED_UP, and creates an in-transit Delivery entity.
        """
        now = self.clock.now()
        allocation = self.allocations.get(allocation_id)
        if allocation is None:
            raise EntityNotFoundError(ErrorCode.ALLOCATION_NOT_FOUND, "Allocation", allocation_id)

        AllocationStateMachine.validate_transition(
            allocation.state, AllocationState.PICKED_UP, allocation_id
        )

        allocation.state = AllocationState.PICKED_UP
        allocation.picked_up_at = now

        batch = self.batches[allocation.batch_id]
        deliv_id = f"deliv_{uuid4().hex[:12]}"

        # Atomically update ledger
        self.ledger.record_pickup(
            batch=batch,
            quantity=allocation.quantity,
            allocation_id=allocation.id,
            delivery_id=deliv_id,
            actor=actor,
            reason=f"Picked up by rider {allocation.rider_id}",
        )

        rider = self.riders[allocation.rider_id]
        rider.status = RiderStatus.IN_TRANSIT

        # Create physical Delivery entity
        delivery = Delivery(
            id=deliv_id,
            allocation_id=allocation.id,
            batch_id=batch.id,
            rider_id=rider.id,
            current_shelter_id=allocation.shelter_id,
            quantity=allocation.quantity,
            state=DeliveryState.PICKED_UP,
            picked_up_at=now,
            destination_history=[allocation.shelter_id],
        )
        self.deliveries[delivery.id] = delivery

        self.record_event(
            event_type=EventType.CARGO_PICKED_UP,
            aggregate_id=delivery.id,
            aggregate_type="Delivery",
            actor=actor,
            payload={"allocation_id": allocation.id, "quantity": delivery.quantity},
        )
        return delivery

    def deliver_cargo(self, delivery_id: str, actor: str = "rider") -> Delivery:
        """Confirm delivery of physical cargo to recipient shelter."""
        now = self.clock.now()
        delivery = self.deliveries.get(delivery_id)
        if delivery is None:
            raise EntityNotFoundError(ErrorCode.DELIVERY_NOT_FOUND, "Delivery", delivery_id)

        DeliveryStateMachine.validate_transition(
            delivery.state, DeliveryState.DELIVERED, delivery_id
        )

        delivery.state = DeliveryState.DELIVERED
        delivery.delivered_at = now

        batch = self.batches[delivery.batch_id]
        # Atomically update ledger
        self.ledger.confirm_delivery(
            batch=batch,
            quantity=delivery.quantity,
            delivery_id=delivery.id,
            actor=actor,
            reason=f"Safely delivered to shelter {delivery.current_shelter_id}",
        )

        rider = self.riders[delivery.rider_id]
        rider.active_load -= delivery.quantity
        if rider.active_load == 0:
            rider.status = RiderStatus.AVAILABLE

        self.record_event(
            event_type=EventType.DELIVERY_COMPLETED,
            aggregate_id=delivery.id,
            aggregate_type="Delivery",
            actor=actor,
            payload={"destination": delivery.current_shelter_id, "quantity": delivery.quantity},
        )
        return delivery

    def expire_allocation(self, allocation_id: str, actor: str = "recovery_worker", reason: str = "Lease expired") -> Allocation:
        """Expire an unpicked allocation and release inventory back to available stock.

        Strict invariant: If cargo has already been PICKED_UP, it CANNOT be expired.
        """
        allocation = self.allocations.get(allocation_id)
        if allocation is None:
            raise EntityNotFoundError(ErrorCode.ALLOCATION_NOT_FOUND, "Allocation", allocation_id)

        AllocationStateMachine.validate_transition(
            allocation.state, AllocationState.EXPIRED, allocation_id
        )

        allocation.state = AllocationState.EXPIRED

        batch = self.batches[allocation.batch_id]
        self.ledger.release_reservation(
            batch=batch,
            quantity=allocation.quantity,
            allocation_id=allocation.id,
            actor=actor,
            reason=reason,
        )

        rider = self.riders[allocation.rider_id]
        rider.active_load -= allocation.quantity
        if rider.active_load == 0:
            rider.status = RiderStatus.AVAILABLE

        shelter = self.shelters[allocation.shelter_id]
        shelter.demand_remaining += allocation.quantity
        shelter.receiving_capacity_remaining += allocation.quantity

        self.record_event(
            event_type=EventType.ALLOCATION_EXPIRED,
            aggregate_id=allocation.id,
            aggregate_type="Allocation",
            actor=actor,
            payload={"quantity": allocation.quantity, "reason": reason},
        )
        return allocation

    def get_batch_ledger(self, batch_id: str) -> list[InventoryLedgerEntry]:
        if batch_id not in self.batches:
            raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", batch_id)
        return self.ledger.get_ledger(batch_id)

    def reconcile_batch(self, batch_id: str) -> ReconciliationReport:
        if batch_id not in self.batches:
            raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", batch_id)
        return self.ledger.reconcile(self.batches[batch_id])

    def load_seed(self, base_time: datetime | None = None) -> None:
        """Load deterministic seed entities into domain memory and record genesis intake."""
        from .seed import create_seed_data

        self.users.clear()
        self.donors.clear()
        self.batches.clear()
        self.riders.clear()
        self.shelters.clear()
        self.allocations.clear()
        self.deliveries.clear()
        self.incidents.clear()
        self.events.clear()
        self.audit_records.clear()
        self.ledger = InventoryLedgerService(clock=self.clock)

        data = create_seed_data(base_time or self.clock.now())
        for user in data["users"]:
            self.users[user.id] = user
        for donor in data["donors"]:
            self.donors[donor.id] = donor
        for batch in data["batches"]:
            self.batches[batch.id] = batch
            # Record initial intake entry in the ledger
            self.ledger.record_intake(batch, reason="Seed data initial intake")
        for rider in data["riders"]:
            self.riders[rider.id] = rider
        for shelter in data["shelters"]:
            self.shelters[shelter.id] = shelter

    @staticmethod
    def _rejection(code: ErrorCode | str, reason: str, evidence: dict[str, object] | None = None) -> DispatchDecision:
        return DispatchDecision(feasible=False, reason_code=str(code), reason=reason, evidence=evidence or {})
