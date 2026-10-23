from fastapi.testclient import TestClient
import pytest

from vigilo.main import app, service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_service_seed():
    # Reset in-memory domain state before each test
    client.post("/v1/seed")


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_clock_endpoints():
    res = client.get("/v1/clock")
    assert res.status_code == 200
    data = res.json()
    assert "current_time" in data
    assert data["clock_type"] == "SimulatedClock"

    # Advance clock by 30 minutes
    advance_res = client.post("/v1/clock/advance", json={"minutes": 30, "seconds": 0})
    assert advance_res.status_code == 200
    advanced_data = advance_res.json()
    assert advanced_data["current_time"] != data["current_time"]


def test_list_and_create_batch():
    # List initial batches
    res = client.get("/v1/batches")
    assert res.status_code == 200
    batches = res.json()
    assert len(batches) >= 4

    # Create new batch
    new_batch = {
        "id": "batch_custom_test",
        "donor_id": "donor_metro_food",
        "item_type": "canned_goods",
        "original_quantity": 250,
        "item_rules": {
            "safe_handling_minutes": 500,
            "safety_buffer_minutes": 20,
            "required_prerequisites": [],
            "storage_requirement": "AMBIENT",
        },
    }
    create_res = client.post("/v1/batches", json=new_batch)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["id"] == "batch_custom_test"
    assert created["available_quantity"] == 250

    # Get batch by ID
    get_res = client.get("/v1/batches/batch_custom_test")
    assert get_res.status_code == 200
    assert get_res.json()["item_type"] == "canned_goods"


def test_rider_operations_and_state_machine():
    res = client.get("/v1/riders")
    assert res.status_code == 200
    riders = res.json()
    assert len(riders) >= 4

    # Record heartbeat
    hb_res = client.post("/v1/riders/rider_alpha/heartbeat")
    assert hb_res.status_code == 200
    assert hb_res.json()["last_heartbeat_at"] is not None

    # Valid status transition: AVAILABLE -> OFFLINE
    status_res = client.patch("/v1/riders/rider_alpha/status", json={"status": "OFFLINE"})
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "OFFLINE"
    assert not status_res.json()["available"]

    # Invalid status transition: OFFLINE -> IN_TRANSIT (must be rejected)
    invalid_res = client.patch("/v1/riders/rider_alpha/status", json={"status": "IN_TRANSIT"})
    assert invalid_res.status_code == 400
    assert invalid_res.json()["detail"]["code"] == "INVALID_STATE_TRANSITION"


def test_shelter_operations_and_demand_update():
    res = client.get("/v1/shelters/shelter_central")
    assert res.status_code == 200
    assert res.json()["open"] is True

    # Update shelter demand
    demand_res = client.patch(
        "/v1/shelters/shelter_central/demand",
        json={"demand_remaining": 85, "receiving_capacity_remaining": 85},
    )
    assert demand_res.status_code == 200
    assert demand_res.json()["demand_remaining"] == 85

    # Update shelter status to CLOSED
    status_res = client.patch("/v1/shelters/shelter_central/status", json={"status": "CLOSED"})
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "CLOSED"
    assert status_res.json()["open"] is False


def test_end_to_end_dispatch_and_physical_delivery_flow():
    # 1. Preview dispatch
    preview_res = client.post(
        "/v1/dispatch/preview",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_beta",
            "shelter_id": "shelter_central",
            "quantity": 30,
            "travel_minutes": 25,
            "handoff_minutes": 10,
        },
    )
    assert preview_res.status_code == 200
    assert preview_res.json()["feasible"] is True

    # 2. Commit dispatch -> creates Allocation in CLAIMED state
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_beta",
            "shelter_id": "shelter_central",
            "quantity": 30,
            "travel_minutes": 25,
            "handoff_minutes": 10,
        },
    )
    assert commit_res.status_code == 201
    alloc_id = commit_res.json()["allocation_id"]

    # Check allocation state
    alloc_res = client.get(f"/v1/allocations/{alloc_id}")
    assert alloc_res.status_code == 200
    assert alloc_res.json()["state"] == "CLAIMED"

    # 3. Rider acknowledges allocation
    ack_res = client.post(f"/v1/allocations/{alloc_id}/acknowledge")
    assert ack_res.status_code == 200
    assert ack_res.json()["state"] == "ACKNOWLEDGED"

    # 4. Cargo is picked up -> creates physical Delivery in PICKED_UP state
    pickup_res = client.post(f"/v1/allocations/{alloc_id}/pickup")
    assert pickup_res.status_code == 200
    deliv_id = pickup_res.json()["id"]
    assert pickup_res.json()["state"] == "PICKED_UP"

    # Verify inventory was transferred to picked_up_quantity
    batch_res = client.get("/v1/batches/batch_prepared_meals")
    assert batch_res.json()["picked_up_quantity"] == 30
    assert batch_res.json()["reserved_quantity"] == 0

    # 5. Deliver cargo to destination
    deliver_res = client.post(f"/v1/deliveries/{deliv_id}/deliver")
    assert deliver_res.status_code == 200
    assert deliver_res.json()["state"] == "DELIVERED"

    # Verify inventory was marked delivered
    batch_res_after = client.get("/v1/batches/batch_prepared_meals")
    assert batch_res_after.json()["delivered_quantity"] == 30
    assert batch_res_after.json()["picked_up_quantity"] == 0

    # 6. Verify operational event stream recorded the lifecycle events
    events_res = client.get("/v1/events")
    assert events_res.status_code == 200
    events = events_res.json()
    event_types = [e["event_type"] for e in events]
    assert "ALLOCATION_CLAIMED" in event_types
    assert "ALLOCATION_ACKNOWLEDGED" in event_types
    assert "CARGO_PICKED_UP" in event_types
    assert "DELIVERY_COMPLETED" in event_types
