-- Vigilo Reproducible Seed Data
-- Matches Chaos Lab scenarios and hard constraints

-- Users
insert into public.users (id, name, email, role, created_at) values
  ('user_admin', 'Admin Coordinator', 'admin@vigilo.example', 'ADMIN', '2026-01-01T08:00:00Z'),
  ('user_donor_metro', 'Metro Food Bank', 'contact@metrofood.org', 'DONOR', '2026-01-01T08:00:00Z'),
  ('user_rider_alpha', 'Alex Rider', 'alex@riders.org', 'RIDER', '2026-01-01T08:00:00Z'),
  ('user_shelter_coord', 'Sam Coordinator', 'sam@shelters.org', 'SHELTER_COORDINATOR', '2026-01-01T08:00:00Z')
on conflict (id) do nothing;

-- Donors
insert into public.donors (id, user_id, organization_name, contact_phone, address, created_at) values
  ('donor_metro_food', 'user_donor_metro', 'Metro Food Relief', '+1-555-0199', '100 Logistics Way, Central', '2026-01-01T08:00:00Z'),
  ('donor_red_cross', null, 'International Relief Reserve', '+1-555-0188', '250 Aid Blvd, North', '2026-01-01T08:00:00Z')
on conflict (id) do nothing;

-- Batches
insert into public.batches (
  id, donor_id, item_type, original_quantity, available_quantity, reserved_quantity,
  picked_up_quantity, delivered_quantity, spoiled_quantity, safe_handling_minutes,
  safety_buffer_minutes, required_prerequisites, storage_requirement, created_at
) values
  ('batch_prepared_meals', 'donor_metro_food', 'prepared_hot_meals', 100, 100, 0, 0, 0, 0, 180, 15, '{}', 'AMBIENT', '2026-01-01T08:00:00Z'),
  ('batch_raw_rations', 'donor_metro_food', 'raw_ration_kits', 200, 200, 0, 0, 0, 0, 1440, 30, '{"clean_water", "cooking_fuel"}', 'AMBIENT', '2026-01-01T08:00:00Z'),
  ('batch_cold_meds', 'donor_red_cross', 'pediatric_antibiotics', 50, 50, 0, 0, 0, 0, 360, 30, '{"refrigeration"}', 'COLD', '2026-01-01T08:00:00Z'),
  ('batch_near_expiry', 'donor_metro_food', 'fresh_sandwiches', 40, 40, 0, 0, 0, 0, 40, 10, '{}', 'AMBIENT', '2026-01-01T08:00:00Z'),
  ('batch_oversized_180', 'donor_metro_food', 'prepared_hot_meals', 180, 180, 0, 0, 0, 0, 240, 20, '{}', 'AMBIENT', '2026-01-01T08:00:00Z')
on conflict (id) do nothing;

-- Riders
insert into public.riders (
  id, capacity, active_load, available, user_id, status, latitude, longitude, last_heartbeat_at
) values
  ('rider_alpha', 30, 0, true, 'user_rider_alpha', 'AVAILABLE', 40.7128, -74.0060, '2026-01-01T08:00:00Z'),
  ('rider_beta', 60, 0, true, null, 'AVAILABLE', 40.7200, -73.9950, '2026-01-01T08:00:00Z'),
  ('rider_gamma', 100, 0, true, null, 'AVAILABLE', 40.7300, -73.9850, '2026-01-01T08:00:00Z'),
  ('rider_offline', 50, 0, false, null, 'OFFLINE', 40.7000, -74.0100, null)
on conflict (id) do nothing;

-- Shelters
insert into public.shelters (
  id, name, demand_remaining, receiving_capacity_remaining, prerequisites, open,
  status, latitude, longitude, open_hour, close_hour
) values
  ('shelter_central', 'Downtown Central Emergency Shelter', 120, 120, '{"clean_water", "cooking_fuel", "refrigeration"}', true, 'OPEN', 40.7150, -74.0000, 6, 23),
  ('shelter_eastside', 'Eastside Community Center', 60, 60, '{"clean_water"}', true, 'OPEN', 40.7250, -73.9800, 8, 20),
  ('shelter_westside', 'Westside Relief Station', 40, 40, '{}', true, 'OPEN', 40.7350, -74.0150, 7, 22),
  ('shelter_closed', 'Flooded North Point Shelter', 50, 50, '{"clean_water"}', false, 'CLOSED', 40.7500, -73.9700, 9, 18)
on conflict (id) do nothing;
