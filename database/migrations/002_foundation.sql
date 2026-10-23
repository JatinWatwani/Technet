-- Vigilo Phase 1 Database Migration: Foundation Schema
-- Users, Donors, Deliveries, Incidents, Operational Events, Audit Records, and Schema Enhancements

-- 1. Users table
create table if not exists public.users (
  id text primary key,
  name text not null,
  email text not null unique,
  role text not null check (role in ('ADMIN', 'DONOR', 'RIDER', 'SHELTER_COORDINATOR', 'EMERGENCY_COORDINATOR')),
  created_at timestamptz not null default now()
);

-- 2. Donors table
create table if not exists public.donors (
  id text primary key,
  user_id text references public.users(id) on delete set null,
  organization_name text not null,
  contact_phone text not null default '',
  address text not null default '',
  created_at timestamptz not null default now()
);

-- 3. Enhance batches with donor relation, item types, and quantity breakdown
alter table public.batches
  add column if not exists donor_id text references public.donors(id) on delete set null,
  add column if not exists item_type text not null default 'prepared_meals',
  add column if not exists reserved_quantity integer not null default 0 check (reserved_quantity >= 0),
  add column if not exists picked_up_quantity integer not null default 0 check (picked_up_quantity >= 0),
  add column if not exists delivered_quantity integer not null default 0 check (delivered_quantity >= 0),
  add column if not exists spoiled_quantity integer not null default 0 check (spoiled_quantity >= 0),
  add column if not exists storage_requirement text not null default 'AMBIENT' check (storage_requirement in ('AMBIENT', 'COLD', 'FROZEN'));

-- 4. Enhance riders with status and geolocation
alter table public.riders
  add column if not exists user_id text references public.users(id) on delete set null,
  add column if not exists status text not null default 'AVAILABLE' check (status in ('AVAILABLE', 'ASSIGNED', 'IN_TRANSIT', 'PAUSED', 'OFFLINE')),
  add column if not exists latitude double precision check (latitude between -90 and 90),
  add column if not exists longitude double precision check (longitude between -180 and 180),
  add column if not exists last_heartbeat_at timestamptz;

-- 5. Enhance shelters with name, status, receiving hours, and geolocation
alter table public.shelters
  add column if not exists name text not null default '',
  add column if not exists status text not null default 'OPEN' check (status in ('OPEN', 'AT_CAPACITY', 'CLOSED', 'REOPENING_REVIEW')),
  add column if not exists latitude double precision check (latitude between -90 and 90),
  add column if not exists longitude double precision check (longitude between -180 and 180),
  add column if not exists open_hour integer not null default 0 check (open_hour between 0 and 24),
  add column if not exists close_hour integer not null default 24 check (close_hour between 0 and 24);

-- 6. Enhance allocations with lease deadlines and lifecycle timestamps
alter table public.allocations
  add column if not exists lease_expires_at timestamptz,
  add column if not exists acknowledged_at timestamptz,
  add column if not exists picked_up_at timestamptz;

-- 7. Deliveries table for physical custody
create table if not exists public.deliveries (
  id text primary key,
  allocation_id uuid not null references public.allocations(id) on delete cascade,
  batch_id text not null references public.batches(id),
  rider_id text not null references public.riders(id),
  current_shelter_id text not null references public.shelters(id),
  quantity integer not null check (quantity > 0),
  state text not null check (state in ('PICKED_UP', 'IN_TRANSIT', 'REROUTE_PENDING', 'DELIVERED', 'INCIDENT_REVIEW')),
  picked_up_at timestamptz not null,
  delivered_at timestamptz,
  latitude double precision check (latitude between -90 and 90),
  longitude double precision check (longitude between -180 and 180),
  destination_history text[] not null default '{}'
);

create index if not exists deliveries_rider_idx on public.deliveries(rider_id);
create index if not exists deliveries_shelter_idx on public.deliveries(current_shelter_id);
create index if not exists deliveries_state_idx on public.deliveries(state);

-- 8. Incidents table
create table if not exists public.incidents (
  id text primary key,
  severity text not null check (severity in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  status text not null check (status in ('OPEN', 'INVESTIGATING', 'ESCALATED', 'RESOLVED')),
  affected_entity_type text not null,
  affected_entity_id text not null,
  reason_code text not null,
  description text not null,
  evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create index if not exists incidents_status_idx on public.incidents(status);
create index if not exists incidents_entity_idx on public.incidents(affected_entity_type, affected_entity_id);

-- 9. Operational Events table (Append-only)
create table if not exists public.operational_events (
  id text primary key,
  event_type text not null,
  aggregate_id text not null,
  aggregate_type text not null,
  occurred_at timestamptz not null default now(),
  payload jsonb not null default '{}'::jsonb,
  actor text not null default 'system',
  correlation_id text not null,
  evidence jsonb not null default '{}'::jsonb
);

create index if not exists events_aggregate_idx on public.operational_events(aggregate_type, aggregate_id);
create index if not exists events_occurred_at_idx on public.operational_events(occurred_at);

-- 10. Audit Records table
create table if not exists public.audit_records (
  id text primary key,
  event_id text not null,
  actor text not null,
  command text not null,
  decision text not null,
  constraints_evaluated text[] not null default '{}',
  evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists audit_created_at_idx on public.audit_records(created_at);
