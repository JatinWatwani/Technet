from fastapi.testclient import TestClient
import pytest

from vigilo.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_seed():
    client.post("/v1/seed")


def test_get_batch_ledger_and_reconciliation_endpoints():
    # Initial seed creates an intake ledger entry
    ledger_res = client.get("/v1/batches/batch_prepared_meals/ledger")
    assert ledger_res.status_code == 200
    entries = ledger_res.json()
    assert len(entries) >= 1
    assert entries[0]["entry_type"] == "INTAKE"
    assert entries[0]["quantity"] == 100

    # Initial reconciliation
    reconcile_res = client.get("/v1/batches/batch_prepared_meals/reconcile")
    assert reconcile_res.status_code == 200
    report = reconcile_res.json()
    assert report["is_valid"] is True
    assert report["current_balance"]["available"] == 100
    assert report["reconciled_balance"]["available"] == 100
    assert len(report["discrepancies"]) == 0


def test_allocation_lifecycle_mirrors_in_ledger():
    # 1. Commit allocation
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 25,
            "travel_minutes": 15,
            "handoff_minutes": 5,
        },
    )
    assert commit_res.status_code == 201
    alloc_id = commit_res.json()["allocation_id"]

    # Ledger should contain RESERVATION_HOLD
    ledger_res = client.get("/v1/batches/batch_prepared_meals/ledger")
    entries = ledger_res.json()
    hold_entries = [e for e in entries if e["entry_type"] == "RESERVATION_HOLD"]
    assert len(hold_entries) == 1
    assert hold_entries[0]["quantity"] == 25
    assert hold_entries[0]["balance_after"]["reserved"] == 25
    assert hold_entries[0]["balance_after"]["available"] == 75

    # 2. Cancel allocation -> releases reservation back to available
    cancel_res = client.post(f"/v1/allocations/{alloc_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["state"] == "CANCELLED"

    # Ledger should contain RESERVATION_RELEASE
    ledger_res_2 = client.get("/v1/batches/batch_prepared_meals/ledger")
    release_entries = [e for e in ledger_res_2.json() if e["entry_type"] == "RESERVATION_RELEASE"]
    assert len(release_entries) == 1
    assert release_entries[0]["quantity"] == 25
    assert release_entries[0]["balance_after"]["available"] == 100
    assert release_entries[0]["balance_after"]["reserved"] == 0

    # Reconciliation must verify 100% mathematical consistency
    reconcile_res = client.get("/v1/batches/batch_prepared_meals/reconcile")
    assert reconcile_res.json()["is_valid"] is True
    assert reconcile_res.json()["current_balance"]["available"] == 100


def test_compensating_adjustment_api():
    # Record compensating adjustment for damaged inventory
    adj_payload = {
        "quantity": 10,
        "from_state": "AVAILABLE",
        "to_state": "SPOILED",
        "reason": "Accidental seal breach during warehouse inspection",
        "actor": "logistics_manager",
    }
    adj_res = client.post("/v1/batches/batch_prepared_meals/adjustments", json=adj_payload)
    assert adj_res.status_code == 201
    entry = adj_res.json()
    assert entry["entry_type"] == "COMPENSATING_ADJUSTMENT"
    assert entry["balance_after"]["available"] == 90
    assert entry["balance_after"]["spoiled"] == 10

    # Batch state reflects adjustment
    batch_res = client.get("/v1/batches/batch_prepared_meals")
    assert batch_res.json()["available_quantity"] == 90
    assert batch_res.json()["spoiled_quantity"] == 10

    # Reconciliation still proves mathematical integrity
    reconcile_res = client.get("/v1/batches/batch_prepared_meals/reconcile")
    assert reconcile_res.json()["is_valid"] is True
