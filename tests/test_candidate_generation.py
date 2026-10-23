from datetime import datetime, timezone
import pytest

from vigilo.domain.candidate_engine import CandidateEngine
from vigilo.domain.dispatch import DispatchService
from vigilo.domain.models import (
    Batch,
    ItemRules,
    ReceivingHours,
    Rider,
    RiderStatus,
    Shelter,
    ShelterStatus,
)

NOW = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def scenario_a_environment():
    # Scenario A: 180 hot meals needing multi-rider split
    batch = Batch(
        id="batch_oversized_180",
        original_quantity=180,
        item_rules=ItemRules(safe_handling_minutes=180, safety_buffer_minutes=15),
        created_at=NOW,
    )

    riders = [
        Rider(id="rider_alpha", capacity=20, available=True, status=RiderStatus.AVAILABLE, last_heartbeat_at=NOW),
        Rider(id="rider_beta", capacity=60, available=True, status=RiderStatus.AVAILABLE, last_heartbeat_at=NOW),
        Rider(id="rider_gamma", capacity=100, available=True, status=RiderStatus.AVAILABLE, last_heartbeat_at=NOW),
        Rider(id="rider_offline", capacity=50, available=False, status=RiderStatus.OFFLINE, last_heartbeat_at=NOW),
    ]

    shelters = [
        Shelter(
            id="shelter_central",
            demand_remaining=120,
            receiving_capacity_remaining=120,
            open=True,
            status=ShelterStatus.OPEN,
            receiving_hours=ReceivingHours(open_hour=8, close_hour=20),
        ),
        Shelter(
            id="shelter_east",
            demand_remaining=80,
            receiving_capacity_remaining=80,
            open=True,
            status=ShelterStatus.OPEN,
            receiving_hours=ReceivingHours(open_hour=8, close_hour=20),
        ),
    ]

    return batch, riders, shelters


def test_candidate_generation_and_ranking(scenario_a_environment):
    batch, riders, shelters = scenario_a_environment

    result = CandidateEngine.generate_and_rank_candidates(
        batch=batch,
        riders=riders,
        shelters=shelters,
        now=NOW,
        default_travel_minutes=20,
        default_handoff_minutes=10,
    )

    # Offline rider should be rejected
    offline_candidates = [c for c in result.rejected_candidates if c.rider_id == "rider_offline"]
    assert len(offline_candidates) > 0

    # Feasible candidates should be ranked
    assert len(result.feasible_candidates) > 0
    top_candidate = result.feasible_candidates[0]
    assert top_candidate.rank == 1
    assert "Top recommendation" in top_candidate.ranking_explanation
    assert top_candidate.score >= result.feasible_candidates[-1].score


def test_scenario_a_multi_rider_batch_split(scenario_a_environment):
    batch, riders, shelters = scenario_a_environment

    result = CandidateEngine.generate_and_rank_candidates(
        batch=batch,
        riders=riders,
        shelters=shelters,
        now=NOW,
        default_travel_minutes=25,
        default_handoff_minutes=10,
    )

    assert result.split_plan is not None
    plan = result.split_plan
    assert plan.total_batch_quantity == 180
    assert plan.allocated_quantity == 180
    assert plan.remaining_unallocated == 0
    assert plan.is_fully_allocated is True

    # Check that riders are allocated greedily by capacity: gamma (100), beta (60), alpha (20)
    allocations = {a.rider_id: a.quantity for a in plan.assignments}
    assert allocations.get("rider_gamma") == 100
    assert allocations.get("rider_beta") == 60
    assert allocations.get("rider_alpha") == 20
    assert "rider_offline" not in allocations


def test_candidate_generation_via_dispatch_service():
    service = DispatchService()
    service.load_seed()

    result = service.generate_candidates("batch_oversized_180")
    assert result.batch_id == "batch_oversized_180"
    assert len(result.feasible_candidates) > 0
    assert result.split_plan is not None
    assert result.split_plan.is_fully_allocated is True
