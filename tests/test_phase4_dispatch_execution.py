"""Integration tests for Phase 4 Dispatch Execution, Lease Deadlines, Outbox, and Audit trail."""
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest

from vigilo.main import app, global_clock

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_state():
    client.post("/v1/seed")


def test_full_dispatch_lifecycle_and_audit_reconstruction():
    # 1. Commit a valid dispatch
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 25,
            "travel_minutes": 20,
            "handoff_minutes": 10,
        },
    )
    assert commit_res.status_code == 201
    alloc_data = commit_res.json()
    alloc_id = alloc_data["allocation_id"]
    assert alloc_data["state"] == "CLAIMED"

    # 2. Verify outbox message was staged in PENDING status
    outbox_res = client.get("/v1/outbox/messages")
    assert outbox_res.status_code == 200
    messages = outbox_res.json()
    assert len(messages) > 0
    claimed_msg = next((m for m in messages if m["event_type"] == "ALLOCATION_CLAIMED"), None)
    assert claimed_msg is not None
    assert claimed_msg["status"] == "PENDING"

    # 3. Publish outbox messages
    pub_res = client.post("/v1/outbox/publish")
    assert pub_res.status_code == 200
    assert pub_res.json()["published_count"] > 0

    # Verify status changed to PUBLISHED
    outbox_after = client.get("/v1/outbox/messages").json()
    claimed_after = next((m for m in outbox_after if m["id"] == claimed_msg["id"]), None)
    assert claimed_after["status"] == "PUBLISHED"
    assert claimed_after["published_at"] is not None

    # 4. Acknowledge allocation with authorized role
    ack_res = client.post(
        f"/v1/allocations/{alloc_id}/acknowledge",
        headers={"X-Actor": "rider_gamma", "X-Actor-Role": "RIDER"},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["state"] == "ACKNOWLEDGED"

    # 5. Confirm pickup by rider
    pickup_res = client.post(
        f"/v1/allocations/{alloc_id}/pickup",
        headers={"X-Actor": "rider_gamma", "X-Actor-Role": "RIDER"},
    )
    assert pickup_res.status_code == 200
    deliv_data = pickup_res.json()
    deliv_id = deliv_data["id"]
    assert deliv_data["state"] == "PICKED_UP"
    assert deliv_data["quantity"] == 25

    # 6. Deliver cargo to destination shelter
    deliver_res = client.post(
        f"/v1/deliveries/{deliv_id}/deliver",
        headers={"X-Actor": "rider_gamma", "X-Actor-Role": "RIDER"},
    )
    assert deliver_res.status_code == 200
    assert deliver_res.json()["state"] == "DELIVERED"

    # 7. Reconstruct complete batch history from audit and immutable ledger
    audit_res = client.get("/v1/audit/inventory/batch_prepared_meals")
    assert audit_res.status_code == 200
    history = audit_res.json()
    assert history["batch_id"] == "batch_prepared_meals"
    assert history["original_quantity"] == 100
    assert history["current_status"]["available"] == 75
    assert history["current_status"]["delivered"] == 25
    assert history["ledger_entries_count"] >= 4
    assert history["related_events_count"] >= 4


def test_lease_expiration_blocks_late_acknowledgement():
    # 1. Commit dispatch
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 10,
            "travel_minutes": 15,
            "handoff_minutes": 5,
        },
    )
    assert commit_res.status_code == 201
    alloc_id = commit_res.json()["allocation_id"]

    # 2. Advance clock by 20 minutes (past 15-minute lease)
    client.post("/v1/clock/advance", json={"minutes": 20, "seconds": 0})

    # 3. Attempt to acknowledge -> must be rejected with CLAIM_EXPIRED
    ack_res = client.post(
        f"/v1/allocations/{alloc_id}/acknowledge",
        headers={"X-Actor": "rider_gamma", "X-Actor-Role": "RIDER"},
    )
    assert ack_res.status_code == 400
    data = ack_res.json()
    assert data["detail"]["code"] == "CLAIM_EXPIRED"


def test_role_based_authorization():
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 10,
            "travel_minutes": 15,
            "handoff_minutes": 5,
        },
    )
    assert commit_res.status_code == 201
    alloc_id = commit_res.json()["allocation_id"]

    # Unauthorized role DONOR attempting to acknowledge
    ack_res = client.post(
        f"/v1/allocations/{alloc_id}/acknowledge",
        headers={"X-Actor": "unauthorized_user", "X-Actor-Role": "DONOR"},
    )
    assert ack_res.status_code == 403
    assert ack_res.json()["detail"]["code"] == "AUTHORIZATION_DENIED"


def test_cancel_unpicked_allocation_restores_inventory():
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 20,
            "travel_minutes": 15,
            "handoff_minutes": 5,
        },
    )
    assert commit_res.status_code == 201
    alloc_id = commit_res.json()["allocation_id"]

    # Cancel the unpicked allocation
    cancel_res = client.post(
        f"/v1/allocations/{alloc_id}/cancel",
        params={"reason": "Rider flat tire"},
        headers={"X-Actor": "dispatcher", "X-Actor-Role": "DISPATCHER"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["state"] == "CANCELLED"

    # Verify inventory was restored to available
    batch_res = client.get("/v1/batches/batch_prepared_meals")
    assert batch_res.json()["available_quantity"] == 100
    assert batch_res.json()["reserved_quantity"] == 0


def test_cannot_cancel_picked_up_cargo():
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 15,
            "travel_minutes": 15,
            "handoff_minutes": 5,
        },
    )
    assert commit_res.status_code == 201
    alloc_id = commit_res.json()["allocation_id"]

    # Pickup cargo
    client.post(f"/v1/allocations/{alloc_id}/pickup")

    # Attempt to cancel picked-up allocation -> Must be rejected!
    cancel_res = client.post(
        f"/v1/allocations/{alloc_id}/cancel",
        headers={"X-Actor": "dispatcher", "X-Actor-Role": "DISPATCHER"},
    )
    assert cancel_res.status_code == 400
    assert cancel_res.json()["detail"]["code"] == "INVALID_STATE_TRANSITION"
