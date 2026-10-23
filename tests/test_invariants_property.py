from datetime import datetime, timezone
from hypothesis import given, strategies as st
import pytest

from vigilo.domain.models import Batch, ItemRules, Rider


@given(
    original_qty=st.integers(min_value=1, max_value=10000),
    reserved=st.integers(min_value=0, max_value=10000),
    picked_up=st.integers(min_value=0, max_value=10000),
    delivered=st.integers(min_value=0, max_value=10000),
    spoiled=st.integers(min_value=0, max_value=10000),
)
def test_batch_quantity_conservation_property(original_qty, reserved, picked_up, delivered, spoiled):
    """Property test: Batch quantity conservation equation must strictly hold."""
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rules = ItemRules(safe_handling_minutes=120)

    sum_subquantities = reserved + picked_up + delivered + spoiled
    available = original_qty - sum_subquantities

    if available >= 0:
        # Should construct validly and preserve invariants
        batch = Batch(
            id="batch_prop",
            original_quantity=original_qty,
            available_quantity=available,
            reserved_quantity=reserved,
            picked_up_quantity=picked_up,
            delivered_quantity=delivered,
            spoiled_quantity=spoiled,
            item_rules=rules,
            created_at=created_at,
        )
        assert (
            batch.available_quantity
            + batch.reserved_quantity
            + batch.picked_up_quantity
            + batch.delivered_quantity
            + batch.spoiled_quantity
            == original_qty
        )
    else:
        # Sum of subquantities exceeds original quantity, available is negative
        with pytest.raises(ValueError):
            Batch(
                id="batch_prop_invalid",
                original_quantity=original_qty,
                available_quantity=available,
                reserved_quantity=reserved,
                picked_up_quantity=picked_up,
                delivered_quantity=delivered,
                spoiled_quantity=spoiled,
                item_rules=rules,
                created_at=created_at,
            )


@given(
    capacity=st.integers(min_value=1, max_value=5000),
    active_load=st.integers(min_value=0, max_value=10000),
)
def test_rider_capacity_invariants_property(capacity, active_load):
    """Property test: Rider active load must never exceed capacity."""
    if active_load <= capacity:
        rider = Rider(id="rider_prop", capacity=capacity, active_load=active_load)
        assert rider.remaining_capacity >= 0
        assert rider.remaining_capacity == capacity - active_load
    else:
        with pytest.raises(ValueError):
            Rider(id="rider_prop_invalid", capacity=capacity, active_load=active_load)


@given(
    initial_qty=st.integers(min_value=20, max_value=2000),
    q1=st.integers(min_value=1, max_value=10),
    q2=st.integers(min_value=1, max_value=10),
)
def test_ledger_reconciliation_property(initial_qty, q1, q2):
    """Property test: Ledger reconciliation must always produce an exact, discrepancy-free report."""
    from vigilo.domain.clock import SimulatedClock
    from vigilo.domain.ledger_service import InventoryLedgerService

    clock = SimulatedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    ledger = InventoryLedgerService(clock=clock)
    batch = Batch(
        id=f"batch_prop_{initial_qty}",
        original_quantity=initial_qty,
        item_rules=ItemRules(safe_handling_minutes=180),
        created_at=clock.now(),
    )
    ledger.record_intake(batch)

    # Perform holds, releases, pickups
    ledger.hold_reservation(batch, q1, allocation_id="alloc_1")
    ledger.record_pickup(batch, q1, allocation_id="alloc_1", delivery_id="deliv_1")
    ledger.confirm_delivery(batch, q1, delivery_id="deliv_1")

    if batch.available_quantity >= q2:
        ledger.hold_reservation(batch, q2, allocation_id="alloc_2")
        ledger.release_reservation(batch, q2, allocation_id="alloc_2")

    report = ledger.reconcile(batch)
    assert report.is_valid is True
    assert len(report.discrepancies) == 0
    assert report.reconciled_balance.total == initial_qty

