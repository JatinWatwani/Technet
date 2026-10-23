from datetime import datetime, timezone
import pytest

from vigilo.domain.clock import SimulatedClock
from vigilo.domain.errors import StateTransitionError
from vigilo.domain.ledger import (
    InventoryConflictError,
    InventoryInsufficientError,
    InventoryState,
    LedgerEntryType,
)
from vigilo.domain.ledger_service import InventoryLedgerService
from vigilo.domain.models import Batch, ItemRules


@pytest.fixture
def test_clock():
    return SimulatedClock(datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def ledger_service(test_clock):
    return InventoryLedgerService(clock=test_clock)


@pytest.fixture
def sample_batch(test_clock):
    return Batch(
        id="batch_test_100",
        original_quantity=100,
        item_rules=ItemRules(safe_handling_minutes=180),
        created_at=test_clock.now(),
    )


def test_intake_entry_records_initial_balance(ledger_service, sample_batch):
    entry = ledger_service.record_intake(sample_batch, reason="Genesis batch donation")

    assert entry.entry_type == LedgerEntryType.INTAKE
    assert entry.quantity == 100
    assert entry.from_state is None
    assert entry.to_state == InventoryState.AVAILABLE
    assert entry.balance_after.available == 100
    assert entry.balance_after.total == 100

    ledger = ledger_service.get_ledger(sample_batch.id)
    assert len(ledger) == 1
    assert ledger[0].id == entry.id


def test_hold_reservation_and_insufficient_inventory(ledger_service, sample_batch):
    ledger_service.record_intake(sample_batch)

    # Valid hold 40 units
    hold_entry = ledger_service.hold_reservation(
        batch=sample_batch,
        quantity=40,
        allocation_id="alloc_1",
    )
    assert hold_entry.entry_type == LedgerEntryType.RESERVATION_HOLD
    assert hold_entry.quantity == 40
    assert hold_entry.balance_after.available == 60
    assert hold_entry.balance_after.reserved == 40
    assert sample_batch.available_quantity == 60
    assert sample_batch.reserved_quantity == 40

    # Attempting to hold more than remaining available (61 > 60) must fail
    with pytest.raises(InventoryInsufficientError):
        ledger_service.hold_reservation(
            batch=sample_batch,
            quantity=61,
            allocation_id="alloc_2",
        )

    # Invariants intact
    assert sample_batch.available_quantity == 60
    assert sample_batch.reserved_quantity == 40


def test_release_reservation_back_to_available(ledger_service, sample_batch):
    ledger_service.record_intake(sample_batch)
    ledger_service.hold_reservation(sample_batch, 50, allocation_id="alloc_1")

    # Release 50 units (e.g. rider dropped out / lease expired)
    release_entry = ledger_service.release_reservation(
        batch=sample_batch,
        quantity=50,
        allocation_id="alloc_1",
        reason="Claim expired before pickup",
    )
    assert release_entry.entry_type == LedgerEntryType.RESERVATION_RELEASE
    assert release_entry.quantity == 50
    assert release_entry.balance_after.available == 100
    assert release_entry.balance_after.reserved == 0
    assert sample_batch.available_quantity == 100
    assert sample_batch.reserved_quantity == 0


def test_pickup_and_delivery_lifecycle(ledger_service, sample_batch):
    ledger_service.record_intake(sample_batch)
    ledger_service.hold_reservation(sample_batch, 30, allocation_id="alloc_1")

    # Confirm pickup
    pickup_entry = ledger_service.record_pickup(
        batch=sample_batch,
        quantity=30,
        allocation_id="alloc_1",
        delivery_id="deliv_1",
    )
    assert pickup_entry.entry_type == LedgerEntryType.PICKUP_CONFIRMED
    assert sample_batch.reserved_quantity == 0
    assert sample_batch.picked_up_quantity == 30
    assert pickup_entry.balance_after.picked_up == 30

    # Invariant check: Cannot release cargo after pickup via unpicked release worker!
    with pytest.raises(InventoryConflictError):
        ledger_service.release_reservation(sample_batch, 30, allocation_id="alloc_1")

    # Confirm delivery
    deliv_entry = ledger_service.confirm_delivery(
        batch=sample_batch,
        quantity=30,
        delivery_id="deliv_1",
    )
    assert deliv_entry.entry_type == LedgerEntryType.DELIVERY_CONFIRMED
    assert sample_batch.picked_up_quantity == 0
    assert sample_batch.delivered_quantity == 30
    assert deliv_entry.balance_after.delivered == 30


def test_full_reconciliation_proof(ledger_service, sample_batch):
    ledger_service.record_intake(sample_batch)
    ledger_service.hold_reservation(sample_batch, 40, "alloc_1")
    ledger_service.record_pickup(sample_batch, 40, "alloc_1", "deliv_1")
    ledger_service.confirm_delivery(sample_batch, 40, "deliv_1")
    ledger_service.hold_reservation(sample_batch, 20, "alloc_2")

    report = ledger_service.reconcile(sample_batch)

    assert report.is_valid is True
    assert len(report.discrepancies) == 0
    assert report.entry_count == 5
    assert report.reconciled_balance.available == 40
    assert report.reconciled_balance.reserved == 20
    assert report.reconciled_balance.delivered == 40
    assert report.reconciled_balance.total == 100


def test_compensating_adjustment_reconciliation(ledger_service, sample_batch):
    ledger_service.record_intake(sample_batch)

    # 10 units spoiled due to temperature break
    adj_entry = ledger_service.record_compensating_adjustment(
        batch=sample_batch,
        quantity=10,
        from_state=InventoryState.AVAILABLE,
        to_state=InventoryState.SPOILED,
        actor="quality_inspector",
        reason="Cooling compressor failure during storage",
    )
    assert adj_entry.entry_type == LedgerEntryType.COMPENSATING_ADJUSTMENT
    assert sample_batch.available_quantity == 90
    assert sample_batch.spoiled_quantity == 10

    # Full reconciliation still passes with exact math
    report = ledger_service.reconcile(sample_batch)
    assert report.is_valid is True
    assert report.reconciled_balance.available == 90
    assert report.reconciled_balance.spoiled == 10
    assert report.reconciled_balance.total == 100
