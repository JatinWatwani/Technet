from oopsloop.domain.seed import create_seed_data, get_default_seed_timestamp


def test_seed_data_reproducibility():
    t = get_default_seed_timestamp()
    seed1 = create_seed_data(t)
    seed2 = create_seed_data(t)

    assert len(seed1["users"]) == len(seed2["users"])
    assert len(seed1["donors"]) == len(seed2["donors"])
    assert len(seed1["batches"]) == len(seed2["batches"])
    assert len(seed1["riders"]) == len(seed2["riders"])
    assert len(seed1["shelters"]) == len(seed2["shelters"])


def test_seed_entities_adhere_to_invariants():
    seed = create_seed_data()
    # All batches have quantity conservation
    for b in seed["batches"]:
        b.validate_invariants()
        assert b.available_quantity == b.original_quantity

    # Riders capacity valid
    for r in seed["riders"]:
        assert r.capacity > 0
        assert r.active_load == 0
        assert r.remaining_capacity == r.capacity

    # Shelters have positive or zero demand
    for s in seed["shelters"]:
        assert s.demand_remaining >= 0
        assert s.receiving_capacity_remaining >= 0


def test_chaos_lab_scenarios_represented_in_seeds():
    seed = create_seed_data()
    batch_ids = {b.id for b in seed["batches"]}
    rider_ids = {r.id for r in seed["riders"]}
    shelter_ids = {s.id for s in seed["shelters"]}

    # Scenario A: Oversized 180 batch
    assert "batch_oversized_180" in batch_ids
    # Scenario E: Missing prerequisites batch
    assert "batch_raw_rations" in batch_ids
    # Scenario D: Short safe-handling deadline
    assert "batch_near_expiry" in batch_ids

    # Shelters: full prerequisite, partial, closed
    assert "shelter_central" in shelter_ids
    assert "shelter_eastside" in shelter_ids
    assert "shelter_closed" in shelter_ids

    # Riders with distinct capacities
    assert "rider_alpha" in rider_ids
    assert "rider_beta" in rider_ids
    assert "rider_gamma" in rider_ids
