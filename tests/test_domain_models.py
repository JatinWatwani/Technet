from datetime import datetime, timedelta, timezone
import pytest

from vigilo.domain.models import (
    Batch,
    GeoLocation,
    ItemRules,
    ReceivingHours,
    Rider,
    RiderStatus,
    Shelter,
    ShelterStatus,
    StorageRequirement,
    User,
    UserRole,
)


def test_batch_quantity_conservation():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rules = ItemRules(safe_handling_minutes=120)

    # Valid: auto-initializes available_quantity = original_quantity
    b = Batch(id="b1", original_quantity=100, item_rules=rules, created_at=created_at)
    assert b.available_quantity == 100
    assert b.reserved_quantity == 0
    assert b.picked_up_quantity == 0

    # Valid manual breakdown
    b2 = Batch(
        id="b2",
        original_quantity=100,
        available_quantity=40,
        reserved_quantity=20,
        picked_up_quantity=30,
        delivered_quantity=10,
        spoiled_quantity=0,
        item_rules=rules,
        created_at=created_at,
    )
    assert sum([b2.available_quantity, b2.reserved_quantity, b2.picked_up_quantity, b2.delivered_quantity]) == 100

    # Invariant violation: sum != original_quantity
    with pytest.raises(ValueError, match="Quantity conservation violated"):
        Batch(
            id="b3",
            original_quantity=100,
            available_quantity=90,
            reserved_quantity=20,  # 90 + 20 = 110 != 100
            item_rules=rules,
            created_at=created_at,
        )

    # Negative quantity disallowed
    with pytest.raises(ValueError, match="Quantities cannot be negative"):
        Batch(
            id="b4",
            original_quantity=100,
            available_quantity=110,
            reserved_quantity=-10,
            item_rules=rules,
            created_at=created_at,
        )


def test_rider_capacity_invariants():
    r = Rider(id="r1", capacity=50, active_load=20)
    assert r.remaining_capacity == 30

    with pytest.raises(ValueError, match="capacity must be positive"):
        Rider(id="r2", capacity=0)

    with pytest.raises(ValueError, match="active_load cannot be negative"):
        Rider(id="r3", capacity=50, active_load=-5)

    with pytest.raises(ValueError, match="active_load cannot exceed total capacity"):
        Rider(id="r4", capacity=50, active_load=51)


def test_shelter_receiving_hours_and_invariants():
    hours = ReceivingHours(open_hour=8, close_hour=20)
    assert hours.is_within(8)
    assert hours.is_within(12)
    assert hours.is_within(19)
    assert not hours.is_within(20)
    assert not hours.is_within(7)

    # Overnight receiving
    night_hours = ReceivingHours(open_hour=22, close_hour=6)
    assert night_hours.is_within(23)
    assert night_hours.is_within(2)
    assert not night_hours.is_within(12)

    s = Shelter(
        id="s1",
        name="Main",
        demand_remaining=50,
        receiving_capacity_remaining=50,
        prerequisites=frozenset({"clean_water"}),
        open=False,
    )
    assert s.status == ShelterStatus.CLOSED

    with pytest.raises(ValueError, match="demand_remaining cannot be negative"):
        Shelter(id="s2", demand_remaining=-1, receiving_capacity_remaining=10)


def test_item_rules_safe_until():
    created = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    rules = ItemRules(safe_handling_minutes=90, safety_buffer_minutes=15)
    assert rules.safe_until(created) == created + timedelta(minutes=90)
