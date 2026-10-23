"""Database-backed persistent DispatchService with ACID transactions and row-level locking."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Generator
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from ..db.repository import DatabaseRepository
from ..db.session import get_global_session_factory
from ..domain.clock import Clock, SystemClock
from ..domain.dispatch import DispatchDecision, DispatchRequest, DispatchService
from ..domain.errors import (
    EntityNotFoundError,
    ErrorCode,
    StateTransitionError,
    VigiloError,
)
from ..domain.events import AuditRecord, EventType, OperationalEvent
from ..domain.ledger import (
    InventoryLedgerEntry,
    InventoryState,
    LedgerEntryType,
    ReconciliationReport,
)
from ..domain.models import (
    Allocation,
    AllocationState,
    Batch,
    Delivery,
    DeliveryState,
    RiderStatus,
    StorageRequirement,
)
from ..domain.outbox import OutboxMessage, OutboxPublisher, OutboxStatus
from ..domain.safety_engine import SafetyEngine
from ..domain.state_machines import AllocationStateMachine, DeliveryStateMachine


class PersistentDispatchService(DispatchService):
    """Production PostgreSQL/Database-backed DispatchService.

    Executes all state transitions, inventory ledger entries, and allocations
    within ACID database transactions using SELECT ... FOR UPDATE row-level locking.
    """

    def __init__(self, clock: Clock | None = None, session_factory: sessionmaker[Session] | None = None) -> None:
        super().__init__(clock=clock)
        self.session_factory = session_factory or get_global_session_factory()
        self._sync_cache_from_db()

    @contextmanager
    def _session(self) -> Generator[Session, None, None]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _sync_cache_from_db(self) -> None:
        """Hydrate in-memory lookup cache from database tables."""
        try:
            with self._session() as session:
                repo = DatabaseRepository(session)
                for b in repo.list_batches():
                    self.batches[b.id] = b
                for r in repo.list_riders():
                    self.riders[r.id] = r
                for s in repo.list_shelters():
                    self.shelters[s.id] = s
        except Exception:
            # Table might be empty on initial boot
            pass

    def commit(self, request: DispatchRequest, actor: str = "dispatcher") -> Allocation:
        now = request.now or self.clock.now()

        with self._session() as session:
            repo = DatabaseRepository(session)

            # 1. Acquire row-level locks on batch, rider, and shelter
            batch = repo.get_batch(request.batch_id, for_update=True)
            if batch is None:
                raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", request.batch_id)

            rider = repo.get_rider(request.rider_id, for_update=True)
            if rider is None:
                raise EntityNotFoundError(ErrorCode.RIDER_NOT_FOUND, "Rider", request.rider_id)

            shelter = repo.get_shelter(request.shelter_id, for_update=True)
            if shelter is None:
                raise EntityNotFoundError(ErrorCode.SHELTER_NOT_FOUND, "Shelter", request.shelter_id)

            # 2. Evaluate feasibility
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
                raise VigiloError(
                    code=report.primary_failure_code or ErrorCode.DISPATCH_REJECTED,
                    message=report.primary_failure_reason or "Assignment infeasible",
                    evidence=report.evidence,
                )

            # 3. Safe handling deadlines and 15-minute lease
            safe_until = batch.item_rules.safe_until(batch.created_at)
            lease_expires_at = now + timedelta(minutes=15)
            allocation_id = f"alloc_{uuid4().hex[:12]}"

            # 4. Record ledger reservation hold
            entry = self.ledger.hold_reservation(
                batch=batch,
                quantity=request.quantity,
                allocation_id=allocation_id,
                actor=actor,
                reason=f"Dispatched {request.quantity} units to {shelter.id} via rider {rider.id}",
                idempotency_key=request.idempotency_key,
            )
            repo.append_ledger_entry(entry)

            # 5. Update rider & shelter
            rider.active_load += request.quantity
            rider.status = RiderStatus.ASSIGNED
            shelter.demand_remaining -= request.quantity
            shelter.receiving_capacity_remaining -= request.quantity

            # 6. Create and persist allocation
            allocation = Allocation(
                id=allocation_id,
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

            repo.save_batch(batch)
            repo.save_rider(rider)
            repo.save_shelter(shelter)
            repo.save_allocation(allocation)

            # 7. Record operational event and transactional outbox message
            event = OperationalEvent.create(
                event_type=EventType.ALLOCATION_CLAIMED,
                aggregate_id=allocation.id,
                aggregate_type="Allocation",
                occurred_at=now,
                actor=actor,
                payload={"batch_id": batch.id, "rider_id": rider.id, "shelter_id": shelter.id, "quantity": request.quantity},
            )
            repo.append_event(event)
            outbox_msg = OutboxMessage.from_event(event)
            repo.append_outbox_message(outbox_msg)

            # 8. Record audit trail
            audit = AuditRecord.record(
                actor=actor,
                command="dispatch.commit",
                decision="COMMITTED",
                constraints=report.evaluated_rules,
                evidence=report.evidence,
                now=now,
                event_id=event.id,
            )
            repo.append_audit_record(audit)

            # Sync in-memory cache
            self.batches[batch.id] = batch
            self.riders[rider.id] = rider
            self.shelters[shelter.id] = shelter
            self.allocations[allocation.id] = allocation
            self.events.append(event)
            self.outbox_messages.append(outbox_msg)
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

        with self._session() as session:
            repo = DatabaseRepository(session)
            allocation = repo.get_allocation(allocation_id, for_update=True)
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
            repo.save_allocation(allocation)

            event = OperationalEvent.create(
                event_type=EventType.ALLOCATION_ACKNOWLEDGED,
                aggregate_id=allocation.id,
                aggregate_type="Allocation",
                occurred_at=now,
                actor=actor,
                payload={"state": allocation.state.value, "batch_id": allocation.batch_id},
            )
            repo.append_event(event)
            outbox_msg = OutboxMessage.from_event(event)
            repo.append_outbox_message(outbox_msg)

            audit = AuditRecord.record(
                actor=actor,
                command="allocation.acknowledge",
                decision="ACKNOWLEDGED",
                constraints=["LEASE_ACTIVE"],
                evidence={"allocation_id": allocation_id, "state": allocation.state.value},
                now=now,
                event_id=event.id,
            )
            repo.append_audit_record(audit)

            self.allocations[allocation.id] = allocation
            self.events.append(event)
            self.outbox_messages.append(outbox_msg)
            self.audit_records.append(audit)
            return allocation

    def pickup_allocation(self, allocation_id: str, actor: str = "rider", actor_role: str | None = None) -> Delivery:
        now = self.clock.now()
        if actor_role and actor_role not in ("RIDER", "ADMIN", "DISPATCHER"):
            raise VigiloError(
                ErrorCode.AUTHORIZATION_DENIED,
                f"Actor role '{actor_role}' is not authorized to pick up cargo",
                evidence={"actor": actor, "actor_role": actor_role},
            )

        with self._session() as session:
            repo = DatabaseRepository(session)
            allocation = repo.get_allocation(allocation_id, for_update=True)
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

            batch = repo.get_batch(allocation.batch_id, for_update=True)
            if batch is None:
                raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", allocation.batch_id)

            rider = repo.get_rider(allocation.rider_id, for_update=True)
            if rider is None:
                raise EntityNotFoundError(ErrorCode.RIDER_NOT_FOUND, "Rider", allocation.rider_id)

            deliv_id = f"deliv_{uuid4().hex[:12]}"
            allocation.state = AllocationState.PICKED_UP
            allocation.picked_up_at = now

            entry = self.ledger.record_pickup(
                batch=batch,
                quantity=allocation.quantity,
                allocation_id=allocation.id,
                delivery_id=deliv_id,
                actor=actor,
                reason=f"Picked up by rider {allocation.rider_id}",
            )
            repo.append_ledger_entry(entry)

            rider.status = RiderStatus.IN_TRANSIT

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

            repo.save_allocation(allocation)
            repo.save_batch(batch)
            repo.save_rider(rider)
            repo.save_delivery(delivery)

            event = OperationalEvent.create(
                event_type=EventType.CARGO_PICKED_UP,
                aggregate_id=delivery.id,
                aggregate_type="Delivery",
                occurred_at=now,
                actor=actor,
                payload={"allocation_id": allocation.id, "quantity": delivery.quantity, "batch_id": batch.id},
            )
            repo.append_event(event)
            outbox_msg = OutboxMessage.from_event(event)
            repo.append_outbox_message(outbox_msg)

            audit = AuditRecord.record(
                actor=actor,
                command="allocation.pickup",
                decision="PICKED_UP",
                constraints=["SAFE_HANDLING_DEADLINE", "PHYSICAL_CUSTODY_TRANSFERRED"],
                evidence={"allocation_id": allocation.id, "delivery_id": delivery.id, "quantity": delivery.quantity},
                now=now,
                event_id=event.id,
            )
            repo.append_audit_record(audit)

            self.allocations[allocation.id] = allocation
            self.batches[batch.id] = batch
            self.riders[rider.id] = rider
            self.deliveries[delivery.id] = delivery
            self.events.append(event)
            self.outbox_messages.append(outbox_msg)
            self.audit_records.append(audit)
            return delivery

    def deliver_cargo(self, delivery_id: str, actor: str = "rider", actor_role: str | None = None) -> Delivery:
        now = self.clock.now()
        if actor_role and actor_role not in ("RIDER", "ADMIN", "DISPATCHER", "SHELTER_COORDINATOR"):
            raise VigiloError(
                ErrorCode.AUTHORIZATION_DENIED,
                f"Actor role '{actor_role}' is not authorized to confirm delivery",
                evidence={"actor": actor, "actor_role": actor_role},
            )

        with self._session() as session:
            repo = DatabaseRepository(session)
            delivery = repo.get_delivery(delivery_id, for_update=True)
            if delivery is None:
                raise EntityNotFoundError(ErrorCode.DELIVERY_NOT_FOUND, "Delivery", delivery_id)

            DeliveryStateMachine.validate_transition(
                delivery.state, DeliveryState.DELIVERED, delivery_id
            )

            batch = repo.get_batch(delivery.batch_id, for_update=True)
            if batch is None:
                raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", delivery.batch_id)

            rider = repo.get_rider(delivery.rider_id, for_update=True)
            if rider is None:
                raise EntityNotFoundError(ErrorCode.RIDER_NOT_FOUND, "Rider", delivery.rider_id)

            delivery.state = DeliveryState.DELIVERED
            delivery.delivered_at = now

            entry = self.ledger.confirm_delivery(
                batch=batch,
                quantity=delivery.quantity,
                delivery_id=delivery.id,
                actor=actor,
                reason=f"Safely delivered to shelter {delivery.current_shelter_id}",
            )
            repo.append_ledger_entry(entry)

            rider.active_load -= delivery.quantity
            if rider.active_load == 0:
                rider.status = RiderStatus.AVAILABLE

            shelter = repo.get_shelter(delivery.current_shelter_id, for_update=True)
            if shelter:
                shelter.demand_remaining = max(0, shelter.demand_remaining - delivery.quantity)
                repo.save_shelter(shelter)
                self.shelters[shelter.id] = shelter

            repo.save_delivery(delivery)
            repo.save_batch(batch)
            repo.save_rider(rider)

            event = OperationalEvent.create(
                event_type=EventType.DELIVERY_COMPLETED,
                aggregate_id=delivery.id,
                aggregate_type="Delivery",
                occurred_at=now,
                actor=actor,
                payload={"destination": delivery.current_shelter_id, "quantity": delivery.quantity, "batch_id": batch.id},
            )
            repo.append_event(event)
            outbox_msg = OutboxMessage.from_event(event)
            repo.append_outbox_message(outbox_msg)

            audit = AuditRecord.record(
                actor=actor,
                command="delivery.complete",
                decision="DELIVERED",
                constraints=["INVENTORY_CONSERVED", "DELIVERY_CONFIRMED"],
                evidence={"delivery_id": delivery.id, "quantity": delivery.quantity, "destination": delivery.current_shelter_id},
                now=now,
                event_id=event.id,
            )
            repo.append_audit_record(audit)

            self.deliveries[delivery.id] = delivery
            self.batches[batch.id] = batch
            self.riders[rider.id] = rider
            self.events.append(event)
            self.outbox_messages.append(outbox_msg)
            self.audit_records.append(audit)
            return delivery

    def cancel_allocation(
        self,
        allocation_id: str,
        actor: str = "dispatcher",
        reason: str = "Manual cancellation",
        actor_role: str | None = None,
    ) -> Allocation:
        now = self.clock.now()
        if actor_role and actor_role not in ("ADMIN", "DISPATCHER", "RIDER", "SHELTER_COORDINATOR"):
            raise VigiloError(
                ErrorCode.AUTHORIZATION_DENIED,
                f"Actor role '{actor_role}' is not authorized to cancel allocations",
                evidence={"actor": actor, "actor_role": actor_role},
            )

        with self._session() as session:
            repo = DatabaseRepository(session)
            allocation = repo.get_allocation(allocation_id, for_update=True)
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

            batch = repo.get_batch(allocation.batch_id, for_update=True)
            if batch is None:
                raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", allocation.batch_id)

            rider = repo.get_rider(allocation.rider_id, for_update=True)
            if rider is None:
                raise EntityNotFoundError(ErrorCode.RIDER_NOT_FOUND, "Rider", allocation.rider_id)

            shelter = repo.get_shelter(allocation.shelter_id, for_update=True)
            if shelter is None:
                raise EntityNotFoundError(ErrorCode.SHELTER_NOT_FOUND, "Shelter", allocation.shelter_id)

            allocation.state = AllocationState.CANCELLED
            entry = self.ledger.release_reservation(
                batch=batch,
                quantity=allocation.quantity,
                allocation_id=allocation.id,
                actor=actor,
                reason=reason,
            )
            repo.append_ledger_entry(entry)

            rider.active_load -= allocation.quantity
            if rider.active_load == 0:
                rider.status = RiderStatus.AVAILABLE

            shelter.demand_remaining += allocation.quantity
            shelter.receiving_capacity_remaining += allocation.quantity

            repo.save_allocation(allocation)
            repo.save_batch(batch)
            repo.save_rider(rider)
            repo.save_shelter(shelter)

            event = OperationalEvent.create(
                event_type=EventType.ALLOCATION_CANCELLED,
                aggregate_id=allocation.id,
                aggregate_type="Allocation",
                occurred_at=now,
                actor=actor,
                payload={"quantity": allocation.quantity, "reason": reason},
            )
            repo.append_event(event)
            outbox_msg = OutboxMessage.from_event(event)
            repo.append_outbox_message(outbox_msg)

            audit = AuditRecord.record(
                actor=actor,
                command="allocation.cancel",
                decision="CANCELLED",
                constraints=["UNPICKED_INVENTORY_RELEASED"],
                evidence={"allocation_id": allocation_id, "quantity": allocation.quantity, "reason": reason},
                now=now,
                event_id=event.id,
            )
            repo.append_audit_record(audit)

            self.allocations[allocation.id] = allocation
            self.batches[batch.id] = batch
            self.riders[rider.id] = rider
            self.shelters[shelter.id] = shelter
            self.events.append(event)
            self.outbox_messages.append(outbox_msg)
            self.audit_records.append(audit)
            return allocation

    def expire_allocation(self, allocation_id: str, actor: str = "recovery_worker", reason: str = "Lease expired") -> Allocation:
        now = self.clock.now()
        with self._session() as session:
            repo = DatabaseRepository(session)
            allocation = repo.get_allocation(allocation_id, for_update=True)
            if allocation is None:
                raise EntityNotFoundError(ErrorCode.ALLOCATION_NOT_FOUND, "Allocation", allocation_id)

            AllocationStateMachine.validate_transition(
                allocation.state, AllocationState.EXPIRED, allocation_id
            )

            batch = repo.get_batch(allocation.batch_id, for_update=True)
            if batch is None:
                raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", allocation.batch_id)

            rider = repo.get_rider(allocation.rider_id, for_update=True)
            if rider is None:
                raise EntityNotFoundError(ErrorCode.RIDER_NOT_FOUND, "Rider", allocation.rider_id)

            shelter = repo.get_shelter(allocation.shelter_id, for_update=True)
            if shelter is None:
                raise EntityNotFoundError(ErrorCode.SHELTER_NOT_FOUND, "Shelter", allocation.shelter_id)

            allocation.state = AllocationState.EXPIRED
            entry = self.ledger.release_reservation(
                batch=batch,
                quantity=allocation.quantity,
                allocation_id=allocation.id,
                actor=actor,
                reason=reason,
            )
            repo.append_ledger_entry(entry)

            rider.active_load -= allocation.quantity
            if rider.active_load == 0:
                rider.status = RiderStatus.AVAILABLE

            shelter.demand_remaining += allocation.quantity
            shelter.receiving_capacity_remaining += allocation.quantity

            repo.save_allocation(allocation)
            repo.save_batch(batch)
            repo.save_rider(rider)
            repo.save_shelter(shelter)

            event = OperationalEvent.create(
                event_type=EventType.ALLOCATION_EXPIRED,
                aggregate_id=allocation.id,
                aggregate_type="Allocation",
                occurred_at=now,
                actor=actor,
                payload={"quantity": allocation.quantity, "reason": reason},
            )
            repo.append_event(event)
            outbox_msg = OutboxMessage.from_event(event)
            repo.append_outbox_message(outbox_msg)

            audit = AuditRecord.record(
                actor=actor,
                command="allocation.expire",
                decision="EXPIRED",
                constraints=["UNPICKED_INVENTORY_RELEASED"],
                evidence={"allocation_id": allocation_id, "quantity": allocation.quantity, "reason": reason},
                now=now,
                event_id=event.id,
            )
            repo.append_audit_record(audit)

            self.allocations[allocation.id] = allocation
            self.batches[batch.id] = batch
            self.riders[rider.id] = rider
            self.shelters[shelter.id] = shelter
            self.events.append(event)
            self.outbox_messages.append(outbox_msg)
            self.audit_records.append(audit)
            return allocation

    def publish_outbox(self, limit: int = 50) -> int:
        count = 0
        now = self.clock.now()
        with self._session() as session:
            repo = DatabaseRepository(session)
            pending = repo.get_pending_outbox_messages(limit=limit)
            for msg in pending:
                success = self.outbox_publisher.publish(msg, now)
                if success:
                    repo.mark_outbox_message_published(msg.id, msg.published_at or now)
                    count += 1
                else:
                    repo.mark_outbox_message_failed(msg.id, msg.last_error or "Publication failed")
        return count

    def get_audit_record(self, audit_id: str) -> AuditRecord | None:
        with self._session() as session:
            repo = DatabaseRepository(session)
            return repo.get_audit_record(audit_id)

    def list_audit_records(self, limit: int = 50) -> list[AuditRecord]:
        with self._session() as session:
            repo = DatabaseRepository(session)
            return repo.list_audit_records(limit=limit)

    def reconstruct_batch_history(self, batch_id: str) -> dict[str, Any]:
        with self._session() as session:
            repo = DatabaseRepository(session)
            batch = repo.get_batch(batch_id)
            if batch is None:
                raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", batch_id)
            entries = repo.get_ledger_entries(batch_id)
            all_events = repo.list_events(limit=200)
            events = [
                e for e in all_events
                if e.aggregate_id == batch_id
                or (isinstance(e.payload, dict) and e.payload.get("batch_id") == batch_id)
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
                "allocations_count": sum(1 for a in self.allocations.values() if a.batch_id == batch_id),
                "deliveries_count": sum(1 for d in self.deliveries.values() if d.batch_id == batch_id),
            }

    def get_batch_ledger(self, batch_id: str) -> list[InventoryLedgerEntry]:
        with self._session() as session:
            repo = DatabaseRepository(session)
            entries = repo.get_ledger_entries(batch_id)
            if not entries:
                if batch_id not in self.batches and repo.get_batch(batch_id) is None:
                    raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", batch_id)
            return entries

    def reconcile_batch(self, batch_id: str) -> ReconciliationReport:
        with self._session() as session:
            repo = DatabaseRepository(session)
            batch = repo.get_batch(batch_id)
            if batch is None:
                raise EntityNotFoundError(ErrorCode.BATCH_NOT_FOUND, "Batch", batch_id)
            entries = repo.get_ledger_entries(batch_id)
            return self.ledger.reconcile(batch, entries=entries)

    def load_seed(self, base_time: datetime | None = None) -> None:
        """Seed both in-memory cache and persistent database tables."""
        super().load_seed(base_time=base_time)
        with self._session() as session:
            repo = DatabaseRepository(session)
            for b in self.batches.values():
                repo.save_batch(b)
            for r in self.riders.values():
                repo.save_rider(r)
            for s in self.shelters.values():
                repo.save_shelter(s)
            for batch_id in self.batches:
                for entry in self.ledger.get_ledger(batch_id):
                    repo.append_ledger_entry(entry)
