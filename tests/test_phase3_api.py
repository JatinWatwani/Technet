from fastapi.testclient import TestClient
import pytest

from vigilo.main import app


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/v1/seed")
    return c


def test_api_generate_candidates(client):
    response = client.post("/v1/dispatch/candidates?batch_id=batch_oversized_180")
    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == "batch_oversized_180"
    assert data["feasible_count"] > 0
    assert data["split_plan"] is not None
    assert data["split_plan"]["is_fully_allocated"] is True
    assert len(data["split_plan"]["assignments"]) > 0

    # Top recommendation has ranking explanation
    top = data["feasible_candidates"][0]
    assert top["rank"] == 1
    assert "Top recommendation" in top["ranking_explanation"]


def test_api_generate_candidates_not_found(client):
    response = client.post("/v1/dispatch/candidates?batch_id=nonexistent_batch")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "BATCH_NOT_FOUND"


def test_api_safety_clock(client):
    response = client.get(
        "/v1/batches/batch_oversized_180/safety-clock",
        params={
            "shelter_id": "shelter_central",
            "travel_minutes": 25,
            "handoff_minutes": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == "batch_oversized_180"
    assert data["shelter_id"] == "shelter_central"
    assert data["is_feasible"] is True
    assert data["remaining_decision_window_minutes"] > 0
    assert "safe_deadline" in data
    assert "latest_useful_decision_time" in data


def test_api_safety_clock_not_found(client):
    response = client.get(
        "/v1/batches/nonexistent/safety-clock",
        params={"shelter_id": "shelter_central"},
    )
    assert response.status_code == 404


def test_api_safety_evaluate_feasible(client):
    response = client.post(
        "/v1/safety/evaluate",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 25,
            "travel_minutes": 20,
            "handoff_minutes": 10,
            "is_route_accessible": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["feasible"] is True
    assert data["primary_failure_code"] is None
    assert len(data["evaluated_rules"]) >= 10
    assert len(data["rule_results"]) >= 10


def test_api_safety_evaluate_infeasible_flooded_route(client):
    response = client.post(
        "/v1/safety/evaluate",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_gamma",
            "shelter_id": "shelter_central",
            "quantity": 25,
            "travel_minutes": 20,
            "handoff_minutes": 10,
            "is_route_accessible": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["feasible"] is False
    assert data["primary_failure_code"] == "ROUTE_INFEASIBLE"
    assert "blocked or rendered inaccessible" in data["primary_failure_reason"]


def test_api_safety_evaluate_infeasible_capacity_exceeded(client):
    # rider_alpha has capacity 20, asking for 50
    response = client.post(
        "/v1/safety/evaluate",
        json={
            "batch_id": "batch_prepared_meals",
            "rider_id": "rider_alpha",
            "shelter_id": "shelter_central",
            "quantity": 50,
            "travel_minutes": 20,
            "handoff_minutes": 10,
            "is_route_accessible": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["feasible"] is False
    assert data["primary_failure_code"] == "RIDER_CAPACITY_EXCEEDED"
