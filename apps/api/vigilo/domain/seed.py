from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    Batch,
    Donor,
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


def get_default_seed_timestamp() -> datetime:
    return datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


def create_seed_data(base_time: datetime | None = None) -> dict[str, list[object]]:
    """Generate deterministic, reproducible operational seed data matching Chaos Lab requirements."""
    now = base_time or get_default_seed_timestamp()

    # 1. Users
    users = [
        User(id="user_admin", name="Admin Coordinator", email="admin@vigilo.org", role=UserRole.ADMIN, created_at=now),
        User(id="user_donor_metro", name="Metro Food Bank", email="contact@metrofood.org", role=UserRole.DONOR, created_at=now),
        User(id="user_rider_alpha", name="Alex Rider", email="alex@riders.org", role=UserRole.RIDER, created_at=now),
        User(id="user_shelter_coord", name="Sam Coordinator", email="sam@shelters.org", role=UserRole.SHELTER_COORDINATOR, created_at=now),
    ]

    # 2. Donors
    donors = [
        Donor(
            id="donor_metro_food",
            user_id="user_donor_metro",
            organization_name="Metro Food Relief",
            contact_phone="+1-555-0199",
            address="100 Logistics Way, Central",
            created_at=now,
        ),
        Donor(
            id="donor_red_cross",
            organization_name="International Relief Reserve",
            contact_phone="+1-555-0188",
            address="250 Aid Blvd, North",
            created_at=now,
        ),
    ]

    # 3. Batches with distinct handling profiles and prerequisites
    batches = [
        # Standard perishable meals (180 mins safe handling, 15 min buffer)
        Batch(
            id="batch_prepared_meals",
            donor_id="donor_metro_food",
            item_type="prepared_hot_meals",
            original_quantity=100,
            available_quantity=100,
            created_at=now,
            item_rules=ItemRules(
                safe_handling_minutes=180,
                safety_buffer_minutes=15,
                required_prerequisites=frozenset(),
                storage_requirement=StorageRequirement.AMBIENT,
            ),
        ),
        # Raw ration kits (requires clean water and cooking fuel at receiving shelter)
        Batch(
            id="batch_raw_rations",
            donor_id="donor_metro_food",
            item_type="raw_ration_kits",
            original_quantity=200,
            available_quantity=200,
            created_at=now,
            item_rules=ItemRules(
                safe_handling_minutes=1440,
                safety_buffer_minutes=30,
                required_prerequisites=frozenset({"clean_water", "cooking_fuel"}),
                storage_requirement=StorageRequirement.AMBIENT,
            ),
        ),
        # Temperature-sensitive supplies (cold-chain requirements)
        Batch(
            id="batch_cold_meds",
            donor_id="donor_red_cross",
            item_type="pediatric_antibiotics",
            original_quantity=50,
            available_quantity=50,
            created_at=now,
            item_rules=ItemRules(
                safe_handling_minutes=360,
                safety_buffer_minutes=30,
                required_prerequisites=frozenset({"refrigeration"}),
                storage_requirement=StorageRequirement.COLD,
            ),
        ),
        # Near-expiry scenario batch (40 min deadline, 10 min buffer)
        Batch(
            id="batch_near_expiry",
            donor_id="donor_metro_food",
            item_type="fresh_sandwiches",
            original_quantity=40,
            available_quantity=40,
            created_at=now,
            item_rules=ItemRules(
                safe_handling_minutes=40,
                safety_buffer_minutes=10,
                required_prerequisites=frozenset(),
                storage_requirement=StorageRequirement.AMBIENT,
            ),
        ),
        # Oversized batch for Scenario A (180 meals to split across riders)
        Batch(
            id="batch_oversized_180",
            donor_id="donor_metro_food",
            item_type="prepared_hot_meals",
            original_quantity=180,
            available_quantity=180,
            created_at=now,
            item_rules=ItemRules(
                safe_handling_minutes=240,
                safety_buffer_minutes=20,
                required_prerequisites=frozenset(),
                storage_requirement=StorageRequirement.AMBIENT,
            ),
        ),
    ]

    # 4. Volunteer Riders with varied capacity and locations
    riders = [
        Rider(
            id="rider_alpha",
            capacity=30,
            active_load=0,
            available=True,
            status=RiderStatus.AVAILABLE,
            location=GeoLocation(latitude=40.7128, longitude=-74.0060),
            last_heartbeat_at=now,
        ),
        Rider(
            id="rider_beta",
            capacity=60,
            active_load=0,
            available=True,
            status=RiderStatus.AVAILABLE,
            location=GeoLocation(latitude=40.7200, longitude=-73.9950),
            last_heartbeat_at=now,
        ),
        Rider(
            id="rider_gamma",
            capacity=100,
            active_load=0,
            available=True,
            status=RiderStatus.AVAILABLE,
            location=GeoLocation(latitude=40.7300, longitude=-73.9850),
            last_heartbeat_at=now,
        ),
        Rider(
            id="rider_offline",
            capacity=50,
            active_load=0,
            available=False,
            status=RiderStatus.OFFLINE,
            location=GeoLocation(latitude=40.7000, longitude=-74.0100),
            last_heartbeat_at=None,
        ),
    ]

    # 5. Receiving Shelters with varying capacity, prerequisites, and hours
    shelters = [
        Shelter(
            id="shelter_central",
            name="Downtown Central Emergency Shelter",
            demand_remaining=120,
            receiving_capacity_remaining=120,
            prerequisites=frozenset({"clean_water", "cooking_fuel", "refrigeration"}),
            open=True,
            status=ShelterStatus.OPEN,
            location=GeoLocation(latitude=40.7150, longitude=-74.0000),
            receiving_hours=ReceivingHours(open_hour=6, close_hour=23),
        ),
        Shelter(
            id="shelter_eastside",
            name="Eastside Community Center",
            demand_remaining=60,
            receiving_capacity_remaining=60,
            prerequisites=frozenset({"clean_water"}),  # Missing cooking_fuel & refrigeration
            open=True,
            status=ShelterStatus.OPEN,
            location=GeoLocation(latitude=40.7250, longitude=-73.9800),
            receiving_hours=ReceivingHours(open_hour=8, close_hour=20),
        ),
        Shelter(
            id="shelter_westside",
            name="Westside Relief Station",
            demand_remaining=40,
            receiving_capacity_remaining=40,
            prerequisites=frozenset(),
            open=True,
            status=ShelterStatus.OPEN,
            location=GeoLocation(latitude=40.7350, longitude=-74.0150),
            receiving_hours=ReceivingHours(open_hour=7, close_hour=22),
        ),
        Shelter(
            id="shelter_closed",
            name="Flooded North Point Shelter",
            demand_remaining=50,
            receiving_capacity_remaining=50,
            prerequisites=frozenset({"clean_water"}),
            open=False,
            status=ShelterStatus.CLOSED,
            location=GeoLocation(latitude=40.7500, longitude=-73.9700),
            receiving_hours=ReceivingHours(open_hour=9, close_hour=18),
        ),
    ]

    return {
        "users": users,
        "donors": donors,
        "batches": batches,
        "riders": riders,
        "shelters": shelters,
    }
