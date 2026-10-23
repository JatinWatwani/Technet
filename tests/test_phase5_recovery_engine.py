from __future__ import annotations

from datetime import timedelta
from fastapi.testclient import TestClient
import pytest

from vigilo.main import app, service
from vigilo.domain.models import ShelterStatus, DeliveryState, AllocationState

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_state():
    """Reset seed data and clock before each test."""
    client.post("/v1/seed")


def test_ghost_reservation_recovery_and_expiration_worker():
    """Verify that unpicked allocations past lease deadline recover safely via the expiration worker."""
    # 1. Commit an allocation
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 30,
            "travel_minutes": 15,
            "handoff_minutes": 5,
        },
    )
    assert commit_res.status_code == 201
    alloc_id = commit_res.json()["allocation_id"]

    # Verify inventory is reserved
    ledger_entries = client.get("/v1/batches/batch_prepared_meals/ledger").json()
    assert any(e["entry_type"] == "RESERVATION_HOLD" and e["quantity"] == 30 for e in ledger_entries)

    # 2. Advance time past the 15-minute lease deadline (advance 20 minutes)
    adv_res = client.post("/v1/clock/advance", json={"minutes": 20})
    assert adv_res.status_code == 200

    # 3. Trigger expiration worker sweep
    sweep_res = client.post("/v1/workers/expire-allocations")
    assert sweep_res.status_code == 200
    data = sweep_res.json()
    assert data["expired_count"] >= 1
    assert alloc_id in data["expired_ids"]

    # 4. Verify allocation state is now EXPIRED
    alloc_res = client.get(f"/v1/allocations/{alloc_id}")
    assert alloc_res.status_code == 200
    assert alloc_res.json()["state"] == "EXPIRED"

    # 5. Verify reserved inventory was released back to available stock in the immutable ledger
    ledger_after = client.get("/v1/batches/batch_prepared_meals/ledger").json()
    releases = [e for e in ledger_after if e["entry_type"] == "RESERVATION_RELEASE" and e["allocation_id"] == alloc_id]
    assert len(releases) == 1
    assert releases[0]["balance_after"]["available"] == 100
    assert releases[0]["balance_after"]["reserved"] == 0

    # 6. Verify mathematical reconciliation
    rec_res = client.get("/v1/batches/batch_prepared_meals/reconcile")
    assert rec_res.status_code == 200
    assert rec_res.json()["is_valid"] is True


def test_cargo_picked_up_cannot_be_expired_or_dumped_into_inventory():
    """Verify strict invariant: once picked up, cargo CANNOT be expired by the worker."""
    # 1. Commit, acknowledge, and pick up cargo
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

    ack_res = client.post(
        f"/v1/allocations/{alloc_id}/acknowledge",
        headers={"X-Actor-Role": "RIDER", "X-Actor": "rider_gamma"},
    )
    assert ack_res.status_code == 200

    pickup_res = client.post(
        f"/v1/allocations/{alloc_id}/pickup",
        headers={"X-Actor-Role": "RIDER", "X-Actor": "rider_gamma"},
    )
    assert pickup_res.status_code == 200
    deliv_id = pickup_res.json()["id"]

    # 2. Advance time by 20 minutes
    client.post("/v1/clock/advance", json={"minutes": 20})

    # 3. Expiration worker sweep runs
    sweep_res = client.post("/v1/workers/expire-allocations")
    assert sweep_res.status_code == 200
    assert alloc_id not in sweep_res.json().get("expired_ids", [])

    # Verify allocation is still PICKED_UP
    alloc_res = client.get(f"/v1/allocations/{alloc_id}")
    assert alloc_res.json()["state"] == "PICKED_UP"

    # Verify inventory ledger: picked_up balance remains 25, available remains 75
    reconcile = client.get("/v1/batches/batch_prepared_meals/reconcile").json()
    assert reconcile["current_balance"]["picked_up"] == 25
    assert reconcile["current_balance"]["available"] == 75


