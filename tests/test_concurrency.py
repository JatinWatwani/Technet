from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest

from vigilo.domain.clock import SimulatedClock
from vigilo.domain.ledger import InventoryInsufficientError
from vigilo.domain.ledger_service import InventoryLedgerService
from vigilo.domain.models import Batch, ItemRules


def test_concurrent_reservations_prevent_double_allocation():
    clock = SimulatedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    ledger = InventoryLedgerService(clock=clock)

    # Batch with exactly 50 units
    batch = Batch(
        id="batch_concurrent_50",
        original_quantity=50,
        item_rules=ItemRules(safe_handling_minutes=180),
        created_at=clock.now(),
    )
    ledger.record_intake(batch)

    # 12 concurrent workers each trying to claim 10 units (Total demand: 120 vs 50 available)
    successes = []
    failures = []

    def attempt_reservation(worker_id: int):
        try:
            entry = ledger.hold_reservation(
                batch=batch,
                quantity=10,
                allocation_id=f"alloc_worker_{worker_id}",
                actor=f"worker_{worker_id}",
                reason="Concurrent reservation race test",
            )
            successes.append(entry)
        except InventoryInsufficientError as exc:
            failures.append(exc)

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(attempt_reservation, i) for i in range(12)]
        for f in futures:
            f.result()

    # Invariants under concurrency:
    # 1. Exactly 5 reservations succeeded (5 * 10 = 50)
    assert len(successes) == 5
    # 2. Exactly 7 reservations failed due to insufficient stock
    assert len(failures) == 7
    # 3. No over-allocation / negative inventory
    assert batch.available_quantity == 0
    assert batch.reserved_quantity == 50
    assert batch.available_quantity + batch.reserved_quantity == 50

    # 4. Reconciliation proof passes 100%
    report = ledger.reconcile(batch)
    assert report.is_valid is True
    assert len(report.discrepancies) == 0
    assert report.reconciled_balance.available == 0
    assert report.reconciled_balance.reserved == 50
    assert report.reconciled_balance.total == 50
