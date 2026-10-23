from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from vigilo.domain.clock import SimulatedClock
from vigilo.domain.ledger_service import InventoryLedgerService
from vigilo.domain.models import Batch, ItemRules
from vigilo.main import app

client = TestClient(app)


def test_ledger_service_idempotency():
    clock = SimulatedClock(datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc))
    service = InventoryLedgerService(clock=clock)
    batch = Batch(id="b_idem", original_quantity=100, item_rules=ItemRules(180), created_at=clock.now())
    service.record_intake(batch)

    # First attempt with key
    key = "idem_req_12345"
    e1 = service.hold_reservation(batch, 40, "alloc_idem", idempotency_key=key)
    assert batch.available_quantity == 60
    assert batch.reserved_quantity == 40

    # Second attempt with same key (e.g. network retry)
    e2 = service.hold_reservation(batch, 40, "alloc_idem", idempotency_key=key)

    # Must return exact same entry ID and NOT deduct inventory twice!
    assert e1.id == e2.id
    assert batch.available_quantity == 60
    assert batch.reserved_quantity == 40
    assert len(service.get_ledger(batch.id)) == 2  # intake + 1 hold entry only


def test_api_dispatch_commit_idempotency():
    client.post("/v1/seed")

    payload = {
        "batch_id": "batch_prepared_meals",
        "rider_id": "rider_gamma",
        "shelter_id": "shelter_central",
        "quantity": 30,
        "travel_minutes": 20,
        "handoff_minutes": 10,
        "idempotency_key": "api_key_retry_999",
    }

    # First commit
    res1 = client.post("/v1/dispatch/commit", json=payload)
    assert res1.status_code == 201
    alloc_id_1 = res1.json()["allocation_id"]

    # Check inventory deduction
    batch_res_1 = client.get("/v1/batches/batch_prepared_meals")
    assert batch_res_1.json()["available_quantity"] == 70  # 100 - 30

    # Second commit with same idempotency key
    res2 = client.post("/v1/dispatch/commit", json=payload)
    assert res2.status_code == 201
    alloc_id_2 = res2.json()["allocation_id"]

    # Must return the identical allocation ID
    assert alloc_id_1 == alloc_id_2

    # Inventory must NOT be deducted again
    batch_res_2 = client.get("/v1/batches/batch_prepared_meals")
    assert batch_res_2.json()["available_quantity"] == 70
