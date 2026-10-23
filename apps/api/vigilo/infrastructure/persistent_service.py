"""Database-backed persistent DispatchService with ACID transactions and row-level locking."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
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
from ..domain.events import EventType, OperationalEvent
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

            # 3. Safe handling deadlines and lease
            safe_until = batch.item_rules.safe_until(batch.created_at)
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
                safe_until=safe_until,
            )

            repo.save_batch(batch)
            repo.save_rider(rider)
            repo.save_shelter(shelter)
            repo.save_allocation(allocation)

            # 7. Record operational event
            event = OperationalEvent.create(
                event_type=EventType.ALLOCATION_CLAIMED,
                aggregate_id=allocation.id,
                aggregate_type="Allocation",
                occurred_at=now,
                actor=actor,
                payload={"batch_id": batch.id, "rider_id": rider.id, "shelter_id": shelter.id, "quantity": request.quantity},
            )
            repo.append_event(event)

            # Sync in-memory cache
            self.batches[batch.id] = batch
            self.riders[rider.id] = rider
            self.shelters[shelter.id] = shelter
            self.allocations[allocation.id] = allocation
            self.events.append(event)

            return allocation

    def acknowledge_allocation(self, allocation_id: str, actor: str = "rider") -> Allocation:
        now = self.clock.now()
        with self._session() as session:
            repo = DatabaseRepository(session)
            allocation = repo.get_allocation(allocation_id, for_update=True)
            if allocation is None:
                raise EntityNotFoundError(ErrorCode.ALLOCATION_NOT_FOUND, "Allocation", allocation_id)

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
                payload={"state": allocation.state.value},
            )
            repo.append_event(event)

            self.allocations[allocation.id] = allocation
            self.events.append(event)
            return allocation

    def pickup_allocation(self, allocation_id: str, actor: str = "rider") -> Delivery:
        now = self.clock.now()
        with self._session() as session:
            repo = DatabaseRepository(session)
            allocation = repo.get_allocation(allocation_id, for_update=True)
            if allocation is None:
                raise EntityNotFoundError(ErrorCode.ALLOCATION_NOT_FOUND, "Allocation", allocation_id)

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
                payload={"allocation_id": allocation.id, "quantity": delivery.quantity},
            )
            repo.append_event(event)

            self.allocations[allocation.id] = allocation
            self.batches[batch.id] = batch
            self.riders[rider.id] = rider
            self.deliveries[delivery.id] = delivery
            self.events.append(event)
            return delivery

    def deliver_cargo(self, delivery_id: str, actor: str = "rider") -> Delivery:
        now = self.clock.now()
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

            repo.save_delivery(delivery)
            repo.save_batch(batch)
            repo.save_rider(rider)

            event = OperationalEvent.create(
                event_type=EventType.DELIVERY_COMPLETED,
                aggregate_id=delivery.id,
                aggregate_type="Delivery",
                occurred_at=now,
                actor=actor,
                payload={"destination": delivery.current_shelter_id, "quantity": delivery.quantity},
            )
            repo.append_event(event)

            self.deliveries[delivery.id] = delivery
            self.batches[batch.id] = batch
            self.riders[rider.id] = rider
            self.events.append(event)
            return delivery

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

            self.allocations[allocation.id] = allocation
            self.batches[batch.id] = batch
            self.riders[rider.id] = rider
            self.shelters[shelter.id] = shelter
            self.events.append(event)
            return allocation

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
