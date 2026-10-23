from __future__ import annotations

from datetime import datetime
from threading import RLock
from typing import Any
from uuid import uuid4

from .clock import Clock, SystemClock
from .errors import EntityNotFoundError, ErrorCode, StateTransitionError
from .ledger import (
    InventoryBalanceSnapshot,
    InventoryConflictError,
    InventoryInsufficientError,
    InventoryLedgerEntry,
    InventoryState,
    LedgerEntryType,
    ReconciliationReport,
)
from .models import Batch


class InventoryLedgerService:
    """Authoritative ledger engine enforcing quantity conservation, immutability,
    transactional boundaries, and idempotent retries."""

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock = clock or SystemClock()
        # Append-only ledger storage: batch_id -> list of entries
        self._entries: dict[str, list[InventoryLedgerEntry]] = {}
        # Idempotency registry: key -> InventoryLedgerEntry
        self._idempotency_records: dict[str, InventoryLedgerEntry] = {}
        # Batch locks for concurrency safety
        self._locks: dict[str, RLock] = {}
        self._global_lock = RLock()

    def _get_batch_lock(self, batch_id: str) -> RLock:
        with self._global_lock:
            if batch_id not in self._locks:
                self._locks[batch_id] = RLock()
            return self._locks[batch_id]

    def record_intake(
        self,
        batch: Batch,
        actor: str = "system",
        reason: str = "Initial batch intake",
        idempotency_key: str | None = None,
    ) -> InventoryLedgerEntry:
        """Record genesis entry for a new donation batch."""
        lock = self._get_batch_lock(batch.id)
        with lock:
            if idempotency_key and idempotency_key in self._idempotency_records:
                return self._idempotency_records[idempotency_key]

            now = self.clock.now()
            snapshot = InventoryBalanceSnapshot(
                available=batch.available_quantity,
                reserved=batch.reserved_quantity,
                picked_up=batch.picked_up_quantity,
                delivered=batch.delivered_quantity,
                spoiled=batch.spoiled_quantity,
            )

            entry = InventoryLedgerEntry(
                id=f"led_{uuid4().hex[:12]}",
                batch_id=batch.id,
                entry_type=LedgerEntryType.INTAKE,
                quantity=batch.original_quantity,
                from_state=None,
                to_state=InventoryState.AVAILABLE,
                actor=actor,
                command="inventory.intake",
                reason=reason,
                occurred_at=now,
                balance_after=snapshot,
                idempotency_key=idempotency_key,
            )

            self._append_entry(batch.id, entry)
            if idempotency_key:
                self._idempotency_records[idempotency_key] = entry
            return entry

    def hold_reservation(
        self,
        batch: Batch,
        quantity: int,
        allocation_id: str,
        actor: str = "dispatcher",
        reason: str = "Reserved for rider dispatch claim",
        idempotency_key: str | None = None,
    ) -> InventoryLedgerEntry:
        """Transition quantity from AVAILABLE to RESERVED."""
        if quantity <= 0:
            raise ValueError("Reservation quantity must be positive")

        lock = self._get_batch_lock(batch.id)
        with lock:
            if idempotency_key and idempotency_key in self._idempotency_records:
                return self._idempotency_records[idempotency_key]

            if batch.available_quantity < quantity:
                raise InventoryInsufficientError(
                    f"Batch '{batch.id}' has insufficient available inventory",
                    {"available": batch.available_quantity, "requested": quantity},
                )

            batch.available_quantity -= quantity
            batch.reserved_quantity += quantity
            batch.validate_invariants()

            snapshot = self._take_snapshot(batch)
            entry = InventoryLedgerEntry(
                id=f"led_{uuid4().hex[:12]}",
                batch_id=batch.id,
                entry_type=LedgerEntryType.RESERVATION_HOLD,
                quantity=quantity,
                from_state=InventoryState.AVAILABLE,
                to_state=InventoryState.RESERVED,
                actor=actor,
                command="dispatch.hold",
                reason=reason,
                occurred_at=self.clock.now(),
                balance_after=snapshot,
                allocation_id=allocation_id,
                idempotency_key=idempotency_key,
            )

            self._append_entry(batch.id, entry)
            if idempotency_key:
                self._idempotency_records[idempotency_key] = entry
            return entry

    def release_reservation(
        self,
        batch: Batch,
        quantity: int,
        allocation_id: str,
        actor: str = "recovery_worker",
        reason: str = "Unpicked claim lease expired or cancelled",
        idempotency_key: str | None = None,
    ) -> InventoryLedgerEntry:
        """Release an unpicked allocation from RESERVED back to AVAILABLE.
        
        Invariant:
        Cannot release cargo if it has already been picked up!
        """
        if quantity <= 0:
            raise ValueError("Release quantity must be positive")

        lock = self._get_batch_lock(batch.id)
        with lock:
            if idempotency_key and idempotency_key in self._idempotency_records:
                return self._idempotency_records[idempotency_key]

            if batch.reserved_quantity < quantity:
                raise InventoryConflictError(
                    f"Cannot release {quantity} units: batch '{batch.id}' only has {batch.reserved_quantity} reserved",
                    {"reserved": batch.reserved_quantity, "requested_release": quantity},
                )

            batch.reserved_quantity -= quantity
            batch.available_quantity += quantity
            batch.validate_invariants()

            snapshot = self._take_snapshot(batch)
            entry = InventoryLedgerEntry(
                id=f"led_{uuid4().hex[:12]}",
                batch_id=batch.id,
                entry_type=LedgerEntryType.RESERVATION_RELEASE,
                quantity=quantity,
                from_state=InventoryState.RESERVED,
                to_state=InventoryState.AVAILABLE,
                actor=actor,
                command="allocation.release",
                reason=reason,
                occurred_at=self.clock.now(),
                balance_after=snapshot,
                allocation_id=allocation_id,
                idempotency_key=idempotency_key,
            )

            self._append_entry(batch.id, entry)
            if idempotency_key:
                self._idempotency_records[idempotency_key] = entry
            return entry

    def record_pickup(
        self,
        batch: Batch,
        quantity: int,
        allocation_id: str,
        delivery_id: str,
        actor: str = "rider",
        reason: str = "Physical cargo picked up by rider",
        idempotency_key: str | None = None,
    ) -> InventoryLedgerEntry:
        """Transition quantity from RESERVED to PICKED_UP (physical chain of custody)."""
        if quantity <= 0:
            raise ValueError("Pickup quantity must be positive")

        lock = self._get_batch_lock(batch.id)
        with lock:
            if idempotency_key and idempotency_key in self._idempotency_records:
                return self._idempotency_records[idempotency_key]

            if batch.reserved_quantity < quantity:
                raise InventoryConflictError(
                    f"Cannot confirm pickup: batch '{batch.id}' has {batch.reserved_quantity} reserved, needed {quantity}",
                    {"reserved": batch.reserved_quantity, "requested": quantity},
                )

            batch.reserved_quantity -= quantity
            batch.picked_up_quantity += quantity
            batch.validate_invariants()

            snapshot = self._take_snapshot(batch)
            entry = InventoryLedgerEntry(
                id=f"led_{uuid4().hex[:12]}",
                batch_id=batch.id,
                entry_type=LedgerEntryType.PICKUP_CONFIRMED,
                quantity=quantity,
                from_state=InventoryState.RESERVED,
                to_state=InventoryState.PICKED_UP,
                actor=actor,
                command="cargo.pickup",
                reason=reason,
                occurred_at=self.clock.now(),
                balance_after=snapshot,
                allocation_id=allocation_id,
                delivery_id=delivery_id,
                idempotency_key=idempotency_key,
            )

            self._append_entry(batch.id, entry)
            if idempotency_key:
                self._idempotency_records[idempotency_key] = entry
            return entry

    def confirm_delivery(
        self,
        batch: Batch,
        quantity: int,
        delivery_id: str,
        actor: str = "rider",
        reason: str = "Delivered to receiving shelter",
        idempotency_key: str | None = None,
    ) -> InventoryLedgerEntry:
        """Transition physical cargo from PICKED_UP to DELIVERED."""
        if quantity <= 0:
            raise ValueError("Delivery quantity must be positive")

        lock = self._get_batch_lock(batch.id)
        with lock:
            if idempotency_key and idempotency_key in self._idempotency_records:
                return self._idempotency_records[idempotency_key]

            if batch.picked_up_quantity < quantity:
                raise InventoryConflictError(
                    f"Cannot confirm delivery: batch '{batch.id}' has {batch.picked_up_quantity} picked up, needed {quantity}",
                    {"picked_up": batch.picked_up_quantity, "requested": quantity},
                )

            batch.picked_up_quantity -= quantity
            batch.delivered_quantity += quantity
            batch.validate_invariants()

            snapshot = self._take_snapshot(batch)
            entry = InventoryLedgerEntry(
                id=f"led_{uuid4().hex[:12]}",
                batch_id=batch.id,
                entry_type=LedgerEntryType.DELIVERY_CONFIRMED,
                quantity=quantity,
                from_state=InventoryState.PICKED_UP,
                to_state=InventoryState.DELIVERED,
                actor=actor,
                command="cargo.deliver",
                reason=reason,
                occurred_at=self.clock.now(),
                balance_after=snapshot,
                delivery_id=delivery_id,
                idempotency_key=idempotency_key,
            )

            self._append_entry(batch.id, entry)
            if idempotency_key:
                self._idempotency_records[idempotency_key] = entry
            return entry

    def record_loss_or_spoilage(
        self,
        batch: Batch,
        quantity: int,
        from_state: InventoryState,
        to_state: InventoryState,
        actor: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> InventoryLedgerEntry:
        """Deduct damaged, spoiled, or lost supplies.
        
        Invariant:
        Delivered inventory cannot be marked as loss or spoiled through this workflow.
        """
        if to_state not in (InventoryState.SPOILED, InventoryState.DAMAGED, InventoryState.LOST):
            raise ValueError("Target state must be SPOILED, DAMAGED, or LOST")
        if from_state == InventoryState.DELIVERED:
            raise StateTransitionError("Inventory", from_state.value, to_state.value, "Delivered aid cannot be written off")

        lock = self._get_batch_lock(batch.id)
        with lock:
            if idempotency_key and idempotency_key in self._idempotency_records:
                return self._idempotency_records[idempotency_key]

            # Verify balance in from_state
            if from_state == InventoryState.AVAILABLE:
                if batch.available_quantity < quantity:
                    raise InventoryInsufficientError("Insufficient available quantity to write off")
                batch.available_quantity -= quantity
            elif from_state == InventoryState.RESERVED:
                if batch.reserved_quantity < quantity:
                    raise InventoryInsufficientError("Insufficient reserved quantity to write off")
                batch.reserved_quantity -= quantity
            elif from_state == InventoryState.PICKED_UP:
                if batch.picked_up_quantity < quantity:
                    raise InventoryInsufficientError("Insufficient in-transit quantity to write off")
                batch.picked_up_quantity -= quantity
            else:
                raise ValueError(f"Unsupported from_state '{from_state}' for write-off")

            batch.spoiled_quantity += quantity
            batch.validate_invariants()

            snapshot = self._take_snapshot(batch)
            entry_type = (
                LedgerEntryType.SPOILAGE_RECORDED
                if to_state == InventoryState.SPOILED
                else LedgerEntryType.DAMAGE_RECORDED
            )

            entry = InventoryLedgerEntry(
                id=f"led_{uuid4().hex[:12]}",
                batch_id=batch.id,
                entry_type=entry_type,
                quantity=quantity,
                from_state=from_state,
                to_state=to_state,
                actor=actor,
                command="inventory.write_off",
                reason=reason,
                occurred_at=self.clock.now(),
                balance_after=snapshot,
                idempotency_key=idempotency_key,
            )

            self._append_entry(batch.id, entry)
            if idempotency_key:
                self._idempotency_records[idempotency_key] = entry
            return entry

    def record_compensating_adjustment(
        self,
        batch: Batch,
        quantity: int,
        from_state: InventoryState,
        to_state: InventoryState,
        actor: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> InventoryLedgerEntry:
        """Append an immutable compensating ledger entry to correct an operational discrepancy.
        
        Strict rule: Never mutate past entries. Record a compensating movement with explicit justification.
        """
        if not reason or len(reason.strip()) < 5:
            raise ValueError("Compensating adjustment requires a comprehensive reason for audit integrity")

        lock = self._get_batch_lock(batch.id)
        with lock:
            if idempotency_key and idempotency_key in self._idempotency_records:
                return self._idempotency_records[idempotency_key]

            # Validate from_state capacity
            if from_state == InventoryState.AVAILABLE:
                if batch.available_quantity < quantity:
                    raise InventoryInsufficientError("Available balance is less than adjustment quantity")
                batch.available_quantity -= quantity
            elif from_state == InventoryState.RESERVED:
                if batch.reserved_quantity < quantity:
                    raise InventoryInsufficientError("Reserved balance is less than adjustment quantity")
                batch.reserved_quantity -= quantity
            elif from_state == InventoryState.PICKED_UP:
                if batch.picked_up_quantity < quantity:
                    raise InventoryInsufficientError("Picked up balance is less than adjustment quantity")
                batch.picked_up_quantity -= quantity
            elif from_state == InventoryState.DELIVERED:
                raise StateTransitionError("Inventory", from_state.value, to_state.value, "Delivered stock cannot be reversed")
            else:
                raise ValueError(f"Cannot adjust from {from_state}")

            # Apply to target state
            if to_state == InventoryState.AVAILABLE:
                batch.available_quantity += quantity
            elif to_state == InventoryState.RESERVED:
                batch.reserved_quantity += quantity
            elif to_state == InventoryState.SPOILED:
                batch.spoiled_quantity += quantity
            else:
                raise ValueError(f"Cannot adjust to {to_state}")

            batch.validate_invariants()
            snapshot = self._take_snapshot(batch)

            entry = InventoryLedgerEntry(
                id=f"led_{uuid4().hex[:12]}",
                batch_id=batch.id,
                entry_type=LedgerEntryType.COMPENSATING_ADJUSTMENT,
                quantity=quantity,
                from_state=from_state,
                to_state=to_state,
                actor=actor,
                command="inventory.compensate",
                reason=reason,
                occurred_at=self.clock.now(),
                balance_after=snapshot,
                idempotency_key=idempotency_key,
            )

            self._append_entry(batch.id, entry)
            if idempotency_key:
                self._idempotency_records[idempotency_key] = entry
            return entry

    def get_ledger(self, batch_id: str) -> list[InventoryLedgerEntry]:
        """Return the immutable sequence of quantity movements for a batch."""
        lock = self._get_batch_lock(batch_id)
        with lock:
            return list(self._entries.get(batch_id, []))

    def reconcile(self, batch: Batch) -> ReconciliationReport:
        """Execute full mathematical reconciliation of all ledger movements.
        
        Replays all entries from genesis and verifies that the sum matches
        both the batch balance and the original quantity.
        """
        lock = self._get_batch_lock(batch.id)
        with lock:
            entries = self._entries.get(batch.id, [])
            now = self.clock.now()

            calc_available = 0
            calc_reserved = 0
            calc_picked_up = 0
            calc_delivered = 0
            calc_spoiled = 0
            calc_damaged = 0
            calc_lost = 0

            discrepancies: list[str] = []

            for entry in entries:
                # Deduct from source state
                if entry.from_state == InventoryState.AVAILABLE:
                    calc_available -= entry.quantity
                elif entry.from_state == InventoryState.RESERVED:
                    calc_reserved -= entry.quantity
                elif entry.from_state == InventoryState.PICKED_UP:
                    calc_picked_up -= entry.quantity
                elif entry.from_state == InventoryState.DELIVERED:
                    calc_delivered -= entry.quantity
                elif entry.from_state == InventoryState.SPOILED:
                    calc_spoiled -= entry.quantity

                # Add to destination state
                if entry.to_state == InventoryState.AVAILABLE:
                    calc_available += entry.quantity
                elif entry.to_state == InventoryState.RESERVED:
                    calc_reserved += entry.quantity
                elif entry.to_state == InventoryState.PICKED_UP:
                    calc_picked_up += entry.quantity
                elif entry.to_state == InventoryState.DELIVERED:
                    calc_delivered += entry.quantity
                elif entry.to_state == InventoryState.SPOILED:
                    calc_spoiled += entry.quantity
                elif entry.to_state == InventoryState.DAMAGED:
                    calc_damaged += entry.quantity
                elif entry.to_state == InventoryState.LOST:
                    calc_lost += entry.quantity

            reconciled = InventoryBalanceSnapshot(
                available=calc_available,
                reserved=calc_reserved,
                picked_up=calc_picked_up,
                delivered=calc_delivered,
                spoiled=calc_spoiled,
                damaged=calc_damaged,
                lost=calc_lost,
            )

            current = self._take_snapshot(batch)

            if reconciled.available != current.available:
                discrepancies.append(f"Available mismatch: ledger={reconciled.available} vs batch={current.available}")
            if reconciled.reserved != current.reserved:
                discrepancies.append(f"Reserved mismatch: ledger={reconciled.reserved} vs batch={current.reserved}")
            if reconciled.picked_up != current.picked_up:
                discrepancies.append(f"Picked up mismatch: ledger={reconciled.picked_up} vs batch={current.picked_up}")
            if reconciled.delivered != current.delivered:
                discrepancies.append(f"Delivered mismatch: ledger={reconciled.delivered} vs batch={current.delivered}")
            if reconciled.spoiled != current.spoiled:
                discrepancies.append(f"Spoiled mismatch: ledger={reconciled.spoiled} vs batch={current.spoiled}")

            if reconciled.total != batch.original_quantity:
                discrepancies.append(f"Conservation mismatch: total sum={reconciled.total} != original={batch.original_quantity}")

            is_valid = len(discrepancies) == 0

            return ReconciliationReport(
                batch_id=batch.id,
                original_quantity=batch.original_quantity,
                current_balance=current,
                reconciled_balance=reconciled,
                is_valid=is_valid,
                entry_count=len(entries),
                discrepancies=discrepancies,
                checked_at=now,
            )

    def _append_entry(self, batch_id: str, entry: InventoryLedgerEntry) -> None:
        if batch_id not in self._entries:
            self._entries[batch_id] = []
        self._entries[batch_id].append(entry)

    @staticmethod
    def _take_snapshot(b: Batch) -> InventoryBalanceSnapshot:
        return InventoryBalanceSnapshot(
            available=b.available_quantity,
            reserved=b.reserved_quantity,
            picked_up=b.picked_up_quantity,
            delivered=b.delivered_quantity,
            spoiled=b.spoiled_quantity,
        )
