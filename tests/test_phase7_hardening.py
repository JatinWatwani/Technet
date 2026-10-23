import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from vigilo.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_seed():
    """Ensure clean seeded state before each test."""
    client.post("/v1/seed")


def test_health_endpoints():
    """Verify both /health and /v1/health return 200 OK status."""
    res1 = client.get("/health")
    assert res1.status_code == 200
    assert res1.json() == {"status": "ok"}

    res2 = client.get("/v1/health")
    assert res2.status_code == 200
    assert res2.json() == {"status": "ok"}


def test_readiness_probe():
    """Verify /v1/ready reports storage, clock, ledger reconciliation, and worker readiness."""
    res = client.get("/v1/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "clock" in data
    assert "storage" in data
    assert "ledger" in data
    assert data["ledger"]["reconciled"] is True
    assert data["workers"]["sweeper_ready"] is True


def test_metrics_json_schema():
    """Verify /v1/metrics exposes structured operational and inventory metrics."""
    res = client.get("/v1/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert metrics["system_status"] == "HEALTHY"
    assert metrics["batches_count"] >= 4
    assert metrics["riders_total"] >= 4
    assert metrics["shelters_total"] >= 4
    assert metrics["inventory_spoiled_units"] == 0
    assert metrics["ledger_reconciliation_healthy"] is True
    assert metrics["audit_records_total"] >= 0


def test_metrics_prometheus_format():
    """Verify /v1/metrics returns Prometheus exposition format when requested."""
    res = client.get("/v1/metrics?format=prometheus")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    text = res.text
    assert "# HELP vigilo_system_status" in text
    assert "# TYPE vigilo_system_status gauge" in text
    assert "vigilo_system_status 1" in text
    assert "vigilo_batches_total" in text
    assert "vigilo_inventory_spoiled_units" in text
    assert "vigilo_ledger_reconciliation_healthy 1" in text


def test_audit_decision_and_inventory_trail():
    """Verify /v1/audit/decisions and /v1/audit/inventory endpoints provide full traceability."""
    # 1. Commit a dispatch to produce an audit record
    commit_res = client.post(
        "/v1/dispatch/commit",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_alpha",
            "shelter_id": "shelter_central",
            "quantity": 25,
            "travel_minutes": 20,
            "handoff_minutes": 5,
        },
    )
    assert commit_res.status_code == 201

    # 2. Inspect events
    events_res = client.get("/v1/events")
    assert events_res.status_code == 200
    events = events_res.json()
    claim_event = next(e for e in events if e["event_type"] == "ALLOCATION_CLAIMED")
    assert claim_event["payload"]["batch_id"] == "batch_prepared_meals"

    # 3. Inspect audit inventory history
    audit_inv_res = client.get("/v1/audit/inventory/batch_prepared_meals")
    assert audit_inv_res.status_code == 200
    inv_data = audit_inv_res.json()
    assert inv_data["batch_id"] == "batch_prepared_meals"
    assert inv_data["ledger_entries_count"] >= 2  # intake + reservation hold
    assert len(inv_data["ledger_timeline"]) >= 2


def test_emergency_override_requires_admin_role():
    """Verify non-admin roles are rejected when attempting emergency overrides."""
    payload = {
        "override_type": "RECEIVING_HOURS_OVERRIDE",
        "target_entity_type": "Shelter",
        "target_entity_id": "shelter_central",
        "justification": "Emergency night deliveries during flood crisis",
        "authorized_by": "Ops Manager",
    }

    # No role header -> 403
    res_no_role = client.post("/v1/emergency/override", json=payload)
    assert res_no_role.status_code == 403

    # Rider role -> 403
    res_rider = client.post("/v1/emergency/override", json=payload, headers={"X-Actor-Role": "RIDER"})
    assert res_rider.status_code == 403


def test_emergency_override_execution_and_audit():
    """Verify Admin can execute emergency override, modifying rules and recording audit record."""
    payload = {
        "override_type": "RECEIVING_HOURS_OVERRIDE",
        "target_entity_type": "Shelter",
        "target_entity_id": "shelter_eastside",
        "justification": "Hurricane disaster declaration: open shelter 24/7 for relief delivery",
        "authorized_by": "Director Maria Santos",
    }

    res = client.post(
        "/v1/emergency/override",
        json=payload,
        headers={"X-Actor-Role": "ADMIN", "X-Actor": "Director Maria Santos"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "EXECUTED"
    assert data["override_type"] == "RECEIVING_HOURS_OVERRIDE"
    assert data["applied_changes"]["receiving_hours"] == "0-24 (24/7 Emergency Access)"
    assert len(data["audit_record_id"]) > 0

    # Verify shelter receiving hours were updated
    shelter_res = client.get("/v1/shelters/shelter_eastside")
    assert shelter_res.status_code == 200
    assert shelter_res.json()["receiving_hours"]["open_hour"] == 0
    assert shelter_res.json()["receiving_hours"]["close_hour"] == 24

    # Verify audit trail recorded emergency override
    events_res = client.get("/v1/events")
    event_types = [e["event_type"] for e in events_res.json()]
    assert "EMERGENCY_OVERRIDE_EXECUTED" in event_types