def test_shelter_closure_cascading_recovery_and_in_transit_rerouting():
    """Verify shelter closure triggers cascading recovery:
    - Unpicked allocations are cancelled and released to inventory.
    - Physical cargo is preserved in transit and rerouted to an alternative shelter."""
    # 1. Commit an unpicked allocation to shelter_central
    commit_1 = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_cold_meds",
            "rider_id": "rider_beta",
            "shelter_id": "shelter_central",
            "quantity": 10,
            "travel_minutes": 10,
            "handoff_minutes": 5,
        },
    )
    assert commit_1.status_code == 201
    unpicked_alloc_id = commit_1.json()["allocation_id"]

    # 2. Commit, acknowledge, and pickup a delivery to shelter_central
    commit_2 = client.post(
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
    assert commit_2.status_code == 201
    picked_alloc_id = commit_2.json()["allocation_id"]

    client.post(
        f"/v1/allocations/{picked_alloc_id}/acknowledge",
        headers={"X-Actor-Role": "RIDER", "X-Actor": "rider_gamma"},
    )
    pickup_res = client.post(
        f"/v1/allocations/{picked_alloc_id}/pickup",
        headers={"X-Actor-Role": "RIDER", "X-Actor": "rider_gamma"},
    )
    assert pickup_res.status_code == 200
    delivery_id = pickup_res.json()["id"]

    # 3. Preview reroute for the delivery before closure
    preview_res = client.post(f"/v1/deliveries/{delivery_id}/reroute/preview")
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["delivery_id"] == delivery_id
    assert len(preview_data["candidates"]) > 0
    assert any(c["feasible"] for c in preview_data["candidates"])

    # 4. Close shelter_central (with auto_reroute=True)
    close_res = client.post(
        "/v1/shelters/shelter_central/close",
        json={"reason": "Flash flood warning at facility", "auto_reroute": True},
        headers={"X-Actor-Role": "DISPATCHER", "X-Actor": "dispatcher"},
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"

    # 5. Verify unpicked allocation was CANCELLED and inventory restored
    unpicked_alloc = client.get(f"/v1/allocations/{unpicked_alloc_id}").json()
    assert unpicked_alloc["state"] == "CANCELLED"

    meds_ledger = client.get("/v1/batches/batch_cold_meds/ledger").json()
    assert any(e["entry_type"] == "RESERVATION_RELEASE" and e["allocation_id"] == unpicked_alloc_id for e in meds_ledger)

    # 6. Verify physical cargo was automatically rerouted to a feasible alternative shelter
    deliv_after = service.deliveries[delivery_id]
    assert deliv_after.current_shelter_id != "shelter_central"
    assert "shelter_central" in deliv_after.destination_history
    assert deliv_after.current_shelter_id in deliv_after.destination_history
    assert deliv_after.state == DeliveryState.IN_TRANSIT

    # 7. Deliver cargo to the new destination shelter
    deliv_res = client.post(
        f"/v1/deliveries/{delivery_id}/deliver",
        headers={"X-Actor-Role": "RIDER", "X-Actor": "rider_gamma"},
    )
    assert deliv_res.status_code == 200
    assert deliv_res.json()["state"] == "DELIVERED"


def test_unrecoverable_closure_escalates_to_explicit_incident():
    """Verify that when no alternative destination is feasible, delivery transitions to INCIDENT_REVIEW
    and creates an explicit CRITICAL incident without dropping cargo."""
    # 1. Close all potential alternative shelters first
    for s_id in ["shelter_eastside", "shelter_westside", "shelter_closed"]:
        if s_id in service.shelters:
            service.shelters[s_id].status = ShelterStatus.CLOSED
            service.shelters[s_id].open = False

    # 2. Pick up cargo destined for shelter_central
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

    client.post(
        f"/v1/allocations/{alloc_id}/acknowledge",
        headers={"X-Actor-Role": "RIDER", "X-Actor": "rider_gamma"},
    )
    pickup_res = client.post(
        f"/v1/allocations/{alloc_id}/pickup",
        headers={"X-Actor-Role": "RIDER", "X-Actor": "rider_gamma"},
    )
    assert pickup_res.status_code == 200
    deliv_id = pickup_res.json()["id"]

    # 3. Close the last open shelter (shelter_central)
    close_res = client.post(
        "/v1/shelters/shelter_central/close",
        json={"reason": "Structural damage", "auto_reroute": True},
        headers={"X-Actor-Role": "DISPATCHER", "X-Actor": "dispatcher"},
    )
    assert close_res.status_code == 200

    # 4. Delivery cannot be rerouted: must be in INCIDENT_REVIEW
    deliv = service.deliveries[deliv_id]
    assert deliv.state == DeliveryState.INCIDENT_REVIEW

    # 5. Explicit Incident must exist
    incidents_res = client.get("/v1/incidents?affected_entity_type=Delivery")
    assert incidents_res.status_code == 200
    incidents = incidents_res.json()
    deliv_inc = next((i for i in incidents if i["affected_entity_id"] == deliv_id), None)
    assert deliv_inc is not None
    assert deliv_inc["severity"] == "CRITICAL"
    assert deliv_inc["status"] == "OPEN"
    assert deliv_inc["reason_code"] == "RECOVERY_NOT_FEASIBLE"


def test_heartbeat_monitor_and_incident_resolution_flow():
    """Verify heartbeat monitor detects stale telemetry and test incident escalation/resolution."""
    # 1. Assign rider with active cargo
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 20,
            "travel_minutes": 10,
            "handoff_minutes": 5,
        },
    )
    assert commit_res.status_code == 201

    # 2. Set rider heartbeat to 2 hours in the past
    now = service.clock.now()
    service.riders["rider_gamma"].last_heartbeat_at = now - timedelta(hours=2)

    # 3. Run heartbeat monitor sweep
    sweep_res = client.post("/v1/workers/monitor-heartbeats?max_staleness_minutes=30")
    assert sweep_res.status_code == 200
    assert sweep_res.json()["stale_riders_incident_count"] >= 1
    inc_id = sweep_res.json()["incident_ids"][0]

    # 4. Fetch incident
    inc_res = client.get(f"/v1/incidents/{inc_id}")
    assert inc_res.status_code == 200
    inc_data = inc_res.json()
    assert inc_data["affected_entity_id"] == "rider_gamma"
    assert inc_data["reason_code"] == "RIDER_HEARTBEAT_EXPIRED"

    # 5. Escalate incident
    esc_res = client.post(f"/v1/incidents/{inc_id}/escalate", json={"reason": "Cannot contact rider phone"})
    assert esc_res.status_code == 200
    assert esc_res.json()["status"] == "ESCALATED"
    assert esc_res.json()["severity"] == "CRITICAL"

    # 6. Resolve incident
    res_res = client.post(f"/v1/incidents/{inc_id}/resolve", json={"resolution_notes": "Rider checked in via radio"})
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"
    assert res_res.json()["resolved_at"] is not None


def test_worker_run_all_sweeps():
    """Verify running the combined periodic sweeps endpoint."""
    res = client.post("/v1/workers/run-sweeps")
    assert res.status_code == 200
    data = res.json()
    assert "expired_allocations_count" in data
    assert "stale_rider_heartbeats_count" in data
    assert "safety_deadline_incidents_count" in data
    assert "incidents_created" in data
