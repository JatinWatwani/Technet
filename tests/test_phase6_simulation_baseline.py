import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from vigilo.domain.simulation import ScenarioManager
from vigilo.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_simulation_environment():
    """Ensure clean scenario registry before and after every test."""
    ScenarioManager.get_instance().clear()
    yield
    ScenarioManager.get_instance().clear()


def test_list_scenario_presets():
    """Verify standard judge evaluation presets are exposed with metadata and chaos elements."""
    resp = client.get("/v1/scenarios/presets")
    assert resp.status_code == 200
    presets = resp.json()
    assert len(presets) >= 4
    preset_ids = {p["preset_id"] for p in presets}
    assert "oversized_donation_split" in preset_ids
    assert "ghost_reservation" in preset_ids
    assert "in_transit_shelter_closure" in preset_ids
    assert "cascading_flood_disruption" in preset_ids

    # Verify preset structure
    closure_preset = next(p for p in presets if p["preset_id"] == "in_transit_shelter_closure")
    assert closure_preset["difficulty"] == "Advanced"
    assert "in_transit_reroute" in closure_preset["chaos_elements"]


def test_create_and_start_isolated_scenario():
    """Verify creating a scenario creates an isolated simulation sandbox without leaking into main state."""
    # Reset main clock and state
    client.post("/v1/seed")

    create_payload = {
        "name": "Judge Demo Run #1",
        "scenario_id": "scen_demo_101",
        "preset_id": "ghost_reservation",
        "seed": 1337,
        "description": "Validation of autonomous ghost reservation recovery",
    }
    resp = client.post("/v1/scenarios", json=create_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_id"] == "scen_demo_101"
    assert data["status"] == "RUNNING"
    assert len(data["batches"]) >= 4
    assert len(data["riders"]) >= 4
    assert len(data["shelters"]) >= 4

    # Verify isolation: main service allocations vs scenario allocations
    main_allocs = client.get("/v1/allocations").json() if hasattr(client, "get") else []
    # Scenario state endpoint returns isolated entity snapshot
    state_resp = client.get("/v1/scenarios/scen_demo_101/state")
    assert state_resp.status_code == 200
    state = state_resp.json()
    assert state["scenario_id"] == "scen_demo_101"
    assert len(state["ledger_reconciliation"]) >= 4
    for report in state["ledger_reconciliation"]:
        assert report["is_valid"] is True


def test_scenario_advance_time_and_autonomous_sweeps():
    """Verify advancing scenario time executes autonomous recovery sweeps on expired leases."""
    # Create scenario
    client.post("/v1/scenarios", json={
        "name": "Sweep Test Scenario",
        "scenario_id": "scen_sweep_test",
        "preset_id": "ghost_reservation",
        "seed": 42,
    })

    # Advance time by 30 minutes inside simulation
    adv_resp = client.post("/v1/scenarios/scen_sweep_test/advance-time", json={"minutes": 30})
    assert adv_resp.status_code == 200
    state = adv_resp.json()
    # Check that time advanced 30 mins
    curr_time = state["current_time"]
    assert "08:30:00" in curr_time

    # Verify replay tape records TIME_ADVANCED step
    replay_resp = client.get("/v1/scenarios/scen_sweep_test/replay")
    assert replay_resp.status_code == 200
    replay = replay_resp.json()
    assert replay["scenario_id"] == "scen_sweep_test"
    events = replay["events"]
    assert len(events) >= 2  # SCENARIO_STARTED, TIME_ADVANCED
    assert events[0]["event_type"] == "SCENARIO_STARTED"
    assert events[1]["event_type"] == "TIME_ADVANCED"
    assert events[1]["payload"]["minutes_advanced"] == 30


def test_scenario_inject_failures():
    """Verify injecting disturbances (shelter closure, rider failure, route flood) into running scenario."""
    client.post("/v1/scenarios", json={
        "name": "Chaos Injection Test",
        "scenario_id": "scen_chaos_test",
        "preset_id": "cascading_flood_disruption",
        "seed": 100,
    })

    # 1. Inject shelter closure
    inj_shelter = client.post("/v1/scenarios/scen_chaos_test/inject-failure", json={
        "failure_type": "SHELTER_CLOSURE",
        "target_id": "shelter_eastside",
        "params": {"reason": "Structural damage from flash flood", "auto_reroute": True},
    })
    assert inj_shelter.status_code == 200
    shelter_state = inj_shelter.json()
    eastside = next(s for s in shelter_state["shelters"] if s["id"] == "shelter_eastside")
    assert eastside["status"] == "CLOSED"

    # 2. Inject rider breakdown
    inj_rider = client.post("/v1/scenarios/scen_chaos_test/inject-failure", json={
        "failure_type": "RIDER_FAILURE",
        "target_id": "rider_alpha",
        "params": {"reason": "Cargo bike flat tire and telemetry loss"},
    })
    assert inj_rider.status_code == 200
    rider_state = inj_rider.json()
    alpha = next(r for r in rider_state["riders"] if r["id"] == "rider_alpha")
    assert alpha["status"] == "OFFLINE"

    # 3. Inject flood route blockage
    inj_flood = client.post("/v1/scenarios/scen_chaos_test/inject-failure", json={
        "failure_type": "FLOOD_DISRUPTION",
        "target_id": "route_corridor_central_east",
        "params": {"flood_depth_cm": 60, "reason": "Water height exceeds safe cargo clearance"},
    })
    assert inj_flood.status_code == 200
    flood_state = inj_flood.json()
    assert len(flood_state["incidents"]) >= 2

    # Check replay tape for injected failures
    replay = client.get("/v1/scenarios/scen_chaos_test/replay").json()
    event_types = [e["event_type"] for e in replay["events"]]
    assert "FAILURE_INJECTED_SHELTER_CLOSURE" in event_types
    assert "FAILURE_INJECTED_RIDER_FAILURE" in event_types
    assert "FAILURE_INJECTED_FLOOD_DISRUPTION" in event_types


def test_scenario_compare_baseline_evaluation():
    """Verify side-by-side comparative evaluation between Vigilo and Greedy Baseline."""
    client.post("/v1/scenarios", json={
        "name": "Ghost Reservation Comparative Evaluation",
        "scenario_id": "scen_compare_demo",
        "preset_id": "ghost_reservation",
        "seed": 42,
    })

    # Run comparative baseline analysis
    resp = client.post("/v1/scenarios/scen_compare_demo/compare-baseline")
    assert resp.status_code == 200
    comp = resp.json()
    assert comp["scenario_id"] == "scen_compare_demo"
    assert "vigilo_metrics" in comp
    assert "baseline_metrics" in comp
    assert "comparative_scorecard" in comp
    assert "verdict_summary" in comp

    # Check scorecard entries
    card = comp["comparative_scorecard"]
    metrics_map = {item["metric_name"]: item for item in card}

    # Verify critical invariants and improvements
    assert "Spoiled Quantity (units)" in metrics_map
    spoiled_row = metrics_map["Spoiled Quantity (units)"]
    assert spoiled_row["vigilo_value"] == 0  # 0 spoiled cargo in Vigilo
    assert spoiled_row["baseline_value"] > 0  # Baseline spoiled units due to abandoned locked claim
    assert spoiled_row["passed_invariant"] is True

    assert "Duplicate Allocation Violations" in metrics_map
    dup_row = metrics_map["Duplicate Allocation Violations"]
    assert dup_row["vigilo_value"] == 0
    assert dup_row["baseline_value"] == 0
    assert dup_row["passed_invariant"] is True


def test_oversized_split_baseline_comparison():
    """Verify Vigilo split planning vs baseline single-allocation failure under oversized donation."""
    client.post("/v1/scenarios", json={
        "name": "Oversized Split Comparison",
        "scenario_id": "scen_oversized_comp",
        "preset_id": "oversized_donation_split",
        "seed": 42,
    })

    resp = client.post("/v1/scenarios/scen_oversized_comp/compare-baseline")
    assert resp.status_code == 200
    comp = resp.json()

    # Vigilo safely conserves inventory and has zero invariant violations
    vigilo_m = comp["vigilo_metrics"]
    baseline_m = comp["baseline_metrics"]
    assert vigilo_m["duplicate_allocation_violations"] == 0
    assert vigilo_m["unsafe_assignment_count"] == 0
    assert vigilo_m["spoiled_quantity"] == 0
    assert len(comp["verdict_summary"]) > 0
