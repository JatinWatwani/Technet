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
from .outbox import OutboxMessage, OutboxPublisher, OutboxStatus
from .candidate_engine import CandidateAssignment, CandidateEngine, CandidateGenerationResult
from .ledger import (
    InventoryLedgerEntry,
    InventoryState,
    ReconciliationReport,
)
from .ledger_service import InventoryLedgerService
from .safety_engine import LastSafeDecisionClock, SafetyEngine, SafetyEvaluationReport
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
        self.outbox_messages: list[OutboxMessage] = []
        self.outbox_publisher = OutboxPublisher()

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
        outbox_msg = OutboxMessage.from_event(event)
        self.outbox_messages.append(outbox_msg)
        return event

    def publish_outbox(self, limit: int = 50) -> int:
        """Publish pending outbox messages to registered subscribers."""
        count = 0
        now = self.clock.now()
        for msg in self.outbox_messages:
            if msg.status == OutboxStatus.PENDING:
                success = self.outbox_publisher.publish(msg, now)
                if success:
                    count += 1
                if count >= limit:
                    break
        return count

    def preview(self, request: DispatchRequest) -> DispatchDecision:
        now = request.now or self.clock.now()
        batch = self.batches.get(request.batch_id)
        rider = self.riders.get(request.rider_id)
        shelter = self.shelters.get(request.shelter_id)

        if batch is None:
            return self._rejection(ErrorCode.BATCH_NOT_FOUND, "The batch does not exist.")
        if rider is None:
            return self._rejection(ErrorCode.RIDER_NOT_FOUND, "The rider does not exist.")
        if shelter is None:
            return self._rejection(ErrorCode.SHELTER_NOT_FOUND, "The shelter does not exist.")

        report = SafetyEngine.evaluate_feasibility(
            batch=batch,
            rider=rider,
            shelter=shelter,
            quantity=request.quantity,
            travel_minutes=request.travel_minutes,
            handoff_minutes=request.handoff_minutes,
            now=now,
        )

        if not report.feasible:
            return self._rejection(
                code=report.primary_failure_code or "DISPATCH_REJECTED",
                reason=report.primary_failure_reason or "Assignment infeasible",
                evidence=report.evidence,
            )

        return DispatchDecision(feasible=True, evidence=report.evidence)

    def evaluate_safety(
        self,
        batch_id: str,
        rider_id: str,
        shelter_id: str,
        quantity: int,
        travel_minutes: int,
        handoff_minutes: int,
        is_route_accessible: bool = True,
    ) -> SafetyEvaluationReport:
        batch = self.batches.get(batch_id)
        rider = self.riders.get(rider_id)
        shelter = self.shelters.get(shelter_id)

        if batch is None:
            raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", batch_id)
        if rider is None:
            raise EntityNotFoundError(ErrorCode.RIDER_NOT_FOUND, "Rider", rider_id)
        if shelter is None:
            raise EntityNotFoundError(ErrorCode.SHELTER_NOT_FOUND, "Shelter", shelter_id)

        return SafetyEngine.evaluate_feasibility(
            batch=batch,
            rider=rider,
            shelter=shelter,
            quantity=quantity,
            travel_minutes=travel_minutes,
            handoff_minutes=handoff_minutes,
            now=self.clock.now(),
            is_route_accessible=is_route_accessible,
        )

    def calculate_safety_clock(
        self,
        batch_id: str,
        shelter_id: str,
        travel_minutes: int = 25,
        handoff_minutes: int = 10,
    ) -> LastSafeDecisionClock:
        batch = self.batches.get(batch_id)
        if batch is None:
            raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", batch_id)
        shelter = self.shelters.get(shelter_id)
        if shelter is None:
            raise EntityNotFoundError(ErrorCode.SHELTER_NOT_FOUND, "Shelter", shelter_id)

        return SafetyEngine.calculate_last_safe_decision(
            batch=batch,
            shelter_id=shelter_id,
            travel_minutes=travel_minutes,
            handoff_minutes=handoff_minutes,
            now=self.clock.now(),
        )

    def generate_candidates(self, batch_id: str) -> CandidateGenerationResult:
        batch = self.batches.get(batch_id)
        if batch is None:
            raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", batch_id)

        return CandidateEngine.generate_and_rank_candidates(
            batch=batch,
            riders=list(self.riders.values()),
            shelters=list(self.shelters.values()),
            now=self.clock.now(),
        )

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

    def acknowledge_allocation(self, allocation_id: str, actor: str = "rider", actor_role: str | None = None) -> Allocation:
        now = self.clock.now()
        if actor_role and actor_role not in ("RIDER", "ADMIN", "DISPATCHER"):
            raise VigiloError(
                ErrorCode.AUTHORIZATION_DENIED,
                f"Actor role '{actor_role}' is not authorized to acknowledge allocations",
                evidence={"actor": actor, "actor_role": actor_role},
            )

        allocation = self.allocations.get(allocation_id)
        if allocation is None:
            raise EntityNotFoundError(ErrorCode.ALLOCATION_NOT_FOUND, "Allocation", allocation_id)

        if allocation.lease_expires_at and now > allocation.lease_expires_at:
            raise VigiloError(
                ErrorCode.CLAIM_EXPIRED,
                f"Allocation lease expired at {allocation.lease_expires_at.isoformat()}",
                evidence={"lease_expires_at": allocation.lease_expires_at.isoformat(), "now": now.isoformat()},
            )

        AllocationStateMachine.validate_transition(
            allocation.state, AllocationState.ACKNOWLEDGED, allocation_id
        )

        allocation.state = AllocationState.ACKNOWLEDGED
        allocation.acknowledged_at = now

        event = self.record_event(
            event_type=EventType.ALLOCATION_ACKNOWLEDGED,
            aggregate_id=allocation.id,
            aggregate_type="Allocation",
            actor=actor,
            payload={"state": allocation.state.value, "batch_id": allocation.batch_id},
        )
        audit = AuditRecord.record(
            actor=actor,
            command="allocation.acknowledge",
            decision="ACKNOWLEDGED",
            constraints=["LEASE_ACTIVE"],
            evidence={"allocation_id": allocation_id, "state": allocation.state.value},
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)
        return allocation

    def pickup_allocation(self, allocation_id: str, actor: str = "rider", actor_role: str | None = None) -> Delivery:
        """Confirm physical pickup of cargo by the rider.

        Transitions ledger state from RESERVED to PICKED_UP,
        updates allocation state to PICKED_UP, and creates an in-transit Delivery entity.
        """
        now = self.clock.now()
        if actor_role and actor_role not in ("RIDER", "ADMIN", "DISPATCHER"):
            raise VigiloError(
                ErrorCode.AUTHORIZATION_DENIED,
                f"Actor role '{actor_role}' is not authorized to pick up cargo",
                evidence={"actor": actor, "actor_role": actor_role},
            )

        allocation = self.allocations.get(allocation_id)
        if allocation is None:
            raise EntityNotFoundError(ErrorCode.ALLOCATION_NOT_FOUND, "Allocation", allocation_id)

        if allocation.state == AllocationState.CLAIMED and allocation.lease_expires_at and now > allocation.lease_expires_at:
            raise VigiloError(
                ErrorCode.CLAIM_EXPIRED,
                f"Allocation lease expired at {allocation.lease_expires_at.isoformat()} prior to pickup",
                evidence={"lease_expires_at": allocation.lease_expires_at.isoformat(), "now": now.isoformat()},
            )

        if now > allocation.safe_until:
            raise VigiloError(
                ErrorCode.SAFETY_DEADLINE_UNSAFE,
                f"Safe-handling deadline passed at {allocation.safe_until.isoformat()}",
                evidence={"safe_until": allocation.safe_until.isoformat(), "now": now.isoformat()},
            )

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

        event = self.record_event(
            event_type=EventType.CARGO_PICKED_UP,
            aggregate_id=delivery.id,
            aggregate_type="Delivery",
            actor=actor,
            payload={"allocation_id": allocation.id, "quantity": delivery.quantity, "batch_id": batch.id},
        )
        audit = AuditRecord.record(
            actor=actor,
            command="allocation.pickup",
            decision="PICKED_UP",
            constraints=["SAFE_HANDLING_DEADLINE", "PHYSICAL_CUSTODY_TRANSFERRED"],
            evidence={"allocation_id": allocation.id, "delivery_id": delivery.id, "quantity": delivery.quantity},
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)
        return delivery

    def deliver_cargo(self, delivery_id: str, actor: str = "rider", actor_role: str | None = None) -> Delivery:
        """Confirm delivery of physical cargo to recipient shelter."""
        now = self.clock.now()
        if actor_role and actor_role not in ("RIDER", "ADMIN", "DISPATCHER", "SHELTER_COORDINATOR"):
            raise VigiloError(
                ErrorCode.AUTHORIZATION_DENIED,
                f"Actor role '{actor_role}' is not authorized to confirm delivery",
                evidence={"actor": actor, "actor_role": actor_role},
            )

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

        shelter = self.shelters.get(delivery.current_shelter_id)
        if shelter:
            shelter.demand_remaining = max(0, shelter.demand_remaining - delivery.quantity)

        event = self.record_event(
            event_type=EventType.DELIVERY_COMPLETED,
            aggregate_id=delivery.id,
            aggregate_type="Delivery",
            actor=actor,
            payload={"destination": delivery.current_shelter_id, "quantity": delivery.quantity, "batch_id": batch.id},
        )
        audit = AuditRecord.record(
            actor=actor,
            command="delivery.complete",
            decision="DELIVERED",
            constraints=["INVENTORY_CONSERVED", "DELIVERY_CONFIRMED"],
            evidence={"delivery_id": delivery.id, "quantity": delivery.quantity, "destination": delivery.current_shelter_id},
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)
        return delivery

    def cancel_allocation(
        self,
        allocation_id: str,
        actor: str = "dispatcher",
        reason: str = "Manual cancellation",
        actor_role: str | None = None,
    ) -> Allocation:
        """Cancel an unpicked allocation and release inventory reservation back to available stock."""
        now = self.clock.now()
        if actor_role and actor_role not in ("ADMIN", "DISPATCHER", "RIDER", "SHELTER_COORDINATOR"):
            raise VigiloError(
                ErrorCode.AUTHORIZATION_DENIED,
                f"Actor role '{actor_role}' is not authorized to cancel allocations",
                evidence={"actor": actor, "actor_role": actor_role},
            )

        allocation = self.allocations.get(allocation_id)
        if allocation is None:
            raise EntityNotFoundError(ErrorCode.ALLOCATION_NOT_FOUND, "Allocation", allocation_id)

        if allocation.state == AllocationState.PICKED_UP:
            raise StateTransitionError(
                "Allocation",
                str(allocation.state),
                str(AllocationState.CANCELLED),
                "Picked-up cargo cannot be released as available stock.",
            )

        AllocationStateMachine.validate_transition(
            allocation.state, AllocationState.CANCELLED, allocation_id
        )

        allocation.state = AllocationState.CANCELLED

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

        event = self.record_event(
            event_type=EventType.ALLOCATION_CANCELLED,
            aggregate_id=allocation.id,
            aggregate_type="Allocation",
            actor=actor,
            payload={"quantity": allocation.quantity, "reason": reason},
        )
        audit = AuditRecord.record(
            actor=actor,
            command="allocation.cancel",
            decision="CANCELLED",
            constraints=["UNPICKED_INVENTORY_RELEASED"],
            evidence={"allocation_id": allocation_id, "quantity": allocation.quantity, "reason": reason},
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)
        return allocation

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

        event = self.record_event(
            event_type=EventType.ALLOCATION_EXPIRED,
            aggregate_id=allocation.id,
            aggregate_type="Allocation",
            actor=actor,
            payload={"quantity": allocation.quantity, "reason": reason, "batch_id": batch.id},
        )
        audit = AuditRecord.record(
            actor=actor,
            command="allocation.expire",
            decision="EXPIRED",
            constraints=["UNPICKED_INVENTORY_RELEASED"],
            evidence={"allocation_id": allocation_id, "quantity": allocation.quantity, "reason": reason},
            now=self.clock.now(),
            event_id=event.id,
        )
        self.audit_records.append(audit)
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

    def reconstruct_batch_history(self, batch_id: str) -> dict[str, Any]:
        """Reconstruct full verifiable timeline of a batch purely from events and ledger entries."""
        if batch_id not in self.batches:
            raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", batch_id)
        batch = self.batches[batch_id]
        entries = self.get_batch_ledger(batch_id)
        allocs = [a for a in self.allocations.values() if a.batch_id == batch_id]
        delivs = [d for d in self.deliveries.values() if d.batch_id == batch_id]
        alloc_ids = {a.id for a in allocs}
        deliv_ids = {d.id for d in delivs}
        events = [
            e for e in self.events
            if e.aggregate_id == batch_id
            or e.aggregate_id in alloc_ids
            or e.aggregate_id in deliv_ids
            or (isinstance(e.payload, dict) and (
                e.payload.get("batch_id") == batch_id
                or e.payload.get("allocation_id") in alloc_ids
            ))
        ]

        return {
            "batch_id": batch.id,
            "original_quantity": batch.original_quantity,
            "current_status": {
                "available": batch.available_quantity,
                "reserved": batch.reserved_quantity,
                "picked_up": batch.picked_up_quantity,
                "delivered": batch.delivered_quantity,
                "spoiled": batch.spoiled_quantity,
            },
            "ledger_entries_count": len(entries),
            "ledger_timeline": [e.to_dict() for e in entries],
            "related_events_count": len(events),
            "allocations_count": len(allocs),
            "deliveries_count": len(delivs),
        }

    # -------------------------------------------------------------------------
    # Phase 5: Incident Management
    # -------------------------------------------------------------------------
    def create_incident(
        self,
        severity: IncidentSeverity | str,
        affected_entity_type: str,
        affected_entity_id: str,
        reason_code: str,
        description: str,
        evidence: dict[str, Any] | None = None,
        actor: str = "system",
    ) -> Incident:
        now = self.clock.now()
        sev = IncidentSeverity(severity) if isinstance(severity, str) else severity
        inc_id = f"inc_{uuid4().hex[:12]}"
        incident = Incident(
            id=inc_id,
            severity=sev,
            status=IncidentStatus.OPEN,
            affected_entity_type=affected_entity_type,
            affected_entity_id=affected_entity_id,
            reason_code=reason_code,
            description=description,
            created_at=now,
            evidence=evidence or {},
        )
        self.incidents[incident.id] = incident

        event = self.record_event(
            event_type=EventType.INCIDENT_RECORDED,
            aggregate_id=incident.id,
            aggregate_type="Incident",
            actor=actor,
            payload={
                "severity": incident.severity.value,
                "reason_code": incident.reason_code,
                "affected_entity": f"{affected_entity_type}:{affected_entity_id}",
            },
            evidence=evidence,
        )
        audit = AuditRecord.record(
            actor=actor,
            command="incident.create",
            decision="RECORDED",
            constraints=["INCIDENT_ESCALATION_POLICY"],
            evidence={"incident_id": incident.id, "reason_code": reason_code},
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)
        return incident

    def get_incident(self, incident_id: str) -> Incident:
        incident = self.incidents.get(incident_id)
        if incident is None:
            raise EntityNotFoundError(ErrorCode.INCIDENT_NOT_FOUND, "Incident", incident_id)
        return incident

    def list_incidents(
        self,
        status: str | None = None,
        severity: str | None = None,
        affected_entity_type: str | None = None,
    ) -> list[Incident]:
        results = list(self.incidents.values())
        if status:
            results = [i for i in results if i.status == status or i.status.value == status]
        if severity:
            results = [i for i in results if i.severity == severity or i.severity.value == severity]
        if affected_entity_type:
            results = [i for i in results if i.affected_entity_type == affected_entity_type]
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    def escalate_incident(
        self,
        incident_id: str,
        reason: str = "Escalated for immediate review",
        actor: str = "operator",
    ) -> Incident:
        now = self.clock.now()
        incident = self.get_incident(incident_id)
        incident.status = IncidentStatus.ESCALATED
        incident.severity = IncidentSeverity.CRITICAL
        incident.evidence["escalation_reason"] = reason

        event = self.record_event(
            event_type=EventType.INCIDENT_ESCALATED,
            aggregate_id=incident.id,
            aggregate_type="Incident",
            actor=actor,
            payload={"reason": reason},
        )
        audit = AuditRecord.record(
            actor=actor,
            command="incident.escalate",
            decision="ESCALATED",
            constraints=["INCIDENT_ESCALATION_POLICY"],
            evidence={"incident_id": incident.id, "reason": reason},
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)
        return incident

    def resolve_incident(
        self,
        incident_id: str,
        resolution_notes: str = "Resolved by operations",
        actor: str = "operator",
    ) -> Incident:
        now = self.clock.now()
        incident = self.get_incident(incident_id)
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = now
        incident.evidence["resolution_notes"] = resolution_notes

        event = self.record_event(
            event_type=EventType.INCIDENT_RESOLVED,
            aggregate_id=incident.id,
            aggregate_type="Incident",
            actor=actor,
            payload={"resolution_notes": resolution_notes},
        )
        audit = AuditRecord.record(
            actor=actor,
            command="incident.resolve",
            decision="RESOLVED",
            constraints=["INCIDENT_ESCALATION_POLICY"],
            evidence={"incident_id": incident.id, "resolution_notes": resolution_notes},
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)
        return incident

    # -------------------------------------------------------------------------
    # Phase 5: Shelter Closure & Cascading Recovery
    # -------------------------------------------------------------------------
    def close_shelter(
        self,
        shelter_id: str,
        actor: str = "dispatcher",
        reason: str = "Shelter closed due to operational conditions",
        auto_reroute: bool = True,
    ) -> tuple[Shelter, list[Allocation], list[Delivery], list[Incident]]:
        """Close a shelter and initiate cascading recovery:
        - Unpicked allocations are cancelled and inventory returned to available stock.
        - Physical in-transit cargo is never released to stock; it transitions to REROUTE_PENDING
          and is rerouted or escalated to an INCIDENT_REVIEW."""
        now = self.clock.now()
        shelter = self.shelters.get(shelter_id)
        if shelter is None:
            raise EntityNotFoundError(ErrorCode.SHELTER_NOT_FOUND, "Shelter", shelter_id)

        ShelterStateMachine.validate_transition(shelter.status, ShelterStatus.CLOSED, shelter_id)
        shelter.status = ShelterStatus.CLOSED
        shelter.open = False

        event = self.record_event(
            event_type=EventType.SHELTER_STATUS_CHANGED,
            aggregate_id=shelter.id,
            aggregate_type="Shelter",
            actor=actor,
            payload={"status": shelter.status.value, "reason": reason},
        )
        audit = AuditRecord.record(
            actor=actor,
            command="shelter.close",
            decision="CLOSED",
            constraints=["RECIPIENT_CAPACITY_PRESERVED"],
            evidence={"shelter_id": shelter.id, "reason": reason},
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)

        cancelled_allocations: list[Allocation] = []
        affected_deliveries: list[Delivery] = []
        created_incidents: list[Incident] = []

        # 1. Recover unpicked allocations
        for alloc in list(self.allocations.values()):
            if alloc.shelter_id == shelter_id and alloc.state in (AllocationState.CLAIMED, AllocationState.ACKNOWLEDGED):
                cancelled = self.cancel_allocation(
                    alloc.id,
                    actor=actor,
                    reason=f"Shelter {shelter_id} closed before pickup",
                )
                cancelled_allocations.append(cancelled)

        # 2. Recover physical in-transit deliveries (Strict Invariant: Physical cargo is NOT inventory)
        for deliv in list(self.deliveries.values()):
            if deliv.current_shelter_id == shelter_id and deliv.state in (DeliveryState.PICKED_UP, DeliveryState.IN_TRANSIT):
                DeliveryStateMachine.validate_transition(deliv.state, DeliveryState.REROUTE_PENDING, deliv.id)
                deliv.state = DeliveryState.REROUTE_PENDING
                affected_deliveries.append(deliv)

                self.record_event(
                    event_type=EventType.DELIVERY_REROUTE_REQUESTED,
                    aggregate_id=deliv.id,
                    aggregate_type="Delivery",
                    actor=actor,
                    payload={"original_shelter_id": shelter_id, "quantity": deliv.quantity, "batch_id": deliv.batch_id},
                )

                if auto_reroute:
                    preview = self.preview_reroute(deliv.id)
                    rec_id = preview.get("recommended_shelter_id")
                    if rec_id:
                        self.commit_reroute(deliv.id, target_shelter_id=rec_id, actor=actor, reason="Auto-reroute upon shelter closure")
                    else:
                        # Unrecoverable closure: escalate to INCIDENT_REVIEW
                        DeliveryStateMachine.validate_transition(deliv.state, DeliveryState.INCIDENT_REVIEW, deliv.id)
                        deliv.state = DeliveryState.INCIDENT_REVIEW
                        inc = self.create_incident(
                            severity=IncidentSeverity.CRITICAL,
                            affected_entity_type="Delivery",
                            affected_entity_id=deliv.id,
                            reason_code=ErrorCode.RECOVERY_NOT_FEASIBLE,
                            description=f"Delivery {deliv.id} cannot be safely rerouted following closure of shelter {shelter_id}",
                            evidence={
                                "delivery_id": deliv.id,
                                "closed_shelter_id": shelter_id,
                                "quantity": deliv.quantity,
                                "batch_id": deliv.batch_id,
                                "candidates_evaluated": preview.get("candidates", []),
                            },
                            actor=actor,
                        )
                        created_incidents.append(inc)

        return shelter, cancelled_allocations, affected_deliveries, created_incidents

    def reopen_shelter(self, shelter_id: str, actor: str = "dispatcher") -> Shelter:
        """Reopen a previously closed shelter."""
        now = self.clock.now()
        shelter = self.shelters.get(shelter_id)
        if shelter is None:
            raise EntityNotFoundError(ErrorCode.SHELTER_NOT_FOUND, "Shelter", shelter_id)

        ShelterStateMachine.validate_transition(shelter.status, ShelterStatus.OPEN, shelter_id)
        shelter.status = ShelterStatus.OPEN
        shelter.open = True

        event = self.record_event(
            event_type=EventType.SHELTER_STATUS_CHANGED,
            aggregate_id=shelter.id,
            aggregate_type="Shelter",
            actor=actor,
            payload={"status": shelter.status.value},
        )
        audit = AuditRecord.record(
            actor=actor,
            command="shelter.reopen",
            decision="REOPENED",
            constraints=["RECIPIENT_CAPACITY_RESTORED"],
            evidence={"shelter_id": shelter.id},
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)
        return shelter

    # -------------------------------------------------------------------------
    # Phase 5: In-Transit Rerouting Workflow
    # -------------------------------------------------------------------------
    def preview_reroute(self, delivery_id: str) -> dict[str, Any]:
        """Preview and score alternative destinations for an in-transit delivery."""
        delivery = self.deliveries.get(delivery_id)
        if delivery is None:
            raise EntityNotFoundError(ErrorCode.DELIVERY_NOT_FOUND, "Delivery", delivery_id)

        if delivery.state not in (
            DeliveryState.PICKED_UP,
            DeliveryState.IN_TRANSIT,
            DeliveryState.REROUTE_PENDING,
            DeliveryState.INCIDENT_REVIEW,
        ):
            raise StateTransitionError(
                "Delivery",
                str(delivery.state),
                str(DeliveryState.REROUTE_PENDING),
                "Delivered cargo cannot be rerouted",
            )

        batch = self.batches.get(delivery.batch_id)
        if batch is None:
            raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", delivery.batch_id)

        rider = self.riders.get(delivery.rider_id)
        now = self.clock.now()
        safe_until = batch.item_rules.safe_until(batch.created_at)

        candidates: list[dict[str, Any]] = []
        best_candidate_id: str | None = None
        best_score = -1.0

        for shelter in self.shelters.values():
            if shelter.id == delivery.current_shelter_id:
                continue

            reasons: list[str] = []
            travel_min = 20.0
            if rider and rider.location and shelter.location:
                deg_dist = ((rider.location.latitude - shelter.location.latitude)**2 + (rider.location.longitude - shelter.location.longitude)**2)**0.5
                km = deg_dist * 111.0
                travel_min = max(5.0, round(km / 25.0 * 60, 1))

            handoff_min = 5.0
            total_transit = travel_min + handoff_min + batch.item_rules.safety_buffer_minutes
            est_arrival = now + timedelta(minutes=total_transit)
            safety_margin = (safe_until - est_arrival).total_seconds() / 60.0

            if shelter.status != ShelterStatus.OPEN or not shelter.open:
                reasons.append("Shelter is closed")
            if shelter.demand_remaining < delivery.quantity:
                reasons.append(f"Demand insufficient (need {delivery.quantity}, has {shelter.demand_remaining})")
            if shelter.receiving_capacity_remaining < delivery.quantity:
                reasons.append(f"Receiving capacity insufficient (need {delivery.quantity}, has {shelter.receiving_capacity_remaining})")
            if est_arrival > safe_until:
                reasons.append(f"Arrival ({est_arrival.isoformat()}) exceeds safe handling deadline ({safe_until.isoformat()})")
            if not shelter.receiving_hours.is_open(est_arrival.hour):
                reasons.append(f"Arrival at {est_arrival.hour}:00 outside operating hours ({shelter.receiving_hours.open_hour}:00 - {shelter.receiving_hours.close_hour}:00)")
            if not batch.item_rules.required_prerequisites.issubset(shelter.prerequisites):
                missing = batch.item_rules.required_prerequisites - shelter.prerequisites
                reasons.append(f"Missing prerequisites: {sorted(list(missing))}")

            is_feasible = (len(reasons) == 0)
            score = 0.0
            if is_feasible:
                score = (shelter.demand_remaining * 2.0) + (max(0, safety_margin) * 0.5) + max(0, 100 - travel_min)
                if score > best_score:
                    best_score = score
                    best_candidate_id = shelter.id

            candidates.append({
                "shelter_id": shelter.id,
                "shelter_name": shelter.name,
                "travel_minutes": travel_min,
                "estimated_arrival": est_arrival,
                "safety_margin_minutes": safety_margin,
                "demand_remaining": shelter.demand_remaining,
                "receiving_capacity_remaining": shelter.receiving_capacity_remaining,
                "score": round(score, 2),
                "feasible": is_feasible,
                "rejection_reasons": reasons,
            })

        candidates.sort(key=lambda c: (c["feasible"], c["score"]), reverse=True)

        return {
            "delivery_id": delivery_id,
            "current_shelter_id": delivery.current_shelter_id,
            "quantity": delivery.quantity,
            "safe_until": safe_until,
            "recommended_shelter_id": best_candidate_id,
            "candidates": candidates,
        }

    def commit_reroute(
        self,
        delivery_id: str,
        target_shelter_id: str | None = None,
        actor: str = "dispatcher",
        reason: str = "In-transit reroute",
        actor_role: str | None = None,
    ) -> Delivery:
        """Commit an in-transit delivery reroute to an alternative shelter."""
        now = self.clock.now()
        if actor_role and actor_role not in ("ADMIN", "DISPATCHER", "RIDER"):
            raise VigiloError(
                ErrorCode.AUTHORIZATION_DENIED,
                f"Actor role '{actor_role}' is not authorized to reroute deliveries",
                evidence={"actor": actor, "actor_role": actor_role},
            )

        delivery = self.deliveries.get(delivery_id)
        if delivery is None:
            raise EntityNotFoundError(ErrorCode.DELIVERY_NOT_FOUND, "Delivery", delivery_id)

        if delivery.state == DeliveryState.DELIVERED:
            raise StateTransitionError(
                "Delivery",
                str(delivery.state),
                str(DeliveryState.IN_TRANSIT),
                "Delivered cargo cannot be rerouted",
            )

        if target_shelter_id is None:
            preview = self.preview_reroute(delivery_id)
            target_shelter_id = preview.get("recommended_shelter_id")
            if not target_shelter_id:
                raise VigiloError(
                    ErrorCode.RECOVERY_NOT_FEASIBLE,
                    "No feasible alternative destination available for reroute",
                    evidence={"delivery_id": delivery_id},
                )

        target_shelter = self.shelters.get(target_shelter_id)
        if target_shelter is None:
            raise EntityNotFoundError(ErrorCode.SHELTER_NOT_FOUND, "Shelter", target_shelter_id)

        if target_shelter.status != ShelterStatus.OPEN or not target_shelter.open:
            raise VigiloError(
                ErrorCode.SHELTER_CLOSED,
                f"Target shelter {target_shelter_id} is closed",
                evidence={"shelter_id": target_shelter_id},
            )

        if target_shelter.demand_remaining < delivery.quantity:
            raise VigiloError(
                ErrorCode.SHELTER_DEMAND_EXCEEDED,
                f"Target shelter demand remaining ({target_shelter.demand_remaining}) is less than delivery quantity ({delivery.quantity})",
                evidence={"demand_remaining": target_shelter.demand_remaining, "quantity": delivery.quantity},
            )

        old_shelter_id = delivery.current_shelter_id

        if delivery.state in (DeliveryState.PICKED_UP, DeliveryState.REROUTE_PENDING, DeliveryState.INCIDENT_REVIEW):
            DeliveryStateMachine.validate_transition(delivery.state, DeliveryState.IN_TRANSIT, delivery_id)
            delivery.state = DeliveryState.IN_TRANSIT

        delivery.current_shelter_id = target_shelter_id
        if target_shelter_id not in delivery.destination_history:
            delivery.destination_history.append(target_shelter_id)

        target_shelter.demand_remaining = max(0, target_shelter.demand_remaining - delivery.quantity)
        target_shelter.receiving_capacity_remaining = max(0, target_shelter.receiving_capacity_remaining - delivery.quantity)

        event = self.record_event(
            event_type=EventType.DELIVERY_REROUTED,
            aggregate_id=delivery.id,
            aggregate_type="Delivery",
            actor=actor,
            payload={
                "old_shelter_id": old_shelter_id,
                "new_shelter_id": target_shelter_id,
                "quantity": delivery.quantity,
                "batch_id": delivery.batch_id,
                "reason": reason,
            },
        )
        audit = AuditRecord.record(
            actor=actor,
            command="delivery.reroute",
            decision="REROUTED",
            constraints=["SAFE_HANDLING_DEADLINE", "CAPACITY_AVAILABLE", "ROUTE_FEASIBLE"],
            evidence={
                "delivery_id": delivery.id,
                "old_shelter_id": old_shelter_id,
                "new_shelter_id": target_shelter_id,
                "quantity": delivery.quantity,
                "reason": reason,
            },
            now=now,
            event_id=event.id,
        )
        self.audit_records.append(audit)

        for inc in self.incidents.values():
            if inc.affected_entity_id == delivery.id and inc.status != IncidentStatus.RESOLVED:
                inc.status = IncidentStatus.RESOLVED
                inc.resolved_at = now
                inc.evidence["resolution_notes"] = f"Rerouted to shelter {target_shelter_id}"

        return delivery

    # -------------------------------------------------------------------------
    # Phase 5: Background Sweep Workers
    # -------------------------------------------------------------------------
    def sweep_expired_allocations(self, actor: str = "expiration_worker") -> list[Allocation]:
        """Sweep and expire all unpicked allocations exceeding their lease deadline."""
        now = self.clock.now()
        expired: list[Allocation] = []
        for alloc in list(self.allocations.values()):
            if alloc.state in (AllocationState.CLAIMED, AllocationState.ACKNOWLEDGED) and alloc.lease_expires_at:
                if now > alloc.lease_expires_at:
                    exp = self.expire_allocation(
                        alloc.id,
                        actor=actor,
                        reason="15-minute acknowledgement lease deadline expired",
                    )
                    expired.append(exp)
        return expired

    def sweep_stale_heartbeats(self, max_staleness_minutes: float = 30.0, actor: str = "heartbeat_monitor") -> list[Incident]:
        """Monitor rider heartbeats and raise incidents when active cargo is at risk."""
        now = self.clock.now()
        created_incidents: list[Incident] = []
        for rider in self.riders.values():
            if rider.active_load > 0 or rider.status in (RiderStatus.ASSIGNED, RiderStatus.IN_TRANSIT):
                staleness = (now - rider.last_heartbeat_at).total_seconds() / 60.0 if rider.last_heartbeat_at else 999.0
                if staleness > max_staleness_minutes:
                    existing = [
                        i for i in self.incidents.values()
                        if i.affected_entity_id == rider.id
                        and i.reason_code == ErrorCode.RIDER_HEARTBEAT_EXPIRED
                        and i.status != IncidentStatus.RESOLVED
                    ]
                    if not existing:
                        inc = self.create_incident(
                            severity=IncidentSeverity.HIGH,
                            affected_entity_type="Rider",
                            affected_entity_id=rider.id,
                            reason_code=ErrorCode.RIDER_HEARTBEAT_EXPIRED,
                            description=f"Rider {rider.id} telemetry stale ({round(staleness)} mins since heartbeat) with active cargo ({rider.active_load} units)",
                            evidence={"staleness_minutes": staleness, "active_load": rider.active_load},
                            actor=actor,
                        )
                        created_incidents.append(inc)
        return created_incidents

    def sweep_safety_deadlines(self, buffer_minutes: float = 30.0, actor: str = "safety_monitor") -> list[Incident]:
        """Monitor deliveries approaching safe handling deadlines and create warning incidents."""
        now = self.clock.now()
        created_incidents: list[Incident] = []
        for deliv in self.deliveries.values():
            if deliv.state in (DeliveryState.PICKED_UP, DeliveryState.IN_TRANSIT, DeliveryState.REROUTE_PENDING):
                batch = self.batches.get(deliv.batch_id)
                if batch:
                    safe_until = batch.item_rules.safe_until(batch.created_at)
                    rem = (safe_until - now).total_seconds() / 60.0
                    if rem < buffer_minutes:
                        existing = [
                            i for i in self.incidents.values()
                            if i.affected_entity_id == deliv.id
                            and i.reason_code == ErrorCode.SAFETY_DEADLINE_UNSAFE
                            and i.status != IncidentStatus.RESOLVED
                        ]
                        if not existing:
                            inc = self.create_incident(
                                severity=IncidentSeverity.CRITICAL if rem <= 0 else IncidentSeverity.HIGH,
                                affected_entity_type="Delivery",
                                affected_entity_id=deliv.id,
                                reason_code=ErrorCode.SAFETY_DEADLINE_UNSAFE,
                                description=f"Delivery {deliv.id} has {round(rem)} minutes remaining before safe handling deadline ({safe_until.isoformat()})",
                                evidence={"remaining_minutes": rem, "safe_until": safe_until.isoformat(), "batch_id": batch.id},
                                actor=actor,
                            )
                            created_incidents.append(inc)
        return created_incidents

    def run_all_sweeps(self) -> dict[str, Any]:
        """Execute all periodic background sweep workers in a single pass."""
        expired = self.sweep_expired_allocations()
        stale = self.sweep_stale_heartbeats()
        safety = self.sweep_safety_deadlines()
        published = self.publish_outbox()
        all_incidents = [i.id for i in stale + safety]
        return {
            "expired_allocations_count": len(expired),
            "stale_rider_heartbeats_count": len(stale),
            "safety_deadline_incidents_count": len(safety),
            "published_outbox_count": published,
            "incidents_created": all_incidents,
        }

    @staticmethod
    def _rejection(code: ErrorCode | str, reason: str, evidence: dict[str, object] | None = None) -> DispatchDecision:
        return DispatchDecision(feasible=False, reason_code=str(code), reason=reason, evidence=evidence or {})
