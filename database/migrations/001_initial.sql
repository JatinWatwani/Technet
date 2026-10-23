create extension if not exists pgcrypto;

create table public.batches (
  id text primary key,
  original_quantity integer not null check (original_quantity > 0),
  available_quantity integer not null check (available_quantity >= 0),
  safe_handling_minutes integer not null check (safe_handling_minutes > 0),
  safety_buffer_minutes integer not null default 0 check (safety_buffer_minutes >= 0),
  required_prerequisites text[] not null default '{}',
  created_at timestamptz not null default now(),
  check (available_quantity <= original_quantity)
);

create table public.riders (
  id text primary key,
  capacity integer not null check (capacity > 0),
  active_load integer not null default 0 check (active_load >= 0),
  available boolean not null default true
);

create table public.shelters (
  id text primary key,
  demand_remaining integer not null default 0 check (demand_remaining >= 0),
  receiving_capacity_remaining integer not null default 0 check (receiving_capacity_remaining >= 0),
  prerequisites text[] not null default '{}',
  open boolean not null default true
);

create table public.allocations (
  id uuid primary key default gen_random_uuid(),
  batch_id text not null references public.batches(id),
  rider_id text not null references public.riders(id),
  shelter_id text not null references public.shelters(id),
  quantity integer not null check (quantity > 0),
  travel_minutes integer not null check (travel_minutes >= 0),
  handoff_minutes integer not null check (handoff_minutes >= 0),
  state text not null check (state in ('CLAIMED', 'ACKNOWLEDGED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED')),
  claimed_at timestamptz not null,
  safe_until timestamptz not null
);

create index allocations_batch_idx on public.allocations(batch_id);
create index allocations_rider_idx on public.allocations(rider_id);
create index allocations_shelter_idx on public.allocations(shelter_id);

create or replace function public.dispatch_allocation(
  p_batch_id text,
  p_rider_id text,
  p_shelter_id text,
  p_quantity integer,
  p_travel_minutes integer,
  p_handoff_minutes integer,
  p_now timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  b public.batches%rowtype;
  r public.riders%rowtype;
  s public.shelters%rowtype;
  new_id uuid;
  safe_until timestamptz;
  estimated_completion timestamptz;
begin
  if p_quantity <= 0 then
    raise exception using message = 'Quantity must be positive', detail = 'INVALID_QUANTITY';
  end if;
  if p_travel_minutes < 0 or p_handoff_minutes < 0 then
    raise exception using message = 'Durations cannot be negative', detail = 'INVALID_DURATION';
  end if;

  select * into b from public.batches where id = p_batch_id for update;
  if not found then
    raise exception using message = 'The batch does not exist', detail = 'BATCH_NOT_FOUND';
  end if;

  select * into r from public.riders where id = p_rider_id for update;
  if not found then
    raise exception using message = 'The rider does not exist', detail = 'RIDER_NOT_FOUND';
  end if;

  select * into s from public.shelters where id = p_shelter_id for update;
  if not found then
    raise exception using message = 'The shelter does not exist', detail = 'SHELTER_NOT_FOUND';
  end if;

  if b.available_quantity < p_quantity then
    raise exception using message = 'The batch does not have enough available inventory', detail = 'INVENTORY_INSUFFICIENT';
  end if;
  if not r.available then
    raise exception using message = 'The rider is not available', detail = 'RIDER_UNAVAILABLE';
  end if;
  if r.capacity - r.active_load < p_quantity then
    raise exception using message = 'The assignment exceeds rider capacity', detail = 'RIDER_CAPACITY_EXCEEDED';
  end if;
  if not s.open then
    raise exception using message = 'The shelter is closed', detail = 'SHELTER_CLOSED';
  end if;
  if s.demand_remaining < p_quantity then
    raise exception using message = 'The assignment exceeds shelter demand', detail = 'SHELTER_DEMAND_EXCEEDED';
  end if;
  if s.receiving_capacity_remaining < p_quantity then
    raise exception using message = 'The assignment exceeds shelter capacity', detail = 'SHELTER_CAPACITY_EXCEEDED';
  end if;
  if not (b.required_prerequisites <@ s.prerequisites) then
    raise exception using message = 'The shelter is missing required prerequisites', detail = 'MISSING_PREREQUISITE';
  end if;

  safe_until := b.created_at + make_interval(mins => b.safe_handling_minutes);
  estimated_completion := p_now + make_interval(mins => p_travel_minutes + p_handoff_minutes + b.safety_buffer_minutes);
  if estimated_completion > safe_until then
    raise exception using message = 'The delivery cannot complete within the safe-handling deadline', detail = 'SAFETY_DEADLINE_UNSAFE';
  end if;

  update public.batches
  set available_quantity = available_quantity - p_quantity
  where id = b.id;

  update public.riders
  set active_load = active_load + p_quantity
  where id = r.id;

  update public.shelters
  set demand_remaining = demand_remaining - p_quantity,
      receiving_capacity_remaining = receiving_capacity_remaining - p_quantity
  where id = s.id;

  insert into public.allocations (
    batch_id, rider_id, shelter_id, quantity, travel_minutes,
    handoff_minutes, state, claimed_at, safe_until
  ) values (
    b.id, r.id, s.id, p_quantity, p_travel_minutes,
    p_handoff_minutes, 'CLAIMED', p_now, safe_until
  ) returning id into new_id;

  return jsonb_build_object(
    'id', new_id,
    'batch_id', b.id,
    'rider_id', r.id,
    'shelter_id', s.id,
    'quantity', p_quantity,
    'travel_minutes', p_travel_minutes,
    'handoff_minutes', p_handoff_minutes,
    'state', 'CLAIMED',
    'claimed_at', p_now,
    'safe_until', safe_until
  );
end;
$$;
